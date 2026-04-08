from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from env.env_loader import load_env_file


@dataclass(frozen=True)
class RuntimeConfig:
    llm_provider: str
    llm_base_url: str
    llm_api_key: str
    llm_model_agent: str
    llm_model_training: str
    llm_model_judge: str
    llm_model_agent_path: str
    llm_weight_manifest_dir: str
    max_steps_per_episode: int


def load_runtime_config() -> RuntimeConfig:
    load_env_file()
    default_model_path = str(
        (Path(__file__).resolve().parents[2] / "Models" / "Qwen2.5-Coder-7B-Instruct-Q6_K.gguf").resolve()
    )
    return RuntimeConfig(
        llm_provider=os.getenv("GRAPHREVIEW_LLM_PROVIDER", "ollama_openai_compat"),
        llm_base_url=os.getenv("GRAPHREVIEW_LLM_BASE_URL", "http://localhost:11434/v1"),
        llm_api_key=os.getenv("GRAPHREVIEW_LLM_API_KEY", "ollama"),
        llm_model_agent=os.getenv("GRAPHREVIEW_LLM_MODEL_AGENT", "qwen2.5-coder-7b-instruct-q6_k"),
        llm_model_training=os.getenv("GRAPHREVIEW_LLM_MODEL_TRAINING", "qwen2.5-coder-7b-instruct-q6_k"),
        llm_model_judge=os.getenv("GRAPHREVIEW_LLM_MODEL_JUDGE", "gemma4:e4b"),
        llm_model_agent_path=os.getenv("GRAPHREVIEW_QWEN_GGUF_PATH", default_model_path),
        llm_weight_manifest_dir=os.getenv("GRAPHREVIEW_WEIGHT_MANIFEST_DIR", "outputs/weights"),
        max_steps_per_episode=int(os.getenv("GRAPHREVIEW_MAX_STEPS_PER_EPISODE", "80")),
    )
