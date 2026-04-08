from __future__ import annotations

from db.schema import AnalyzerFinding
from env.action import ActionType, ReviewAction
from env.reward import RewardReason, ReviewReward, make_reward
from graders.base_grader import BaseGrader, EpisodeState


class EasyGrader(BaseGrader):
	"""Deterministic grading against analyzer findings."""

	LINE_TOLERANCE = 3

	def truth_analyzers(self) -> set[str] | None:
		return {"pylint", "pyflakes", "bandit", "vulture"}

	def grade_action(
		self,
		module_id: str,
		action: ReviewAction,
		findings: list[AnalyzerFinding],
		state: EpisodeState,
	) -> ReviewReward:
		if action.action_type == ActionType.REQUEST_CONTEXT:
			return make_reward(RewardReason.REQUEST_CONTEXT_COST, "Context requested")

		if action.action_type == ActionType.APPROVE:
			has_critical = any(finding.severity.value == "high" for finding in findings)
			if has_critical:
				return make_reward(
					RewardReason.APPROVE_WITH_CRITICAL_ISSUES,
					"Approved despite critical findings",
				)
			return make_reward(RewardReason.EPISODE_COMPLETION_BONUS, "Approved clean module")

		if action.action_type == ActionType.REQUEST_CHANGES:
			if findings:
				return make_reward(RewardReason.EPISODE_COMPLETION_BONUS, "Changes requested")
			return make_reward(
				RewardReason.REQUEST_CHANGES_ON_CLEAN,
				"Requested changes on clean module",
			)

		if action.action_type in {
			ActionType.FLAG_STYLE,
			ActionType.FLAG_BUG,
			ActionType.FLAG_SECURITY,
		}:
			match = self._match_finding(action, findings, state)
			if match is not None:
				state.matched_finding_ids.add(match.id or -1)
				return make_reward(
					RewardReason.CORRECT_FLAG,
					f"Matched finding {match.analyzer}:{match.rule_id} at line {match.line}",
					matched_finding_id=match.id,
				)
			return make_reward(RewardReason.FALSE_POSITIVE_FLAG, "No matching finding")

		return make_reward(RewardReason.NOOP, "Action has no easy-grade impact")

	def _match_finding(
		self,
		action: ReviewAction,
		findings: list[AnalyzerFinding],
		state: EpisodeState,
	) -> AnalyzerFinding | None:
		for finding in findings:
			finding_id = finding.id or -1
			if finding_id in state.matched_finding_ids:
				continue
			if not self._category_matches(action.action_type, finding):
				continue
			if action.target_line is None:
				return finding
			if abs(action.target_line - finding.line) <= self.LINE_TOLERANCE:
				return finding
		return None

	@staticmethod
	def _category_matches(action_type: ActionType, finding: AnalyzerFinding) -> bool:
		if action_type == ActionType.FLAG_SECURITY:
			return finding.analyzer == "bandit"
		if action_type == ActionType.FLAG_STYLE:
			return finding.analyzer in {"pylint", "vulture"} and finding.severity.value == "low"
		if action_type == ActionType.FLAG_BUG:
			return finding.analyzer in {"pyflakes", "pylint", "vulture"} and finding.severity.value in {
				"high",
				"medium",
			}
		return False
