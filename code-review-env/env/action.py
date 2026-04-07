from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, model_validator


class ActionType(StrEnum):
    FLAG_STYLE = "FLAG_STYLE"
    FLAG_BUG = "FLAG_BUG"
    FLAG_SECURITY = "FLAG_SECURITY"
    FLAG_DEPENDENCY_ISSUE = "FLAG_DEPENDENCY_ISSUE"
    ADD_COMMENT = "ADD_COMMENT"
    REQUEST_CONTEXT = "REQUEST_CONTEXT"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    APPROVE = "APPROVE"
    AMEND_REVIEW = "AMEND_REVIEW"


class ReviewAction(BaseModel):
    """Validated action envelope for grading and persistence."""

    model_config = ConfigDict(strict=True, extra="forbid")

    action_type: ActionType
    target_line: int | None = None
    content: str | None = None
    attributed_to: str | None = None
    context_request: str | None = None

    @model_validator(mode="after")
    def validate_required_fields(self) -> "ReviewAction":
        content_required = {
            ActionType.ADD_COMMENT,
            ActionType.AMEND_REVIEW,
        }
        if self.action_type in content_required and not (self.content and self.content.strip()):
            raise ValueError("content is required for ADD_COMMENT and AMEND_REVIEW")

        if self.action_type == ActionType.REQUEST_CONTEXT and not (
            self.context_request and self.context_request.strip()
        ):
            raise ValueError("context_request is required for REQUEST_CONTEXT")

        if self.target_line is not None and self.target_line <= 0:
            raise ValueError("target_line must be positive")

        return self
