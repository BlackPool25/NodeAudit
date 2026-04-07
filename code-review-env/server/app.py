from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from db.store import Store
from env.action import ActionType, ReviewAction
from env.environment import CodeReviewEnv, StepResult
from env.observation import CodeObservation
from env.state import GraphState


class ResetRequest(BaseModel):
	model_config = ConfigDict(strict=True, extra="forbid")

	task_id: str = "style_review"
	module_override: list[str] | None = None
	episode_id: str | None = None


class ResetResponse(BaseModel):
	model_config = ConfigDict(strict=True, extra="forbid")

	observation: CodeObservation


class StepRequest(BaseModel):
	model_config = ConfigDict(strict=True, extra="forbid")

	action: ReviewAction


class TaskRunRequest(BaseModel):
	model_config = ConfigDict(strict=True, extra="forbid")

	module_override: list[str] | None = None
	stop_on_first_done: bool = True


class TaskRunResponse(BaseModel):
	model_config = ConfigDict(strict=True, extra="forbid")

	episode_id: str
	total_steps: int
	total_reward: float
	modules_total: int
	modules_completed: int
	done: bool


class AccuracyReport(BaseModel):
	model_config = ConfigDict(strict=True, extra="forbid")

	episode_id: str
	true_positives: int
	false_positives: int
	false_negatives: int
	precision: float
	recall: float


def _default_source_root() -> str:
	configured = os.getenv("GRAPHREVIEW_SOURCE_ROOT", "sample_project")
	return str(Path(configured).resolve())


def _default_db_path() -> str | None:
	configured = os.getenv("GRAPHREVIEW_DB_PATH", "").strip()
	return configured or None


ENV = CodeReviewEnv(source_root=_default_source_root(), db_path=_default_db_path())
STORE = Store(source_root=_default_source_root(), db_path=_default_db_path())

app = FastAPI(title="GraphReview OpenEnv Server", version="0.4.0")


@app.get("/health")
def health() -> dict[str, object]:
	return {
		"ok": True,
		"source_root": ENV.source_root,
		"database_url_configured": bool(os.getenv("GRAPHREVIEW_DATABASE_URL", "").strip()),
		"turso_url_configured": bool(os.getenv("TURSO_DATABASE_URL", "").strip()),
	}


@app.get("/tasks")
def tasks() -> list[dict[str, object]]:
	return [
		{
			"task_id": task.task_id,
			"task_level": task.task_level,
			"description": task.description,
			"default_modules": task.default_modules,
			"grader": task.grader,
			"max_steps": task.max_steps,
		}
		for task in ENV.available_tasks()
	]


@app.post("/reset", response_model=ResetResponse)
def reset(payload: ResetRequest) -> ResetResponse:
	try:
		observation = ENV.reset(
			task_id=payload.task_id,
			module_override=payload.module_override,
			episode_id=payload.episode_id,
		)
	except Exception as exc:
		raise HTTPException(status_code=400, detail=str(exc)) from exc
	return ResetResponse(observation=observation)


@app.post("/step", response_model=StepResult)
def step(payload: StepRequest) -> StepResult:
	try:
		return ENV.step(payload.action)
	except Exception as exc:
		raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/state", response_model=GraphState)
def state() -> GraphState:
	try:
		return ENV.state()
	except Exception as exc:
		raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/debug/state", response_model=GraphState)
def debug_state() -> GraphState:
	return state()


@app.post("/debug/reset-annotations")
def debug_reset_annotations() -> dict[str, object]:
	cleared = ENV.reset_episode_annotations()
	return {"ok": True, "cleared_modules": cleared}


def _actions_for_module(module_id: str) -> list[ReviewAction]:
	findings = STORE.get_findings(module_id)
	actions: list[ReviewAction] = []
	for finding in findings:
		if finding.tool == "bandit":
			action_type = ActionType.FLAG_SECURITY
		elif finding.severity.value == "low":
			action_type = ActionType.FLAG_STYLE
		else:
			action_type = ActionType.FLAG_BUG
		actions.append(ReviewAction(action_type=action_type, target_line=max(1, finding.line)))
		actions.append(ReviewAction(action_type=ActionType.ADD_COMMENT, content=finding.message))

	if findings:
		actions.append(ReviewAction(action_type=ActionType.REQUEST_CHANGES))
	else:
		actions.append(ReviewAction(action_type=ActionType.APPROVE))
	return actions


