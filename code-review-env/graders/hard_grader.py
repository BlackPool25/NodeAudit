from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from openai import OpenAI

from db.store import Store
from db.schema import LinterFinding
from env.action import ActionType, ReviewAction
from env.reward import RewardReason, ReviewReward, make_reward
from graph.graph_manager import GraphManager
from graders.base_grader import EpisodeState
from graders.medium_grader import MediumGrader


class HardGrader(MediumGrader):
	"""Deterministic graph checks plus temperature-zero judge scoring."""

	DEFAULT_JUDGE_SYSTEM_PROMPT = (
		"You are an RL code-review dependency attribution judge. "
		"Score only the quality of attribution logic, not writing style. "
		"Return strict JSON with keys: score and explanation. "
		"Allowed score values: 0.0, 0.5, 1.0."
	)

	def __init__(self, store: Store, graph_manager: GraphManager) -> None:
		super().__init__(store)
		self.graph_manager = graph_manager
		self.graph = self.graph_manager.load_graph()
		self.judge_model = os.getenv("GRAPHREVIEW_JUDGE_MODEL", "gemma4:e4b")
		self.judge_provider = os.getenv(
			"GRAPHREVIEW_JUDGE_PROVIDER",
			"ollama_openai_compat",
		)
		self.base_url = os.getenv("GRAPHREVIEW_JUDGE_BASE_URL", "http://localhost:11434/v1")
		self.api_key = os.getenv("GRAPHREVIEW_JUDGE_API_KEY", "ollama")
		self.timeout = float(os.getenv("GRAPHREVIEW_JUDGE_TIMEOUT_SECONDS", "30"))
		self.judge_system_prompt = os.getenv(
			"GRAPHREVIEW_JUDGE_SYSTEM_PROMPT",
			self.DEFAULT_JUDGE_SYSTEM_PROMPT,
		)
		self.reasoning_effort = os.getenv("GRAPHREVIEW_JUDGE_REASONING_EFFORT", "none")
		self.think_value = os.getenv("GRAPHREVIEW_JUDGE_THINK", "false").strip().lower()
		self.prompt_hash = hashlib.sha256(self.judge_system_prompt.encode("utf-8")).hexdigest()

	def grade_action(
		self,
		module_id: str,
		action: ReviewAction,
		findings: list[LinterFinding],
		state: EpisodeState,
	) -> ReviewReward:
		if action.action_type != ActionType.FLAG_DEPENDENCY_ISSUE:
			return super().grade_action(module_id, action, findings, state)

		if not action.attributed_to:
			return make_reward(
				RewardReason.INCORRECT_DEPENDENCY_ATTRIBUTION,
				"Missing attributed_to module",
			)

		if module_id not in self.graph or action.attributed_to not in self.graph:
			return make_reward(
				RewardReason.INCORRECT_DEPENDENCY_ATTRIBUTION,
				"Unknown module relationship",
			)

		has_edge = self.graph.has_edge(module_id, action.attributed_to) or self.graph.has_edge(
			action.attributed_to,
			module_id,
		)
		if not has_edge:
			return make_reward(
				RewardReason.INCORRECT_DEPENDENCY_ATTRIBUTION,
				"No dependency relationship found",
			)

		judge_result = self._judge_dependency_reasoning(module_id, action)
		if len(judge_result) == 2:
			judge_score, explanation = judge_result
		else:
			judge_score, explanation = judge_result[0], judge_result[1]
		if judge_score <= 0.0:
			return make_reward(
				RewardReason.INCORRECT_DEPENDENCY_ATTRIBUTION,
				explanation,
				metadata={
					"judge_score": judge_score,
					"judge_provider": self.judge_provider,
					"judge_model": self.judge_model,
					"temperature": 0.0,
					"prompt_hash": self.prompt_hash,
				},
			)

		base_reason = RewardReason.CORRECT_DEPENDENCY_ATTRIBUTION
		reward = make_reward(
			base_reason,
			explanation,
			metadata={
				"judge_score": judge_score,
				"judge_provider": self.judge_provider,
				"judge_model": self.judge_model,
				"temperature": 0.0,
				"prompt_hash": self.prompt_hash,
			},
		)
		return reward

	def _judge_dependency_reasoning(self, module_id: str, action: ReviewAction) -> tuple[float, str]:
		content = action.content or ""
		payload = {
			"current_module": module_id,
			"attributed_to": action.attributed_to,
			"review_comment": content,
			"rubric": "0.0 wrong or unsupported; 0.5 partially justified; 1.0 well-justified root cause",
		}

		try:
			client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout)

			request_kwargs: dict[str, Any] = {
				"model": self.judge_model,
				"temperature": 0,
				"response_format": {"type": "json_object"},
				"messages": [
					{"role": "system", "content": self.judge_system_prompt},
					{"role": "user", "content": json.dumps(payload, sort_keys=True)},
				],
			}

			if self.reasoning_effort in {"none", "low", "medium", "high"}:
				request_kwargs["reasoning_effort"] = self.reasoning_effort

			if self.judge_provider == "ollama_openai_compat":
				if self.think_value in {"true", "false", "low", "medium", "high"}:
					think: bool | str
					if self.think_value in {"low", "medium", "high"}:
						think = self.think_value
					else:
						think = self.think_value == "true"
					request_kwargs["extra_body"] = {"think": think}

			response = client.chat.completions.create(**request_kwargs)
			text = response.choices[0].message.content or ""
			parsed = self._parse_json_object(text)
			score = float(parsed.get("score", 0.0))
			if score not in {0.0, 0.5, 1.0}:
				score = 0.0
			explanation = str(parsed.get("explanation", "Dependency attribution judged"))
			return score, explanation
		except Exception as exc:
			return 0.0, f"Judge unavailable: {exc}"

	@staticmethod
	def _parse_json_object(content: str) -> dict[str, object]:
		text = content.strip()
		if not text:
			return {}
		try:
			return json.loads(text)
		except json.JSONDecodeError:
			start = text.find("{")
			end = text.rfind("}")
			if start >= 0 and end > start:
				return json.loads(text[start : end + 1])
			raise
