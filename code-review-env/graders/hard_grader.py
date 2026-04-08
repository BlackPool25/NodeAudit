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
		"You are a deterministic dependency-attribution judge for an RL code-review environment. "
		"Evaluate only whether the claimed root-cause module attribution is logically supported. "
		"Do not judge prose quality. Ignore style and politeness. "
		"Rubric: 0.0 unsupported/wrong attribution; 0.5 partially supported but incomplete evidence; "
		"1.0 clear and well-supported attribution with correct causal direction. "
		"Return STRICT JSON only: {\"score\": 0.0|0.5|1.0, \"explanation\": \"...\"}."
	)

	def __init__(self, store: Store, graph_manager: GraphManager) -> None:
		super().__init__(store)
		self.graph_manager = graph_manager
		self.graph = self.graph_manager.load_graph()
		self.judge_enabled = os.getenv("GRAPHREVIEW_JUDGE_ENABLED", "true").strip().lower() == "true"
		self.judge_model = os.getenv("GRAPHREVIEW_JUDGE_MODEL", "gemma4:e4b")
		self.judge_provider = os.getenv(
			"GRAPHREVIEW_JUDGE_PROVIDER",
			"ollama_openai_compat",
		)
		self.verifier_provider = os.getenv("GRAPHREVIEW_VERIFIER_PROVIDER", self.judge_provider)
		self.base_url = os.getenv("GRAPHREVIEW_JUDGE_BASE_URL", "http://localhost:11434/v1")
		self.verifier_base_url = os.getenv("GRAPHREVIEW_VERIFIER_BASE_URL", self.base_url)
		self.api_key = os.getenv("GRAPHREVIEW_JUDGE_API_KEY", "ollama")
		self.verifier_api_key = os.getenv("GRAPHREVIEW_VERIFIER_API_KEY", self.api_key)
		self.timeout = float(os.getenv("GRAPHREVIEW_JUDGE_TIMEOUT_SECONDS", "8"))
		self.verifier_timeout = float(os.getenv("GRAPHREVIEW_VERIFIER_TIMEOUT_SECONDS", str(self.timeout)))
		self.judge_system_prompt = os.getenv(
			"GRAPHREVIEW_JUDGE_SYSTEM_PROMPT",
			self.DEFAULT_JUDGE_SYSTEM_PROMPT,
		)
		self.verifier_enabled = os.getenv("GRAPHREVIEW_VERIFIER_ENABLED", "true").strip().lower() == "true"
		self.verifier_model = os.getenv("GRAPHREVIEW_VERIFIER_MODEL", self.judge_model)
		self.verifier_system_prompt = os.getenv(
			"GRAPHREVIEW_VERIFIER_SYSTEM_PROMPT",
			self.DEFAULT_JUDGE_SYSTEM_PROMPT,
		)
		self.reasoning_effort = os.getenv("GRAPHREVIEW_JUDGE_REASONING_EFFORT", "none")
		self.think_value = os.getenv("GRAPHREVIEW_JUDGE_THINK", "false").strip().lower()
		self.max_judge_calls = int(os.getenv("GRAPHREVIEW_JUDGE_MAX_CALLS", "200"))
		self.max_consecutive_failures = int(os.getenv("GRAPHREVIEW_JUDGE_MAX_CONSECUTIVE_FAILURES", "3"))
		self.weight_deterministic = float(os.getenv("GRAPHREVIEW_JUDGE_WEIGHT_DETERMINISTIC", "0.5"))
		self.weight_primary = float(os.getenv("GRAPHREVIEW_JUDGE_WEIGHT_PRIMARY", "0.3"))
		self.weight_verifier = float(os.getenv("GRAPHREVIEW_JUDGE_WEIGHT_VERIFIER", "0.2"))
		self.disagreement_threshold = float(os.getenv("GRAPHREVIEW_JUDGE_DISAGREEMENT_THRESHOLD", "0.5"))
		self._judge_calls = 0
		self._consecutive_failures = 0
		self._judge_cache: dict[str, tuple[float, str]] = {}
		self.prompt_hash = hashlib.sha256(self.judge_system_prompt.encode("utf-8")).hexdigest()
		self.verifier_prompt_hash = hashlib.sha256(self.verifier_system_prompt.encode("utf-8")).hexdigest()

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

		try:
			attributed_to = self.graph_manager.resolve_module_id(action.attributed_to)
		except ValueError:
			return make_reward(
				RewardReason.INCORRECT_DEPENDENCY_ATTRIBUTION,
				"Unknown module relationship",
			)

		if module_id not in self.graph or attributed_to not in self.graph:
			return make_reward(
				RewardReason.INCORRECT_DEPENDENCY_ATTRIBUTION,
				"Unknown module relationship",
			)

		has_edge = self.graph.has_edge(module_id, attributed_to) or self.graph.has_edge(
			attributed_to,
			module_id,
		)
		if not has_edge:
			return make_reward(
				RewardReason.INCORRECT_DEPENDENCY_ATTRIBUTION,
				"No dependency relationship found",
			)

		normalized_action = action.model_copy(update={"attributed_to": attributed_to})
		primary_score, primary_explanation = self._judge_with_model(
			module_id=module_id,
			action=normalized_action,
			model=self.judge_model,
			provider=self.judge_provider,
			base_url=self.base_url,
			api_key=self.api_key,
			timeout=self.timeout,
			system_prompt=self.judge_system_prompt,
			cache_scope="primary",
		)
		verifier_score = primary_score
		verifier_explanation = "Verifier disabled"
		if self.verifier_enabled:
			verifier_score, verifier_explanation = self._judge_with_model(
				module_id=module_id,
				action=normalized_action,
				model=self.verifier_model,
				provider=self.verifier_provider,
				base_url=self.verifier_base_url,
				api_key=self.verifier_api_key,
				timeout=self.verifier_timeout,
				system_prompt=self.verifier_system_prompt,
				cache_scope="verifier",
			)

		final_score, blend = self._blend_scores(
			deterministic_score=1.0,
			primary_score=primary_score,
			verifier_score=verifier_score,
		)

		if final_score < 0.45:
			return make_reward(
				RewardReason.INCORRECT_DEPENDENCY_ATTRIBUTION,
				f"{primary_explanation} | verifier: {verifier_explanation}",
				metadata={
					"judge_score": primary_score,
					"verifier_score": verifier_score,
					"final_score": final_score,
					"blend": json.dumps(blend, sort_keys=True),
					"judge_provider": self.judge_provider,
					"judge_model": self.judge_model,
					"verifier_provider": self.verifier_provider,
					"verifier_model": self.verifier_model,
					"temperature": 0.0,
					"prompt_hash": self.prompt_hash,
					"verifier_prompt_hash": self.verifier_prompt_hash,
				},
			)

		base_reason = RewardReason.CORRECT_DEPENDENCY_ATTRIBUTION
		if final_score < 0.75:
			base_reason = RewardReason.PARTIAL_DEPENDENCY_ATTRIBUTION
		reward = make_reward(
			base_reason,
			f"{primary_explanation} | verifier: {verifier_explanation}",
			metadata={
				"judge_score": primary_score,
				"verifier_score": verifier_score,
				"final_score": final_score,
				"blend": json.dumps(blend, sort_keys=True),
				"judge_provider": self.judge_provider,
				"judge_model": self.judge_model,
				"verifier_provider": self.verifier_provider,
				"verifier_model": self.verifier_model,
				"temperature": 0.0,
				"prompt_hash": self.prompt_hash,
				"verifier_prompt_hash": self.verifier_prompt_hash,
			},
		)
		return reward

	def _judge_with_model(
		self,
		module_id: str,
		action: ReviewAction,
		model: str,
		provider: str,
		base_url: str,
		api_key: str,
		timeout: float,
		system_prompt: str,
		cache_scope: str,
	) -> tuple[float, str]:
		if not self.judge_enabled:
			return 1.0, "Judge disabled by configuration; graph-consistent attribution accepted"

		if self._judge_calls >= self.max_judge_calls:
			return 0.5, "Judge call budget exhausted; using deterministic fallback"

		if self._consecutive_failures >= self.max_consecutive_failures:
			return 0.5, "Judge temporarily disabled after repeated failures"

		content = action.content or ""
		payload = {
			"current_module": module_id,
			"attributed_to": action.attributed_to,
			"review_comment": content,
			"rubric": "0.0 wrong or unsupported; 0.5 partially justified; 1.0 well-justified root cause",
		}
		payload_text = json.dumps(payload, sort_keys=True)
		cache_key = hashlib.sha256(f"{cache_scope}:{model}:{payload_text}".encode("utf-8")).hexdigest()
		cached = self._judge_cache.get(cache_key)
		if cached is not None:
			return cached

		try:
			self._judge_calls += 1
			client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

			request_kwargs: dict[str, Any] = {
				"model": model,
				"temperature": 0.0,
				"response_format": {"type": "json_object"},
				"messages": [
					{"role": "system", "content": system_prompt},
					{"role": "user", "content": payload_text},
				],
			}

			if self.reasoning_effort in {"none", "low", "medium", "high"}:
				request_kwargs["reasoning_effort"] = self.reasoning_effort

			if provider == "ollama_openai_compat":
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
			result = (score, explanation)
			self._judge_cache[cache_key] = result
			self._consecutive_failures = 0
			return result
		except Exception as exc:
			self._consecutive_failures += 1
			if self._consecutive_failures >= self.max_consecutive_failures:
				return 0.5, f"Judge unavailable after repeated failures: {exc}"
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

	def _blend_scores(
		self,
		deterministic_score: float,
		primary_score: float,
		verifier_score: float,
	) -> tuple[float, dict[str, float | bool]]:
		d = max(0.0, min(1.0, deterministic_score))
		p = max(0.0, min(1.0, primary_score))
		v = max(0.0, min(1.0, verifier_score))

		wd = max(self.weight_deterministic, 0.0)
		wp = max(self.weight_primary, 0.0)
		wv = max(self.weight_verifier, 0.0)
		disagreement = abs(p - v)
		disagreement_guard = disagreement >= self.disagreement_threshold
		if disagreement_guard:
			wp = min(wp, 0.1)
			wv = max(wv, 0.4)
			wd = max(wd, 0.5)

		total = wd + wp + wv
		if total <= 0:
			return 0.0, {"wd": 0.0, "wp": 0.0, "wv": 0.0, "disagreement": disagreement, "guard": disagreement_guard}

		wd /= total
		wp /= total
		wv /= total

		final = (wd * d) + (wp * p) + (wv * v)
		if p == 1.0 and v == 0.0:
			final = min(final, 0.45)

		return final, {
			"wd": wd,
			"wp": wp,
			"wv": wv,
			"disagreement": disagreement,
			"guard": disagreement_guard,
		}
