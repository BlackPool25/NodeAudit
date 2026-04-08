from __future__ import annotations

import argparse
import json
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

    summary: dict[str, object] = {
        "target": str(target),
        "levels": {},
    }

    for idx, level in enumerate(args.levels):
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
