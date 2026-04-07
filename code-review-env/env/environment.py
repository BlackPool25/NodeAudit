from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select

from db.schema import ModuleNode
from db.seed import seed_project
from db.store import Store
from env.action import ActionType, ReviewAction
from env.observation import CodeObservation
from env.observation_builder import ObservationBuilder
from env.runtime_config import RuntimeConfig, load_runtime_config
from env.state import EpisodeState, GraphState, ModuleReviewState
from graph.graph_manager import GraphManager
from graders.base_grader import EpisodeState as GraderEpisodeState
from graders.base_grader import BaseGrader
from graders.easy_grader import EasyGrader
from graders.hard_grader import HardGrader
from graders.medium_grader import MediumGrader
from tasks.task_registry import TaskSpec, get_task, list_tasks, resolve_task_modules


class StepResult(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    observation: CodeObservation
    reward: float
    done: bool
    feedback: str
    episode_id: str


@dataclass
class _EpisodeRuntime:
    episode_id: str
    task: TaskSpec
    modules: list[str]
    module_index: int = 0
    step_count: int = 0
    cumulative_reward: float = 0.0
    done: bool = False
    module_steps: dict[str, int] = field(default_factory=dict)
    module_rewards: dict[str, float] = field(default_factory=dict)
    module_last_action: dict[str, str] = field(default_factory=dict)
    module_last_reward: dict[str, float] = field(default_factory=dict)
    grader_states: dict[str, GraderEpisodeState] = field(default_factory=dict)

    @property
    def current_module(self) -> str | None:
        if self.done:
            return None
        if self.module_index >= len(self.modules):
            return None
        return self.modules[self.module_index]

    @property
    def modules_remaining(self) -> int:
        return max(len(self.modules) - self.module_index, 0)


class CodeReviewEnv:
    """OpenEnv-style environment runtime backed by persistent SQLite state."""

    SUPPORTS_CONCURRENT_SESSIONS = False

    def __init__(
        self,
        source_root: str | Path = "sample_project",
        db_path: str | Path | None = None,
        runtime_config: RuntimeConfig | None = None,
    ) -> None:
        self.source_root = str(Path(source_root).resolve())
        self.db_path = str(db_path) if db_path is not None else None
        self.config = runtime_config or load_runtime_config()

        self.store = Store(source_root=self.source_root, db_path=self.db_path)
        self.graph_manager = GraphManager(source_root=self.source_root, db_path=self.db_path)
        self.observation_builder = ObservationBuilder(source_root=self.source_root, db_path=self.db_path)

        self._runtime: _EpisodeRuntime | None = None
        self._grader: BaseGrader | None = None

    def available_tasks(self) -> list[TaskSpec]:
        return list_tasks()

    def reset(
        self,
        task_id: str = "style_review",
        module_override: list[str] | None = None,
        seed: int | None = None,
        episode_id: str | None = None,
    ) -> CodeObservation:
        del seed
        if not self.store.has_nodes():
            seed_project(target_dir=Path(self.source_root), db_path=self.db_path, force=False)
            self.graph_manager.invalidate_cache()

        task = get_task(task_id)
        modules = resolve_task_modules(task, self.graph_manager, module_override=module_override)
        if not modules:
            raise ValueError(f"Task {task_id} has no resolvable modules in current graph")

        runtime = _EpisodeRuntime(
            episode_id=episode_id or str(uuid4()),
            task=task,
            modules=modules,
            module_steps={module_id: 0 for module_id in modules},
            module_rewards={module_id: 0.0 for module_id in modules},
            grader_states={module_id: GraderEpisodeState() for module_id in modules},
        )
        self._runtime = runtime
        self._grader = self._create_grader(task.grader)

        for module_id in modules:
            self.store.create_episode_record(runtime.episode_id, task.task_id, module_id)

        return self.observation_builder.build(
            module_id=modules[0],
            task_description=task.description,
        )

    def step(self, action: ReviewAction) -> StepResult:
        if self._runtime is None or self._grader is None:
            raise RuntimeError("Environment not initialized. Call reset() before step().")

        runtime = self._runtime
        module_id = runtime.current_module
        if module_id is None:
            runtime.done = True
            observation = self._build_terminal_observation(runtime)
            return StepResult(
                observation=observation,
                reward=0.0,
                done=True,
                feedback="Episode already complete",
                episode_id=runtime.episode_id,
            )

        findings = self._grader._sorted_findings(module_id)
        grader_state = runtime.grader_states[module_id]
        reward = self._grader.grade_action(
            module_id=module_id,
            action=action,
            findings=findings,
            state=grader_state,
        )
        grader_state.seen_actions.append(action)

        step_number = runtime.step_count + 1
        self._grader._persist_step(
            module_id=module_id,
            task_id=runtime.task.task_id,
            episode_id=runtime.episode_id,
            step_number=step_number,
            action=action,
            reward=reward,
        )

        runtime.step_count = step_number
        runtime.cumulative_reward += reward.raw_value
        runtime.module_steps[module_id] = runtime.module_steps.get(module_id, 0) + 1
        runtime.module_rewards[module_id] = runtime.module_rewards.get(module_id, 0.0) + reward.raw_value
        runtime.module_last_action[module_id] = action.action_type.value
        runtime.module_last_reward[module_id] = reward.raw_value

        self.store.update_episode_record(
            episode_id=runtime.episode_id,
            module_id=module_id,
            total_steps=runtime.module_steps[module_id],
            cumulative_reward=runtime.module_rewards[module_id],
        )

        end_module = action.action_type in {ActionType.APPROVE, ActionType.REQUEST_CHANGES}
        if end_module:
            runtime.module_index += 1

        if runtime.module_index >= len(runtime.modules):
            runtime.done = True
        if runtime.step_count >= max(runtime.task.max_steps, self.config.max_steps_per_episode):
            runtime.done = True

        next_module = runtime.current_module
        if runtime.done or next_module is None:
            observation = self._build_terminal_observation(runtime)
        else:
            context_request = action.context_request if action.action_type == ActionType.REQUEST_CONTEXT else None
            observation = self.observation_builder.build(
                module_id=next_module,
                task_description=runtime.task.description,
                context_request=context_request,
            )

        return StepResult(
            observation=observation,
            reward=reward.raw_value,
            done=runtime.done,
            feedback=reward.feedback,
            episode_id=runtime.episode_id,
        )

    def reset_episode_annotations(self) -> int:
        if self._runtime is None:
            return 0
        return self.store.clear_annotations_for_episode(self._runtime.episode_id)

    def state(self) -> GraphState:
        if self._runtime is None:
            raise RuntimeError("Environment not initialized. Call reset() first.")
        runtime = self._runtime

        snapshot = self.store.get_full_graph()
        annotations = self.store.get_review_annotations(episode_id=runtime.episode_id)
        last_by_module: dict[str, tuple[str, float]] = {}
        for annotation in annotations:
            last_by_module[annotation.module_id] = (annotation.action_type, annotation.reward_given)

        modules: list[ModuleReviewState] = []
        with Session(self.store.engine) as session:
            node_rows = list(
                session.exec(
                    select(ModuleNode).where(ModuleNode.source_root == self.store.config.source_root)
                ).all()
            )
        for node in sorted(node_rows, key=lambda item: item.module_id):
            action_name, last_reward = last_by_module.get(node.module_id, (None, 0.0))
            modules.append(
                ModuleReviewState(
                    module_id=node.module_id,
                    review_status=node.review_status.value,
                    issues_found=len(self.store.get_findings(node.module_id)),
                    last_action=action_name,
                    last_reward=last_reward,
                    updated_at=node.updated_at.isoformat(),
                )
            )

        return GraphState(
            episode=EpisodeState(
                episode_id=runtime.episode_id,
                task_id=runtime.task.task_id,
                current_module_id=runtime.current_module,
                modules_remaining=runtime.modules_remaining,
                step_count=runtime.step_count,
                cumulative_reward=runtime.cumulative_reward,
                done=runtime.done,
                status="complete" if runtime.done else "running",
            ),
            modules=modules,
            module_count=len(snapshot.nodes),
            edge_count=len(snapshot.edges),
            annotation_count=len(annotations),
        )

    def _create_grader(self, grader_name: str) -> BaseGrader:
        if grader_name == "easy":
            return EasyGrader(self.store)
        if grader_name == "medium":
            return MediumGrader(self.store)
        if grader_name == "hard":
            return HardGrader(self.store, self.graph_manager)
        raise ValueError(f"Unknown grader type: {grader_name}")

    def _build_terminal_observation(self, runtime: _EpisodeRuntime) -> CodeObservation:
        fallback = runtime.modules[-1]
        return self.observation_builder.build(
            module_id=fallback,
            task_description=f"{runtime.task.description} (episode complete)",
        )
