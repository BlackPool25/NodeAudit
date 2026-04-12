from __future__ import annotations

import dataclasses
import json
import os
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from db.store import Store
from env.environment import CodeReviewEnv
from env.observation import CodeObservation
from llm.agent_runner import GemmaAgentRunner
from llm.thinking_judge import JudgeVerdict, ThinkingJudge


@dataclasses.dataclass(frozen=True)
class TrajectoryStep:
    module_id: str
    task_id: str
    step_number: int
    prompt: str
    thinking_trace: str
    action_json: str
    env_reward: float
    judge_score: float
    final_reward: float
    judge_verdict: str


@dataclasses.dataclass(frozen=True)
class TrajectoryEpisode:
    run_id: str
    episode_id: str
    task_id: str
    total_steps: int
    cumulative_reward: float
    steps: list[TrajectoryStep]


@dataclasses.dataclass(frozen=True)
class DPOPair:
    prompt: str
    chosen: str
    rejected: str


def compute_composite_reward(env_reward: float, judge_score: float) -> float:
    return min(1.0, max(0.0, (float(env_reward) * 0.6) + (float(judge_score) * 0.4)))


class TrajectoryCollector:
    def __init__(
        self,
        source_root: str,
        db_path: str | None = None,
        run_id: str | None = None,
    ) -> None:
        self.source_root = str(Path(source_root).resolve())
        self.db_path = db_path
        self.run_id = run_id or f"tr-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"

        self.store = Store(source_root=self.source_root, db_path=db_path)
        self.env = CodeReviewEnv(source_root=self.source_root, db_path=db_path)
        self.agent = GemmaAgentRunner(model_path=os.getenv("GRAPHREVIEW_GEMMA_GGUF_PATH"))
        self.judge = ThinkingJudge(model_name=os.getenv("JUDGE_MODEL", "Qwen/Qwen2.5-7B-Instruct"))

    def run_episodes(self, task_ids: list[str], episodes_per_task: int = 2) -> list[TrajectoryEpisode]:
        episodes: list[TrajectoryEpisode] = []
        for task_id in task_ids:
            for _ in range(max(episodes_per_task, 1)):
                observation = self.env.reset(task_id=task_id)
                state = self.env.state()
                episode_id = state.episode.episode_id
                step_index = 0
                done = False
                cumulative = 0.0
                rows: list[TrajectoryStep] = []

                while not done:
                    step_index += 1
                    prompt = self._observation_prompt(observation)
                    agent_out = self.agent.run(observation)
                    step_result = self.env.step(agent_out.action)

                    env_reward = self._normalize_reward(step_result.reward)
                    judge = self._maybe_judge(
                        observation=observation,
                        thinking_trace=agent_out.thinking_trace,
                        action_json=agent_out.action.model_dump_json(exclude_none=True),
                        action_type=agent_out.action.action_type.value,
                    )
                    judge_score = judge.score if judge is not None else 0.0
                    final_reward = compute_composite_reward(env_reward=env_reward, judge_score=judge_score)
                    cumulative += final_reward

                    verdict_summary = ""
                    if judge is not None:
                        verdict_summary = (
                            f"{judge.reasoning_depth} | right: {judge.what_was_right} | wrong: {judge.what_was_wrong}"
                        )

                    row = TrajectoryStep(
                        module_id=observation.module_id,
                        task_id=task_id,
                        step_number=step_index,
                        prompt=prompt,
                        thinking_trace=agent_out.thinking_trace,
                        action_json=agent_out.action.model_dump_json(exclude_none=True),
                        env_reward=env_reward,
                        judge_score=judge_score,
                        final_reward=final_reward,
                        judge_verdict=verdict_summary,
                    )
                    rows.append(row)

                    self._persist_step(row)

                    observation = step_result.observation
                    done = bool(step_result.done)

                episodes.append(
                    TrajectoryEpisode(
                        run_id=self.run_id,
                        episode_id=episode_id,
                        task_id=task_id,
                        total_steps=len(rows),
                        cumulative_reward=cumulative,
                        steps=rows,
                    )
                )
        return episodes

    def build_dpo_pairs(self, episodes: list[TrajectoryEpisode]) -> list[DPOPair]:
        grouped: dict[tuple[str, str, str], list[TrajectoryStep]] = defaultdict(list)
        for episode in episodes:
            for step in episode.steps:
                key = (step.task_id, step.module_id, step.prompt)
                grouped[key].append(step)

        pairs: list[DPOPair] = []
        for _, steps in grouped.items():
            best = max(steps, key=lambda item: item.final_reward)
            worst = min(steps, key=lambda item: item.final_reward)
            if best.final_reward <= 0.6 or worst.final_reward >= 0.3:
                continue
            pairs.append(
                DPOPair(
                    prompt=best.prompt,
                    chosen=self._response_block(best.thinking_trace, best.action_json),
                    rejected=self._response_block(worst.thinking_trace, worst.action_json),
                )
            )
            pairs.append(
                DPOPair(
                    prompt=best.prompt,
                    chosen=self._response_block(best.thinking_trace, best.action_json),
                    rejected=self._synthetic_wrong_attribution(best.action_json),
                )
            )
        return pairs

    def save_outputs(self, episodes: list[TrajectoryEpisode], dpo_pairs: list[DPOPair], output_dir: str = "outputs") -> dict[str, str]:
        root = Path(output_dir).resolve()
        root.mkdir(parents=True, exist_ok=True)

        trajectories_path = root / f"{self.run_id}_trajectories.jsonl"
        dpo_path = root / f"{self.run_id}_dpo_pairs.jsonl"
        stable_training_dir = root / "training"
        stable_training_dir.mkdir(parents=True, exist_ok=True)
        stable_dataset_path = stable_training_dir / "dataset.latest.jsonl"
        stable_dpo_path = stable_training_dir / "dpo_pairs.jsonl"

        with trajectories_path.open("w", encoding="utf-8") as handle:
            for episode in episodes:
                payload = dataclasses.asdict(episode)
                handle.write(json.dumps(payload, sort_keys=True) + "\n")

        with dpo_path.open("w", encoding="utf-8") as handle:
            for pair in dpo_pairs:
                handle.write(json.dumps(dataclasses.asdict(pair), sort_keys=True) + "\n")

        flat_records: list[dict[str, object]] = []
        for episode in episodes:
            for step in episode.steps:
                text = self._response_block(step.thinking_trace, step.action_json)
                flat_records.append(
                    {
                        "module_id": f"{Path(self.source_root).name}/{step.module_id}",
                        "task_id": step.task_id,
                        "text": text,
                        "chosen": text,
                        "reward": step.final_reward,
                    }
                )

        with stable_dataset_path.open("w", encoding="utf-8") as handle:
            for item in flat_records:
                handle.write(json.dumps(item, sort_keys=True) + "\n")

        with stable_dpo_path.open("w", encoding="utf-8") as handle:
            for pair in dpo_pairs:
                handle.write(json.dumps(dataclasses.asdict(pair), sort_keys=True) + "\n")

        return {
            "trajectories": str(trajectories_path),
            "dpo_pairs": str(dpo_path),
            "dataset_latest": str(stable_dataset_path),
            "dpo_pairs_latest": str(stable_dpo_path),
        }

    def _observation_prompt(self, observation: CodeObservation) -> str:
        deps = "\n".join(f"- {item.module_id}: {item.summary}" for item in observation.dependency_summaries)
        dependents = "\n".join(f"- {item.module_id}: {item.summary}" for item in observation.dependent_summaries)
        reviews = "\n".join(f"- {item}" for item in observation.neighbor_reviews)
        return (
            f"Module: {observation.module_id}\n"
            f"Code:\n{observation.code}\n\n"
            f"AST Summary: {json.dumps(observation.ast_summary, ensure_ascii=True)}\n"
            f"Dependencies:\n{deps or '- none'}\n"
            f"Dependents:\n{dependents or '- none'}\n"
            f"Prior neighbor reviews:\n{reviews or '- none'}\n"
            f"Task: {observation.task_description}\n"
            f"Available actions: {', '.join(observation.available_actions)}\n"
            f"Token budget remaining: {observation.token_usage}\n"
        )

    def _normalize_reward(self, raw_reward: float) -> float:
        clipped = max(-2.0, min(2.0, float(raw_reward)))
        return (clipped + 2.0) / 4.0

    def _maybe_judge(
        self,
        *,
        observation: CodeObservation,
        thinking_trace: str,
        action_json: str,
        action_type: str,
    ) -> JudgeVerdict | None:
        if action_type not in {"FLAG_DEPENDENCY_ISSUE", "APPROVE", "REQUEST_CHANGES"}:
            return None

        ground_truth = self.store.get_analyzer_findings_for_module(observation.module_id)
        best_finding = "none"
        if ground_truth:
            primary = sorted(
                ground_truth,
                key=lambda item: (item.severity.value != "high", item.line),
            )[0]
            best_finding = f"{primary.analyzer}:{primary.rule_id}:{primary.module_id}:{primary.line}:{primary.message}"

        graph_context = (
            f"module={observation.module_id};"
            f"deps={[item.module_id for item in observation.dependency_summaries]};"
            f"dependents={[item.module_id for item in observation.dependent_summaries]}"
        )

        try:
            return self.judge.score(
                finding=best_finding,
                thinking_trace=thinking_trace,
                action=self._action_from_json(action_json),
                graph_context=graph_context,
            )
        except Exception:
            return JudgeVerdict(
                score=0.0,
                causal_chain_correct=False,
                attribution_correct=False,
                reasoning_depth="shallow",
                what_was_right="",
                what_was_wrong="judge_call_failed",
            )

    def _action_from_json(self, action_json: str):
        from env.action import ActionType, ReviewAction

        payload = json.loads(action_json)
        action_type = ActionType(str(payload.get("action_type", "REQUEST_CHANGES")))
        return ReviewAction(
            action_type=action_type,
            target_line=payload.get("target_line"),
            content=payload.get("content"),
            attributed_to=payload.get("attributed_to"),
            context_request=payload.get("context_request"),
        )

    def _persist_step(self, step: TrajectoryStep) -> None:
        self.store.create_training_annotation(
            run_id=self.run_id,
            module_id=step.module_id,
            task_id=step.task_id,
            judge_verdict=step.judge_verdict,
            avg_reward=step.final_reward,
            action_type=json.loads(step.action_json).get("action_type", "UNKNOWN"),
            action_payload=step.action_json,
            thinking_quality=step.judge_score,
            correct_attribution="" if '"attributed_to"' not in step.action_json else "candidate",
            wrong_attribution="",
        )

    def _response_block(self, thinking: str, action_json: str) -> str:
        return f"<think>\n{thinking}\n</think>\n<action>\n{action_json}\n</action>"

    def _synthetic_wrong_attribution(self, action_json: str) -> str:
        try:
            payload = json.loads(action_json)
            payload["attributed_to"] = "__wrong_module__"
            rewritten = json.dumps(payload, ensure_ascii=True)
        except Exception:
            rewritten = '{"action_type":"FLAG_DEPENDENCY_ISSUE","attributed_to":"__wrong_module__"}'
        return f"<think>\nIncorrect attribution injected for contrast\n</think>\n<action>\n{rewritten}\n</action>"
