from graph.token_budget import MAX_TOTAL_TOKENS, TokenBudget


def test_token_budget_enforces_hard_cap() -> None:
    budget = TokenBudget()
    huge = "x" * 50000

    result = budget.enforce(
        {
            "code": huge,
            "ast_summary_text": huge,
            "dependency_summaries": [huge, huge],
            "dependent_summaries": [huge],
            "neighbor_reviews": [huge],
            "task_description": huge,
            "available_actions": ["FLAG_BUG"],
            "requested_context_code": huge,
        }
    )

    assert result.total_tokens <= MAX_TOTAL_TOKENS


def test_token_budget_marks_truncation() -> None:
    budget = TokenBudget()
    huge = "z" * 20000

    result = budget.enforce(
        {
            "code": huge,
            "ast_summary_text": "{}",
            "dependency_summaries": [],
            "dependent_summaries": [],
            "neighbor_reviews": [],
            "task_description": "task",
            "available_actions": ["REQUEST_CONTEXT"],
            "requested_context_code": huge,
        }
    )

    trimmed_code = str(result.payload["code"])
    assert "[TRUNCATED]" in trimmed_code
