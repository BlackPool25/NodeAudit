from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import networkx as nx
from sqlmodel import Session, select

from db.schema import ModuleEdge, ModuleNode
from db.store import Store
from parser.ast_parser import parse_directory


@dataclass
class GraphLoadResult:
    graph: nx.DiGraph
    loaded_from_cache: bool


class DependencyGraph:
    def __init__(self, target_dir: str | Path, db_path: str | Path | None = None) -> None:
        self.target_dir = Path(target_dir).resolve()
        self.store = Store(source_root=str(self.target_dir), db_path=db_path)

    def load_or_build(self, force_reparse: bool = False) -> GraphLoadResult:
        if force_reparse or not self.store.has_nodes():
            parse_directory(self.target_dir, db_path=str(self.store.config.db_path))
            loaded_from_cache = False
        else:
            loaded_from_cache = True
        return GraphLoadResult(graph=self._build_graph(), loaded_from_cache=loaded_from_cache)

    def _build_graph(self) -> nx.DiGraph:
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
                ast_summary=node.ast_summary,
                review_status=node.review_status.value,
            )

        for edge in edges:
            graph.add_edge(
                edge.source_module_id,
                edge.target_module_id,
                import_line=edge.import_line,
                edge_type=edge.edge_type.value,
                weight=edge.weight,
            )

        return graph

    def traversal_order(self, graph: nx.DiGraph | None = None) -> list[str]:
        graph = graph or self._build_graph()
        if graph.number_of_nodes() == 0:
            return []

        if not nx.is_directed_acyclic_graph(graph):
            # Fall back to deterministic ordering if cyclic imports exist.
            return sorted(graph.nodes())

        centrality = nx.betweenness_centrality(graph)
        indegree = {node: graph.in_degree(node) for node in graph.nodes()}
        queue = [node for node, deg in indegree.items() if deg == 0]
        order: list[str] = []

        def rank(node: str) -> tuple[float, float, str]:
            return (
                float(graph.out_degree(node)),
                float(centrality.get(node, 0.0)),
                node,
            )

        while queue:
            queue.sort(key=rank)
            current = queue.pop(0)
            order.append(current)
            for successor in sorted(graph.successors(current)):
                indegree[successor] -= 1
                if indegree[successor] == 0:
                    queue.append(successor)

        return order


if __name__ == "__main__":
    manager = DependencyGraph(target_dir="sample_codebase")
    result = manager.load_or_build()
    print(
        f"Loaded graph with {result.graph.number_of_nodes()} nodes and "
        f"{result.graph.number_of_edges()} edges (cache={result.loaded_from_cache})"
    )
    print("Traversal order:", manager.traversal_order(result.graph))
