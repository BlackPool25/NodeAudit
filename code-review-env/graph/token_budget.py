from __future__ import annotations

import math
from dataclasses import dataclass

MAX_TOTAL_TOKENS = 2000

COMPONENT_LIMITS: dict[str, int] = {
    "current_code": 800,
    "ast_summary": 100,
    "direct_deps": 250,
    "dependents": 150,
    "neighbor_reviews": 120,
    "task_and_actions": 200,
    "requested_context": 800,
}


def estimate_tokens(text: str) -> int:
    """Deterministic approximation with conservative floor for non-empty text."""
    if not text:
        return 0
    return max(1, int(math.ceil(len(text) / 4)))


def truncate_to_budget(text: str, max_tokens: int, suffix_notice: str = "\n... [TRUNCATED]") -> str:
    if max_tokens <= 0:
        return ""

    current = estimate_tokens(text)
    if current <= max_tokens:
        return text

    notice_tokens = estimate_tokens(suffix_notice)
    content_budget = max(max_tokens - notice_tokens, 0)
    max_chars = content_budget * 4
    trimmed = text[:max_chars]
    return f"{trimmed}{suffix_notice}" if trimmed else suffix_notice.strip()


@dataclass(frozen=True)
class BudgetResult:
    payload: dict[str, object]
    token_usage: dict[str, int]
    total_tokens: int


class TokenBudget:
    def __init__(self, max_total_tokens: int = MAX_TOTAL_TOKENS) -> None:
        self.max_total_tokens = max_total_tokens

    def _trim_component(self, text: str, component_name: str) -> str:
        limit = COMPONENT_LIMITS.get(component_name, self.max_total_tokens)
        return truncate_to_budget(text, limit)

    def enforce(self, payload: dict[str, object]) -> BudgetResult:
        normalized = dict(payload)
        usage: dict[str, int] = {}

        current_code = str(normalized.get("code", ""))
        ast_summary = str(normalized.get("ast_summary_text", ""))
        dep_text = "\n".join(str(item) for item in normalized.get("dependency_summaries", []))
        dependent_text = "\n".join(str(item) for item in normalized.get("dependent_summaries", []))
        review_text = "\n".join(str(item) for item in normalized.get("neighbor_reviews", []))
        task_actions = "\n".join(
            [
                str(normalized.get("task_description", "")),
                " ".join(str(a) for a in normalized.get("available_actions", [])),
            ]
        )
        requested_context = str(normalized.get("requested_context_code", ""))

        current_code = self._trim_component(current_code, "current_code")
        ast_summary = self._trim_component(ast_summary, "ast_summary")
        dep_text = self._trim_component(dep_text, "direct_deps")
        dependent_text = self._trim_component(dependent_text, "dependents")
        review_text = self._trim_component(review_text, "neighbor_reviews")
        task_actions = self._trim_component(task_actions, "task_and_actions")
        requested_context = self._trim_component(requested_context, "requested_context")

        normalized["code"] = current_code
        normalized["ast_summary_text"] = ast_summary
        normalized["dependency_summaries_text"] = dep_text
        normalized["dependent_summaries_text"] = dependent_text
        normalized["neighbor_reviews_text"] = review_text
        normalized["task_actions_text"] = task_actions
        normalized["requested_context_code"] = requested_context

        usage["current_code"] = estimate_tokens(current_code)
        usage["ast_summary"] = estimate_tokens(ast_summary)
        usage["direct_deps"] = estimate_tokens(dep_text)
        usage["dependents"] = estimate_tokens(dependent_text)
        usage["neighbor_reviews"] = estimate_tokens(review_text)
        usage["task_and_actions"] = estimate_tokens(task_actions)
        usage["requested_context"] = estimate_tokens(requested_context)

        total = sum(usage.values())
        if total > self.max_total_tokens:
            overflow = total - self.max_total_tokens
            requested_limit = max(estimate_tokens(requested_context) - overflow, 0)
            requested_context = truncate_to_budget(requested_context, requested_limit)
            normalized["requested_context_code"] = requested_context
            usage["requested_context"] = estimate_tokens(requested_context)
            total = sum(usage.values())

        if total > self.max_total_tokens:
            overflow = total - self.max_total_tokens
            code_limit = max(estimate_tokens(current_code) - overflow, 0)
            current_code = truncate_to_budget(current_code, code_limit)
            normalized["code"] = current_code
            usage["current_code"] = estimate_tokens(current_code)
            total = sum(usage.values())

        if total > self.max_total_tokens:
            raise ValueError("Unable to enforce token budget within hard limit")

        return BudgetResult(payload=normalized, token_usage=usage, total_tokens=total)
