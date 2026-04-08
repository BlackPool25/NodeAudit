from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from graders.review_runner import generate_reports, run_review


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Unified GraphReview runner: seed + run easy/medium/hard + generate artifacts"
    )
    parser.add_argument("target", help="Target Python project folder")
    parser.add_argument("--db-path", default=None, help="Optional SQLite DB path")
    parser.add_argument("--force-seed", action="store_true", help="Force graph reseed")
    parser.add_argument("--skip-seed", action="store_true", help="Skip seeding and reuse DB")
    parser.add_argument("--modules", nargs="*", default=None, help="Optional module focus list")
    parser.add_argument("--filter-hops", type=int, default=1, help="Neighbor expansion hops for --modules")
    parser.add_argument("--output-dir", default="outputs", help="Artifacts output directory")
    parser.add_argument("--report-prefix", default="graphreview_full", help="Artifact prefix")
    parser.add_argument("--no-progress", action="store_true", help="Disable progress logs")
    parser.add_argument(
        "--llm-mode",
        choices=["fast", "judge", "fused"],
        default=None,
        help=(
            "fast=disable judge/verifier/edge-summary for speed, "
            "judge=primary judge only, fused=primary+verifier"
        ),
    )
    parser.add_argument(
        "--edge-summary",
        action="store_true",
        help="Enable LLM edge summaries during seed (can be slow)",
    )
    parser.add_argument(
        "--no-prompt",
        action="store_true",
        help="Disable interactive configuration questions",
    )
    parser.add_argument(
        "--think-level",
        choices=["off", "low", "medium", "high"],
        default="off",
        help="Thinking level for judge/verifier on compatible providers",
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=["none", "low", "medium", "high"],
        default="none",
        help="Reasoning effort for judge/verifier models that support it",
    )
    parser.add_argument(
        "--levels",
        nargs="*",
        choices=["easy", "medium", "hard"],
        default=["easy", "medium", "hard"],
        help="Review levels to run",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    target = Path(args.target).resolve()

    if args.no_progress:
        os.environ["GRAPHREVIEW_PROGRESS"] = "false"

    selected_mode = args.llm_mode
    selected_edge_summary = args.edge_summary
    selected_levels = args.levels
    selected_think_level = args.think_level
    selected_reasoning_effort = args.reasoning_effort

    if not args.no_prompt and selected_mode is None:
        print("GraphReview configuration")
        print("1) full (fused judge + verifier)")
        print("2) judge-only")
        print("3) fast")
        mode_choice = input("Choose mode [1/2/3] (default 1): ").strip() or "1"
        selected_mode = {"1": "fused", "2": "judge", "3": "fast"}.get(mode_choice, "fused")

        edge_choice = input("Enable edge LLM summaries? [y/N]: ").strip().lower()
        selected_edge_summary = edge_choice in {"y", "yes"}

        levels_choice = input(
            "Run levels (comma separated: easy,medium,hard) [default easy,medium,hard]: "
        ).strip()
        if levels_choice:
            parsed_levels = [part.strip() for part in levels_choice.split(",") if part.strip()]
            valid = [lvl for lvl in parsed_levels if lvl in {"easy", "medium", "hard"}]
            selected_levels = valid or ["easy", "medium", "hard"]

        think_choice = input("Thinking level for judge/verifier [off/low/medium/high] (default off): ").strip().lower()
        if think_choice in {"off", "low", "medium", "high"}:
            selected_think_level = think_choice

        effort_choice = input("Reasoning effort [none/low/medium/high] (default none): ").strip().lower()
        if effort_choice in {"none", "low", "medium", "high"}:
            selected_reasoning_effort = effort_choice

    if selected_mode is None:
        selected_mode = "fused"

    summary: dict[str, object] = {
        "target": str(target),
        "levels": {},
        "llm_mode": selected_mode,
        "think_level": selected_think_level,
        "reasoning_effort": selected_reasoning_effort,
    }

    os.environ["GRAPHREVIEW_JUDGE_THINK"] = "false" if selected_think_level == "off" else selected_think_level
    os.environ["GRAPHREVIEW_JUDGE_REASONING_EFFORT"] = selected_reasoning_effort

    if selected_mode == "fast":
        os.environ["GRAPHREVIEW_JUDGE_ENABLED"] = "false"
        os.environ["GRAPHREVIEW_VERIFIER_ENABLED"] = "false"
        os.environ["GRAPHREVIEW_EDGE_SUMMARY_ENABLED"] = "true" if selected_edge_summary else "false"
        os.environ["GRAPHREVIEW_HARD_ISSUE_FINDER_ENABLED"] = "false"
    elif selected_mode == "judge":
        os.environ["GRAPHREVIEW_JUDGE_ENABLED"] = "true"
        os.environ["GRAPHREVIEW_VERIFIER_ENABLED"] = "false"
        os.environ["GRAPHREVIEW_EDGE_SUMMARY_ENABLED"] = "true" if selected_edge_summary else "false"
        os.environ["GRAPHREVIEW_HARD_ISSUE_FINDER_ENABLED"] = "true"
    else:
        os.environ["GRAPHREVIEW_JUDGE_ENABLED"] = "true"
        os.environ["GRAPHREVIEW_VERIFIER_ENABLED"] = "true"
        os.environ["GRAPHREVIEW_EDGE_SUMMARY_ENABLED"] = "true" if selected_edge_summary else "false"
        os.environ["GRAPHREVIEW_HARD_ISSUE_FINDER_ENABLED"] = "true"

    for idx, level in enumerate(selected_levels):
        scores = run_review(
            target=target,
            db_path=args.db_path,
            grader_level=level,
            force_seed=args.force_seed if idx == 0 else False,
            skip_seed=args.skip_seed if idx == 0 else True,
            show_progress=not args.no_progress,
            module_filter=args.modules,
            filter_hops=args.filter_hops,
        )
        total = float(sum(scores.values()))
        summary["levels"][level] = {
            "modules": len(scores),
            "raw_total": total,
            "avg_raw_per_module": (total / len(scores)) if scores else 0.0,
        }

    artifacts = generate_reports(
        target=target,
        db_path=args.db_path,
        output_dir=args.output_dir,
        module_filter=args.modules,
        filter_hops=args.filter_hops,
        report_prefix=args.report_prefix,
    )

    summary["artifacts"] = {
        "markdown": artifacts.markdown_path,
        "json": artifacts.json_path,
        "html": artifacts.html_path,
        "confidence_score": artifacts.confidence_score,
        "module_count": artifacts.module_count,
        "edge_count": artifacts.edge_count,
    }

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
