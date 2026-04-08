from __future__ import annotations

import argparse
import json
from pathlib import Path


def export_sft_dataset(transitions_path: Path, output_path: Path) -> int:
    """Convert transition logs into a simple instruction-tuning JSONL dataset."""
    if not transitions_path.exists():
        raise FileNotFoundError(f"Transitions file not found: {transitions_path}")

    rows = transitions_path.read_text(encoding="utf-8").splitlines()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with output_path.open("w", encoding="utf-8") as out:
        for row in rows:
            payload = json.loads(row)
            sample = {
                "instruction": (
                    "Review this module using graph-aware reasoning and choose the best next action."
                ),
                "input": payload.get("observation_summary", ""),
                "output": json.dumps(payload.get("action_payload", {}), sort_keys=True),
                "meta": {
                    "reward": payload.get("reward", 0.0),
                    "task_id": payload.get("task_id", ""),
                    "module_id": payload.get("module_id", ""),
                },
            }
            out.write(json.dumps(sample, sort_keys=True) + "\n")
            count += 1
    return count


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare LoRA fine-tuning dataset from GraphReview transitions")
    parser.add_argument(
        "--transitions",
        default="outputs/lora/transitions.jsonl",
        help="Input transition JSONL produced by runtime",
    )
    parser.add_argument(
        "--output",
        default="outputs/lora/sft_dataset.jsonl",
        help="Output SFT JSONL dataset path",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    count = export_sft_dataset(Path(args.transitions), Path(args.output))
    print(json.dumps({"ok": True, "samples": count, "output": args.output}, indent=2))


if __name__ == "__main__":
    main()
