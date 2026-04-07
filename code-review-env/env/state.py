from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModuleReviewState(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    module_id: str
    module_summary: str | None = None
    review_status: str
    latest_review_summary: str | None = None
    issues_found: int = 0
    last_action: str | None = None
    last_reward: float = 0.0
    updated_at: str


class EpisodeState(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    episode_id: str
    task_id: str
    current_module_id: str | None = None
    modules_remaining: int
    step_count: int
    cumulative_reward: float
    done: bool
    status: str


class GraphState(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    episode: EpisodeState
    modules: list[ModuleReviewState] = Field(default_factory=list)
    module_count: int
    edge_count: int
    annotation_count: int
    total_annotation_count: int = 0
