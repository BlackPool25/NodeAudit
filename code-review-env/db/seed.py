from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from db.store import Store
from parser.ast_parser import parse_python_file
from parser.chunker import chunk_module
from parser.graph_builder import build_edges
from parser.linter import run_linters
from parser.summarizer import summarize_module
from llm.edge_summarizer import EdgeSummarizer, EdgeSummaryInput


_SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
}


def _progress_enabled() -> bool:
    return os.getenv("GRAPHREVIEW_PROGRESS", "true").lower() == "true"


def _seed_workers() -> int:
    default_workers = min(4, os.cpu_count() or 1)
    configured = int(os.getenv("GRAPHREVIEW_SEED_WORKERS", str(default_workers)))
    return max(1, configured)


def _iter_python_files(target_dir: Path) -> list[Path]:
    max_files = int(os.getenv("GRAPHREVIEW_MAX_FILES", "5000"))
    py_files: list[Path] = []
    for path in sorted(target_dir.rglob("*.py")):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        py_files.append(path)
        if len(py_files) >= max_files:
            break
    return py_files


def _codebase_hash(target_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in _iter_python_files(target_dir):
        rel = path.relative_to(target_dir).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _seed_meta_key(source_root: str) -> str:
    return f"seeded:{source_root}"


def _analyze_file(path: Path, target_dir: Path) -> tuple[Path, object, list[object], str, object]:
    parsed = parse_python_file(path, target_dir)
    issues = run_linters(path)
    summary = summarize_module(parsed, issues)
    chunk_result = chunk_module(parsed, max_lines=300)
    return path, parsed, issues, summary, chunk_result


def seed_project(target_dir: Path, db_path: str | None = None, force: bool = False) -> dict[str, object]:
    target_dir = target_dir.resolve()
    store = Store(source_root=str(target_dir), db_path=db_path)

    current_hash = _codebase_hash(target_dir)
    meta_key = _seed_meta_key(str(target_dir))
    existing_raw = store.get_meta(meta_key)
    existing = json.loads(existing_raw) if existing_raw else {}

    if (
        not force
        and store.has_nodes()
        and existing.get("codebase_hash") == current_hash
        and existing.get("seeded") is True
    ):
        return {
            "seeded": True,
            "loaded_from_cache": True,
            "codebase_hash": current_hash,
            "node_count": int(existing.get("node_count", 0)),
            "edge_count": int(existing.get("edge_count", 0)),
        }

    store.clear_source_graph()

    py_files = _iter_python_files(target_dir)
    total_files = len(py_files)
    analysis_by_path: dict[Path, tuple[object, list[object], str, object]] = {}
    workers = _seed_workers()

    if _progress_enabled():
        print(f"[SEED] Analyzing {total_files} files with {workers} workers...", flush=True)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_analyze_file, path, target_dir) for path in py_files]
        for idx, future in enumerate(as_completed(futures), start=1):
            path, parsed, issues, summary, chunk_result = future.result()
            analysis_by_path[path] = (parsed, issues, summary, chunk_result)
            if _progress_enabled():
                rel = path.relative_to(target_dir).as_posix()
                print(f"[SEED] analyzed {idx}/{total_files}: {rel}", flush=True)

    parsed_modules = [analysis_by_path[path][0] for path in py_files]
    module_ids = {parsed.module_id for parsed in parsed_modules}

    chunk_ids_by_parent: dict[str, set[str]] = {}

    for idx, path in enumerate(py_files, start=1):
        parsed, issues, summary, chunk_result = analysis_by_path[path]
        linter_flags = json.dumps([issue.model_dump() for issue in issues])
        parent = chunk_result.parent

        if _progress_enabled():
            rel = path.relative_to(target_dir).as_posix()
            print(f"[SEED] storing {idx}/{total_files}: {rel}", flush=True)

        store.upsert_node(
            module_id=parent.module_id,
            name=parent.name,
            raw_code=parent.code,
            ast_summary=summary,
            summary=summary,
            linter_flags=linter_flags,
            dependency_reason="Imports and symbol usage captured from AST",
            parent_module_id=parent.parent_module_id,
            is_chunk=parent.is_chunk,
        )

        if chunk_result.chunks:
            chunk_ids_by_parent[parent.module_id] = {chunk.module_id for chunk in chunk_result.chunks}

        for chunk in chunk_result.chunks:
            chunk_summary = f"Chunk {chunk.name} lines {chunk.start_line}-{chunk.end_line}"
            store.upsert_node(
                module_id=chunk.module_id,
                name=chunk.name,
                raw_code=chunk.code,
                ast_summary=chunk_summary,
                summary=chunk_summary,
                linter_flags="[]",
                dependency_reason="Top-level class/function chunk",
                parent_module_id=chunk.parent_module_id,
                is_chunk=chunk.is_chunk,
            )

        store.replace_findings_for_module(parsed.module_id, [issue.model_dump() for issue in issues])

    edges = build_edges(parsed_modules, module_ids, chunk_ids_by_parent)
    edge_summarizer = EdgeSummarizer()
    for edge in edges:
        connection_summary = edge_summarizer.summarize(
            EdgeSummaryInput(
                source_module_id=edge.source_module_id,
                target_module_id=edge.target_module_id,
                edge_type=edge.edge_type.value,
                import_line=edge.import_line,
                scope=edge.scope,
            )
        )
        store.upsert_edge(
            source_module_id=edge.source_module_id,
            target_module_id=edge.target_module_id,
            edge_type=edge.edge_type,
            import_line=edge.import_line,
            weight=edge.weight,
            connection_summary=connection_summary,
        )

    snapshot = store.get_full_graph()
    meta_payload = {
        "seeded": True,
        "seeded_at": datetime.now(UTC).isoformat(),
        "codebase_hash": current_hash,
        "node_count": len(snapshot.nodes),
        "edge_count": len(snapshot.edges),
    }
    store.set_meta(meta_key, json.dumps(meta_payload))

    return {
        "seeded": True,
        "loaded_from_cache": False,
        "codebase_hash": current_hash,
        "node_count": len(snapshot.nodes),
        "edge_count": len(snapshot.edges),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed graph database from Python project")
    parser.add_argument("target", help="Path to target codebase")
    parser.add_argument("--db-path", default=None, help="Path to SQLite database")
    parser.add_argument("--force", action="store_true", help="Force re-parse even if seeded")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    result = seed_project(Path(args.target), db_path=args.db_path, force=args.force)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
