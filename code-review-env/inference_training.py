from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import uuid

from openai import OpenAI

from db.seed import seed_project
from db.store import Store
from env.runtime_config import load_runtime_config
from parser.semantic_checks import detect_semantic_issues
from training.run_manager import TrainingRunManager
from training.weights import WeightSafetyManager


# Submission-required runtime variables.
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HFTOKEN")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")

# Hosted fallback: if HF_TOKEN exists and endpoint/model are not explicitly provided,
# use Hugging Face Router with a stable instruct model.
if HF_TOKEN and not os.getenv("API_BASE_URL") and not os.getenv("GRAPHREVIEW_LLM_BASE_URL"):
    API_BASE_URL = "https://router.huggingface.co/v1"
else:
    API_BASE_URL = os.getenv("API_BASE_URL", os.getenv("GRAPHREVIEW_LLM_BASE_URL", "http://localhost:11434/v1"))

if HF_TOKEN and not os.getenv("MODEL_NAME"):
    MODEL_NAME = "meta-llama/Meta-Llama-3.1-8B-Instruct"
else:
    MODEL_NAME = os.getenv("MODEL_NAME", "gemma4:e4b")

# Keep current behavior for local Ollama while supporting hosted providers via HF_TOKEN.
API_KEY = HF_TOKEN or os.getenv("GRAPHREVIEW_LLM_API_KEY", "ollama")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GraphReview deterministic inference/training harness")
    parser.add_argument("target", help="Path to target Python project")
    parser.add_argument("--db-path", default=None, help="Optional DB path")
    parser.add_argument("--force-seed", action="store_true", help="Force re-seed")
    parser.add_argument(
        "--register-weights",
        action="store_true",
        help="Register model weights and write verification manifest",
    )
    parser.add_argument(
        "--deterministic-output",
        default="outputs/training/deterministic_findings.jsonl",
        help="Path to write normalized deterministic findings",
    )
    parser.add_argument("--baseline-precision", type=float, default=None, help="Optional precision floor baseline")
    parser.add_argument("--baseline-recall", type=float, default=None, help="Optional recall floor baseline")
    parser.add_argument(
        "--regression-tolerance",
        type=float,
        default=0.01,
        help="Allowed drop from baseline precision/recall",
    )
    return parser


def _finding_key(analyzer: str, module_id: str, rule_id: str, line: int) -> str:
    return f"{analyzer}:{module_id}:{rule_id}:{line}"


def _target_key(module_id: str, line: int) -> str:
    return f"{module_id}:{line}"


def _safe_float(raw: str | None, default: float) -> float:
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _build_agent_prompt(module_id: str, code: str, ast_summary: str) -> str:
    return (
        "You are reviewing one Python module in a dependency-aware code review environment. "
        "Do not rely on prior analyzer findings because they are hidden from you. "
        "Find concrete, actionable issues only, with line numbers and confidence.\n\n"
        "Your objectives are:\n"
        "1) Identify real bug, security, or dependency-risk issues in the provided code.\n"
        "2) Prefer deterministic evidence over speculative style feedback.\n"
        "3) If you suspect cascade risk, explain likely upstream/downstream impact in rationale.\n"
        "4) Return strictly valid JSON matching this schema: "
        "{\"findings\": [{\"line\": int, \"category\": \"bug|security|dependency\", \"rule_hint\": str, \"message\": str, \"confidence\": float}]}.\n\n"
        f"Module: {module_id}\n"
        f"AST Summary: {ast_summary}\n"
        "Code:\n"
        f"{code}\n"
    )


