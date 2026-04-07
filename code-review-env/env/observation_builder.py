from __future__ import annotations

import json
from pathlib import Path

from sqlmodel import Session, select

from db.schema import ModuleNode
from env.observation import CodeObservation, NeighborSummary, RequestedContext
from graph.graph_manager import GraphManager
from graph.token_budget import TokenBudget


DEFAULT_ACTIONS = [
	"FLAG_STYLE",
	"FLAG_BUG",
	"FLAG_SECURITY",
	"FLAG_DEPENDENCY_ISSUE",
	"ADD_COMMENT",
	"REQUEST_CONTEXT",
	"REQUEST_CHANGES",
	"APPROVE",
	"AMEND_REVIEW",
]


class ObservationBuilder:
	def __init__(self, source_root: str | Path, db_path: str | Path | None = None) -> None:
		self.graph_manager = GraphManager(source_root=source_root, db_path=db_path)
		self.token_budget = TokenBudget()

	def _fetch_node(self, module_id: str) -> ModuleNode:
		with Session(self.graph_manager.store.engine) as session:
			node = session.exec(
				select(ModuleNode).where(
					ModuleNode.source_root == self.graph_manager.store.config.source_root,
					ModuleNode.module_id == module_id,
				)
			).first()
		if not node:
			raise ValueError(f"Unknown module_id: {module_id}")
		return node

	@staticmethod
	def _ast_summary_payload(ast_summary: str) -> dict[str, object]:
		try:
			loaded = json.loads(ast_summary)
		except json.JSONDecodeError:
			return {"text": ast_summary}
		return loaded if isinstance(loaded, dict) else {"items": loaded}

	def build(
		self,
		module_id: str,
		task_description: str,
		available_actions: list[str] | None = None,
		context_request: str | None = None,
	) -> CodeObservation:
		graph = self.graph_manager.load_graph()
		module_id = self.graph_manager.resolve_module_id(module_id)

		node = self._fetch_node(module_id)
		centrality = self.graph_manager.centrality()

		dependencies = list(graph.successors(module_id))
		dependents = list(graph.predecessors(module_id))

		dep_ranked = sorted(dependencies, key=lambda n: (-float(centrality.get(n, 0.0)), n))[:5]
		dependent_ranked = sorted(dependents, key=lambda n: (-float(centrality.get(n, 0.0)), n))[:3]

		dependency_summaries: list[NeighborSummary] = []
		dependent_summaries: list[NeighborSummary] = []
		neighbor_reviews: list[str] = []

		for dep_id in dep_ranked:
			dep_node = self._fetch_node(dep_id)
			dependency_summaries.append(
				NeighborSummary(
					module_id=dep_id,
					relation="dependency",
					summary=dep_node.summary or dep_node.ast_summary,
					review_snippet=dep_node.review_summary,
				)
			)
			if dep_node.review_summary:
				neighbor_reviews.append(f"{dep_id}: {dep_node.review_summary}")

		for depd_id in dependent_ranked:
			depd_node = self._fetch_node(depd_id)
			dependent_summaries.append(
				NeighborSummary(
					module_id=depd_id,
					relation="dependent",
					summary=depd_node.summary or depd_node.ast_summary,
					review_snippet=depd_node.review_summary,
				)
			)
			if depd_node.review_summary:
				neighbor_reviews.append(f"{depd_id}: {depd_node.review_summary}")

		requested_context: RequestedContext | None = None
		requested_context_code = ""
		if context_request:
			context_request = self.graph_manager.resolve_module_id(context_request)
			context_node = self._fetch_node(context_request)
			requested_context_code = context_node.raw_code

		actions = available_actions or DEFAULT_ACTIONS
		budgeted = self.token_budget.enforce(
			{
				"code": node.raw_code,
				"ast_summary_text": node.ast_summary,
				"dependency_summaries": [item.model_dump_json() for item in dependency_summaries],
				"dependent_summaries": [item.model_dump_json() for item in dependent_summaries],
				"neighbor_reviews": neighbor_reviews[:4],
				"task_description": task_description,
				"available_actions": actions,
				"requested_context_code": requested_context_code,
			}
		)

		if context_request:
			context_trimmed = budgeted.payload.get("requested_context_code", "")
			requested_context = RequestedContext(
				module_id=context_request,
				code=str(context_trimmed),
				was_truncated=str(context_trimmed) != requested_context_code,
			)

		dependency_summaries_bounded = self._trim_neighbor_summaries(
			dependency_summaries,
			str(budgeted.payload.get("dependency_summaries_text", "")),
		)
		dependent_summaries_bounded = self._trim_neighbor_summaries(
			dependent_summaries,
			str(budgeted.payload.get("dependent_summaries_text", "")),
		)
		neighbor_reviews_bounded = [
			line for line in str(budgeted.payload.get("neighbor_reviews_text", "")).splitlines() if line.strip()
		]

		return CodeObservation(
			module_id=module_id,
			code=str(budgeted.payload.get("code", "")),
			module_summary=node.summary or node.ast_summary,
			ast_summary=self._ast_summary_payload(str(budgeted.payload.get("ast_summary_text", ""))),
			dependency_summaries=dependency_summaries_bounded,
			dependent_summaries=dependent_summaries_bounded,
			neighbor_reviews=neighbor_reviews_bounded,
			task_description=task_description,
			available_actions=actions,
			requested_context=requested_context,
			token_usage=budgeted.token_usage,
			total_tokens=budgeted.total_tokens,
			within_budget=budgeted.total_tokens <= self.token_budget.max_total_tokens,
		)

	@staticmethod
	def _trim_neighbor_summaries(
		summaries: list[NeighborSummary],
		serialized_text: str,
	) -> list[NeighborSummary]:
		if not summaries or not serialized_text.strip():
			return []

		max_count = serialized_text.count("\n") + 1
		bounded = summaries[:max_count]
		if "[TRUNCATED]" in serialized_text and bounded:
			last = bounded[-1]
			bounded[-1] = NeighborSummary(
				module_id=last.module_id,
				relation=last.relation,
				summary=f"{last.summary}\n... [TRUNCATED]",
				review_snippet=last.review_snippet,
			)
		return bounded
