from __future__ import annotations

import re

from db.schema import AnalyzerFinding
from env.action import ActionType, ReviewAction
from env.reward import RewardReason, ReviewReward, make_reward
from graders.base_grader import EpisodeState
from graders.easy_grader import EasyGrader


class MediumGrader(EasyGrader):
	"""Deterministic easy grading plus keyword-based comment attribution."""

	KEYWORD_MIN_JACCARD = 0.3

	def truth_analyzers(self) -> set[str] | None:
		return {"mypy", "pyright"}

	def grade_action(
		self,
		module_id: str,
		action: ReviewAction,
		findings: list[AnalyzerFinding],
		state: EpisodeState,
	) -> ReviewReward:
		if action.action_type == ActionType.ADD_COMMENT:
			if not action.content:
				return make_reward(RewardReason.FALSE_POSITIVE_FLAG, "Missing comment content")
			match = self._best_comment_match(action.content, findings)
			if match is not None:
				return make_reward(
					RewardReason.ACCURATE_COMMENT,
					f"Comment aligns with finding at line {match.line}",
					matched_finding_id=match.id,
				)
			return make_reward(RewardReason.FALSE_POSITIVE_FLAG, "Comment not aligned to findings")

		if action.action_type == ActionType.AMEND_REVIEW:
			if action.content and action.content.strip():
				return make_reward(RewardReason.CORRECT_AMENDMENT, "Review amendment accepted")
			return make_reward(RewardReason.FALSE_POSITIVE_FLAG, "Invalid amendment")

		return super().grade_action(module_id, action, findings, state)

	def _best_comment_match(self, comment: str, findings: list[AnalyzerFinding]) -> AnalyzerFinding | None:
		comment_tokens = self._tokenize(comment)
		if not comment_tokens:
			return None

		best: tuple[float, AnalyzerFinding] | None = None
		for finding in findings:
			rule_hint = str(getattr(finding, "rule_id", getattr(finding, "code", "")))
			message = str(getattr(finding, "message", ""))
			finding_tokens = self._tokenize(f"{rule_hint} {message}")
			if not finding_tokens:
				continue
			score = self._jaccard(comment_tokens, finding_tokens)
			if score >= self.KEYWORD_MIN_JACCARD:
				if best is None or score > best[0]:
					best = (score, finding)
		return best[1] if best else None

	@staticmethod
	def _tokenize(text: str) -> set[str]:
		return {token for token in re.split(r"[^a-z0-9]+", text.lower()) if len(token) >= 3}

	@staticmethod
	def _jaccard(left: set[str], right: set[str]) -> float:
		union = left | right
		if not union:
			return 0.0
		return len(left & right) / len(union)
