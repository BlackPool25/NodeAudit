from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Optional

from sqlmodel import Field, SQLModel


class EdgeType(StrEnum):
    EXPLICIT_IMPORT = "explicit_import"
    IMPLICIT_DEPENDENCY = "implicit_dependency"
    INTRA_FILE = "intra_file"
    CIRCULAR = "circular"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEWED = "reviewed"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ModuleNode(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_root: str = Field(index=True)
    module_id: str = Field(index=True)
    name: Optional[str] = None
    raw_code: str
    ast_summary: str
    summary: Optional[str] = None
    linter_flags: str = "[]"
    parent_module_id: Optional[str] = Field(default=None, index=True)
    is_chunk: bool = False
    dependency_reason: str = ""
    review_annotation: Optional[str] = None
    review_status: ReviewStatus = Field(default=ReviewStatus.PENDING)
    review_summary: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ModuleEdge(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_root: str = Field(index=True)
    source_module_id: str = Field(index=True)
    target_module_id: str = Field(index=True)
    edge_type: EdgeType = Field(default=EdgeType.EXPLICIT_IMPORT)
    import_line: str
    weight: float = 1.0


class LinterFinding(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_root: str = Field(index=True)
    module_id: str = Field(index=True)
    tool: str = Field(index=True)
    line: int
    severity: Severity
    code: str
    message: str


class ReviewAnnotation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_root: str = Field(index=True)
    module_id: str = Field(index=True)
    episode_id: str = Field(index=True)
    task_id: Optional[str] = Field(default=None, index=True)
    step_number: int
    action_type: str
    note: str
    reward_given: float = 0.0
    attributed_to: Optional[str] = Field(default=None, index=True)
    is_amendment: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EpisodeRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_root: str = Field(index=True)
    episode_id: str = Field(index=True)
    task_id: str = Field(index=True)
    module_id: str = Field(index=True)
    total_steps: int
    cumulative_reward: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TaskDefinition(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_root: str = Field(index=True)
    task_id: str = Field(index=True)
    task_level: str = Field(index=True)
    target_module_id: str = Field(index=True)
    description: str
    ground_truth_ref: str


class SeedMeta(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: str
