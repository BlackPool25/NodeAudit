from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from db.store import Store
from visualizer.pyvis_renderer import _build_network


OUTCOME_COLORS = {
    "well_learned": "#22c55e",
    "partially_learned": "#f59e0b",
    "failed": "#ef4444",
    "not_visited": "#6b7280",
}


@dataclass(frozen=True)
class TrainingSummary:
    run_id: str
    episodes: int
    steps: int
    avg_reward: float
    avg_judge: float
    dpo_pairs: int
    top_failures: list[str]
    top_successes: list[str]


def _outcome(avg_reward: float, judge_score: float, wrong_attr_count: int, touched: bool) -> str:
    if not touched:
        return "not_visited"
    if avg_reward > 0.7 and judge_score > 0.7 and wrong_attr_count == 0:
        return "well_learned"
    if avg_reward < 0.4 or wrong_attr_count > 0:
        return "failed"
    return "partially_learned"


def build_training_graph(*, source_root: str, run_id: str, db_path: str | None = None, output_path: str = "outputs/NodeAudit_graph.html") -> Path:
    store = Store(source_root=source_root, db_path=db_path)
    snapshot = store.get_full_graph()
    annotations = store.get_training_annotations(run_id)

    by_module: dict[str, list[Any]] = defaultdict(list)
    for item in annotations:
        by_module[item.module_id].append(item)

    net = _build_network(height="920px", width="100%")

    failed_edges: set[tuple[str, str]] = set()
    all_rewards: list[float] = []
    all_judges: list[float] = []

    for node in snapshot.nodes:
        rows = by_module.get(node.module_id, [])
        touched = bool(rows)
        rewards = [float(row.avg_reward) for row in rows]
        judges = [float(row.thinking_quality) for row in rows]
        avg_reward = (sum(rewards) / len(rewards)) if rewards else 0.0
        avg_judge = (sum(judges) / len(judges)) if judges else 0.0
        all_rewards.extend(rewards)
        all_judges.extend(judges)

        action_counts: Counter[str] = Counter()
        correct: list[str] = []
        wrong: list[str] = []
        judge_text: list[str] = []

        for row in rows:
            try:
                action_counts.update(json.loads(row.action_counts_json))
            except Exception:
                if row.action_type:
                    action_counts[row.action_type] += 1
            try:
                correct.extend(json.loads(row.correct_attributions_json))
            except Exception:
                pass
            try:
                wrong.extend(json.loads(row.wrong_attributions_json))
            except Exception:
                pass
            if row.judge_verdict:
                judge_text.append(row.judge_verdict)

            if row.action_type == "FLAG_DEPENDENCY_ISSUE":
                try:
                    payload = json.loads(row.action_payload)
                except Exception:
                    payload = {}
                target = str(payload.get("attributed_to") or "")
                if target and wrong:
                    failed_edges.add((node.module_id, target))

        outcome = _outcome(avg_reward, avg_judge, len(wrong), touched)
        actions_pretty = ", ".join(f"{k}x{v}" for k, v in sorted(action_counts.items())) or "none"
        judge_verdict = judge_text[-1] if judge_text else "not judged"

        tooltip = (
            f"Module: {node.module_id}\n"
            f"Avg Reward: {avg_reward:.2f}\n"
            f"Judge Score: {avg_judge:.2f}\n"
            f"Correct Attributions: {', '.join(correct) if correct else 'none'}\n"
            f"Wrong: {', '.join(wrong) if wrong else 'none'}\n"
            f"Actions: {actions_pretty}\n"
            f"Judge Verdict: {judge_verdict}"
        )

        net.add_node(
            n_id=node.module_id,
            label=node.module_id,
            title=tooltip,
            color=OUTCOME_COLORS[outcome],
            value=1.0 + max(0.0, avg_reward),
            shape="dot",
        )

    for edge in snapshot.edges:
        is_failed = (edge.source_module_id, edge.target_module_id) in failed_edges
        net.add_edge(
            source=edge.source_module_id,
            to=edge.target_module_id,
            title=edge.connection_summary or edge.import_line,
            color="#ef4444" if is_failed else "#2563eb",
            width=2.2 if is_failed else 1.4,
            arrows="to",
        )

    summary = _summarize(run_id=run_id, annotations=annotations, rewards=all_rewards, judges=all_judges)

    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    net.write_html(str(output), open_browser=False, notebook=False)

    html = output.read_text(encoding="utf-8")
    html = re.sub(r'<link[^>]*cdn\.jsdelivr\.net[^>]*>\s*', "", html, flags=re.IGNORECASE)
    html = re.sub(r'<script[^>]*cdn\.jsdelivr\.net[^>]*>\s*</script>\s*', "", html, flags=re.IGNORECASE)
    panel = (
        "<aside style='position:fixed;right:0;top:0;width:340px;height:100%;"
        "background:#0f172a;color:#e2e8f0;padding:18px;overflow:auto;z-index:1000;'>"
        f"<h3 style='margin:0 0 12px 0;'>Training Run: {summary.run_id}</h3>"
        f"<p>Episodes: {summary.episodes} | Steps: {summary.steps}</p>"
        f"<p>Avg Reward: {summary.avg_reward:.2f}</p>"
        f"<p>Judge Scores: {summary.avg_judge:.2f}</p>"
        f"<p>DPO pairs built: {summary.dpo_pairs}</p>"
        "<h4>Top 3 Failures</h4>"
        f"<ul>{''.join(f'<li>{item}</li>' for item in summary.top_failures)}</ul>"
        "<h4>Top 3 Successes</h4>"
        f"<ul>{''.join(f'<li>{item}</li>' for item in summary.top_successes)}</ul>"
        "</aside>"
    )

    html = html.replace("</body>", f"{panel}</body>")
    output.write_text(html, encoding="utf-8")
    return output


def _summarize(*, run_id: str, annotations: list[Any], rewards: list[float], judges: list[float]) -> TrainingSummary:
    episodes = len({(item.task_id, item.module_id) for item in annotations})
    steps = len(annotations)
    avg_reward = (sum(rewards) / len(rewards)) if rewards else 0.0
    avg_judge = (sum(judges) / len(judges)) if judges else 0.0

    module_scores: dict[str, float] = defaultdict(float)
    module_counts: dict[str, int] = defaultdict(int)
    for row in annotations:
        module_scores[row.module_id] += float(row.avg_reward)
        module_counts[row.module_id] += 1

    sorted_modules = sorted(
        module_scores,
        key=lambda module_id: module_scores[module_id] / max(1, module_counts[module_id]),
    )
    top_failures = sorted_modules[:3]
    top_successes = list(reversed(sorted_modules[-3:])) if sorted_modules else []

    return TrainingSummary(
        run_id=run_id,
        episodes=episodes,
        steps=steps,
        avg_reward=avg_reward,
        avg_judge=avg_judge,
        dpo_pairs=max(0, steps // 4),
        top_failures=top_failures,
        top_successes=top_successes,
    )
