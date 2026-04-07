from pathlib import Path

from db.seed import seed_project
from parser.ast_parser import parse_python_file
from parser.chunker import chunk_module


def test_seed_project_uses_hash_cache(tmp_path: Path) -> None:
    db_path = tmp_path / "seed.db"
    target = Path("sample_project")

    first = seed_project(target, db_path=str(db_path), force=False)
    second = seed_project(target, db_path=str(db_path), force=False)

    assert first["loaded_from_cache"] is False
    assert second["loaded_from_cache"] is True
    assert first["node_count"] == second["node_count"]
    assert first["edge_count"] == second["edge_count"]


def test_chunker_splits_large_module_into_sub_nodes() -> None:
    root = Path("sample_project")
    parsed = parse_python_file(root / "huge_module.py", root)
    chunked = chunk_module(parsed, max_lines=300)

    assert chunked.parent.module_id == "huge_module"
    assert chunked.parent.code == ""
    assert len(chunked.chunks) >= 2
    assert all(chunk.parent_module_id == "huge_module" for chunk in chunked.chunks)
    assert any("::helper_alpha" in chunk.module_id for chunk in chunked.chunks)
