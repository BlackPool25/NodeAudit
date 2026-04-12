from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import textwrap
from dataclasses import dataclass, field
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
REPORT_PATH = OUTPUTS / "verification_report.txt"


@dataclass
class VerificationState:
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)

    def fail(self, msg: str) -> None:
        self.failures.append(msg)
        self.info.append(f"FAIL: {msg}")

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)
        self.info.append(f"WARNING: {msg}")

    def ok(self, msg: str) -> None:
        self.info.append(f"PASS: {msg}")


def _run_python(code: str, timeout: int = 120) -> tuple[int, str, str]:
    proc = subprocess.run(
        [str(ROOT / ".venv" / "bin" / "python"), "-c", code],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _run_cmd(cmd: list[str], timeout: int = 180, cwd: pathlib.Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _pyright_bin() -> str:
    candidate = ROOT / ".venv" / "bin" / "pyright"
    return str(candidate) if candidate.exists() else "pyright"


def section_1_rocm_and_unsloth(state: VerificationState) -> None:
    state.info.append("\n=== SECTION 1: AMD ROCm + Unsloth Setup ===")

    rc, out, err = _run_python(
        textwrap.dedent(
            """
            import torch
            print(f"cuda_available={torch.cuda.is_available()}")
            if torch.cuda.is_available():
                p = torch.cuda.get_device_properties(0)
                print(f"device={torch.cuda.get_device_name(0)}")
                print(f"hip={torch.version.hip}")
                print(f"vram={p.total_memory/1e9:.1f}")
            """
        )
    )
    if rc != 0:
        state.warn(f"ROCm detection script failed: {err.strip() or out.strip()}")
    elif "cuda_available=True" not in out:
        state.warn("CUDA/ROCm not available in current environment; set HSA_OVERRIDE_GFX_VERSION=11.0.0 on RX 7900 GRE")
    else:
        state.ok("ROCm/CUDA available")

    rc, out, err = _run_python(
        "import unsloth, unsloth_zoo; print(unsloth.__version__)"
    )
    if rc != 0:
        msg = err.strip() or out.strip()
        if "no usable HIP accelerator" in msg or "NotImplementedError" in msg:
            state.warn(f"Unsloth import requires ROCm torch wheels in this host env: {msg}")
        else:
            state.fail(f"Unsloth import failed: {msg}")
    else:
        state.ok("Unsloth import check passed")

    train_src = (ROOT / "training" / "train_lora.py").read_text(encoding="utf-8")
    if "load_in_4bit=True" in train_src:
        state.fail("train_lora.py still has load_in_4bit=True")
    elif "load_in_4bit=False" in train_src and "load_in_16bit=True" in train_src:
        state.ok("QLoRA AMD guard check passed")
    else:
        state.fail("train_lora.py missing explicit load_in_4bit/load_in_16bit AMD config")

    if 'use_gradient_checkpointing="unsloth"' not in train_src:
        state.fail('train_lora.py missing use_gradient_checkpointing="unsloth"')
    else:
        state.ok("Gemma4 gradient checkpointing guard passed")


def section_2_static_analysis(state: VerificationState) -> None:
    state.info.append("\n=== SECTION 2: Static Analysis Pipeline ===")

    rc, out, _ = _run_cmd(["grep", "-r", "semgrep", "analyzers/", "db/", "inference.py"], timeout=30)
    if rc == 0 and out.strip():
        state.fail(f"Semgrep references remain:\n{out.strip()}")
    else:
        state.ok("Semgrep removed from core runtime paths")

    test_file = pathlib.Path("/tmp/pyright_test.py")
    test_file.write_text("def f(x: int) -> str:\n    return x\n", encoding="utf-8")
    rc, out, err = _run_cmd([_pyright_bin(), "--outputjson", str(test_file)], timeout=30)
    if rc not in {0, 1}:
        state.fail(f"Pyright invocation failed: {err.strip()}")
    else:
        try:
            payload = json.loads(out)
            errors = [d for d in payload.get("generalDiagnostics", []) if d.get("severity") == "error"]
            if not errors:
                state.fail("Pyright failed to report known type error")
            else:
                state.ok(f"Pyright JSON check passed ({len(errors)} errors on test file)")
        except Exception as exc:
            state.fail(f"Pyright JSON decode failed: {exc}")

    rc, out, err = _run_python(
        textwrap.dedent(
            """
            from analyzers.ast_checker import run_all
            import pathlib, textwrap
            p = pathlib.Path('/tmp/ast_test.py')
            p.write_text(textwrap.dedent('''
            def bad_default(x=[]):
                return x
            try:
                pass
            except:
                pass
            x = None
            if x == None:
                pass
            '''))
            findings = run_all(str(p))
            print(sorted({f.rule for f in findings}))
            """
        )
    )
    if rc != 0:
        state.fail(f"AST checker execution failed: {err.strip() or out.strip()}")
    else:
        rules = set(json.loads(out.strip().replace("'", '"')) if out.strip().startswith("[") else [])
        expected = {"mutable_default_arg", "bare_except", "none_equality_check"}
        if not expected.issubset(rules):
            state.fail(f"AST checker missing expected rules. got={rules}")
        else:
            state.ok("AST checker known-pattern checks passed")

    rc, out, err = _run_python(
        textwrap.dedent(
            """
            from analyzers.pipeline import run_pipeline
            findings = run_pipeline('sample_project')
            print(len(findings))
            print(sorted({f.severity for f in findings}))
            """
        ),
        timeout=180,
    )
    if rc != 0:
        state.fail(f"Analyzer pipeline run failed: {err.strip() or out.strip()}")
    else:
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        count = int(lines[0]) if lines else 0
        severities = set()
        if len(lines) > 1:
            try:
                severities = set(json.loads(lines[1].replace("'", '"')))
            except Exception:
                pass
        if count <= 10:
            state.fail(f"Pipeline findings too low: {count}")
        elif "high" not in severities:
            state.fail(f"Pipeline produced no high severity findings: {severities}")
        else:
            state.ok(f"Pipeline findings check passed ({count})")


def section_3_agent_judge(state: VerificationState) -> None:
    state.info.append("\n=== SECTION 3: Agent + Judge ===")

    rc, out, err = _run_python(
        textwrap.dedent(
            """
            from llm.agent_runner import extract_thinking_and_action
            import json
            test_output = '''
            <think>
            root cause is config.py
            </think>
            <action>
            {"action_type": "FLAG_DEPENDENCY_ISSUE", "target_line": 34, "content": "x", "attributed_to": "config"}
            </action>
            '''
            thinking, action = extract_thinking_and_action(test_output)
            print(len(thinking))
            print(action.get('action_type',''))
            print(action.get('attributed_to',''))
            """
        )
    )
    if rc != 0:
        state.fail(f"Thinking extraction check failed: {err.strip() or out.strip()}")
    else:
        vals = [l.strip() for l in out.splitlines() if l.strip()]
        if len(vals) < 3 or int(vals[0]) <= 20 or vals[1] != "FLAG_DEPENDENCY_ISSUE" or vals[2] != "config":
            state.fail(f"Thinking extraction invalid output: {vals}")
        else:
            state.ok("Thinking trace extraction check passed")

    if not os.getenv("HF_TOKEN"):
        state.warn("HF_TOKEN missing; skipping live judge API scoring check")
    else:
        rc, out, err = _run_python(
            textwrap.dedent(
                """
                from llm.thinking_judge import score_thinking
                result = score_thinking(
                    thinking_trace='Bug is in config.py due to None timeout',
                    action={'action_type': 'FLAG_DEPENDENCY_ISSUE', 'attributed_to': 'config'},
                    finding={'module_id': 'config', 'severity': 'error', 'message': 'Missing key returns None'},
                    graph_context={'config': {'dependents': ['checkout']}}
                )
                print(result['score'])
                print('what_was_right' in result and 'what_was_wrong' in result)
                """
            ),
            timeout=90,
        )
        if rc != 0:
            state.fail(f"Judge scoring failed: {err.strip() or out.strip()}")
        else:
            lines = [l.strip() for l in out.splitlines() if l.strip()]
            if not lines:
                state.fail("Judge scoring returned empty output")
            else:
                score = float(lines[0])
                if not (0.0 <= score <= 1.0):
                    state.fail(f"Judge score out of range: {score}")
                else:
                    state.ok("Judge scoring API check passed")

    rc, out, err = _run_python(
        "from training.trajectory_collector import compute_composite_reward as c; print(c(0.6,0.8)); print(c(0.6,0.1))"
    )
    if rc != 0:
        state.fail(f"Composite reward helper failed: {err.strip() or out.strip()}")
    else:
        lines = [float(x.strip()) for x in out.splitlines() if x.strip()]
        if len(lines) != 2 or abs(lines[0] - (0.6 * 0.6 + 0.8 * 0.4)) > 1e-3 or lines[1] >= lines[0]:
            state.fail("Composite reward formula verification failed")
        else:
            state.ok("Composite reward formula check passed")


def section_4_training_data(state: VerificationState) -> None:
    state.info.append("\n=== SECTION 4: Training Data Quality ===")
    dataset_path = ROOT / "outputs" / "training" / "dataset.latest.jsonl"
    if not dataset_path.exists():
        state.warn("dataset.latest.jsonl missing; run inference.py <target> or trajectory collection first")
        return

    records = [json.loads(l) for l in dataset_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if len(records) < 50:
        state.fail(f"Training records too low: {len(records)}")
    else:
        state.ok(f"Training record count OK: {len(records)}")

    thinking_count = sum(1 for r in records if "<think>" in str(r.get("text", "")) or "<think>" in str(r.get("chosen", "")))
    ratio = thinking_count / max(1, len(records))
    if ratio < 0.75:
        state.fail(f"Reasoning ratio too low: {ratio:.0%}")
    else:
        state.ok(f"Reasoning ratio check passed: {ratio:.0%}")

    dpo_path = ROOT / "outputs" / "training" / "dpo_pairs.jsonl"
    if dpo_path.exists():
        pairs = [json.loads(l) for l in dpo_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        invalid = [p for p in pairs[:20] if not (p.get("prompt") and p.get("chosen") and p.get("rejected") and p.get("chosen") != p.get("rejected"))]
        if invalid:
            state.fail("Invalid DPO pairs detected in spot-check")
        else:
            state.ok(f"DPO pairs spot-check passed ({len(pairs)})")
    else:
        state.warn("No dpo_pairs.jsonl yet (run trajectory collector first)")

    train_modules = {str(r.get("module_id", "")) for r in records}
    eval_modules = {"cart", "checkout", "auth", "config", "payments"}
    leaked = train_modules & eval_modules
    if leaked:
        state.fail(f"Eval leakage detected: {sorted(leaked)}")
    else:
        state.ok("No direct eval-module leakage in module_id field")


def section_5_env_integrity(state: VerificationState) -> None:
    state.info.append("\n=== SECTION 5: RL Environment Integrity ===")

    if shutil.which("openenv"):
        rc, out, err = _run_cmd(["openenv", "validate"], timeout=120)
        if rc != 0:
            state.fail(f"openenv validate failed: {err.strip() or out.strip()}")
        else:
            state.ok("openenv validate passed")
    else:
        state.warn("openenv CLI not available; skipping openenv validate")

    rc, out, err = _run_python(
        textwrap.dedent(
            """
            from env.environment import CodeReviewEnv
            from env.action import ReviewAction, ActionType
            env = CodeReviewEnv(source_root='sample_project')
            obs = env.reset(task_id='style_review')
            assert obs.within_budget
            assert len(obs.available_actions) > 0
            result = env.step(ReviewAction(action_type=ActionType.REQUEST_CHANGES))
            reward_value = result.reward if isinstance(result.reward, (int,float)) else result.reward.raw_value
            print(reward_value)
            """
        ),
        timeout=120,
    )
    if rc != 0:
        state.fail(f"Environment step verification failed: {err.strip() or out.strip()}")
    else:
        reward = float([l for l in out.splitlines() if l.strip()][-1])
        if not (-2.0 <= reward <= 2.0):
            state.fail(f"Reward out of expected range: {reward}")
        else:
            state.ok("Environment reward-range check passed")


def section_6_hf_readiness(state: VerificationState) -> None:
    state.info.append("\n=== SECTION 6: HF Deployment Readiness ===")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    if "7860" not in dockerfile or "CMD" not in dockerfile:
        state.fail("Dockerfile missing required HF Spaces port/CMD settings")
    else:
        state.ok("Dockerfile port and CMD check passed")

    server_src = (ROOT / "server" / "app.py").read_text(encoding="utf-8")
    for banned in ["import torch", "import llama_cpp", "from unsloth"]:
        if banned in server_src:
            state.fail(f"server/app.py contains banned runtime GPU import: {banned}")
            break
    else:
        state.ok("server/app.py runtime GPU import guard passed")

    inf_src = (ROOT / "inference.py").read_text(encoding="utf-8")
    if "os.getenv" not in inf_src and "os.environ" not in inf_src:
        state.fail("inference.py does not appear to read environment variables")
    else:
        state.ok("inference.py environment-variable check passed")


def section_7_inference_logs(state: VerificationState) -> None:
    state.info.append("\n=== SECTION 7: Inference Script Compliance ===")
    env = os.environ.copy()
    env.setdefault("GRAPHREVIEW_AGENT_INFERENCE_ENABLED", "false")

    proc = subprocess.run(
        [str(ROOT / ".venv" / "bin" / "python"), "inference.py", "sample_project"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=1200,
        check=False,
        env=env,
    )
    stdout = proc.stdout
    if "[START]" not in stdout or "[END]" not in stdout:
        state.fail("inference.py missing START/END logs")
        return

    end_lines = [l for l in stdout.splitlines() if "[END]" in l]
    if not end_lines:
        state.fail("No END line in inference output")
        return

    try:
        end_data = json.loads(end_lines[-1].split("[END]", 1)[1].strip())
    except Exception as exc:
        state.fail(f"END payload JSON parse failed: {exc}")
        return

    required = ["agent_findings", "deterministic_findings", "model", "precision", "recall", "run_id"]
    missing = [k for k in required if k not in end_data]
    if missing:
        state.fail(f"END payload missing fields: {missing}")
    else:
        state.ok("END payload fields check passed")

    if "agent_llm_disabled" in stdout:
        state.fail("inference logs still contain agent_llm_disabled marker")

    recall = float(end_data.get("recall", 0.0))
    if recall <= 0.05:
        state.fail(f"Recall too low: {recall:.3f}")
    else:
        state.ok(f"Recall threshold check passed ({recall:.3f})")

    scores: list[float] = [float(end_data.get("precision", 0.0))]
    for _ in range(2):
        p = subprocess.run(
            [str(ROOT / ".venv" / "bin" / "python"), "inference.py", "sample_project"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=1200,
            check=False,
            env=env,
        )
        end = [l for l in p.stdout.splitlines() if "[END]" in l]
        if not end:
            state.fail("Reproducibility run missing END log")
            return
        payload = json.loads(end[-1].split("[END]", 1)[1].strip())
        scores.append(float(payload.get("precision", 0.0)))

    variance = max(scores) - min(scores)
    if variance >= 0.1:
        state.fail(f"Precision variance too high: scores={scores}, variance={variance:.3f}")
    else:
        state.ok(f"Baseline reproducibility check passed: {scores}")


def section_8_training_graph(state: VerificationState) -> None:
    state.info.append("\n=== SECTION 8: Training Graph Output ===")

    # Build graph for latest run if needed.
    rc, out, err = _run_python(
        textwrap.dedent(
            """
            from db.store import Store
            from visualizer.training_graph import build_training_graph
            store = Store(source_root='sample_project')
            runs = store.list_training_runs(limit=1)
            if runs:
                path = build_training_graph(source_root='sample_project', run_id=runs[0].run_id)
                print(path)
            """
        ),
        timeout=180,
    )
    if rc != 0:
        state.warn(f"Graph build helper failed for latest run: {err.strip() or out.strip()}")

    graph_path = ROOT / "outputs" / "NodeAudit_graph.html"
    if not graph_path.exists():
        state.fail("Training graph HTML not generated at outputs/NodeAudit_graph.html")
        return

    content = graph_path.read_text(encoding="utf-8")
    if len(content) <= 10_000:
        state.fail("Training graph HTML too small")
    elif "vis-network" not in content and "pyvis" not in content.lower():
        state.fail("Training graph file does not look like a valid pyvis artifact")
    else:
        state.ok("Training graph structure check passed")

    cdn_refs = re.findall(r'https?://(?!localhost)[^\s"\']+\.js', content)
    external = [u for u in cdn_refs if "cdnjs" not in u and "unpkg" not in u]
    if external:
        state.warn(f"External JS refs remain in graph HTML: {external[:3]}")

    if "training" not in content.lower() and "avg_reward" not in content.lower():
        state.fail("Training graph is missing training outcome annotation text")
    else:
        state.ok("Training graph annotation text check passed")


def run_verification_suite() -> VerificationState:
    state = VerificationState()
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    section_1_rocm_and_unsloth(state)
    section_2_static_analysis(state)
    section_3_agent_judge(state)
    section_4_training_data(state)
    section_5_env_integrity(state)
    section_6_hf_readiness(state)
    section_7_inference_logs(state)
    section_8_training_graph(state)

    REPORT_PATH.write_text("\n".join(state.info) + "\n", encoding="utf-8")
    return state


def test_verification_suite() -> None:
    state = run_verification_suite()
    assert not state.failures, "\n".join(state.failures)


if __name__ == "__main__":
    result = run_verification_suite()
    print("\n".join(result.info))
    if result.failures:
        print(f"\nVerification failed with {len(result.failures)} FAIL items")
        sys.exit(1)
    print("\nVerification passed with no FAIL items")
