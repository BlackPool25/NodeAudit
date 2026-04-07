from __future__ import annotations

from typing import TYPE_CHECKING

from parser.linter import LinterIssue

if TYPE_CHECKING:
    from parser.ast_parser import ParsedModule


def _truncate_tokens(text: str, max_tokens: int = 100) -> str:
    words = text.split()
    if len(words) <= max_tokens:
        return text
    return " ".join(words[:max_tokens])


def summarize_module(parsed: ParsedModule, issues: list[LinterIssue]) -> str:
    exports = ", ".join(parsed.function_signatures[:5])
    deps = ", ".join(sorted(set(parsed.dependencies))[:5])
    summary = (
        f"exports: [{exports}] | issues: {len(issues)} | depends_on: [{deps}]"
    )
    return _truncate_tokens(summary, max_tokens=100)
