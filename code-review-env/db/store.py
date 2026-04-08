from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator, Optional
import json

from pydantic import BaseModel
from sqlmodel import Session, delete, select

from db.migrations import get_default_db_path, get_engine, init_db
from db.schema import (
    AnalyzerFinding,
    AnalyzerRun,
    AnalyzerStatus,
    EdgeType,
    EpisodeRecord,
    LinterFinding,
    ModuleEdge,
    ModuleNode,
    ReviewAnnotation,
    ReviewStatus,
    SeedMeta,
    Severity,
    TrainingRun,
)


@dataclass
class DBConfig:
    source_root: str
    db_path: Path


class NeighborSummary(BaseModel):
    module_id: str
    ast_summary: str
    review_summary: Optional[str]


class NodeWithNeighbors(BaseModel):
    module_id: str
    ast_summary: str
    review_status: ReviewStatus
    neighbors: list[NeighborSummary]


class GraphNodeRecord(BaseModel):
    module_id: str
    ast_summary: str
    review_status: ReviewStatus


class GraphEdgeRecord(BaseModel):
    source_module_id: str
    target_module_id: str
    weight: float
    import_line: str
    connection_summary: str


class GraphSnapshot(BaseModel):
    nodes: list[GraphNodeRecord]
    edges: list[GraphEdgeRecord]


