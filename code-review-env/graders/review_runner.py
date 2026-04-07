from __future__ import annotations

import argparse
import time
import uuid
from pathlib import Path
from collections import deque

from db.seed import seed_project
from db.store import Store
from env.action import ActionType, ReviewAction
from graph.graph_manager import GraphManager
from graders.easy_grader import EasyGrader
from graders.hard_grader import HardGrader
from graders.medium_grader import MediumGrader
from visualizer.report_generator import GeneratedArtifacts, generate_phase5_outputs


def _action_from_finding(tool: str, severity: str, line: int, message: str) -> list[ReviewAction]:
    if tool == "bandit":
        flag = ActionType.FLAG_SECURITY
    elif severity == "low":
        flag = ActionType.FLAG_STYLE
    else:
        flag = ActionType.FLAG_BUG

    actions = [ReviewAction(action_type=flag, target_line=max(line, 1))]
    actions.append(ReviewAction(action_type=ActionType.ADD_COMMENT, content=message))
    return actions


def _build_actions_for_module(store: Store, graph: GraphManager, module_id: str) -> list[ReviewAction]:
    findings = store.get_findings(module_id)
    actions: list[ReviewAction] = []
    for finding in findings:
        actions.extend(
            _action_from_finding(
                tool=finding.tool,
                severity=finding.severity.value,
                line=finding.line,
                message=finding.message,
            )
        )

    incoming = graph.get_neighbors(module_id, direction="in")
    if findings and incoming:
        actions.append(
            ReviewAction(
                action_type=ActionType.FLAG_DEPENDENCY_ISSUE,
                attributed_to=incoming[0],
                content="Potential upstream dependency contribution",
            )
        )

    if findings:
        actions.append(ReviewAction(action_type=ActionType.REQUEST_CHANGES))
    else:
        actions.append(ReviewAction(action_type=ActionType.APPROVE))
    return actions


def _resolve_module_scope(graph: GraphManager, module_filter: list[str] | None, hops: int) -> list[str]:
    traversal = graph.traversal_order()
    if not module_filter:
        return traversal

    graph_obj = graph.load_graph()
    seeds = [graph.resolve_module_id(item) for item in module_filter]
    visited = set(seeds)
    queue: deque[tuple[str, int]] = deque((seed, 0) for seed in seeds)
    max_hops = max(hops, 0)

    while queue:
        node, depth = queue.popleft()
        if depth >= max_hops:
            continue
        neighbors = set(graph_obj.successors(node))
        neighbors.update(graph_obj.predecessors(node))
        for neighbor in sorted(neighbors):
            if neighbor in visited:
                continue
            visited.add(neighbor)
            queue.append((neighbor, depth + 1))

    rank = {module_id: idx for idx, module_id in enumerate(traversal)}
    return sorted(visited, key=lambda module_id: (rank.get(module_id, 10_000), module_id))


def run_review(
    target: Path,
    db_path: str | None,
    grader_level: str,
    force_seed: bool,
    skip_seed: bool,
    show_progress: bool,
    module_filter: list[str] | None = None,
    filter_hops: int = 1,
) -> dict[str, float]:
    if not skip_seed:
        if show_progress:
            print("[SEED] Starting parse/lint/store pipeline...", flush=True)
        seed_project(target_dir=target, db_path=db_path, force=force_seed)
        if show_progress:
            print("[SEED] Done.", flush=True)

    store = Store(source_root=str(target), db_path=db_path)
    graph = GraphManager(source_root=target, db_path=db_path)

    if grader_level == "easy":
        grader = EasyGrader(store)
    elif grader_level == "medium":
        grader = MediumGrader(store)
    else:
        grader = HardGrader(store, graph)

    module_scores: dict[str, float] = {}
    module_order = _resolve_module_scope(graph, module_filter=module_filter, hops=filter_hops)
    total_modules = len(module_order)
    start = time.perf_counter()
    for idx, module_id in enumerate(module_order, start=1):
        if show_progress:
            print(f"[REVIEW] {idx}/{total_modules} module={module_id}", flush=True)
        actions = _build_actions_for_module(store, graph, module_id)
        summary = grader.grade_episode(
            module_id=module_id,
            task_id=f"{grader_level}_review",
            episode_id=str(uuid.uuid4()),
            actions=actions,
        )
        module_scores[module_id] = summary.raw_total
    if show_progress:
        elapsed = time.perf_counter() - start
        print(f"[REVIEW] Completed {total_modules} modules in {elapsed:.2f}s", flush=True)
    return module_scores


def generate_reports(
    target: Path,
    db_path: str | None,
    output_dir: str,
    module_filter: list[str] | None,
    filter_hops: int,
    report_prefix: str,
) -> GeneratedArtifacts:
    return generate_phase5_outputs(
        source_root=target,
        db_path=db_path,
        output_dir=output_dir,
        module_filter=module_filter,
        hops=filter_hops,
        report_prefix=report_prefix,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run deterministic module reviews")
    parser.add_argument("target", help="Path to Python project to review")
    parser.add_argument("--db-path", default=None, help="Optional SQLite db path")
    parser.add_argument(
        "--grader",
        default="medium",
        choices=["easy", "medium", "hard"],
        help="Grader strategy",
    )
    parser.add_argument("--force-seed", action="store_true", help="Force reseeding")
    parser.add_argument("--skip-seed", action="store_true", help="Skip seed phase and use existing DB state")
    parser.add_argument("--no-progress", action="store_true", help="Disable progress logging")
    parser.add_argument(
        "--modules",
        nargs="*",
        default=None,
        help="Optional module ids/paths to focus on (scope expands to related modules)",
    )
    parser.add_argument(
        "--filter-hops",
        type=int,
        default=1,
        help="Neighbor hop expansion when --modules is provided",
    )
    parser.add_argument("--report", action="store_true", help="Generate Phase 5 JSON/Markdown/HTML artifacts")
    parser.add_argument("--output-dir", default="outputs", help="Output directory for report artifacts")
    parser.add_argument("--report-prefix", default="graphreview", help="Artifact file prefix")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    target = Path(args.target).resolve()
    scores = run_review(
        target=target,
        db_path=args.db_path,
        grader_level=args.grader,
        force_seed=args.force_seed,
        skip_seed=args.skip_seed,
        show_progress=not args.no_progress,
        module_filter=args.modules,
        filter_hops=args.filter_hops,
    )
    total = sum(scores.values())
    print(f"Reviewed modules: {len(scores)}")
    print(f"Total raw reward: {total:.2f}")
    for module_id, score in sorted(scores.items()):
        print(f"- {module_id}: {score:.2f}")

    if args.report:
        artifacts = generate_reports(
            target=target,
            db_path=args.db_path,
            output_dir=args.output_dir,
            module_filter=args.modules,
            filter_hops=args.filter_hops,
            report_prefix=args.report_prefix,
        )
        print("Generated artifacts:")
        print(f"- markdown: {artifacts.markdown_path}")
        print(f"- json: {artifacts.json_path}")
        print(f"- html: {artifacts.html_path}")
        print(f"- confidence_score: {artifacts.confidence_score:.3f}")


if __name__ == "__main__":
    main()