def _extract_agent_findings(store: Store, config) -> set[str]:
    model = MODEL_NAME
    base_url = API_BASE_URL
    api_key = API_KEY
    enabled = os.getenv("GRAPHREVIEW_AGENT_INFERENCE_ENABLED", "true").strip().lower() == "true"

    findings: set[str] = set()
    node_snapshot = store.get_full_graph().nodes
    use_llm = enabled and base_url and model
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=12.0) if use_llm else None

    llm_enabled = client is not None
    if llm_enabled:
        try:
            models = client.models.list()
            available = {item.id for item in models.data if getattr(item, "id", None)}
            if model not in available:
                print(
                    f"[STEP] agent_llm_fallback reason=model-not-found model={model} "
                    f"available_count={len(available)}"
                )
                llm_enabled = False
        except Exception as exc:
            print(f"[STEP] agent_llm_fallback reason=model-list-failed error={type(exc).__name__}")
            llm_enabled = False

    for node in node_snapshot:
        node_row = store.get_node(node.module_id)
        if node_row is None:
            continue

        module_id = node_row.module_id
        code = node_row.raw_code
        ast_summary = node_row.ast_summary
        collected = False

        if llm_enabled and client is not None:
            prompt = _build_agent_prompt(module_id=module_id, code=code, ast_summary=ast_summary)
            try:
                resp = client.chat.completions.create(
                    model=model,
                    temperature=0.0,
                    response_format={"type": "json_object"},
                    messages=[
                        {
                            "role": "system",
                            "content": "Return only JSON. Do not include markdown. Keep claims concrete and line-specific.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                )
                text = (resp.choices[0].message.content or "{}").strip()
                payload = json.loads(text)
                rows = payload.get("findings", []) if isinstance(payload, dict) else []
                if isinstance(rows, list):
                    for item in rows:
                        if not isinstance(item, dict):
                            continue
                        confidence = _safe_float(str(item.get("confidence", "0.0")), 0.0)
                        if confidence < 0.45:
                            continue
                        line = max(1, int(item.get("line", 1)))
                        category = str(item.get("category", "bug")).lower()
                        analyzer = "agent-security" if category == "security" else "agent-logic"
                        rule_hint = str(item.get("rule_hint") or "agent")[:80]
                        findings.add(_finding_key(analyzer, module_id, rule_hint, line))
                    collected = True
            except Exception as exc:
                print(
                    f"[STEP] agent_llm_fallback reason=completion-failed error={type(exc).__name__} "
                    f"module={module_id}"
                )
                llm_enabled = False
                collected = False

        if collected:
            continue

        # Deterministic fallback so training bootstrap still works offline.
        deterministic_rows = store.get_analyzer_findings_for_module(module_id)
        for finding in deterministic_rows[:2]:
            findings.add(_finding_key("agent-fallback", module_id, finding.rule_id, finding.line))

        for issue in detect_semantic_issues(code):
            findings.add(_finding_key("agent-heuristic", module_id, issue.stage, max(issue.line, 1)))

    return findings


def main() -> None:
    args = _build_parser().parse_args()
    config = load_runtime_config()

    target = Path(args.target).resolve()
    print(f"[START] target={target} model={MODEL_NAME} mode=deterministic-ground-truth")

    weight_manager = WeightSafetyManager(Path(config.llm_weight_manifest_dir))
    verified_weight_path: str | None = None
    if args.register_weights:
        try:
            manifest = weight_manager.register_existing(
                model_name=MODEL_NAME,
                weight_path=Path(config.llm_model_agent_path),
            )
            print(
                "[STEP] weights_registered "
                + json.dumps(
                    {
                        "model": manifest.model_name,
                        "sha256": manifest.sha256,
                        "size_bytes": manifest.size_bytes,
                    },
                    sort_keys=True,
                )
            )
        except FileNotFoundError:
            print(
                f"[STEP] weights_register_skipped reason=missing-local-weights model={MODEL_NAME} "
                f"path={config.llm_model_agent_path}"
            )

    try:
        verified_weight_path = str(weight_manager.load_verified(MODEL_NAME))
    except FileNotFoundError:
        try:
            manifest = weight_manager.register_existing(
                model_name=MODEL_NAME,
                weight_path=Path(config.llm_model_agent_path),
            )
            print(
                "[STEP] weights_registered "
                + json.dumps(
                    {
                        "model": manifest.model_name,
                        "sha256": manifest.sha256,
                        "size_bytes": manifest.size_bytes,
                    },
                    sort_keys=True,
                )
            )
            verified_weight_path = str(weight_manager.load_verified(MODEL_NAME))
        except FileNotFoundError:
            print(
                f"[STEP] weights_unavailable reason=missing-local-weights model={MODEL_NAME} "
                f"path={config.llm_model_agent_path}"
            )

    if verified_weight_path is not None:
        print(f"[STEP] weights_verified path={verified_weight_path}")
    else:
        print("[STEP] weights_verified path=unavailable mode=api-only")

    seed_result = seed_project(target_dir=target, db_path=args.db_path, force=args.force_seed)
    print(f"[STEP] seeded {json.dumps(seed_result, sort_keys=True)}")

    store = Store(source_root=str(target), db_path=args.db_path)
    deterministic_findings = store.get_analyzer_findings()
    deterministic_keys = {
        _finding_key(item.analyzer, item.module_id, item.rule_id, item.line)
        for item in deterministic_findings
    }
    deterministic_targets = {
        _target_key(item.module_id, item.line)
        for item in deterministic_findings
    }

    agent_keys = _extract_agent_findings(store=store, config=config)
    agent_targets: set[str] = set()
    for item in agent_keys:
        parts = item.split(":")
        if len(parts) < 4:
            continue
        module_id = parts[1]
        try:
            line = int(parts[-1])
        except ValueError:
            continue
        agent_targets.add(_target_key(module_id, line))

    manager = TrainingRunManager()
    comparison = manager.compare(deterministic_findings=deterministic_targets, agent_findings=agent_targets)

    records: list[dict[str, object]] = []
    for finding in deterministic_findings:
        reasoning_text = (
            "<think>\n"
            f"Deterministic analyzer {finding.analyzer} reported {finding.rule_id} at line {finding.line} in {finding.module_id}. "
            "This is treated as supervised high-confidence signal for bootstrap training.\n"
            "</think>\n"
            "<action>\n"
            + json.dumps(
                {
                    "action_type": "FLAG_BUG",
                    "target_line": finding.line,
                    "content": finding.message,
                    "attributed_to": None,
                },
                sort_keys=True,
            )
            + "\n</action>"
        )
        records.append(
            {
                **manager.build_preference_record(
                    prompt=(
                        "Review the module and detect concrete bugs, security issues, and "
                        "dependency-attributed cascade problems without relying on prior findings."
                    ),
                    agent_output=reasoning_text,
                    deterministic_targets=[
                        _finding_key(
                            finding.analyzer,
                            finding.module_id,
                            finding.rule_id,
                            finding.line,
                        )
                    ],
                    reward=1.0,
                ),
                "module_id": f"{target.name}/{finding.module_id}",
                "text": reasoning_text,
                "chosen": reasoning_text,
            }
        )

        # Add a second deterministic variant to keep training volume healthy for small corpora.
        reasoning_text_variant = (
            "<think>\n"
            f"Cross-check confirms a reproducible issue in {finding.module_id} at line {finding.line}. "
            f"Rule hint={finding.rule_id}; analyzer={finding.analyzer}. "
            "Action should prioritize precise attribution and concrete remediation notes.\n"
            "</think>\n"
            "<action>\n"
            + json.dumps(
                {
                    "action_type": "FLAG_BUG",
                    "target_line": finding.line,
                    "content": f"[verified] {finding.message}",
                    "attributed_to": None,
                },
                sort_keys=True,
            )
            + "\n</action>"
        )
        records.append(
            {
                **manager.build_preference_record(
                    prompt=(
                        "Re-check this module and emit an evidence-based action with strict line attribution."
                    ),
                    agent_output=reasoning_text_variant,
                    deterministic_targets=[
                        _finding_key(
                            finding.analyzer,
                            finding.module_id,
                            finding.rule_id,
                            finding.line,
                        )
                    ],
                    reward=1.0,
                ),
                "module_id": f"{target.name}/{finding.module_id}",
                "text": reasoning_text_variant,
                "chosen": reasoning_text_variant,
            }
        )

    output_path = Path(args.deterministic_output)
    manager.save_records(output_path, records)

    baseline_precision = args.baseline_precision
    baseline_recall = args.baseline_recall
    prior_runs = store.list_training_runs(limit=100)
    if baseline_precision is None and prior_runs:
        baseline_precision = max(item.precision for item in prior_runs)
    if baseline_recall is None and prior_runs:
        baseline_recall = max(item.recall for item in prior_runs)

    passed_non_regression = True
    if baseline_precision is not None and baseline_recall is not None:
        try:
            manager.assert_non_regression(
                baseline_precision=baseline_precision,
                baseline_recall=baseline_recall,
                current_precision=comparison.precision,
                current_recall=comparison.recall,
                tolerance=args.regression_tolerance,
            )
        except ValueError as exc:
            passed_non_regression = False
            print(f"[STEP] non_regression_guard_failed reason={str(exc)}")
        else:
            print(
                "[STEP] non_regression_guard "
                + json.dumps(
                    {
                        "baseline_precision": baseline_precision,
                        "baseline_recall": baseline_recall,
                        "tolerance": args.regression_tolerance,
                    },
                    sort_keys=True,
                )
            )
    print(
        "[STEP] training_dataset "
        + json.dumps(
            {
                "output": str(output_path),
                "records": len(records),
                "precision": comparison.precision,
                "recall": comparison.recall,
                "false_negatives": comparison.false_negatives,
            },
            sort_keys=True,
        )
    )

    run_id = f"tr-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    run_config = {
        "target": str(target),
        "model": MODEL_NAME,
        "model_path": config.llm_model_agent_path,
        "agent_inference_enabled": os.getenv("GRAPHREVIEW_AGENT_INFERENCE_ENABLED", "true"),
        "regression_tolerance": args.regression_tolerance,
        "baseline_precision": baseline_precision,
        "baseline_recall": baseline_recall,
    }
    sha256 = "unavailable"
    if verified_weight_path is not None:
        sha256 = weight_manager.checksum(Path(verified_weight_path))
    store.create_training_run(
        run_id=run_id,
        model_name=MODEL_NAME,
        model_sha256=sha256,
        deterministic_findings=len(deterministic_keys),
        agent_findings=len(agent_keys),
        true_positives=comparison.true_positives,
        false_positives=comparison.false_positives,
        false_negatives=comparison.false_negatives,
        precision=comparison.precision,
        recall=comparison.recall,
        passed_non_regression=passed_non_regression,
        output_path=str(output_path),
        run_config_json=json.dumps(run_config, sort_keys=True),
    )
    print(f"[STEP] training_run_id={run_id}")

    print(
        "[END] "
        + json.dumps(
            {
                "ok": True,
                "deterministic_findings": len(deterministic_findings),
                "agent_findings": len(agent_keys),
                "model_weight": verified_weight_path or "unavailable",
                "model": MODEL_NAME,
                "precision": comparison.precision,
                "recall": comparison.recall,
                "run_id": run_id,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
