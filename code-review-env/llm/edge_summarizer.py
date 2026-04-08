from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass

from openai import OpenAI


@dataclass(frozen=True)
class EdgeSummaryInput:
    source_module_id: str
    target_module_id: str
    edge_type: str
    import_line: str
    scope: str


class EdgeSummarizer:
    """Generate concise edge relationship summaries with deterministic fallback."""

    def __init__(self) -> None:
        self.enabled = os.getenv("GRAPHREVIEW_EDGE_SUMMARY_ENABLED", "false").strip().lower() == "true"
        if os.getenv("PYTEST_CURRENT_TEST"):
            self.enabled = False
        self.base_url = os.getenv("GRAPHREVIEW_EDGE_SUMMARY_BASE_URL", os.getenv("GRAPHREVIEW_LLM_BASE_URL", "http://localhost:11434/v1"))
        self.api_key = os.getenv("GRAPHREVIEW_EDGE_SUMMARY_API_KEY", os.getenv("GRAPHREVIEW_LLM_API_KEY", "ollama"))
        self.model = os.getenv("GRAPHREVIEW_EDGE_SUMMARY_MODEL", os.getenv("GRAPHREVIEW_LLM_MODEL_AGENT", "gemma4:e4b"))
        self.timeout = float(os.getenv("GRAPHREVIEW_EDGE_SUMMARY_TIMEOUT_SECONDS", "8"))
        self.max_calls = int(os.getenv("GRAPHREVIEW_EDGE_SUMMARY_MAX_CALLS", "5000"))
        self._calls = 0
        self._cache: dict[str, str] = {}

    def summarize(self, edge: EdgeSummaryInput) -> str:
        payload = json.dumps(edge.__dict__, sort_keys=True)
        cache_key = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        if cache_key in self._cache:
            return self._cache[cache_key]

        summary = self._fallback_summary(edge)
        if self.enabled and self._calls < self.max_calls:
            try:
                self._calls += 1
                client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout)
                response = client.chat.completions.create(
                    model=self.model,
                    temperature=0.0,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You summarize Python dependency edges. Produce one sentence (max 24 words) "
                                "explaining why source depends on target using the import/call evidence."
                            ),
                        },
                        {"role": "user", "content": payload},
                    ],
                )
                text = (response.choices[0].message.content or "").strip()
                if text:
                    summary = text[:240]
            except Exception:
                # Keep deterministic fallback to avoid breaking seed.
                pass

        self._cache[cache_key] = summary
        return summary

    @staticmethod
    def _fallback_summary(edge: EdgeSummaryInput) -> str:
        edge_kind = edge.edge_type.replace("_", " ")
        evidence = edge.import_line.strip() or "implicit usage"
        if len(evidence) > 120:
            evidence = evidence[:117] + "..."
        return (
            f"{edge.source_module_id} depends on {edge.target_module_id} via {edge_kind}; "
            f"evidence: {evidence}."
        )