class Store:
    def __init__(self, source_root: str, db_path: str | Path | None = None) -> None:
        self.config = DBConfig(
            source_root=str(Path(source_root).resolve()),
            db_path=Path(db_path) if db_path else get_default_db_path(),
        )
        db_echo = os.getenv("GRAPHREVIEW_DB_ECHO", "false").lower() == "true"
        init_db(db_path=self.config.db_path, echo=db_echo)
        self.engine = get_engine(self.config.db_path, echo=db_echo)

    def session(self) -> Iterator[Session]:
        with Session(self.engine) as session:
            yield session

    def upsert_node(
        self,
        module_id: str,
        raw_code: str,
        ast_summary: str,
        dependency_reason: str,
        name: str | None = None,
        summary: str | None = None,
        linter_flags: str = "[]",
        parent_module_id: str | None = None,
        is_chunk: bool = False,
    ) -> ModuleNode:
        with Session(self.engine) as session:
            existing = session.exec(
                select(ModuleNode).where(
                    ModuleNode.source_root == self.config.source_root,
                    ModuleNode.module_id == module_id,
                )
            ).first()
            if existing:
                existing.name = name or existing.name
                existing.raw_code = raw_code
                existing.ast_summary = ast_summary
                existing.summary = summary or existing.summary
                existing.linter_flags = linter_flags
                existing.parent_module_id = parent_module_id
                existing.is_chunk = is_chunk
                existing.dependency_reason = dependency_reason
                existing.updated_at = datetime.now(UTC)
                session.add(existing)
                session.commit()
                session.refresh(existing)
                return existing

            node = ModuleNode(
                source_root=self.config.source_root,
                module_id=module_id,
                name=name,
                raw_code=raw_code,
                ast_summary=ast_summary,
                summary=summary,
                linter_flags=linter_flags,
                parent_module_id=parent_module_id,
                is_chunk=is_chunk,
                dependency_reason=dependency_reason,
            )
            session.add(node)
            session.commit()
            session.refresh(node)
            return node

    def upsert_edge(
        self,
        source_module_id: str,
        target_module_id: str,
        edge_type: EdgeType,
        import_line: str,
        weight: float,
        connection_summary: str = "",
    ) -> ModuleEdge:
        with Session(self.engine) as session:
            existing = session.exec(
                select(ModuleEdge).where(
                    ModuleEdge.source_root == self.config.source_root,
                    ModuleEdge.source_module_id == source_module_id,
                    ModuleEdge.target_module_id == target_module_id,
                    ModuleEdge.import_line == import_line,
                )
            ).first()
            if existing:
                existing.edge_type = edge_type
                existing.weight = weight
                existing.connection_summary = connection_summary or existing.connection_summary
                session.add(existing)
                session.commit()
                session.refresh(existing)
                return existing

            edge = ModuleEdge(
                source_root=self.config.source_root,
                source_module_id=source_module_id,
                target_module_id=target_module_id,
                edge_type=edge_type,
                import_line=import_line,
                weight=weight,
                connection_summary=connection_summary,
            )
            session.add(edge)
            session.commit()
            session.refresh(edge)
            return edge

    def replace_findings_for_module(self, module_id: str, findings: list[dict[str, str | int]]) -> None:
        with Session(self.engine) as session:
            session.exec(
                delete(LinterFinding).where(
                    LinterFinding.source_root == self.config.source_root,
                    LinterFinding.module_id == module_id,
                )
            )
            for finding in findings:
                session.add(
                    LinterFinding(
                        source_root=self.config.source_root,
                        module_id=module_id,
                        tool=str(finding["tool"]),
                        line=int(finding["line"]),
                        severity=Severity(str(finding["severity"])),
                        code=str(finding["code"]),
                        message=str(finding["message"]),
                    )
                )
            session.commit()

    def append_findings_for_module(self, module_id: str, findings: list[dict[str, str | int]]) -> None:
        with Session(self.engine) as session:
            for finding in findings:
                session.add(
                    LinterFinding(
                        source_root=self.config.source_root,
                        module_id=module_id,
                        tool=str(finding["tool"]),
                        line=int(finding["line"]),
                        severity=Severity(str(finding["severity"])),
                        code=str(finding["code"]),
                        message=str(finding["message"]),
                    )
                )
            session.commit()

    def clear_analyzer_data(self) -> None:
        with Session(self.engine) as session:
            session.exec(
                delete(AnalyzerFinding).where(
                    AnalyzerFinding.source_root == self.config.source_root
                )
            )
            session.exec(
                delete(AnalyzerRun).where(
                    AnalyzerRun.source_root == self.config.source_root
                )
            )
            session.commit()

    def create_analyzer_run(
        self,
        *,
        analyzer: str,
        analyzer_version: str,
        status: str,
        findings_count: int,
        command: str,
        command_hash: str,
        error_message: str | None,
    ) -> AnalyzerRun:
        with Session(self.engine) as session:
            run = AnalyzerRun(
                source_root=self.config.source_root,
                analyzer=analyzer,
                analyzer_version=analyzer_version,
                status=AnalyzerStatus(status),
                findings_count=findings_count,
                command=command,
                command_hash=command_hash,
                error_message=error_message,
            )
            session.add(run)
            session.commit()
            session.refresh(run)
            return run

    def add_analyzer_findings(
        self,
        analyzer_run_id: int,
        analyzer: str,
        findings: list[dict[str, str | int]],
    ) -> None:
        with Session(self.engine) as session:
            for item in findings:
                session.add(
                    AnalyzerFinding(
                        source_root=self.config.source_root,
                        analyzer_run_id=analyzer_run_id,
                        analyzer=analyzer,
                        module_id=str(item["module_id"]),
                        line=int(item.get("line", 1)),
                        severity=Severity(str(item.get("severity", "medium"))),
                        rule_id=str(item.get("rule_id", analyzer)),
                        message=str(item.get("message", "")),
                        evidence=str(item.get("evidence", "")),
                    )
                )
            session.commit()

    def get_analyzer_findings(self, module_id: str | None = None) -> list[AnalyzerFinding]:
        with Session(self.engine) as session:
            query = select(AnalyzerFinding).where(
                AnalyzerFinding.source_root == self.config.source_root
            )
            if module_id is not None:
                query = query.where(AnalyzerFinding.module_id == module_id)
            return list(session.exec(query).all())

    def get_analyzer_findings_for_module(
        self,
        module_id: str,
        analyzers: set[str] | None = None,
    ) -> list[AnalyzerFinding]:
        with Session(self.engine) as session:
            query = select(AnalyzerFinding).where(
                AnalyzerFinding.source_root == self.config.source_root,
                AnalyzerFinding.module_id == module_id,
            )
            if analyzers:
                query = query.where(AnalyzerFinding.analyzer.in_(sorted(analyzers)))
            findings = list(session.exec(query).all())
        return sorted(findings, key=lambda item: (item.line, item.analyzer, item.rule_id, item.id or 0))

    def create_training_run(
        self,
        *,
        run_id: str,
        model_name: str,
        model_sha256: str,
        deterministic_findings: int,
        agent_findings: int,
        true_positives: int,
        false_positives: int,
        false_negatives: int,
        precision: float,
        recall: float,
        passed_non_regression: bool,
        output_path: str,
        run_config_json: str,
    ) -> TrainingRun:
        with Session(self.engine) as session:
            record = TrainingRun(
                source_root=self.config.source_root,
                run_id=run_id,
                model_name=model_name,
                model_sha256=model_sha256,
                deterministic_findings=deterministic_findings,
                agent_findings=agent_findings,
                true_positives=true_positives,
                false_positives=false_positives,
                false_negatives=false_negatives,
                precision=precision,
                recall=recall,
                passed_non_regression=passed_non_regression,
                output_path=output_path,
                run_config_json=run_config_json,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return record

    def list_training_runs(self, limit: int = 50) -> list[TrainingRun]:
        bounded_limit = max(1, min(limit, 500))
        with Session(self.engine) as session:
            query = (
                select(TrainingRun)
                .where(TrainingRun.source_root == self.config.source_root)
                .order_by(TrainingRun.created_at.desc())
                .limit(bounded_limit)
            )
            return list(session.exec(query).all())

    def get_training_run(self, run_id: str) -> TrainingRun | None:
        with Session(self.engine) as session:
            query = select(TrainingRun).where(
                TrainingRun.source_root == self.config.source_root,
                TrainingRun.run_id == run_id,
            )
            return session.exec(query).first()

    def get_findings(self, module_id: str) -> list[LinterFinding]:
        with Session(self.engine) as session:
            return list(
                session.exec(
                    select(LinterFinding).where(
                        LinterFinding.source_root == self.config.source_root,
                        LinterFinding.module_id == module_id,
                    )
                ).all()
            )

    def get_node(self, module_id: str) -> Optional[ModuleNode]:
        with Session(self.engine) as session:
            return session.exec(
                select(ModuleNode).where(
                    ModuleNode.source_root == self.config.source_root,
                    ModuleNode.module_id == module_id,
                )
            ).first()

    def get_node_with_neighbors(self, module_id: str) -> Optional[NodeWithNeighbors]:
        with Session(self.engine) as session:
            node = session.exec(
                select(ModuleNode).where(
                    ModuleNode.source_root == self.config.source_root,
                    ModuleNode.module_id == module_id,
                )
            ).first()
            if not node:
                return None

            outgoing = list(
                session.exec(
                    select(ModuleEdge).where(
                        ModuleEdge.source_root == self.config.source_root,
                        ModuleEdge.source_module_id == module_id,
                    )
                ).all()
            )
            incoming = list(
                session.exec(
                    select(ModuleEdge).where(
                        ModuleEdge.source_root == self.config.source_root,
                        ModuleEdge.target_module_id == module_id,
                    )
                ).all()
            )

            neighbor_ids = {edge.target_module_id for edge in outgoing}
            neighbor_ids.update(edge.source_module_id for edge in incoming)

            neighbors: list[NeighborSummary] = []
            for neighbor_id in sorted(neighbor_ids):
                neighbor = session.exec(
                    select(ModuleNode).where(
                        ModuleNode.source_root == self.config.source_root,
                        ModuleNode.module_id == neighbor_id,
                    )
                ).first()
                if neighbor:
                    neighbors.append(
                        NeighborSummary(
                            module_id=neighbor.module_id,
                            ast_summary=neighbor.ast_summary,
                            review_summary=neighbor.review_summary,
                        )
                    )

            return NodeWithNeighbors(
                module_id=node.module_id,
                ast_summary=node.ast_summary,
                review_status=node.review_status,
                neighbors=neighbors,
            )

    def update_annotation(
        self,
        module_id: str,
        episode_id: str,
        step_number: int,
        action_type: str,
        note: str,
        task_id: str | None = None,
        reward_given: float = 0.0,
        attributed_to: str | None = None,
        is_amendment: bool = False,
        review_summary: str | None = None,
        review_status: ReviewStatus | None = None,
    ) -> None:
        with Session(self.engine) as session:
            node = session.exec(
                select(ModuleNode).where(
                    ModuleNode.source_root == self.config.source_root,
                    ModuleNode.module_id == module_id,
                )
            ).first()
            if not node:
                raise ValueError(f"Unknown module: {module_id}")

            node.review_annotation = note
            if review_summary is not None:
                node.review_summary = review_summary
            if review_status is not None:
                node.review_status = review_status
            node.updated_at = datetime.now(UTC)

            session.add(node)
            session.add(
                ReviewAnnotation(
                    source_root=self.config.source_root,
                    module_id=module_id,
                    episode_id=episode_id,
                    task_id=task_id,
                    step_number=step_number,
                    action_type=action_type,
                    note=note,
                    reward_given=reward_given,
                    attributed_to=attributed_to,
                    is_amendment=is_amendment,
                )
            )
            session.commit()

    def get_full_graph(self) -> GraphSnapshot:
        with Session(self.engine) as session:
            nodes = list(
                session.exec(
                    select(ModuleNode).where(ModuleNode.source_root == self.config.source_root)
                ).all()
            )
            edges = list(
                session.exec(
                    select(ModuleEdge).where(ModuleEdge.source_root == self.config.source_root)
                ).all()
            )

        return GraphSnapshot(
            nodes=[
                GraphNodeRecord(
                    module_id=node.module_id,
                    ast_summary=node.ast_summary,
                    review_status=node.review_status,
                )
                for node in nodes
            ],
            edges=[
                GraphEdgeRecord(
                    source_module_id=edge.source_module_id,
                    target_module_id=edge.target_module_id,
                    weight=edge.weight,
                    import_line=edge.import_line,
                    connection_summary=edge.connection_summary,
                )
                for edge in edges
            ],
        )

    def create_episode_record(self, episode_id: str, task_id: str, module_id: str) -> EpisodeRecord:
        with Session(self.engine) as session:
            record = EpisodeRecord(
                source_root=self.config.source_root,
                episode_id=episode_id,
                task_id=task_id,
                module_id=module_id,
                total_steps=0,
                cumulative_reward=0.0,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return record

    def update_episode_record(
        self,
        episode_id: str,
        module_id: str,
        total_steps: int,
        cumulative_reward: float,
    ) -> None:
        with Session(self.engine) as session:
            record = session.exec(
                select(EpisodeRecord).where(
                    EpisodeRecord.source_root == self.config.source_root,
                    EpisodeRecord.episode_id == episode_id,
                    EpisodeRecord.module_id == module_id,
                )
            ).first()
            if not record:
                return
            record.total_steps = total_steps
            record.cumulative_reward = cumulative_reward
            session.add(record)
            session.commit()

    def get_episode_records(self, episode_id: str) -> list[EpisodeRecord]:
        with Session(self.engine) as session:
            return list(
                session.exec(
                    select(EpisodeRecord).where(
                        EpisodeRecord.source_root == self.config.source_root,
                        EpisodeRecord.episode_id == episode_id,
                    )
                ).all()
            )

    def get_review_annotations(self, episode_id: str | None = None) -> list[ReviewAnnotation]:
        with Session(self.engine) as session:
            query = select(ReviewAnnotation).where(
                ReviewAnnotation.source_root == self.config.source_root
            )
            if episode_id is not None:
                query = query.where(ReviewAnnotation.episode_id == episode_id)
            return list(session.exec(query).all())

    def clear_annotations_for_episode(self, episode_id: str) -> int:
        with Session(self.engine) as session:
            touched = list(
                session.exec(
                    select(ReviewAnnotation.module_id).where(
                        ReviewAnnotation.source_root == self.config.source_root,
                        ReviewAnnotation.episode_id == episode_id,
                    )
                ).all()
            )
            session.exec(
                delete(ReviewAnnotation).where(
                    ReviewAnnotation.source_root == self.config.source_root,
                    ReviewAnnotation.episode_id == episode_id,
                )
            )

            unique_touched = sorted(set(str(module_id) for module_id in touched))
            if unique_touched:
                nodes = list(
                    session.exec(
                        select(ModuleNode).where(
                            ModuleNode.source_root == self.config.source_root,
                            ModuleNode.module_id.in_(unique_touched),
                        )
                    ).all()
                )
                for node in nodes:
                    node.review_annotation = None
                    node.review_summary = None
                    node.review_status = ReviewStatus.PENDING
                    node.updated_at = datetime.now(UTC)
                    session.add(node)

            session.commit()
            return len(unique_touched)

    def has_nodes(self) -> bool:
        with Session(self.engine) as session:
            first_node = session.exec(
                select(ModuleNode.id).where(ModuleNode.source_root == self.config.source_root)
            ).first()
            return first_node is not None

    def get_meta(self, key: str) -> Optional[str]:
        with Session(self.engine) as session:
            record = session.get(SeedMeta, key)
            return record.value if record else None

    def set_meta(self, key: str, value: str) -> None:
        with Session(self.engine) as session:
            record = session.get(SeedMeta, key)
            if record:
                record.value = value
                session.add(record)
            else:
                session.add(SeedMeta(key=key, value=value))
            session.commit()

    def clear_source_graph(self) -> None:
        with Session(self.engine) as session:
            session.exec(
                delete(ReviewAnnotation).where(
                    ReviewAnnotation.source_root == self.config.source_root
                )
            )
            session.exec(
                delete(LinterFinding).where(
                    LinterFinding.source_root == self.config.source_root
                )
            )
            session.exec(
                delete(ModuleEdge).where(
                    ModuleEdge.source_root == self.config.source_root
                )
            )
            session.exec(
                delete(ModuleNode).where(
                    ModuleNode.source_root == self.config.source_root
                )
            )
            session.exec(
                delete(AnalyzerFinding).where(
                    AnalyzerFinding.source_root == self.config.source_root
                )
            )
            session.exec(
                delete(AnalyzerRun).where(
                    AnalyzerRun.source_root == self.config.source_root
                )
            )
            session.exec(
                delete(TrainingRun).where(
                    TrainingRun.source_root == self.config.source_root
                )
            )
            session.commit()

    def clear_annotations(self) -> None:
        with Session(self.engine) as session:
            nodes = list(
                session.exec(
                    select(ModuleNode).where(ModuleNode.source_root == self.config.source_root)
                ).all()
            )
            for node in nodes:
                node.review_annotation = None
                node.review_summary = None
                node.review_status = ReviewStatus.PENDING
                node.updated_at = datetime.now(UTC)
                session.add(node)
            session.commit()

    def finding_previously_caught(self, module_id: str, finding_id: int, exclude_task_prefix: str = "hard") -> bool:
        with Session(self.engine) as session:
            annotations = list(
                session.exec(
                    select(ReviewAnnotation).where(
                        ReviewAnnotation.source_root == self.config.source_root,
                        ReviewAnnotation.module_id == module_id,
                    )
                ).all()
            )

        for annotation in annotations:
            task_id = annotation.task_id or ""
            if exclude_task_prefix and task_id.startswith(exclude_task_prefix):
                continue
            try:
                payload = json.loads(annotation.note)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and int(payload.get("matched_finding_id") or -1) == finding_id:
                return True
        return False


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Store query helper")
    parser.add_argument("--root", default="sample_codebase", help="Source root directory")
    parser.add_argument("--db-path", default=None, help="SQLite path")
    parser.add_argument("--module", required=True, help="Module id (without .py)")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    store = Store(source_root=args.root, db_path=args.db_path)
    result = store.get_node_with_neighbors(args.module)
    if result is None:
        print(f"Module '{args.module}' not found")
        return
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
