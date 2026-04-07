from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeConfig:
    llm_provider: str
    llm_base_url: str
    llm_api_key: str
    llm_model_agent: str
    llm_model_judge: str
    max_steps_per_episode: int


def load_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        llm_provider=os.getenv("GRAPHREVIEW_LLM_PROVIDER", "ollama_openai_compat"),
        llm_base_url=os.getenv("GRAPHREVIEW_LLM_BASE_URL", "http://localhost:11434/v1"),
        llm_api_key=os.getenv("GRAPHREVIEW_LLM_API_KEY", "ollama"),
        llm_model_agent=os.getenv("GRAPHREVIEW_LLM_MODEL_AGENT", "gemma4:e4b"),
        llm_model_judge=os.getenv("GRAPHREVIEW_LLM_MODEL_JUDGE", "gemma4:e4b"),
        max_steps_per_episode=int(os.getenv("GRAPHREVIEW_MAX_STEPS_PER_EPISODE", "80")),
    )
