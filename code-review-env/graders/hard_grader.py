from __future__ import annotations

from db.schema import AnalyzerFinding
from db.store import Store
from env.action import ActionType, ReviewAction
from env.reward import RewardReason, ReviewReward, make_reward
from graph.graph_manager import GraphManager
from graders.base_grader import EpisodeState
from graders.medium_grader import MediumGrader

class HardGrader(MediumGrader):
    """Deterministic dependency-attribution grading on high-signal analyzer findings."""

    def __init__(self, store: Store, graph_manager: GraphManager) -> None:
        super().__init__(store)
        self.graph_manager = graph_manager
        self.graph = self.graph_manager.load_graph()

    def truth_analyzers(self) -> set[str] | None:
        return {"pyright", "pysa", "bandit", "pylint", "radon", "ast"}

    def grade_action(
        self,
        module_id: str,
        action: ReviewAction,
        findings: list[AnalyzerFinding],
        state: EpisodeState,
    ) -> ReviewReward:
        if action.action_type != ActionType.FLAG_DEPENDENCY_ISSUE:
            return super().grade_action(module_id, action, findings, state)

        if not action.attributed_to:
            return make_reward(
                RewardReason.INCORRECT_DEPENDENCY_ATTRIBUTION,
                "Missing attributed_to module",
            )

        try:
            attributed_to = self.graph_manager.resolve_module_id(action.attributed_to)
        except ValueError:
            return make_reward(
                RewardReason.INCORRECT_DEPENDENCY_ATTRIBUTION,
                "Unknown attributed module",
            )

        if module_id not in self.graph or attributed_to not in self.graph:
            return make_reward(
                RewardReason.INCORRECT_DEPENDENCY_ATTRIBUTION,
                "Unknown module relationship",
            )

        has_edge = self.graph.has_edge(module_id, attributed_to) or self.graph.has_edge(attributed_to, module_id)
        if not has_edge:
            return make_reward(
                RewardReason.INCORRECT_DEPENDENCY_ATTRIBUTION,
                "No dependency edge found for attribution",
            )

        matched_finding = self._match_hard_finding(action=action, findings=findings, state=state)
        if matched_finding is None:
            return make_reward(
                RewardReason.PARTIAL_DEPENDENCY_ATTRIBUTION,
                "Attribution graph edge is valid but no matching deterministic cascade finding was identified",
                metadata={"deterministic_only": True},
            )

        state.matched_finding_ids.add(matched_finding.id or -1)
        return make_reward(
            RewardReason.CORRECT_DEPENDENCY_ATTRIBUTION,
            f"Matched deterministic cascade finding {matched_finding.analyzer}:{matched_finding.rule_id} at line {matched_finding.line}",
            matched_finding_id=matched_finding.id,
            metadata={"deterministic_only": True},
        )

    def _match_hard_finding(
        self,
        action: ReviewAction,
        findings: list[AnalyzerFinding],
        state: EpisodeState,
    ) -> AnalyzerFinding | None:
        allowed = self.truth_analyzers() or set()
        for finding in findings:
            finding_id = finding.id or -1
            if finding_id in state.matched_finding_ids:
                continue
            if finding.analyzer not in allowed:
                continue
            if action.target_line is None:
                return finding
            if abs(action.target_line - finding.line) <= self.LINE_TOLERANCE:
                return finding
        return None
