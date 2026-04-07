from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import networkx as nx

from db.seed import seed_project
from graph.graph_manager import GraphManager


@dataclass
class GraphLoadResult:
    graph: nx.DiGraph
    loaded_from_cache: bool


class DependencyGraph:
    def __init__(self, target_dir: str | Path, db_path: str | Path | None = None) -> None:
        self.target_dir = Path(target_dir).resolve()
        self.graph_manager = GraphManager(source_root=self.target_dir, db_path=db_path)

    def load_or_build(self, force_reparse: bool = False) -> GraphLoadResult:
        result = seed_project(
            self.target_dir,
            db_path=str(self.graph_manager.store.config.db_path),
            force=force_reparse,
        )
        loaded_from_cache = bool(result.get("loaded_from_cache", False))
        return GraphLoadResult(graph=self._build_graph(), loaded_from_cache=loaded_from_cache)

    def _build_graph(self) -> nx.DiGraph:
        return self.graph_manager.load_graph()

    def traversal_order(self, graph: nx.DiGraph | None = None) -> list[str]:
        if graph is None:
            return self.graph_manager.traversal_order()
        if graph.number_of_nodes() == 0:
            return []
        centrality = nx.betweenness_centrality(graph, normalized=True)
        return sorted(
            graph.nodes(),
            key=lambda node: (
                int(graph.out_degree(node)),
                float(centrality.get(node, 0.0)),
                str(node),
            ),
        )


if __name__ == "__main__":
    manager = DependencyGraph(target_dir="sample_codebase")
    result = manager.load_or_build()
    print(
        f"Loaded graph with {result.graph.number_of_nodes()} nodes and "
        f"{result.graph.number_of_edges()} edges (cache={result.loaded_from_cache})"
    )
    print("Traversal order:", manager.traversal_order(result.graph))
