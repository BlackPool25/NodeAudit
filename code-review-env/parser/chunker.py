from __future__ import annotations

import ast
from pydantic import BaseModel

from parser.ast_parser import ParsedModule


class ChunkNode(BaseModel):
    module_id: str
    name: str
    code: str
    parent_module_id: str | None = None
    is_chunk: bool = False
    start_line: int = 1
    end_line: int = 1


class ChunkResult(BaseModel):
    parent: ChunkNode
    chunks: list[ChunkNode]


def _slice_lines(source: str, start: int, end: int) -> str:
    lines = source.splitlines()
    start_idx = max(start - 1, 0)
    end_idx = min(end, len(lines))
    return "\n".join(lines[start_idx:end_idx]).strip()


def chunk_module(parsed: ParsedModule, max_lines: int = 300) -> ChunkResult:
    line_count = len(parsed.raw_code.splitlines())
    if line_count <= max_lines:
        parent = ChunkNode(
            module_id=parsed.module_id,
            name=parsed.module_id.split(".")[-1],
            code=parsed.raw_code,
            is_chunk=False,
            start_line=1,
            end_line=line_count,
        )
        return ChunkResult(parent=parent, chunks=[])

    try:
        tree = ast.parse(parsed.raw_code)
    except SyntaxError:
        parent = ChunkNode(
            module_id=parsed.module_id,
            name=parsed.module_id.split(".")[-1],
            code=parsed.raw_code,
            is_chunk=False,
            start_line=1,
            end_line=line_count,
        )
        return ChunkResult(parent=parent, chunks=[])

    chunks: list[ChunkNode] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start_line = int(getattr(node, "lineno", 1))
            end_line = int(getattr(node, "end_lineno", start_line))
            chunk_id = f"{parsed.module_id}::{node.name}"
            chunks.append(
                ChunkNode(
                    module_id=chunk_id,
                    name=node.name,
                    code=_slice_lines(parsed.raw_code, start_line, end_line),
                    parent_module_id=parsed.module_id,
                    is_chunk=True,
                    start_line=start_line,
                    end_line=end_line,
                )
            )

    if not chunks:
        chunks.append(
            ChunkNode(
                module_id=f"{parsed.module_id}::module_body",
                name="module_body",
                code=parsed.raw_code,
                parent_module_id=parsed.module_id,
                is_chunk=True,
                start_line=1,
                end_line=line_count,
            )
        )

    parent = ChunkNode(
        module_id=parsed.module_id,
        name=parsed.module_id.split(".")[-1],
        code="",
        is_chunk=False,
        start_line=1,
        end_line=line_count,
    )
    return ChunkResult(parent=parent, chunks=chunks)
