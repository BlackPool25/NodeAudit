from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import json
from typing import Iterable

from db.schema import LinterFinding, ReviewStatus
from db.store import Store
from env.action import ActionType, ReviewAction
from env.reward import EpisodeGradeSummary, ReviewReward, normalize_reward


@dataclass
class EpisodeState:
    matched_finding_ids: set[int] = field(default_factory=set)
    seen_actions: list[ReviewAction] = field(default_factory=list)


class BaseGrader(ABC):
    """Shared deterministic grading flow and persistence behavior."""

    def __init__(self, store: Store) -> None:
        self.store = store

    @abstractmethod
    def grade_action(
        self,
        module_id: str,
        action: ReviewAction,
        findings: list[LinterFinding],
        state: EpisodeState,
    ) -> ReviewReward:
        raise NotImplementedError

    def grade_episode(
        self,
        module_id: str,
        task_id: str,
        episode_id: str,
        actions: Iterable[ReviewAction],
    ) -> EpisodeGradeSummary:
        findings = self._sorted_findings(module_id)
        state = EpisodeState()
        rewards: list[ReviewReward] = []

        for step_number, action in enumerate(actions, start=1):
            reward = self.grade_action(module_id, action, findings, state)
            state.seen_actions.append(action)
            rewards.append(reward)
            self._persist_step(
                module_id=module_id,
                task_id=task_id,
                episode_id=episode_id,
                step_number=step_number,
                action=action,
                reward=reward,
            )

        raw_total = sum(reward.raw_value for reward in rewards)
        normalized_total = normalize_reward(max(-1.0, min(1.0, raw_total)))
        return EpisodeGradeSummary(
            module_id=module_id,
            raw_total=raw_total,
            normalized_total=normalized_total,
            rewards=rewards,
        )

    def _persist_step(
        self,
        module_id: str,
        task_id: str,
        episode_id: str,
        step_number: int,
        action: ReviewAction,
        reward: ReviewReward,
    ) -> None:
        status = ReviewStatus.IN_PROGRESS
        if action.action_type.name in {"APPROVE", "REQUEST_CHANGES"}:
            status = ReviewStatus.REVIEWED

        payload = {
            "action_type": action.action_type.value,
            "feedback": reward.feedback,
            "reward_reason": reward.reason.value,
            "raw_reward": reward.raw_value,
            "normalized_reward": reward.normalized_value,
            "matched_finding_id": reward.matched_finding_id,
            "metadata": reward.metadata,
        }
        note = json.dumps(payload, sort_keys=True)
        summary = f"{action.action_type.value}: {reward.feedback}"
        self.store.update_annotation(
            module_id=module_id,
            episode_id=episode_id,
            step_number=step_number,
            action_type=action.action_type.value,
            note=note,
            task_id=task_id,
            reward_given=reward.raw_value,
            attributed_to=action.attributed_to,
            is_amendment=action.action_type == ActionType.AMEND_REVIEW,
            review_summary=summary,
            review_status=status,
        )

    def _sorted_findings(self, module_id: str) -> list[LinterFinding]:
        findings = self.store.get_findings(module_id)
        return sorted(findings, key=lambda item: (item.line, item.tool, item.code, item.id or 0))