@app.post("/tasks/{task_id}/run", response_model=TaskRunResponse)
def run_task(task_id: str, payload: TaskRunRequest) -> TaskRunResponse:
	try:
		observation = ENV.reset(task_id=task_id, module_override=payload.module_override)
	except Exception as exc:
		raise HTTPException(status_code=400, detail=str(exc)) from exc

	progress_enabled = os.getenv("GRAPHREVIEW_PROGRESS", "true").lower() == "true"
	state_snapshot = ENV.state()
	modules_total = len(state_snapshot.modules)
	if progress_enabled:
		print(f"[TASK] task={task_id} modules_total={modules_total}", flush=True)

	done = False
	total_reward = 0.0
	total_steps = 0
	episode_id = ""
	completed_modules: set[str] = set()

	while not done:
		module_id = observation.module_id
		if progress_enabled:
			print(
				f"[TASK] module={module_id} steps={total_steps} reward={total_reward:.2f}",
				flush=True,
			)
		actions = _actions_for_module(module_id)
		for action in actions:
			result = ENV.step(action)
			observation = result.observation
			episode_id = result.episode_id
			total_reward += result.reward
			total_steps += 1
			done = result.done
			if progress_enabled:
				print(
					f"[TASK] step={total_steps} action={action.action_type.value} reward={result.reward:.2f} done={done}",
					flush=True,
				)
			if done and payload.stop_on_first_done:
				break
		if actions and actions[-1].action_type in {ActionType.REQUEST_CHANGES, ActionType.APPROVE}:
			completed_modules.add(module_id)
		if done:
			break

	return TaskRunResponse(
		episode_id=episode_id,
		total_steps=total_steps,
		total_reward=total_reward,
		modules_total=modules_total,
		modules_completed=len(completed_modules),
		done=done,
	)


@app.get("/reports/accuracy", response_model=AccuracyReport)
def review_accuracy(episode_id: str = Query(default="")) -> AccuracyReport:
	if not episode_id:
		try:
			current_state = ENV.state()
			episode_id = current_state.episode.episode_id
		except Exception as exc:
			raise HTTPException(status_code=400, detail=f"Episode id required: {exc}") from exc

	annotations = STORE.get_review_annotations(episode_id=episode_id)
	if not annotations:
		raise HTTPException(status_code=404, detail=f"No annotations for episode {episode_id}")

	true_positives = 0
	false_positives = 0
	false_negatives = 0
	by_module: dict[str, set[int]] = {}
	for annotation in annotations:
		findings = STORE.get_findings(annotation.module_id)
		by_module.setdefault(annotation.module_id, set())
		if annotation.action_type in {
			ActionType.FLAG_STYLE.value,
			ActionType.FLAG_BUG.value,
			ActionType.FLAG_SECURITY.value,
		}:
			matched = False
			for finding in findings:
				if finding.id is not None and finding.id not in by_module[annotation.module_id]:
					by_module[annotation.module_id].add(finding.id)
					matched = True
					break
			if matched:
				true_positives += 1
			else:
				false_positives += 1

	for module_id, consumed in by_module.items():
		all_findings = STORE.get_findings(module_id)
		false_negatives += max(len(all_findings) - len(consumed), 0)

	precision = true_positives / max(true_positives + false_positives, 1)
	recall = true_positives / max(true_positives + false_negatives, 1)
	return AccuracyReport(
		episode_id=episode_id,
		true_positives=true_positives,
		false_positives=false_positives,
		false_negatives=false_negatives,
		precision=precision,
		recall=recall,
	)


@app.get("/graph/export")
def export_graph(episode_id: str = Query(default="")) -> dict[str, object]:
	snapshot = STORE.get_full_graph()
	annotations = STORE.get_review_annotations(episode_id=episode_id or None)
	return {
		"episode_id": episode_id or None,
		"nodes": [node.model_dump() for node in snapshot.nodes],
		"edges": [edge.model_dump() for edge in snapshot.edges],
		"annotations": [
			{
				"module_id": item.module_id,
				"episode_id": item.episode_id,
				"task_id": item.task_id,
				"step_number": item.step_number,
				"action_type": item.action_type,
				"reward_given": item.reward_given,
				"attributed_to": item.attributed_to,
				"note": item.note,
				"created_at": item.created_at.isoformat(),
			}
			for item in annotations
		],
	}
