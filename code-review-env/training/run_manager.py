from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TrainingComparison:
    true_positives: int
    false_positives: int
    false_negatives: int

    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom else 0.0


class TrainingRunManager:
    """Build training-ready datasets and metrics from deterministic findings and agent outputs."""

    def compare(self, deterministic_findings: set[str], agent_findings: set[str]) -> TrainingComparison:
        tp = len(deterministic_findings & agent_findings)
        fp = len(agent_findings - deterministic_findings)
        fn = len(deterministic_findings - agent_findings)
        return TrainingComparison(true_positives=tp, false_positives=fp, false_negatives=fn)

    def build_preference_record(
        self,
        *,
        prompt: str,
        agent_output: str,
        deterministic_targets: list[str],
        reward: float,
    ) -> dict[str, object]:
        return {
            "prompt": prompt,
            "agent_output": agent_output,
            "deterministic_targets": deterministic_targets,
            "reward": reward,
        }

    def save_records(self, path: Path, records: list[dict[str, object]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, sort_keys=True) + "\n")

    def assert_non_regression(
        self,
        *,
        baseline_precision: float,
        baseline_recall: float,
        current_precision: float,
        current_recall: float,
        tolerance: float = 0.01,
    ) -> None:
        min_precision = baseline_precision - tolerance
        min_recall = baseline_recall - tolerance
        if current_precision < min_precision:
            raise ValueError(
                f"Precision regression detected: baseline={baseline_precision:.4f}, current={current_precision:.4f}"
            )
        if current_recall < min_recall:
            raise ValueError(
                f"Recall regression detected: baseline={baseline_recall:.4f}, current={current_recall:.4f}"
            )
