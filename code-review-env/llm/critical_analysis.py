from __future__ import annotations

import json
import os

from openai import OpenAI


def build_critical_analysis(
    *,
    model: str,
    base_url: str,
    api_key: str,
    run_payload: dict[str, object],
) -> str:
    fallback = _fallback_analysis(run_payload)
    enabled = os.getenv("GRAPHREVIEW_SUMMARIZER_ENABLED", "true").strip().lower() == "true"
    if not enabled:
        return fallback

    prompt = {
        "task": (
            "Generate a concise multi-paragraph critical analysis of a deterministic code-review training run. "
            "Focus on what was found, what was missed, and where false positives occurred. "
            "Do not change scores. This is non-scoring narrative only."
        ),
        "run": run_payload,
        "sections": [
            "Summary of model behavior",
            "Deterministic mismatch analysis",
            "Root-cause hypotheses for misses",
            "Actionable next training improvements",
        ],
    }

    try:
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=10.0)
        resp = client.chat.completions.create(
            model=model,
            temperature=0.0,
            messages=[
                {
                    "role": "system",
                    "content": "You write technical critical analysis for deterministic training results. Keep it factual and non-scoring.",
                },
                {"role": "user", "content": json.dumps(prompt, sort_keys=True)},
            ],
        )
        text = (resp.choices[0].message.content or "").strip()
        return text or fallback
    except Exception:
        return fallback


def _fallback_analysis(run_payload: dict[str, object]) -> str:
    tp = int(run_payload.get("true_positives", 0))
    fp = int(run_payload.get("false_positives", 0))
    fn = int(run_payload.get("false_negatives", 0))
    precision = float(run_payload.get("precision", 0.0))
    recall = float(run_payload.get("recall", 0.0))

    return (
        "Deterministic training analysis\n\n"
        f"The run produced precision={precision:.3f} and recall={recall:.3f}, with tp={tp}, fp={fp}, fn={fn}. "
        "This indicates the model either over-reported non-grounded issues or missed analyzer-verified findings.\n\n"
        "Priority improvements: tighten issue confidence calibration, improve dependency-cascade attribution prompts, "
        "and increase exposure to medium/hard deterministic labels during training data generation."
    )
