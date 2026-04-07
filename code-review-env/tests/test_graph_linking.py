from __future__ import annotations

from pathlib import Path

from sqlmodel import Session, select

from db.schema import ModuleEdge
from db.seed import seed_project
from db.store import Store
from parser.ast_parser import parse_python_file
from parser.graph_builder import build_edges


def test_build_edges_resolves_from_import_relative_targets(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "a.py").write_text("from . import b\nfrom .c import x\n", encoding="utf-8")
    (pkg / "b.py").write_text("VALUE = 1\n", encoding="utf-8")
    (pkg / "c.py").write_text("x = 1\n", encoding="utf-8")

    parsed = [parse_python_file(path, tmp_path) for path in sorted(pkg.glob("*.py"))]
    module_ids = {item.module_id for item in parsed}

    edges = build_edges(parsed_modules=parsed, module_ids=module_ids, chunk_ids_by_parent={})
    pairs = {(edge.source_module_id, edge.target_module_id) for edge in edges}

    assert ("pkg.a", "pkg.b") in pairs
    assert ("pkg.a", "pkg.c") in pairs


def test_seed_project_creates_parent_chunk_connectivity_edges(tmp_path: Path) -> None:
    source_root = Path("sample_project").resolve()
    db_path = tmp_path / "graph_edges.db"

    seed_project(source_root, db_path=str(db_path), force=True)
    store = Store(source_root=str(source_root), db_path=str(db_path))

    with Session(store.engine) as session:
        contains_edges = list(
            session.exec(
                select(ModuleEdge).where(
                    ModuleEdge.source_root == store.config.source_root,
                    ModuleEdge.source_module_id == "huge_module",
                    ModuleEdge.import_line.startswith("contains:"),
                )
            ).all()
        )

    assert contains_edges
