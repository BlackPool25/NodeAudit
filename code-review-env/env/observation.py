from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from graph.token_budget import MAX_TOTAL_TOKENS


class NeighborSummary(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    module_id: str
    relation: Literal["dependency", "dependent"]
    summary: str
    review_snippet: str | None = None


class RequestedContext(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    module_id: str
    code: str
    was_truncated: bool


class CodeObservation(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    module_id: str
    code: str
    ast_summary: dict[str, object]
    dependency_summaries: list[NeighborSummary] = Field(default_factory=list)
    dependent_summaries: list[NeighborSummary] = Field(default_factory=list)
    neighbor_reviews: list[str] = Field(default_factory=list)
    task_description: str
    available_actions: list[str] = Field(default_factory=list)
    requested_context: RequestedContext | None = None
    token_usage: dict[str, int]
    total_tokens: int
    within_budget: bool

    @field_validator("module_id", "code", "task_description")
    @classmethod
    def _must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Field cannot be empty")
        return value

    @field_validator("total_tokens")
    @classmethod
    def _budget_hard_cap(cls, value: int) -> int:
        if value > MAX_TOTAL_TOKENS:
            raise ValueError(f"total_tokens exceeds hard cap: {MAX_TOTAL_TOKENS}")
        return value

    @field_validator("within_budget")
    @classmethod
    def _must_be_true(cls, value: bool) -> bool:
        if not value:
            raise ValueError("within_budget must be True")
        return value
