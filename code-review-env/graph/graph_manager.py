from __future__ import annotations

from pathlib import Path
from typing import Literal

import networkx as nx
from sqlmodel import Session, select

from db.schema import ModuleEdge, ModuleNode
from db.store import Store


class GraphManager:
    """Load and query dependency graph state from SQLite."""

    def __init__(self, source_root: str | Path, db_path: str | Path | None = None) -> None:
        self.source_root = str(Path(source_root).resolve())
        self.store = Store(source_root=self.source_root, db_path=db_path)

    def load_graph(self) -> nx.DiGraph:
        graph = nx.DiGraph()
        with Session(self.store.engine) as session:
            nodes = list(
                session.exec(
                    select(ModuleNode).where(ModuleNode.source_root == self.store.config.source_root)
                ).all()
            )
            edges = list(
                session.exec(
                    select(ModuleEdge).where(ModuleEdge.source_root == self.store.config.source_root)
                ).all()
            )

        for node in nodes:
            graph.add_node(
                node.module_id,
                name=node.name,
                raw_code=node.raw_code,
                ast_summary=node.ast_summary,
                summary=node.summary or "",
                linter_flags=node.linter_flags,
                parent_module_id=node.parent_module_id,
                review_status=node.review_status.value,
                review_summary=node.review_summary or "",
                is_chunk=node.is_chunk,
            )

        for edge in edges:
            graph.add_edge(
                edge.source_module_id,
                edge.target_module_id,
                edge_type=edge.edge_type.value,
                import_line=edge.import_line,
                weight=edge.weight,
            )

        return graph

    def get_node(self, module_id: str) -> dict[str, object]:
        graph = self.load_graph()
        if module_id not in graph:
            raise ValueError(f"Unknown module_id: {module_id}")
        return dict(graph.nodes[module_id])

    def get_neighbors(
        self,
        module_id: str,
        direction: Literal["out", "in", "both"] = "both",
        limit: int | None = None,
    ) -> list[str]:
        graph = self.load_graph()
        if module_id not in graph:
            raise ValueError(f"Unknown module_id: {module_id}")

        if direction == "out":
            neighbors = set(graph.successors(module_id))
        elif direction == "in":
            neighbors = set(graph.predecessors(module_id))
        else:
            neighbors = set(graph.successors(module_id))
            neighbors.update(graph.predecessors(module_id))

        ordered = sorted(neighbors)
        if limit is None:
            return ordered
        return ordered[: max(limit, 0)]

    def centrality(self) -> dict[str, float]:
        graph = self.load_graph()
        if graph.number_of_nodes() == 0:
            return {}
        return nx.betweenness_centrality(graph, normalized=True)

    def traversal_order(self) -> list[str]:
        """
        Return a deterministic, leaf-first traversal where high-centrality nodes are later.
        """
        graph = self.load_graph()
        if graph.number_of_nodes() == 0:
            return []

        centrality = self.centrality()

        # For DAGs, reverse topological order visits leaves first.
        if nx.is_directed_acyclic_graph(graph):
            topo_reversed = list(reversed(list(nx.lexicographical_topological_sort(graph))))
            topo_rank = {node: idx for idx, node in enumerate(topo_reversed)}
            return sorted(
                graph.nodes(),
                key=lambda node: (
                    int(topo_rank.get(node, 0)),
                    float(centrality.get(node, 0.0)),
                    str(node),
                ),
            )

        # Stable fallback for cyclic graphs.
        return sorted(
            graph.nodes(),
            key=lambda node: (
                int(graph.out_degree(node)),
                float(centrality.get(node, 0.0)),
                str(node),
            ),
        )
