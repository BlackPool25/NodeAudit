from __future__ import annotations

import json
import os
from dataclasses import dataclass

from huggingface_hub import InferenceClient

from env.action import ActionType, ReviewAction


JUDGE_PROMPT = """
You are a code review judge. Score this agent's thinking trace.

Ground truth finding: {finding}
Agent thinking: {thinking_trace}
Agent action: {action}
Graph context: {graph_context}

Score 0.0-1.0 on:
- causal_chain_correct: Did the agent correctly trace root cause through the graph?
- attribution_correct: Is attributed_to the actual origin module?
- reasoning_depth: Did the agent reason about upstream/downstream impact?

Respond ONLY in JSON:
{"score": 0.0-1.0, "causal_chain_correct": bool, "attribution_correct": bool,
 "reasoning_depth": "shallow|adequate|deep",
 "what_was_right": "...", "what_was_wrong": "..."}
""".strip()


@dataclass(frozen=True)
class JudgeVerdict:
    score: float
    causal_chain_correct: bool
    attribution_correct: bool
    reasoning_depth: str
    what_was_right: str
    what_was_wrong: str


class ThinkingJudge:
    def __init__(self, model_name: str | None = None, token: str | None = None) -> None:
        self.model_name = model_name or os.getenv("JUDGE_MODEL", "Qwen/Qwen2.5-7B-Instruct")
        self.client = InferenceClient(token=token or os.getenv("HF_TOKEN"))
        self.temperature = float(os.getenv("GRAPHREVIEW_JUDGE_TEMPERATURE", "0.3"))
        self.max_tokens = int(os.getenv("GRAPHREVIEW_JUDGE_MAX_TOKENS", "512"))

    def should_judge(self, action: ReviewAction) -> bool:
        return action.action_type.value in {"FLAG_DEPENDENCY_ISSUE", "APPROVE", "REQUEST_CHANGES"}

    def score(
        self,
        *,
        finding: str,
        thinking_trace: str,
        action: ReviewAction,
        graph_context: str,
    ) -> JudgeVerdict:
        prompt = JUDGE_PROMPT.format(
            finding=finding,
            thinking_trace=thinking_trace,
            action=action.model_dump_json(exclude_none=True),
            graph_context=graph_context,
        )
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "Return JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        content = (response.choices[0].message.content or "{}").strip()
        payload = json.loads(content)
        if not isinstance(payload, dict):
            payload = {}

        score = float(payload.get("score", 0.0) or 0.0)
        score = min(1.0, max(0.0, score))
        depth = str(payload.get("reasoning_depth", "shallow"))
        if depth not in {"shallow", "adequate", "deep"}:
            depth = "shallow"

        return JudgeVerdict(
            score=score,
            causal_chain_correct=bool(payload.get("causal_chain_correct", False)),
            attribution_correct=bool(payload.get("attribution_correct", False)),
            reasoning_depth=depth,
            what_was_right=str(payload.get("what_was_right", "")).strip(),
            what_was_wrong=str(payload.get("what_was_wrong", "")).strip(),
        )


def score_thinking(
    *,
    thinking_trace: str,
    action: dict[str, object],
    finding: dict[str, object],
    graph_context: dict[str, object],
    model_name: str | None = None,
) -> dict[str, object]:
    raw_action_type = str(action.get("action_type", "REQUEST_CHANGES")).upper()
    try:
        action_type = ActionType(raw_action_type)
    except ValueError:
        action_type = ActionType.REQUEST_CHANGES

    review_action = ReviewAction(
        action_type=action_type,
        target_line=action.get("target_line"),
        content=action.get("content"),
        attributed_to=action.get("attributed_to"),
        context_request=action.get("context_request"),
    )
    judge = ThinkingJudge(model_name=model_name)
    verdict = judge.score(
        finding=json.dumps(finding, ensure_ascii=True, sort_keys=True),
        thinking_trace=thinking_trace,
        action=review_action,
        graph_context=json.dumps(graph_context, ensure_ascii=True, sort_keys=True),
    )
    return {
        "score": verdict.score,
        "causal_chain_correct": verdict.causal_chain_correct,
        "attribution_correct": verdict.attribution_correct,
        "reasoning_depth": verdict.reasoning_depth,
        "what_was_right": verdict.what_was_right,
        "what_was_wrong": verdict.what_was_wrong,
    }
