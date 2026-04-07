from pathlib import Path

from db.seed import seed_project
from graph.graph_manager import GraphManager


def test_graph_manager_traversal_is_deterministic(tmp_path: Path) -> None:
    db_path = tmp_path / "phase2_graph.db"
    seed_project(Path("sample_project"), db_path=str(db_path), force=True)

    manager = GraphManager(source_root="sample_project", db_path=db_path)
    first = manager.traversal_order()
    second = manager.traversal_order()

    assert first == second
    assert len(first) > 0


def test_graph_manager_neighbor_queries(tmp_path: Path) -> None:
    db_path = tmp_path / "phase2_graph_neighbors.db"
    seed_project(Path("sample_project"), db_path=str(db_path), force=True)

    manager = GraphManager(source_root="sample_project", db_path=db_path)
    graph = manager.load_graph()
    candidate = next(iter(graph.nodes()))

    both = manager.get_neighbors(candidate, direction="both")
    only_out = manager.get_neighbors(candidate, direction="out")
    only_in = manager.get_neighbors(candidate, direction="in")

    assert set(only_out).issubset(set(both))
    assert set(only_in).issubset(set(both))
