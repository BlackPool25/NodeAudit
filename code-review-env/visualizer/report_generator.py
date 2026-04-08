from __future__ import annotations

import ast
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select

from db.schema import LinterFinding, ModuleEdge, ModuleNode, ReviewAnnotation
from db.store import Store
from graph.graph_manager import GraphManager
from visualizer.pyvis_renderer import render_graph_html


class ReviewQualityMetrics(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float
    severity_weighted_coverage: float
    security_coverage: float
    dependency_attribution_validity: float
    consistency: float
    confidence_score: float


class GeneratedArtifacts(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    markdown_path: str
    json_path: str
    html_path: str
    module_count: int
    edge_count: int
    annotation_count: int
    confidence_score: float


@dataclass(frozen=True)
class _Context:
    graph_manager: GraphManager
    store: Store
    module_ids: list[str]


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _parse_note_payload(note: str) -> dict[str, object]:
    text = note.strip()
    if not text:
        return {}
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _resolve_module_scope(graph_manager: GraphManager, module_filter: list[str] | None, hops: int) -> list[str]:
    graph = graph_manager.load_graph()
    if not module_filter:
        return sorted(str(node) for node in graph.nodes())

    seeds: set[str] = set()
    for module_id in module_filter:
        seeds.add(graph_manager.resolve_module_id(module_id))

    related: set[str] = set(seeds)
    frontier = set(seeds)
    hop_count = max(hops, 0)
    for _ in range(hop_count):
        next_frontier: set[str] = set()
        for module_id in frontier:
            next_frontier.update(str(item) for item in graph.successors(module_id))
            next_frontier.update(str(item) for item in graph.predecessors(module_id))
        next_frontier -= related
        related.update(next_frontier)
        frontier = next_frontier

    return sorted(related)


def _load_context(
    source_root: str | Path,
    db_path: str | Path | None,
    module_filter: list[str] | None,
    hops: int,
) -> _Context:
    graph_manager = GraphManager(source_root=source_root, db_path=db_path)
    store = Store(source_root=str(source_root), db_path=db_path)
    module_ids = _resolve_module_scope(graph_manager, module_filter, hops)
    return _Context(graph_manager=graph_manager, store=store, module_ids=module_ids)


def _compatible_finding_ids(action_type: str, findings: list[LinterFinding]) -> list[int]:
    ids: list[int] = []
    for finding in findings:
        if finding.id is None:
            continue
        if action_type == "FLAG_SECURITY" and finding.tool == "bandit":
            ids.append(finding.id)
        elif action_type == "FLAG_STYLE" and finding.tool != "bandit" and finding.severity.value == "low":
            ids.append(finding.id)
        elif action_type == "FLAG_BUG" and (finding.tool == "pyflakes" or finding.severity.value in {"medium", "high"}):
            ids.append(finding.id)
    return ids


def _compute_metrics(
    module_ids: list[str],
    graph_manager: GraphManager,
    findings_by_module: dict[str, list[LinterFinding]],
    annotations_by_module: dict[str, list[ReviewAnnotation]],
) -> ReviewQualityMetrics:
    true_positives = 0
    false_positives = 0
    false_negatives = 0

    severity_weight_total = 0.0
    severity_weight_matched = 0.0
    security_total = 0
    security_matched = 0

    attribution_total = 0
    attribution_valid = 0

    contradictory_modules = 0

    severity_weight = {"low": 1.0, "medium": 2.0, "high": 3.0}

    graph = graph_manager.load_graph()

    for module_id in module_ids:
        findings = findings_by_module.get(module_id, [])
        annotations = sorted(annotations_by_module.get(module_id, []), key=lambda item: item.step_number)

        finding_by_id = {finding.id: finding for finding in findings if finding.id is not None}
        matched_finding_ids: set[int] = set()

        terminal_actions: set[str] = set()
        for annotation in annotations:
            if annotation.action_type in {"APPROVE", "REQUEST_CHANGES"}:
                terminal_actions.add(annotation.action_type)

            if annotation.action_type == "FLAG_DEPENDENCY_ISSUE" and annotation.attributed_to:
                attribution_total += 1
                if annotation.attributed_to in graph and (
                    graph.has_edge(module_id, annotation.attributed_to)
                    or graph.has_edge(annotation.attributed_to, module_id)
                ):
                    attribution_valid += 1

            if annotation.action_type not in {"FLAG_STYLE", "FLAG_BUG", "FLAG_SECURITY"}:
                continue

            payload = _parse_note_payload(annotation.note)
            matched_id = payload.get("matched_finding_id")
            if isinstance(matched_id, int) and matched_id in finding_by_id and matched_id not in matched_finding_ids:
                matched_finding_ids.add(matched_id)
                true_positives += 1
                continue

            compatible = [item for item in _compatible_finding_ids(annotation.action_type, findings) if item not in matched_finding_ids]
            if compatible:
                matched_finding_ids.add(compatible[0])
                true_positives += 1
            else:
                false_positives += 1

        if len(terminal_actions) > 1:
            contradictory_modules += 1

        false_negatives += max(len(findings) - len(matched_finding_ids), 0)

        for finding in findings:
            weight = severity_weight.get(finding.severity.value, 1.0)
            severity_weight_total += weight
            if finding.id in matched_finding_ids:
                severity_weight_matched += weight
            if finding.tool == "bandit":
                security_total += 1
                if finding.id in matched_finding_ids:
                    security_matched += 1

    precision = _safe_div(true_positives, true_positives + false_positives)
    recall = _safe_div(true_positives, true_positives + false_negatives)
    f1 = _safe_div(2 * precision * recall, precision + recall)
    severity_coverage = _safe_div(severity_weight_matched, severity_weight_total)
    security_coverage = _safe_div(security_matched, security_total)
    attribution_validity = _safe_div(attribution_valid, attribution_total)
    consistency = 1.0 - _safe_div(contradictory_modules, len(module_ids))

    confidence_score = (
        0.35 * f1
        + 0.2 * severity_coverage
        + 0.15 * security_coverage
        + 0.2 * attribution_validity
        + 0.1 * consistency
    )
    confidence_score = max(0.0, min(1.0, confidence_score))

    return ReviewQualityMetrics(
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        precision=precision,
        recall=recall,
        f1=f1,
        severity_weighted_coverage=severity_coverage,
        security_coverage=security_coverage,
        dependency_attribution_validity=attribution_validity,
        consistency=consistency,
        confidence_score=confidence_score,
    )


def _extract_module_shape(raw_code: str) -> str:
    try:
        tree = ast.parse(raw_code)
    except SyntaxError:
        return "Could not parse AST for this module."

    functions = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
    async_functions = [node.name for node in tree.body if isinstance(node, ast.AsyncFunctionDef)]
    classes = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]

    parts: list[str] = []
    if functions:
        parts.append(f"functions={', '.join(functions[:6])}")
    if async_functions:
        parts.append(f"async_functions={', '.join(async_functions[:6])}")
    if classes:
        parts.append(f"classes={', '.join(classes[:6])}")

    if not parts:
        return "No top-level functions/classes; likely constants, helpers, or script-style module."
    return " | ".join(parts)


def _build_node_title(
    module: ModuleNode,
    findings: list[LinterFinding],
    annotations: list[ReviewAnnotation],
    status: str,
    confidence_score: float,
) -> str:
    security_findings = [finding for finding in findings if finding.tool == "bandit"]
    latest = annotations[-3:]

    latest_lines = []
    for item in latest:
        latest_lines.append(f"#{item.step_number} {item.action_type}: {item.reward_given:.2f}")

    return (
        f"<b>{module.module_id}</b><br>"
        f"status: {status}<br>"
        f"confidence: {confidence_score:.2f}<br>"
        f"summary: {(module.summary or module.ast_summary)[:420]}<br>"
        f"shape: {_extract_module_shape(module.raw_code)}<br>"
        f"security_findings: {len(security_findings)}<br>"
        f"latest_reviews: {' | '.join(latest_lines) if latest_lines else 'none'}"
    )


def _derive_status(node: ModuleNode, annotations: list[ReviewAnnotation]) -> str:
    if not annotations:
        return node.review_status.value
    last = annotations[-1].action_type
    if last == "APPROVE":
        return "approved"
    if last == "REQUEST_CHANGES":
        return "changes_requested"
    return node.review_status.value


def _build_json_payload(
    *,
    source_root: str,
    module_ids: list[str],
    nodes: list[ModuleNode],
    edges: list[ModuleEdge],
    findings_by_module: dict[str, list[LinterFinding]],
    annotations_by_module: dict[str, list[ReviewAnnotation]],
    metrics: ReviewQualityMetrics,
    episode_id: str | None,
) -> dict[str, object]:
    node_payload = []
    for node in sorted(nodes, key=lambda item: item.module_id):
        annotations = annotations_by_module.get(node.module_id, [])
        status = _derive_status(node, annotations)
        node_payload.append(
            {
                "module_id": node.module_id,
                "name": node.name,
                "status": status,
                "summary": node.summary or node.ast_summary,
                "module_shape": _extract_module_shape(node.raw_code),
                "security_findings": [
                    {
                        "line": finding.line,
                        "code": finding.code,
                        "severity": finding.severity.value,
                        "message": finding.message,
                    }
                    for finding in findings_by_module.get(node.module_id, [])
                    if finding.tool == "bandit"
                ],
                "linter_findings": [
                    {
                        "id": finding.id,
                        "tool": finding.tool,
                        "line": finding.line,
                        "severity": finding.severity.value,
                        "code": finding.code,
                        "message": finding.message,
                    }
                    for finding in findings_by_module.get(node.module_id, [])
                ],
                "reviews": [
                    {
                        "step_number": item.step_number,
                        "action_type": item.action_type,
                        "reward_given": item.reward_given,
                        "attributed_to": item.attributed_to,
                        "is_amendment": item.is_amendment,
                        "note": _parse_note_payload(item.note),
                        "created_at": item.created_at.isoformat(),
                    }
                    for item in annotations
                ],
            }
        )

    edge_payload = [
        {
            "source": edge.source_module_id,
            "target": edge.target_module_id,
            "edge_type": edge.edge_type.value,
            "weight": edge.weight,
            "import_line": edge.import_line,
            "connection_summary": edge.connection_summary,
        }
        for edge in sorted(edges, key=lambda item: (item.source_module_id, item.target_module_id, item.import_line))
    ]

    return {
        "report_schema_version": "1.0.0",
        "source_root": source_root,
        "episode_id": episode_id,
        "scope_modules": module_ids,
        "metrics": metrics.model_dump(),
        "nodes": node_payload,
        "edges": edge_payload,
        "rl_integrity": {
            "trajectory_reconstructable": True,
            "reward_causality_tracked": True,
            "deterministic_replay_notes": "easy/medium deterministic by construction; hard uses judge with temperature=0",
        },
    }


def _build_markdown_report(payload: dict[str, object]) -> str:
    metrics = payload["metrics"]
    lines: list[str] = []
    lines.append("# GraphReview Report")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append(f"- Source root: {payload['source_root']}")
    lines.append(f"- Episode id: {payload.get('episode_id') or 'all'}")
    lines.append(f"- Modules in scope: {len(payload['scope_modules'])}")
    lines.append(f"- Confidence score: {metrics['confidence_score']:.3f}")
    lines.append(f"- Precision: {metrics['precision']:.3f} | Recall: {metrics['recall']:.3f} | F1: {metrics['f1']:.3f}")
    lines.append(
        "- Security coverage: "
        f"{metrics['security_coverage']:.3f} | Dependency attribution validity: {metrics['dependency_attribution_validity']:.3f}"
    )
    lines.append("")

    lines.append("## Security Analysis")
    for node in payload["nodes"]:
        security_findings = node["security_findings"]
        if not security_findings:
            continue
        lines.append(f"### {node['module_id']}")
        for finding in security_findings:
            lines.append(
                "- "
                f"[{finding['severity'].upper()}] {finding['code']} line {finding['line']}: {finding['message']}"
            )
        lines.append("")

    lines.append("## Cascade Attribution Summary")
    for node in payload["nodes"]:
        attributions = [review for review in node["reviews"] if review.get("attributed_to")]
        if not attributions:
            continue
        lines.append(f"### {node['module_id']}")
        for item in attributions:
            lines.append(
                "- "
                f"step {item['step_number']} -> attributed_to={item['attributed_to']} "
                f"action={item['action_type']} reward={item['reward_given']:.2f}"
            )
        lines.append("")

    lines.append("## Module Reviews")
    for node in payload["nodes"]:
        lines.append(f"### {node['module_id']}")
        lines.append(f"- Status: {node['status']}")
        lines.append(f"- Summary: {node['summary']}")
        lines.append(f"- Shape: {node['module_shape']}")
        lines.append(f"- Findings: {len(node['linter_findings'])}")
        lines.append(f"- Reviews: {len(node['reviews'])}")
        if node["reviews"]:
            latest = node["reviews"][-1]
            lines.append(
                "- Latest review: "
                f"step {latest['step_number']} action={latest['action_type']} reward={latest['reward_given']:.2f}"
            )
        lines.append("")

    lines.append("## RL Integrity")
    lines.append("- Trajectory reconstructable from DB annotations and episode records.")
    lines.append("- Reward causality linked to each persisted action payload.")
    lines.append("- Easy/Medium deterministic replay expected; Hard constrained by temperature=0 judge policy.")
    lines.append("")

    return "\n".join(lines).strip() + "\n"


def generate_phase5_outputs(
    *,
    source_root: str | Path,
    db_path: str | Path | None = None,
    output_dir: str | Path = "outputs",
    episode_id: str | None = None,
    module_filter: list[str] | None = None,
    hops: int = 1,
    report_prefix: str = "graphreview",
) -> GeneratedArtifacts:
    source_root_text = str(Path(source_root).resolve())
    context = _load_context(source_root_text, db_path, module_filter, hops)

    with Session(context.store.engine) as session:
        nodes = list(
            session.exec(
                select(ModuleNode).where(
                    ModuleNode.source_root == context.store.config.source_root,
                    ModuleNode.module_id.in_(context.module_ids),
                )
            ).all()
        )

        edges = list(
            session.exec(
                select(ModuleEdge).where(
                    ModuleEdge.source_root == context.store.config.source_root,
                    ModuleEdge.source_module_id.in_(context.module_ids),
                    ModuleEdge.target_module_id.in_(context.module_ids),
                )
            ).all()
        )

        findings = list(
            session.exec(
                select(LinterFinding).where(
                    LinterFinding.source_root == context.store.config.source_root,
                    LinterFinding.module_id.in_(context.module_ids),
                )
            ).all()
        )

        annotation_query = select(ReviewAnnotation).where(
            ReviewAnnotation.source_root == context.store.config.source_root,
            ReviewAnnotation.module_id.in_(context.module_ids),
        )
        if episode_id:
            annotation_query = annotation_query.where(ReviewAnnotation.episode_id == episode_id)
        annotations = list(session.exec(annotation_query).all())

    findings_by_module: dict[str, list[LinterFinding]] = defaultdict(list)
    for finding in findings:
        findings_by_module[finding.module_id].append(finding)

    annotations_by_module: dict[str, list[ReviewAnnotation]] = defaultdict(list)
    for annotation in annotations:
        annotations_by_module[annotation.module_id].append(annotation)

    for module_id in list(annotations_by_module.keys()):
        annotations_by_module[module_id] = sorted(annotations_by_module[module_id], key=lambda item: item.step_number)

    metrics = _compute_metrics(
        module_ids=context.module_ids,
        graph_manager=context.graph_manager,
        findings_by_module=findings_by_module,
        annotations_by_module=annotations_by_module,
    )

    payload = _build_json_payload(
        source_root=source_root_text,
        module_ids=context.module_ids,
        nodes=nodes,
        edges=edges,
        findings_by_module=findings_by_module,
        annotations_by_module=annotations_by_module,
        metrics=metrics,
        episode_id=episode_id,
    )

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    json_path = output_root / f"{report_prefix}_report.json"
    markdown_path = output_root / f"{report_prefix}_report.md"
    html_path = output_root / f"{report_prefix}_graph.html"

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(_build_markdown_report(payload), encoding="utf-8")

    node_map = {node.module_id: node for node in nodes}
    graph = context.graph_manager.load_graph()
    centrality = context.graph_manager.centrality()

    html_nodes: list[dict[str, object]] = []
    for module_id in context.module_ids:
        node = node_map.get(module_id)
        if node is None:
            continue
        module_annotations = annotations_by_module.get(module_id, [])
        status = _derive_status(node, module_annotations)
        html_nodes.append(
            {
                "id": module_id,
                "label": module_id,
                "status": status,
                "size": 8.0 + (centrality.get(module_id, 0.0) * 42.0),
                "title": _build_node_title(
                    module=node,
                    findings=findings_by_module.get(module_id, []),
                    annotations=module_annotations,
                    status=status,
                    confidence_score=metrics.confidence_score,
                ),
            }
        )

    html_edges: list[dict[str, object]] = []
    for edge in edges:
        if edge.source_module_id not in graph or edge.target_module_id not in graph:
            continue
        html_edges.append(
            {
                "source": edge.source_module_id,
                "target": edge.target_module_id,
                "edge_type": edge.edge_type.value,
                "weight": edge.weight,
                "title": (
                    f"{edge.edge_type.value}: {edge.connection_summary or edge.import_line}"
                ),
            }
        )

    render_graph_html(nodes=html_nodes, edges=html_edges, output_path=html_path)

    return GeneratedArtifacts(
        markdown_path=str(markdown_path),
        json_path=str(json_path),
        html_path=str(html_path),
        module_count=len(html_nodes),
        edge_count=len(html_edges),
        annotation_count=len(annotations),
        confidence_score=metrics.confidence_score,
    )
