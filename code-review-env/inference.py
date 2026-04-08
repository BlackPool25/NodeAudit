from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

from openai import OpenAI

from inference_training import main as training_main


# Submission-required runtime variables.
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")

# GraphReview defaults.
BENCHMARK = os.getenv("GRAPHREVIEW_BENCHMARK", "graphreview")
ENV_BASE_URL = os.getenv("GRAPHREVIEW_BASE_URL", "http://127.0.0.1:7860")
TASKS = [
    item.strip()
    for item in os.getenv("GRAPHREVIEW_TASKS", "style_review,logic_review,cascade_review").split(",")
    if item.strip()
]
MAX_STEPS = int(os.getenv("GRAPHREVIEW_MAX_EPISODE_STEPS", "24"))
TEMPERATURE = float(os.getenv("GRAPHREVIEW_INFER_TEMPERATURE", "0.2"))
MAX_TOKENS = int(os.getenv("GRAPHREVIEW_INFER_MAX_TOKENS", "180"))
SUCCESS_SCORE_THRESHOLD = float(os.getenv("GRAPHREVIEW_SUCCESS_THRESHOLD", "0.5"))


@dataclass
class ReviewAction:
    action_type: str
    target_line: int | None = None
    content: str | None = None
    attributed_to: str | None = None
    context_request: str | None = None


@dataclass
class GraphReviewObservation:
    module_id: str
    code: str
    task_description: str
    available_actions: list[str]


@dataclass
class GraphReviewStepResult:
    observation: GraphReviewObservation
    reward: float
    done: bool


class GraphReviewClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def _step_payload(self, action: ReviewAction) -> dict[str, object]:
        payload: dict[str, object] = {"action_type": action.action_type}
        if action.target_line is not None:
            payload["target_line"] = action.target_line
        if action.content:
            payload["content"] = action.content
        if action.attributed_to:
            payload["attributed_to"] = action.attributed_to
        if action.context_request:
            payload["context_request"] = action.context_request
        return {"action": payload}

    def _request_json(self, path: str, payload: dict[str, object]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = urlrequest.Request(
            f"{self.base_url}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlrequest.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urlerror.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
        except urlerror.URLError as exc:
            raise RuntimeError(f"Connection error: {exc.reason}") from exc

    def _parse_result(self, payload: dict[str, Any]) -> GraphReviewStepResult:
        obs = payload.get("observation", {})
        return GraphReviewStepResult(
            observation=GraphReviewObservation(
                module_id=str(obs.get("module_id", "unknown")),
                code=str(obs.get("code", "")),
                task_description=str(obs.get("task_description", "")),
                available_actions=list(obs.get("available_actions", [])),
            ),
            reward=float(payload.get("reward", 0.0) or 0.0),
            done=bool(payload.get("done", False)),
        )

    def reset(self, task_id: str) -> GraphReviewStepResult:
        return self._parse_result(self._request_json("/reset", {"task_id": task_id}))

    def step(self, action: ReviewAction) -> GraphReviewStepResult:
        return self._parse_result(self._request_json("/step", self._step_payload(action)))

    def close(self) -> None:
        return None


def _is_training_mode(argv: list[str]) -> bool:
    # Keep backward compatibility for existing training endpoints that pass a target path.
    return any(not arg.startswith("-") for arg in argv[1:])


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: str | None) -> None:
    action_one_line = action.replace("\n", " ").replace("\r", " ").strip()
    error_val = error if error else "null"
    print(
        f"[STEP] step={step} action={action_one_line} reward={reward:.2f} "
        f"done={str(done).lower()} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: list[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}",
        flush=True,
    )


def _build_prompt(observation: GraphReviewObservation, step: int) -> str:
    code = observation.code[:2200]
    actions = ", ".join(observation.available_actions) if observation.available_actions else "APPROVE"
    return (
        "You are reviewing Python code in GraphReview. Return only compact JSON with keys: "
        "action_type, target_line (optional int), content (optional string), "
        "attributed_to (optional string), context_request (optional string).\n"
        f"Step: {step}\n"
        f"Module: {observation.module_id}\n"
        f"Task: {observation.task_description}\n"
        f"Available actions: {actions}\n"
        "Prefer concrete bug/security/dependency findings over style comments.\n"
        "If uncertain, use REQUEST_CONTEXT or ADD_COMMENT instead of hallucinating.\n"
        f"Code:\n{code}"
    )


def _fallback_action(observation: GraphReviewObservation, step: int) -> ReviewAction:
    if "REQUEST_CONTEXT" in observation.available_actions and step <= 2:
        return ReviewAction(action_type="REQUEST_CONTEXT", context_request="upstream dependency module")
    if "ADD_COMMENT" in observation.available_actions:
        return ReviewAction(
            action_type="ADD_COMMENT",
            target_line=1,
            content="Potential issue requires confirmation from dependency context.",
        )
    if "REQUEST_CHANGES" in observation.available_actions:
        return ReviewAction(action_type="REQUEST_CHANGES")
    return ReviewAction(action_type="APPROVE")


def _action_to_log_string(action: ReviewAction) -> str:
    parts = [f"action_type={action.action_type}"]
    if action.target_line is not None:
        parts.append(f"target_line={action.target_line}")
    if action.content:
        parts.append(f"content={action.content[:90]}")
    if action.attributed_to:
        parts.append(f"attributed_to={action.attributed_to}")
    if action.context_request:
        parts.append(f"context_request={action.context_request}")
    return ";".join(parts)


def _propose_action(client: OpenAI, observation: GraphReviewObservation, step: int) -> ReviewAction:
    prompt = _build_prompt(observation=observation, step=step)
    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "Return valid JSON only. No markdown."},
            {"role": "user", "content": prompt},
        ],
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        stream=False,
    )
    text = (completion.choices[0].message.content or "{}").strip()
    payload = json.loads(text)
    if not isinstance(payload, dict):
        return _fallback_action(observation=observation, step=step)

    action_type = str(payload.get("action_type", "")).strip().upper()
    if not action_type:
        return _fallback_action(observation=observation, step=step)

    if observation.available_actions and action_type not in observation.available_actions:
        return _fallback_action(observation=observation, step=step)

    target_line_raw = payload.get("target_line")
    target_line = None
    if isinstance(target_line_raw, int) and target_line_raw > 0:
        target_line = target_line_raw

    return ReviewAction(
        action_type=action_type,
        target_line=target_line,
        content=str(payload.get("content", "")).strip() or None,
        attributed_to=str(payload.get("attributed_to", "")).strip() or None,
        context_request=str(payload.get("context_request", "")).strip() or None,
    )


