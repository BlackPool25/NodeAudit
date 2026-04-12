from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path


@dataclass(frozen=True)
class TrainingInputs:
    trajectories_path: Path
    dpo_pairs_path: Path
    output_dir: Path
    hf_repo: str | None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Unsloth AMD LoRA training pipeline for NodeAudit")
    parser.add_argument("--trajectories", required=True, help="JSONL produced by trajectory collector")
    parser.add_argument("--dpo-pairs", required=True, help="JSONL preference pairs")
    parser.add_argument("--output-dir", default="outputs", help="Output root")
    parser.add_argument("--push-repo", default=None, help="Optional HF repo for GGUF push")
    return parser


def _build_inputs(args: argparse.Namespace) -> TrainingInputs:
    return TrainingInputs(
        trajectories_path=Path(args.trajectories).resolve(),
        dpo_pairs_path=Path(args.dpo_pairs).resolve(),
        output_dir=Path(args.output_dir).resolve(),
        hf_repo=args.push_repo,
    )


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _trajectory_to_sft_dataset(rows: list[dict[str, object]]):
    examples: list[dict[str, str]] = []
    for episode in rows:
        for step in episode.get("steps", []):
            if not isinstance(step, dict):
                continue
            prompt = str(step.get("prompt") or "")
            thinking = str(step.get("thinking_trace") or "")
            action_json = str(step.get("action_json") or "{}")
            text = f"{prompt}\n<think>\n{thinking}\n</think>\n<action>\n{action_json}\n</action>"
            examples.append({"text": text})

    # Maintain strong reasoning traces in SFT corpus.
    reasoning_examples = [item for item in examples if "<think>" in item["text"]]
    if examples and (len(reasoning_examples) / len(examples)) < 0.75:
        needed = int(0.75 * len(examples)) - len(reasoning_examples)
        examples.extend(reasoning_examples[: max(needed, 0)])

    dataset_cls = getattr(import_module("datasets"), "Dataset")
    return dataset_cls.from_list(examples)


def _pairs_to_dataset(rows: list[dict[str, object]]):
    records: list[dict[str, str]] = []
    for row in rows:
        prompt = str(row.get("prompt") or "")
        chosen = str(row.get("chosen") or "")
        rejected = str(row.get("rejected") or "")
        if not prompt or not chosen or not rejected:
            continue
        records.append({"prompt": prompt, "chosen": chosen, "rejected": rejected})
    dataset_cls = getattr(import_module("datasets"), "Dataset")
    return dataset_cls.from_list(records)


def train(inputs: TrainingInputs) -> dict[str, str]:
    FastLanguageModel = getattr(import_module("unsloth"), "FastLanguageModel")
    trl_mod = import_module("trl")
    SFTTrainer = getattr(trl_mod, "SFTTrainer")
    SFTConfig = getattr(trl_mod, "SFTConfig")
    DPOTrainer = getattr(trl_mod, "DPOTrainer")
    DPOConfig = getattr(trl_mod, "DPOConfig")

    run_id = f"tr-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    output_root = inputs.output_dir / run_id
    lora_dir = output_root / "lora_weights"
    dpo_dir = output_root / "dpo"
    gguf_dir = output_root / "gemma4-nodeaudit"

    output_root.mkdir(parents=True, exist_ok=True)

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/gemma-4-E4B-it",
        max_seq_length=2048,
        load_in_4bit=False,
        load_in_16bit=True,
        full_finetuning=False,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        lora_alpha=16,
        lora_dropout=0,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        use_gradient_checkpointing="unsloth",
        bias="none",
    )

    trajectory_rows = _load_jsonl(inputs.trajectories_path)
    pair_rows = _load_jsonl(inputs.dpo_pairs_path)

    sft_dataset = _trajectory_to_sft_dataset(trajectory_rows)
    dpo_dataset = _pairs_to_dataset(pair_rows)

    sft_trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=sft_dataset,
        dataset_text_field="text",
        args=SFTConfig(
            per_device_train_batch_size=2,
            gradient_accumulation_steps=8,
            num_train_epochs=3,
            learning_rate=2e-4,
            lr_scheduler_type="cosine",
            warmup_ratio=0.1,
            bf16=True,
            logging_steps=5,
            save_strategy="epoch",
            output_dir=str(lora_dir),
        ),
    )
    sft_trainer.train()

    dpo_trainer = DPOTrainer(
        model=model,
        ref_model=None,
        args=DPOConfig(beta=0.1, max_length=2048, bf16=True, output_dir=str(dpo_dir)),
        train_dataset=dpo_dataset,
        tokenizer=tokenizer,
    )
    dpo_trainer.train()

    model.save_pretrained(str(lora_dir))
    tokenizer.save_pretrained(str(lora_dir))
    model.save_pretrained_gguf(str(gguf_dir), tokenizer, quantization_method="q6_k")

    if inputs.hf_repo:
        hf_token = os.getenv("HF_TOKEN")
        if not hf_token:
            raise RuntimeError("HF_TOKEN is required when --push-repo is set")
        model.push_to_hub_gguf(
            inputs.hf_repo,
            tokenizer,
            quantization_method="q6_k",
            token=hf_token,
        )

    metadata = {
        "run_id": run_id,
        "lora_dir": str(lora_dir),
        "dpo_dir": str(dpo_dir),
        "gguf_dir": str(gguf_dir),
        "dpo_pairs": str(len(dpo_dataset)),
    }
    meta_path = output_root / "train_metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "run_id": run_id,
        "lora_dir": str(lora_dir),
        "dpo_dir": str(dpo_dir),
        "gguf_dir": str(gguf_dir),
        "metadata": str(meta_path),
    }


def main() -> None:
    args = _parser().parse_args()
    inputs = _build_inputs(args)
    result = train(inputs)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
