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
        self._graph_cache: nx.DiGraph | None = None
        self._centrality_cache: dict[str, float] | None = None

    def load_graph(self, refresh: bool = False) -> nx.DiGraph:
        if self._graph_cache is not None and not refresh:
            return self._graph_cache.copy()

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
                connection_summary=edge.connection_summary,
            )

        self._graph_cache = graph
        self._centrality_cache = None
        return graph.copy()

    def invalidate_cache(self) -> None:
        self._graph_cache = None
        self._centrality_cache = None

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

    def resolve_module_id(self, module_id: str) -> str:
        graph = self.load_graph()
        if module_id in graph:
            return module_id

        candidate = module_id.strip()
        variants = {
            candidate,
            candidate.replace("/", "."),
            candidate.replace("\\", "."),
        }
        if candidate.endswith(".py"):
            without_suffix = candidate[:-3]
            variants.add(without_suffix)
            variants.add(without_suffix.replace("/", "."))
            variants.add(without_suffix.replace("\\", "."))

        for variant in variants:
            if variant in graph:
                return variant

        lower_lookup = {str(node).lower(): str(node) for node in graph.nodes()}
        for variant in variants:
            resolved = lower_lookup.get(variant.lower())
            if resolved:
                return resolved

        raise ValueError(f"Unknown module_id: {module_id}")

    def centrality(self) -> dict[str, float]:
        if self._centrality_cache is not None:
            return dict(self._centrality_cache)

        graph = self.load_graph()
        if graph.number_of_nodes() == 0:
            self._centrality_cache = {}
            return {}

        self._centrality_cache = nx.betweenness_centrality(graph, normalized=True)
        return dict(self._centrality_cache)

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
