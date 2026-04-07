from __future__ import annotations

import ast
import networkx as nx
from pydantic import BaseModel

from db.schema import EdgeType
from parser.ast_parser import ParsedModule


class EdgeRecord(BaseModel):
    source_module_id: str
    target_module_id: str
    edge_type: EdgeType
    import_line: str
    scope: str
    weight: float


def _build_intra_file_edges(parsed: ParsedModule, available_chunk_ids: set[str]) -> list[EdgeRecord]:
    try:
        tree = ast.parse(parsed.raw_code)
    except SyntaxError:
        return []

    function_names = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    call_edges: list[EdgeRecord] = []

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        source_id = f"{parsed.module_id}::{node.name}"
        if source_id not in available_chunk_ids:
            continue
        for inner in ast.walk(node):
            if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name):
                called = inner.func.id
                if called in function_names:
                    target_id = f"{parsed.module_id}::{called}"
                    if target_id in available_chunk_ids and target_id != source_id:
                        call_edges.append(
                            EdgeRecord(
                                source_module_id=source_id,
                                target_module_id=target_id,
                                edge_type=EdgeType.INTRA_FILE,
                                import_line=f"call:{called}",
                                scope="function_level",
                                weight=0.5,
                            )
                        )

    dedup: dict[tuple[str, str, str], EdgeRecord] = {}
    for edge in call_edges:
        key = (edge.source_module_id, edge.target_module_id, edge.import_line)
        dedup[key] = edge
    return list(dedup.values())


def build_edges(
    parsed_modules: list[ParsedModule],
    module_ids: set[str],
    chunk_ids_by_parent: dict[str, set[str]],
) -> list[EdgeRecord]:
    edges: list[EdgeRecord] = []

    for parsed in parsed_modules:
        source_module_id = parsed.module_id
        for imp in parsed.imports:
            if imp.target_module and imp.target_module in module_ids:
                edge_type = (
                    EdgeType.EXPLICIT_IMPORT
                    if imp.scope == "module_level"
                    else EdgeType.IMPLICIT_DEPENDENCY
                )
                edges.append(
                    EdgeRecord(
                        source_module_id=source_module_id,
                        target_module_id=imp.target_module,
                        edge_type=edge_type,
                        import_line=imp.import_line,
                        scope=imp.scope,
                        weight=imp.weight,
                    )
                )

        available_chunk_ids = chunk_ids_by_parent.get(parsed.module_id, set())
        for chunk_id in sorted(available_chunk_ids):
            edges.append(
                EdgeRecord(
                    source_module_id=parsed.module_id,
                    target_module_id=chunk_id,
                    edge_type=EdgeType.INTRA_FILE,
                    import_line=f"contains:{chunk_id.split('::')[-1]}",
                    scope="module_level",
                    weight=0.2,
                )
            )
        edges.extend(_build_intra_file_edges(parsed, available_chunk_ids))

    graph = nx.DiGraph()
    for edge in edges:
        graph.add_edge(edge.source_module_id, edge.target_module_id)

    for source_module_id, target_module_id in list(graph.edges()):
        if graph.has_edge(target_module_id, source_module_id):
            edges.append(
                EdgeRecord(
                    source_module_id=source_module_id,
                    target_module_id=target_module_id,
                    edge_type=EdgeType.CIRCULAR,
                    import_line="cycle_detected",
                    scope="module_level",
                    weight=1.0,
                )
            )

    dedup: dict[tuple[str, str, str], EdgeRecord] = {}
    for edge in edges:
        key = (edge.source_module_id, edge.target_module_id, edge.import_line)
        dedup[key] = edge
    return list(dedup.values())
