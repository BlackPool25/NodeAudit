from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RewardReason(StrEnum):
	CORRECT_FLAG = "correct_flag"
	ACCURATE_COMMENT = "accurate_comment"
	CORRECT_DEPENDENCY_ATTRIBUTION = "correct_dependency_attribution"
	INCORRECT_DEPENDENCY_ATTRIBUTION = "incorrect_dependency_attribution"
	CORRECT_AMENDMENT = "correct_amendment"
	REQUEST_CONTEXT_COST = "request_context_cost"
	FALSE_POSITIVE_FLAG = "false_positive_flag"
	APPROVE_WITH_CRITICAL_ISSUES = "approve_with_critical_issues"
	REQUEST_CHANGES_ON_CLEAN = "request_changes_on_clean"
	EPISODE_COMPLETION_BONUS = "episode_completion_bonus"
	NOOP = "noop"


RAW_REWARD_TABLE: dict[RewardReason, float] = {
	RewardReason.CORRECT_FLAG: 0.5,
	RewardReason.ACCURATE_COMMENT: 0.3,
	RewardReason.CORRECT_DEPENDENCY_ATTRIBUTION: 0.6,
	RewardReason.INCORRECT_DEPENDENCY_ATTRIBUTION: 0.1,
	RewardReason.CORRECT_AMENDMENT: 0.4,
	RewardReason.REQUEST_CONTEXT_COST: -0.1,
	RewardReason.FALSE_POSITIVE_FLAG: -0.2,
	RewardReason.APPROVE_WITH_CRITICAL_ISSUES: -1.0,
	RewardReason.REQUEST_CHANGES_ON_CLEAN: -0.3,
	RewardReason.EPISODE_COMPLETION_BONUS: 0.2,
	RewardReason.NOOP: 0.0,
}


def normalize_reward(raw_value: float) -> float:
	"""Map raw reward from [-1.0, 1.0] into [0.0, 1.0]."""
	bounded = max(-1.0, min(1.0, raw_value))
	return (bounded + 1.0) / 2.0


class ReviewReward(BaseModel):
	model_config = ConfigDict(strict=True, extra="forbid")

	reason: RewardReason
	raw_value: float
	normalized_value: float
	feedback: str
	matched_finding_id: int | None = None
	metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)

	@field_validator("normalized_value")
	@classmethod
	def validate_normalized(cls, value: float) -> float:
		if value < 0.0 or value > 1.0:
			raise ValueError("normalized_value must be in [0.0, 1.0]")
		return value


class EpisodeGradeSummary(BaseModel):
	model_config = ConfigDict(strict=True, extra="forbid")

	module_id: str
	raw_total: float
	normalized_total: float
	rewards: list[ReviewReward]

	@field_validator("normalized_total")
	@classmethod
	def validate_total(cls, value: float) -> float:
		if value < 0.0 or value > 1.0:
			raise ValueError("normalized_total must be in [0.0, 1.0]")
		return value


def make_reward(
	reason: RewardReason,
	feedback: str,
	matched_finding_id: int | None = None,
	metadata: dict[str, str | int | float | bool] | None = None,
) -> ReviewReward:
	raw_value = RAW_REWARD_TABLE[reason]
	return ReviewReward(
		reason=reason,
		raw_value=raw_value,
		normalized_value=normalize_reward(raw_value),
		feedback=feedback,
		matched_finding_id=matched_finding_id,
		metadata=metadata or {},
	)
