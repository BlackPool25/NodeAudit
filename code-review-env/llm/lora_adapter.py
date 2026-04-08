from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from env.action import ReviewAction


@dataclass(frozen=True)
class TransitionRecord:
    source_root: str
    episode_id: str
    module_id: str
    step_number: int
    action_type: str
    reward: float
    done: bool
    task_id: str
    observation_summary: str
    action_payload: dict[str, object]


class LoRATrajectoryLogger:
    """Append RL transitions to JSONL for optional LoRA fine-tuning workflows."""

    def __init__(self) -> None:
        self.enabled = os.getenv("GRAPHREVIEW_LORA_ENABLED", "false").strip().lower() == "true"
        output_path = os.getenv("GRAPHREVIEW_LORA_DATA_PATH", "outputs/lora/transitions.jsonl")
        self.path = Path(output_path)

    def log(
        self,
        *,
        source_root: str,
        episode_id: str,
        module_id: str,
        step_number: int,
        action: ReviewAction,
        reward: float,
        done: bool,
        task_id: str,
        observation_summary: str,
    ) -> None:
        if not self.enabled:
            return

        record = TransitionRecord(
            source_root=source_root,
            episode_id=episode_id,
            module_id=module_id,
            step_number=step_number,
            action_type=action.action_type.value,
            reward=reward,
            done=done,
            task_id=task_id,
            observation_summary=observation_summary,
            action_payload=action.model_dump(mode="json", exclude_none=True),
        )

        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            **record.__dict__,
            "created_at": datetime.now(UTC).isoformat(),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
