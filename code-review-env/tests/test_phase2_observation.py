from pathlib import Path

import pytest

from db.seed import seed_project
from env.observation import CodeObservation
from env.observation_builder import ObservationBuilder


def test_code_observation_strict_rejects_bad_types() -> None:
    with pytest.raises(Exception):
        CodeObservation(
            module_id="checkout",
            code="print('x')",
            ast_summary={},
            dependency_summaries=[],
            dependent_summaries=[],
            neighbor_reviews=[],
            task_description="review",
            available_actions=[],
            requested_context=None,
            token_usage={},
            total_tokens="100",  # type: ignore[arg-type]
            within_budget=True,
        )


def test_observation_builder_within_budget(tmp_path: Path) -> None:
    db_path = tmp_path / "phase2_obs.db"
    seed_project(Path("sample_project"), db_path=str(db_path), force=True)

    builder = ObservationBuilder(source_root="sample_project", db_path=db_path)
    observation = builder.build(
        module_id="checkout",
        task_description="Find logic and dependency issues",
    )

    assert observation.within_budget is True
    assert observation.total_tokens <= 2000
    assert observation.module_id == "checkout"


def test_request_context_is_bounded(tmp_path: Path) -> None:
    db_path = tmp_path / "phase2_context.db"
    seed_project(Path("sample_project"), db_path=str(db_path), force=True)

    builder = ObservationBuilder(source_root="sample_project", db_path=db_path)
    observation = builder.build(
        module_id="checkout",
        task_description="Investigate dependencies",
        context_request="auth",
    )

    assert observation.requested_context is not None
    assert observation.total_tokens <= 2000