def _normalize_score(rewards: list[float]) -> float:
    if not rewards:
        return 0.0
    avg = sum(rewards) / float(len(rewards))
    # Reward scales vary by grader, so use bounded transform to keep score in [0, 1].
    score = 1.0 / (1.0 + (2.718281828 ** (-avg)))
    return max(0.0, min(1.0, score))


def _build_env() -> GraphReviewClient:
    if LOCAL_IMAGE_NAME:
        # LOCAL_IMAGE_NAME is accepted for contract compatibility;
        # this runner connects to the serving endpoint configured in GRAPHREVIEW_BASE_URL.
        pass
    return GraphReviewClient(base_url=ENV_BASE_URL)


def _run_single_task(task_name: str, model_client: OpenAI) -> None:
    env = _build_env()
    rewards: list[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)
    try:
        try:
            result = env.reset(task_id=task_name)
        except Exception:
            return

        for step in range(1, MAX_STEPS + 1):
            if result.done:
                break

            try:
                action = _propose_action(model_client, result.observation, step)
            except Exception:
                action = _fallback_action(result.observation, step)

            error: str | None = None
            try:
                result = env.step(action)
                reward = float(result.reward or 0.0)
                done = bool(result.done)
            except Exception as exc:
                reward = 0.0
                done = False
                error = str(exc)

            rewards.append(reward)
            steps_taken = step
            log_step(
                step=step,
                action=_action_to_log_string(action),
                reward=reward,
                done=done,
                error=error,
            )
            if done:
                break

        score = _normalize_score(rewards)
        success = score >= SUCCESS_SCORE_THRESHOLD
    finally:
        try:
            env.close()
        finally:
            log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


def _run_submission_mode() -> None:
    api_key = HF_TOKEN or ""
    model_client = OpenAI(base_url=API_BASE_URL, api_key=api_key)
    for task in TASKS:
        _run_single_task(task_name=task, model_client=model_client)


def main() -> None:
    if _is_training_mode(sys.argv):
        training_main()
        return
    _run_submission_mode()


if __name__ == "__main__":
    main()
