from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import json
from typing import Iterable

from db.schema import AnalyzerFinding, ReviewStatus
from db.store import Store
from env.action import ActionType, ReviewAction
from env.reward import EpisodeGradeSummary, ReviewReward, RewardReason, make_reward, normalize_reward


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
        findings: list[AnalyzerFinding],
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

            if (
                task_id.startswith("hard")
                and reward.matched_finding_id is not None
                and self.store.finding_previously_caught(module_id, reward.matched_finding_id, exclude_task_prefix="hard")
            ):
                reward = make_reward(
                    RewardReason.NOOP,
                    f"Finding {reward.matched_finding_id} already caught in earlier stage; hard stage requires new verified evidence",
                    matched_finding_id=reward.matched_finding_id,
                    metadata={"already_caught_prior_stage": True},
                )

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

    def truth_analyzers(self) -> set[str] | None:
        return None

    def _sorted_findings(self, module_id: str) -> list[AnalyzerFinding]:
        analyzers = self.truth_analyzers()
        findings = self.store.get_analyzer_findings_for_module(module_id, analyzers=analyzers)
        if findings:
            return findings

        # Backward-compatible fallback for legacy DBs.
        legacy = self.store.get_findings(module_id)
        fallback: list[AnalyzerFinding] = []
        for item in legacy:
            fallback.append(
                AnalyzerFinding(
                    source_root=self.store.config.source_root,
                    analyzer_run_id=0,
                    analyzer=item.tool,
                    module_id=item.module_id,
                    line=item.line,
                    severity=item.severity,
                    rule_id=item.code,
                    message=item.message,
                    evidence="",
                )
            )
        return sorted(fallback, key=lambda entry: (entry.line, entry.analyzer, entry.rule_id, entry.id or 0))
