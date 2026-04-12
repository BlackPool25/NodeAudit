from __future__ import annotations

import json
import os
import re
from importlib import import_module
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from huggingface_hub import hf_hub_download

from env.action import ActionType, ReviewAction
from env.observation import CodeObservation


THINK_PATTERN = re.compile(r"<think>(.*?)</think>", re.DOTALL | re.IGNORECASE)
ACTION_PATTERN = re.compile(r"<action>(.*?)</action>", re.DOTALL | re.IGNORECASE)


def extract_thinking_and_action(output: str) -> tuple[str, dict[str, Any]]:
    think_match = THINK_PATTERN.search(output)
    action_match = ACTION_PATTERN.search(output)
    thinking_trace = think_match.group(1).strip() if think_match else ""
    if not action_match:
        return thinking_trace, {}
    raw_action = action_match.group(1).strip()
    try:
        payload = json.loads(raw_action)
    except json.JSONDecodeError:
        return thinking_trace, {}
    return thinking_trace, payload if isinstance(payload, dict) else {}


@dataclass(frozen=True)
class AgentResponse:
    thinking_trace: str
    action: ReviewAction
    raw_output: str


class GemmaAgentRunner:
    """Graph-aware review agent backed by Gemma 4 GGUF through llama-cpp-python."""

    def __init__(self, model_path: str | None = None, hf_token: str | None = None) -> None:
        self.repo_id = os.getenv("GRAPHREVIEW_AGENT_MODEL_REPO", "unsloth/gemma-4-E4B-it-GGUF")
        self.filename = os.getenv("GRAPHREVIEW_AGENT_MODEL_FILE", "gemma-4-E4B-it-Q6_K.gguf")
        self.hf_token = hf_token or os.getenv("HF_TOKEN")
        self.local_model_path = Path(model_path).resolve() if model_path else self._download_model()

        llama_cls = getattr(import_module("llama_cpp"), "Llama")
        self.llm = llama_cls(
            model_path=str(self.local_model_path),
            n_ctx=int(os.getenv("GRAPHREVIEW_AGENT_N_CTX", "4096")),
            n_gpu_layers=int(os.getenv("GRAPHREVIEW_AGENT_N_GPU_LAYERS", "35")),
            n_threads=int(os.getenv("GRAPHREVIEW_AGENT_N_THREADS", "4")),
            verbose=False,
        )
        self.temperature = float(os.getenv("GRAPHREVIEW_AGENT_TEMPERATURE", "0.6"))
        self.top_p = float(os.getenv("GRAPHREVIEW_AGENT_TOP_P", "0.95"))
        self.repeat_penalty = float(os.getenv("GRAPHREVIEW_AGENT_REPEAT_PENALTY", "1.1"))
        self.max_tokens = int(os.getenv("GRAPHREVIEW_AGENT_MAX_TOKENS", "1024"))

    def _download_model(self) -> Path:
        cache_dir = Path(os.getenv("GRAPHREVIEW_MODEL_CACHE", "Models")).resolve()
        cache_dir.mkdir(parents=True, exist_ok=True)
        local_file = hf_hub_download(
            repo_id=self.repo_id,
            filename=self.filename,
            token=self.hf_token,
            local_dir=str(cache_dir),
            local_dir_use_symlinks=False,
        )
        return Path(local_file).resolve()

    def run(self, observation: CodeObservation) -> AgentResponse:
        prompt = self._build_prompt(observation)
        completion = self.llm.create_completion(
            prompt=prompt,
            temperature=self.temperature,
            top_p=self.top_p,
            repeat_penalty=self.repeat_penalty,
            max_tokens=self.max_tokens,
            stop=["</action>"],
        )
        text = str(completion["choices"][0]["text"])
        if "</action>" not in text:
            text = text + "</action>"

        thinking_trace, action_payload = self._extract_output(text)
        action = self._to_action(action_payload, observation)
        return AgentResponse(thinking_trace=thinking_trace, action=action, raw_output=text)

    def _build_prompt(self, observation: CodeObservation) -> str:
        dependencies = "\n".join(
            f"- {item.module_id}: {item.summary}" for item in observation.dependency_summaries[:6]
        ) or "- none"
        dependents = "\n".join(
            f"- {item.module_id}: {item.summary}" for item in observation.dependent_summaries[:6]
        ) or "- none"
        neighbor_reviews = "\n".join(f"- {item}" for item in observation.neighbor_reviews[:6]) or "- none"
        actions = ", ".join(observation.available_actions)
        ast_summary = json.dumps(observation.ast_summary, ensure_ascii=True)

        return (
            "<system>\n"
            "You are a code review agent. You review Python modules in dependency order.\n"
            "For each module, you MUST think before acting.\n\n"
            "Output format - STRICT:\n"
            "<think>\n"
            "[Your reasoning: what does this module do, what dependencies does it have,\n"
            "what upstream modules could cause issues here, what is the root cause vs symptom,\n"
            "how confident are you and why]\n"
            "</think>\n"
            "<action>\n"
            "{\"action_type\": \"...\", \"target_line\": null, \"content\": \"...\", \"attributed_to\": null}\n"
            "</action>\n\n"
            "Rules:\n"
            "- Think before EVERY action\n"
            "- For FLAG_DEPENDENCY_ISSUE: attributed_to must be a real module_id from the graph\n"
            "- For APPROVE: only if you are confident no high-severity findings exist\n"
            "- REQUEST_CONTEXT costs reward - only use if you cannot attribute without it\n"
            "</system>\n\n"
            "<observation>\n"
            f"Module: {observation.module_id}\n"
            f"Code:\n{observation.code}\n\n"
            f"AST Summary: {ast_summary}\n"
            f"Dependencies: {dependencies}\n"
            f"Dependents: {dependents}\n"
            f"Prior neighbor reviews: {neighbor_reviews}\n"
            f"Task: {observation.task_description}\n"
            f"Available actions: {actions}\n"
            f"Token budget remaining: {observation.token_usage}\n"
            "</observation>\n\n"
            "Respond now with <think> followed by <action>.\n"
            "<think>"
        )

    def _extract_output(self, output: str) -> tuple[str, dict[str, Any]]:
        return extract_thinking_and_action(output)

    def _to_action(self, payload: dict[str, Any], observation: CodeObservation) -> ReviewAction:
        allowed = set(observation.available_actions)
        action_name = str(payload.get("action_type") or "").strip().upper()
        if action_name not in allowed:
            if "REQUEST_CONTEXT" in allowed:
                return ReviewAction(action_type=ActionType.REQUEST_CONTEXT, context_request=observation.module_id)
            if "REQUEST_CHANGES" in allowed:
                return ReviewAction(action_type=ActionType.REQUEST_CHANGES)
            return ReviewAction(action_type=ActionType.APPROVE)

        target_line = payload.get("target_line")
        normalized_line = target_line if isinstance(target_line, int) and target_line > 0 else None
        content = str(payload.get("content") or "").strip() or None
        attributed_to = str(payload.get("attributed_to") or "").strip() or None
        context_request = str(payload.get("context_request") or "").strip() or None

        return ReviewAction(
            action_type=ActionType(action_name),
            target_line=normalized_line,
            content=content,
            attributed_to=attributed_to,
            context_request=context_request,
        )
