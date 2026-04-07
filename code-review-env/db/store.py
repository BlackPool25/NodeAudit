from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator, Optional

from pydantic import BaseModel
from sqlmodel import Session, delete, select

from db.migrations import get_default_db_path, get_engine, init_db
from db.schema import (
    EdgeType,
    EpisodeRecord,
    LinterFinding,
    ModuleEdge,
    ModuleNode,
    ReviewAnnotation,
    ReviewStatus,
    SeedMeta,
    Severity,
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
