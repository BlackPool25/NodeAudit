from __future__ import annotations

import json
import os
from dataclasses import dataclass

from openai import OpenAI


@dataclass(frozen=True)
class ProposedIssue:
    category: str
    severity: str
    line: int
    title: str
    rationale: str
    confidence: float


class HardIssueFinder:
    """LLM-driven hard-mode issue discovery with strict JSON output."""

    def __init__(self) -> None:
        self.enabled = os.getenv("GRAPHREVIEW_HARD_ISSUE_FINDER_ENABLED", "true").strip().lower() == "true"
        if os.getenv("PYTEST_CURRENT_TEST"):
            self.enabled = False
        self.model = os.getenv("GRAPHREVIEW_HARD_ISSUE_FINDER_MODEL", os.getenv("GRAPHREVIEW_LLM_MODEL_AGENT", "gemma4:e4b"))
        self.base_url = os.getenv("GRAPHREVIEW_HARD_ISSUE_FINDER_BASE_URL", os.getenv("GRAPHREVIEW_LLM_BASE_URL", "http://localhost:11434/v1"))
        self.api_key = os.getenv("GRAPHREVIEW_HARD_ISSUE_FINDER_API_KEY", os.getenv("GRAPHREVIEW_LLM_API_KEY", "ollama"))
        self.timeout = float(os.getenv("GRAPHREVIEW_HARD_ISSUE_FINDER_TIMEOUT_SECONDS", "12"))
        self.max_issues = int(os.getenv("GRAPHREVIEW_HARD_ISSUE_FINDER_MAX_ISSUES", "4"))

    def propose(self, module_id: str, raw_code: str, ast_summary: str) -> list[ProposedIssue]:
        if not self.enabled:
            return []

        payload = {
            "module_id": module_id,
            "ast_summary": ast_summary,
            "raw_code": raw_code,
            "rules": {
                "only_real_bugs": True,
                "avoid_style_only": True,
                "max_issues": self.max_issues,
            },
            "output_schema": {
                "issues": [
                    {
                        "category": "style|bug|security|logic|dependency",
                        "severity": "low|medium|high",
                        "line": 1,
                        "title": "short title",
                        "rationale": "why this is a real bug and concrete impact",
                        "confidence": 0.0,
                    }
                ]
            },
        }

        try:
            client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout)
            resp = client.chat.completions.create(
                model=self.model,
                temperature=0.0,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are the agent in a dependency-aware RL code review environment.\n\n"
                            "Your job is to reason from source code only and propose concrete bugs with evidence. "
                            "You are not allowed to rely on external analyzer outputs, prior findings, or hidden hints.\n\n"
                            "Prioritize logical and dependency-linked defects, including nullable flows and cascade risks. "
                            "For each proposed issue, anchor the rationale to exact code behavior and likely runtime impact.\n\n"
                            "Reject style-only observations and uncertain speculation. Return strictly valid JSON that matches the requested schema."
                        ),
                    },
                    {"role": "user", "content": json.dumps(payload, sort_keys=True)},
                ],
            )
            text = (resp.choices[0].message.content or "{}").strip()
            parsed = self._parse_json(text)
        except Exception:
            return []

        issues = parsed.get("issues", [])
        if not isinstance(issues, list):
            return []

        proposals: list[ProposedIssue] = []
        for item in issues[: self.max_issues]:
            if not isinstance(item, dict):
                continue
            try:
                proposals.append(
                    ProposedIssue(
                        category=str(item.get("category", "bug")),
                        severity=str(item.get("severity", "medium")),
                        line=max(1, int(item.get("line", 1))),
                        title=str(item.get("title", "Potential bug"))[:120],
                        rationale=str(item.get("rationale", ""))[:800],
                        confidence=float(item.get("confidence", 0.0)),
                    )
                )
            except Exception:
                continue
        return proposals

    @staticmethod
    def _parse_json(text: str) -> dict[str, object]:
        try:
            loaded = json.loads(text)
            return loaded if isinstance(loaded, dict) else {}
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                loaded = json.loads(text[start : end + 1])
                return loaded if isinstance(loaded, dict) else {}
            return {}
