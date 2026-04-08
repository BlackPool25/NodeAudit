from __future__ import annotations

from pathlib import Path

from db.seed import seed_project
from db.store import Store
from env.action import ActionType, ReviewAction
from env.reward import RewardReason, normalize_reward
from graph.graph_manager import GraphManager
from graders.base_grader import EpisodeState
from graders.easy_grader import EasyGrader
from graders.hard_grader import HardGrader
from graders.medium_grader import MediumGrader


def _write_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    (project / "a.py").write_text(
        "import b\n\n"
        "def do_work(value):\n"
        "    item = value + 1\n"
        "    return item\n",
        encoding="utf-8",
    )
    (project / "b.py").write_text(
        "import os\n\n"
        "def helper():\n"
        "    return 1\n",
        encoding="utf-8",
    )
    return project


def test_action_validation_and_reward_normalization() -> None:
    action = ReviewAction(action_type=ActionType.REQUEST_CONTEXT, context_request="auth")
    assert action.context_request == "auth"
    assert normalize_reward(-1.0) == 0.0
    assert normalize_reward(1.0) == 1.0


def test_easy_grader_is_deterministic_for_ten_runs(tmp_path: Path) -> None:
    project = _write_project(tmp_path)
    db_path = tmp_path / "deterministic.db"
    seed_project(project, db_path=str(db_path), force=True)

    store = Store(source_root=str(project), db_path=str(db_path))
    grader = EasyGrader(store)
    findings = store.get_findings("b")
    assert findings
    finding = findings[0]

    action = ReviewAction(action_type=ActionType.FLAG_BUG, target_line=max(1, finding.line))
    totals: list[float] = []
    for run_idx in range(10):
        summary = grader.grade_episode(
            module_id="b",
            task_id="easy_review",
            episode_id=f"ep-{run_idx}",
            actions=[action],
        )
        totals.append(summary.raw_total)

    assert len(set(totals)) == 1


def test_medium_grader_comment_scoring(tmp_path: Path) -> None:
    project = _write_project(tmp_path)
    db_path = tmp_path / "medium.db"
    seed_project(project, db_path=str(db_path), force=True)

    store = Store(source_root=str(project), db_path=str(db_path))
    grader = MediumGrader(store)
    findings = store.get_findings("b")
    assert findings
    comment = findings[0].message

    reward = grader.grade_action(
        module_id="b",
        action=ReviewAction(action_type=ActionType.ADD_COMMENT, content=comment),
        findings=findings,
        state=EpisodeState(),
    )
    assert reward.reason in {RewardReason.ACCURATE_COMMENT, RewardReason.FALSE_POSITIVE_FLAG}


def test_hard_grader_dependency_attribution(tmp_path: Path) -> None:
    project = _write_project(tmp_path)
    db_path = tmp_path / "hard.db"
    seed_project(project, db_path=str(db_path), force=True)

    store = Store(source_root=str(project), db_path=str(db_path))
    graph = GraphManager(source_root=str(project), db_path=str(db_path))
    grader = HardGrader(store, graph)

    good = grader.grade_episode(
        module_id="a",
        task_id="hard_review",
        episode_id="ep-hard-1",
        actions=[
            ReviewAction(
                action_type=ActionType.FLAG_DEPENDENCY_ISSUE,
                attributed_to="b",
                target_line=1,
                content="a depends on b",
            )
        ],
    )
    assert good.rewards[0].reason in {
        RewardReason.CORRECT_DEPENDENCY_ATTRIBUTION,
        RewardReason.PARTIAL_DEPENDENCY_ATTRIBUTION,
    }

    bad = grader.grade_episode(
        module_id="a",
        task_id="hard_review",
        episode_id="ep-hard-2",
        actions=[
            ReviewAction(
                action_type=ActionType.FLAG_DEPENDENCY_ISSUE,
                attributed_to="missing",
                content="invalid attribution",
            )
        ],
    )
    assert bad.rewards[0].reason == RewardReason.INCORRECT_DEPENDENCY_ATTRIBUTION
