from pathlib import Path

from env.graph import DependencyGraph


def test_graph_builds_from_sample_codebase(tmp_path: Path) -> None:
    db_path = tmp_path / "graph.db"
    graph_mgr = DependencyGraph(target_dir="sample_codebase", db_path=db_path)
    result = graph_mgr.load_or_build(force_reparse=True)

    assert result.graph.number_of_nodes() >= 5
    assert result.loaded_from_cache is False


def test_graph_second_load_uses_cache(tmp_path: Path) -> None:
    db_path = tmp_path / "graph.db"
    graph_mgr = DependencyGraph(target_dir="sample_codebase", db_path=db_path)
    graph_mgr.load_or_build(force_reparse=True)
    second = graph_mgr.load_or_build(force_reparse=False)

    assert second.loaded_from_cache is True
