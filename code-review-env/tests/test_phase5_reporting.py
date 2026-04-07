from __future__ import annotations

from pathlib import Path

from db.seed import seed_project
from graders.review_runner import run_review
from visualizer.report_generator import generate_phase5_outputs


def test_phase5_generates_artifacts_for_filtered_modules(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GRAPHREVIEW_JUDGE_ENABLED", "false")

    source_root = Path("sample_project").resolve()
    db_path = tmp_path / "phase5.db"
    output_dir = tmp_path / "reports"

    seed_project(source_root, db_path=str(db_path), force=True)
    run_review(
        target=source_root,
        db_path=str(db_path),
        grader_level="hard",
        force_seed=False,
        skip_seed=True,
        show_progress=False,
        module_filter=["checkout"],
        filter_hops=1,
    )

    artifacts = generate_phase5_outputs(
        source_root=source_root,
        db_path=str(db_path),
        output_dir=output_dir,
        module_filter=["checkout"],
        hops=1,
        report_prefix="phase5_test",
    )

    assert Path(artifacts.markdown_path).exists()
    assert Path(artifacts.json_path).exists()
    assert Path(artifacts.html_path).exists()
    assert 0.0 <= artifacts.confidence_score <= 1.0

    json_text = Path(artifacts.json_path).read_text(encoding="utf-8")
    assert '"metrics"' in json_text
    assert '"security_coverage"' in json_text

    html_text = Path(artifacts.html_path).read_text(encoding="utf-8")
    assert "vis-network" in html_text
