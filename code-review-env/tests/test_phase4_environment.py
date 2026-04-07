from __future__ import annotations

from pathlib import Path

from db.seed import seed_project
from env.action import ActionType, ReviewAction
from env.environment import CodeReviewEnv


def _seed(tmp_path: Path) -> tuple[Path, Path]:
    source_root = Path("sample_project").resolve()
    db_path = tmp_path / "phase4_env.db"
    seed_project(source_root, db_path=str(db_path), force=True)
    return source_root, db_path


def test_phase4_reset_step_state_flow(tmp_path: Path) -> None:
    source_root, db_path = _seed(tmp_path)
    env = CodeReviewEnv(source_root=source_root, db_path=db_path)

    obs = env.reset(task_id="style_review")
    assert obs.module_id == "cart"

    step_1 = env.step(ReviewAction(action_type=ActionType.FLAG_STYLE, target_line=1))
    assert step_1.done is False

    step_2 = env.step(ReviewAction(action_type=ActionType.REQUEST_CHANGES))
    assert step_2.done is True

    snapshot = env.state()
    assert snapshot.episode.task_id == "style_review"
    assert snapshot.annotation_count >= 2


def test_module_override_policy_expands_neighbors_for_harder_tasks(tmp_path: Path) -> None:
    source_root, db_path = _seed(tmp_path)
    env = CodeReviewEnv(source_root=source_root, db_path=db_path)

    obs = env.reset(task_id="logic_review", module_override=["checkout"])
    assert obs.module_id in {"checkout", "auth", "payments", "cart"}


def test_reset_episode_annotations_only_current_episode(tmp_path: Path) -> None:
    source_root, db_path = _seed(tmp_path)
    env = CodeReviewEnv(source_root=source_root, db_path=db_path)

    env.reset(task_id="style_review")
    env.step(ReviewAction(action_type=ActionType.FLAG_STYLE, target_line=1))
    before = env.state().annotation_count
    assert before >= 1

    cleared_modules = env.reset_episode_annotations()
    after = env.state().annotation_count

    assert cleared_modules >= 1
    assert after == 0
