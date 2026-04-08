from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import uvicorn
import networkx as nx

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select

from analyzers.pipeline import AnalyzerPipeline
from db.schema import ModuleEdge, ModuleNode
from db.store import Store
from env.env_loader import load_env_file
from env.action import ActionType, ReviewAction
from env.environment import CodeReviewEnv, StepResult
from env.observation import CodeObservation
from env.state import GraphState
from env.runtime_config import load_runtime_config
from llm.critical_analysis import build_critical_analysis
from training.run_manager import TrainingRunManager
from training.weights import WeightSafetyManager
from visualizer.report_generator import GeneratedArtifacts, generate_phase5_outputs

load_env_file()


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


class ReportGenerateRequest(BaseModel):
	model_config = ConfigDict(strict=True, extra="forbid")

	episode_id: str | None = None
	module_override: list[str] | None = None
	hops: int = 1
	output_dir: str = "outputs"
	report_prefix: str = "graphreview"


class ReportGenerateResponse(BaseModel):
	model_config = ConfigDict(strict=True, extra="forbid")

	artifacts: GeneratedArtifacts


class ResultSummary(BaseModel):
	model_config = ConfigDict(strict=True, extra="forbid")

	report_path: str
	report_title: str
	report_json_url: str
	graph_html_url: str
	markdown_url: str | None = None
	confidence_score: float | None = None
	node_count: int | None = None
	edge_count: int | None = None
	generated_at: float


class ConnectivitySummary(BaseModel):
	model_config = ConfigDict(strict=True, extra="forbid")

	node_count: int
	edge_count: int
	connected_components: int
	largest_component_size: int
	isolated_nodes: int
	isolation_ratio: float


class ResultDetail(BaseModel):
	model_config = ConfigDict(strict=True, extra="forbid")

	report: dict[str, object]
	connectivity: ConnectivitySummary
	db_columns: dict[str, list[str]]


class AnalyzerRunRequest(BaseModel):
	model_config = ConfigDict(strict=True, extra="forbid")

	timeout_seconds: int = 45


class AnalyzerRunResponse(BaseModel):
	model_config = ConfigDict(strict=True, extra="forbid")

	runs: list[dict[str, object]]
	finding_count: int


class TrainingBootstrapResponse(BaseModel):
	model_config = ConfigDict(strict=True, extra="forbid")

	weight_path: str
	weight_sha256: str
	deterministic_findings: int
	precision: float
	recall: float


class TrainingRunRequest(BaseModel):
	model_config = ConfigDict(strict=True, extra="forbid")

	force_seed: bool = False
	deterministic_output: str = "outputs/training/dataset.latest.jsonl"
	baseline_precision: float | None = None
	baseline_recall: float | None = None
	regression_tolerance: float = 0.01


class TrainingRunResponse(BaseModel):
	model_config = ConfigDict(strict=True, extra="forbid")

	ok: bool
	exit_code: int
	stdout_tail: str
	end_payload: dict[str, object] | None = None


class TrainingRunRecord(BaseModel):
	model_config = ConfigDict(strict=True, extra="forbid")

	run_id: str
	model_name: str
	model_sha256: str
	deterministic_findings: int
	agent_findings: int
	true_positives: int
	false_positives: int
	false_negatives: int
	precision: float
	recall: float
	passed_non_regression: bool
	output_path: str
	created_at: str


class TrainingRunAnalysisResponse(BaseModel):
	model_config = ConfigDict(strict=True, extra="forbid")

	run_id: str
	model_name: str
	analysis: str
	non_scoring: bool = True


OUTPUT_ROOT = Path(os.getenv("GRAPHREVIEW_OUTPUT_DIR", "outputs")).resolve()
UI_INDEX_PATH = Path(__file__).resolve().parent / "static" / "index.html"
STATIC_ROOT = Path(__file__).resolve().parent / "static"


def _default_source_root() -> str:
	configured = os.getenv("GRAPHREVIEW_SOURCE_ROOT", "sample_project")
	return str(Path(configured).resolve())


def _default_db_path() -> str | None:
	configured = os.getenv("GRAPHREVIEW_DB_PATH", "").strip()
	return configured or None


ENV = CodeReviewEnv(source_root=_default_source_root(), db_path=_default_db_path())
STORE = Store(source_root=_default_source_root(), db_path=_default_db_path())

app = FastAPI(title="GraphReview OpenEnv Server", version="0.4.0")
app.mount("/artifacts", StaticFiles(directory=str(OUTPUT_ROOT), check_dir=False), name="artifacts")
app.mount("/static", StaticFiles(directory=str(STATIC_ROOT), check_dir=True), name="static")


def _artifact_url(path: Path) -> str:
	rel = path.relative_to(OUTPUT_ROOT).as_posix()
	return f"/artifacts/{rel}"


def _safe_artifact_path(report_path: str) -> Path:
	path = (OUTPUT_ROOT / report_path).resolve()
	if not str(path).startswith(str(OUTPUT_ROOT)):
		raise HTTPException(status_code=400, detail="Invalid report path")
	if not path.is_file():
		raise HTTPException(status_code=404, detail=f"Report file not found: {report_path}")
	return path


def _discover_results() -> list[ResultSummary]:
	if not OUTPUT_ROOT.exists():
		return []

	results: list[ResultSummary] = []
	for report_json in sorted(OUTPUT_ROOT.rglob("*_report.json")):
		prefix = report_json.name.removesuffix("_report.json")
		graph_html = report_json.with_name(f"{prefix}_graph.html")
		markdown = report_json.with_name(f"{prefix}_report.md")

		confidence: float | None = None
		node_count: int | None = None
		edge_count: int | None = None
		report_title = report_json.parent.name

		try:
			payload = json.loads(report_json.read_text(encoding="utf-8"))
			metrics = payload.get("metrics", {})
			confidence = float(metrics.get("confidence_score")) if "confidence_score" in metrics else None
			nodes = payload.get("nodes", [])
			edges = payload.get("edges", [])
			node_count = len(nodes) if isinstance(nodes, list) else None
			edge_count = len(edges) if isinstance(edges, list) else None
			report_title = str(payload.get("source_root") or report_title)
		except Exception:
			pass

		rel = report_json.relative_to(OUTPUT_ROOT).as_posix()
		results.append(
			ResultSummary(
				report_path=rel,
				report_title=report_title,
				report_json_url=_artifact_url(report_json),
				graph_html_url=_artifact_url(graph_html) if graph_html.exists() else "",
				markdown_url=_artifact_url(markdown) if markdown.exists() else None,
				confidence_score=confidence,
				node_count=node_count,
				edge_count=edge_count,
				generated_at=report_json.stat().st_mtime,
			)
		)

	results.sort(key=lambda item: item.generated_at, reverse=True)
	return results


def _connectivity_summary_for_scope(scope_modules: list[str]) -> ConnectivitySummary:
	with Session(STORE.engine) as session:
		nodes = list(
			session.exec(
				select(ModuleNode).where(
					ModuleNode.source_root == STORE.config.source_root,
					ModuleNode.module_id.in_(scope_modules),
				)
			).all()
		)
		edges = list(
			session.exec(
				select(ModuleEdge).where(
					ModuleEdge.source_root == STORE.config.source_root,
					ModuleEdge.source_module_id.in_(scope_modules),
					ModuleEdge.target_module_id.in_(scope_modules),
				)
			).all()
		)

	graph = nx.Graph()
	for node in nodes:
		graph.add_node(node.module_id)
	for edge in edges:
		graph.add_edge(edge.source_module_id, edge.target_module_id)

	components = list(nx.connected_components(graph)) if graph.number_of_nodes() else []
	largest_component = max((len(component) for component in components), default=0)
	isolated_nodes = sum(1 for _, degree in graph.degree() if degree == 0)
	node_count = graph.number_of_nodes()

	return ConnectivitySummary(
		node_count=node_count,
		edge_count=graph.number_of_edges(),
		connected_components=len(components),
		largest_component_size=largest_component,
		isolated_nodes=isolated_nodes,
		isolation_ratio=(isolated_nodes / node_count) if node_count else 0.0,
	)


@app.get("/", response_class=HTMLResponse)
def ui_home() -> HTMLResponse:
	if not UI_INDEX_PATH.exists():
		raise HTTPException(status_code=500, detail="UI index not found")
	return HTMLResponse(UI_INDEX_PATH.read_text(encoding="utf-8"))


@app.get("/ui", response_class=FileResponse)
def ui_index() -> FileResponse:
	if not UI_INDEX_PATH.exists():
		raise HTTPException(status_code=500, detail="UI index not found")
	return FileResponse(path=UI_INDEX_PATH)


@app.get("/ui/results", response_model=list[ResultSummary])
def ui_results() -> list[ResultSummary]:
	return _discover_results()


@app.get("/ui/result", response_model=ResultDetail)
def ui_result(report_path: str = Query(..., min_length=1)) -> ResultDetail:
	report_json = _safe_artifact_path(report_path)
	try:
		payload = json.loads(report_json.read_text(encoding="utf-8"))
	except Exception as exc:
		raise HTTPException(status_code=400, detail=f"Invalid report JSON: {exc}") from exc

	scope_modules = payload.get("scope_modules", [])
	if not isinstance(scope_modules, list) or not all(isinstance(item, str) for item in scope_modules):
		raise HTTPException(status_code=400, detail="Report payload missing scope_modules")

	connectivity = _connectivity_summary_for_scope(scope_modules)

	return ResultDetail(
		report=payload,
		connectivity=connectivity,
		db_columns={
			"module_node": [
				"id",
				"source_root",
				"module_id",
				"name",
				"raw_code",
				"ast_summary",
				"summary",
				"linter_flags",
				"parent_module_id",
				"is_chunk",
				"dependency_reason",
				"review_annotation",
				"review_status",
				"review_summary",
				"created_at",
				"updated_at",
			],
			"module_edge": [
				"id",
				"source_root",
				"source_module_id",
				"target_module_id",
				"edge_type",
				"import_line",
				"weight",
				"connection_summary",
			],
		},
	)


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


@app.post("/reports/generate", response_model=ReportGenerateResponse)
def generate_report(payload: ReportGenerateRequest) -> ReportGenerateResponse:
	try:
		artifacts = generate_phase5_outputs(
			source_root=ENV.source_root,
			db_path=_default_db_path(),
			output_dir=payload.output_dir,
			episode_id=payload.episode_id,
			module_filter=payload.module_override,
			hops=payload.hops,
			report_prefix=payload.report_prefix,
		)
	except Exception as exc:
		raise HTTPException(status_code=400, detail=str(exc)) from exc
	return ReportGenerateResponse(artifacts=artifacts)


@app.post("/analysis/run", response_model=AnalyzerRunResponse)
def run_deterministic_analysis(payload: AnalyzerRunRequest) -> AnalyzerRunResponse:
	pipeline = AnalyzerPipeline(target_dir=Path(ENV.source_root), timeout_seconds=payload.timeout_seconds)
	findings, summaries = pipeline.run_all()

	for summary in summaries:
		run = STORE.create_analyzer_run(
			analyzer=summary.analyzer,
			analyzer_version=summary.analyzer_version,
			status=summary.status,
			findings_count=summary.findings,
			command=summary.command,
			command_hash=summary.command_hash,
			error_message=summary.error_message,
		)
		tool_findings = [
			{
				"module_id": item.module_id,
				"line": item.line,
				"severity": item.severity,
				"rule_id": item.rule_id,
				"message": item.message,
				"evidence": item.evidence,
			}
			for item in findings
			if item.analyzer == summary.analyzer
		]
		if tool_findings:
			STORE.add_analyzer_findings(
				analyzer_run_id=int(run.id or 0),
				analyzer=summary.analyzer,
				findings=tool_findings,
			)

	runs_payload = [
		{
			"analyzer": item.analyzer,
			"status": item.status,
			"findings": item.findings,
			"error_message": item.error_message,
		}
		for item in summaries
	]
	return AnalyzerRunResponse(runs=runs_payload, finding_count=len(findings))


@app.post("/training/bootstrap", response_model=TrainingBootstrapResponse)
def bootstrap_training() -> TrainingBootstrapResponse:
	config = load_runtime_config()
	weight_manager = WeightSafetyManager(Path(config.llm_weight_manifest_dir))
	model_name = os.getenv("MODEL_NAME", "gemma4:e4b")
	weight_path = "unavailable"
	sha256 = "unavailable"
	try:
		verified_path = weight_manager.load_verified(model_name)
		weight_path = str(verified_path)
		sha256 = weight_manager.checksum(verified_path)
	except FileNotFoundError:
		try:
			manifest = weight_manager.register_existing(model_name=model_name, weight_path=Path(config.llm_model_agent_path))
			weight_path = manifest.source_path
			sha256 = manifest.sha256
		except FileNotFoundError:
			# In containerized deployments (e.g., HF Space), local GGUF files may not exist.
			# Bootstrap should still return deterministic coverage metrics instead of a 500 error.
			pass

	manager = TrainingRunManager()
	try:
		deterministic = STORE.get_analyzer_findings()
	except Exception:
		deterministic = []
	deterministic_keys = {
		f"{item.analyzer}:{item.module_id}:{item.rule_id}:{item.line}"
		for item in deterministic
	}
	comparison = manager.compare(deterministic_findings=deterministic_keys, agent_findings=set())

	return TrainingBootstrapResponse(
		weight_path=weight_path,
		weight_sha256=sha256,
		deterministic_findings=len(deterministic),
		precision=comparison.precision,
		recall=comparison.recall,
	)


@app.post("/training/run", response_model=TrainingRunResponse)
def run_training(payload: TrainingRunRequest) -> TrainingRunResponse:
	cmd = [
		sys.executable,
		"inference.py",
		str(Path(ENV.source_root)),
		"--deterministic-output",
		payload.deterministic_output,
		"--regression-tolerance",
		str(payload.regression_tolerance),
	]
	if payload.force_seed:
		cmd.append("--force-seed")
	if payload.baseline_precision is not None:
		cmd.extend(["--baseline-precision", str(payload.baseline_precision)])
	if payload.baseline_recall is not None:
		cmd.extend(["--baseline-recall", str(payload.baseline_recall)])

	try:
		proc = subprocess.run(
			cmd,
			cwd=str(Path(__file__).resolve().parents[1]),
			capture_output=True,
			text=True,
			check=False,
			timeout=180,
		)
	except subprocess.TimeoutExpired as exc:
		partial = (exc.stdout or "") + ("\n" + exc.stderr if exc.stderr else "")
		lines = [line for line in partial.splitlines() if line.strip()]
		return TrainingRunResponse(
			ok=False,
			exit_code=124,
			stdout_tail="\n".join(lines[-40:]),
			end_payload=None,
		)

	output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
	lines = [line for line in output.splitlines() if line.strip()]
	stdout_tail = "\n".join(lines[-40:])
	end_payload: dict[str, object] | None = None
	for line in reversed(lines):
		if line.startswith("[END] "):
			try:
				loaded = json.loads(line.removeprefix("[END] ").strip())
				if isinstance(loaded, dict):
					end_payload = loaded
			except Exception:
				end_payload = None
			break

	return TrainingRunResponse(
		ok=proc.returncode == 0,
		exit_code=proc.returncode,
		stdout_tail=stdout_tail,
		end_payload=end_payload,
	)


@app.get("/training/runs", response_model=list[TrainingRunRecord])
def training_runs(limit: int = Query(default=30, ge=1, le=200)) -> list[TrainingRunRecord]:
	runs = STORE.list_training_runs(limit=limit)
	return [
		TrainingRunRecord(
			run_id=item.run_id,
			model_name=item.model_name,
			model_sha256=item.model_sha256,
			deterministic_findings=item.deterministic_findings,
			agent_findings=item.agent_findings,
			true_positives=item.true_positives,
			false_positives=item.false_positives,
			false_negatives=item.false_negatives,
			precision=item.precision,
			recall=item.recall,
			passed_non_regression=item.passed_non_regression,
			output_path=item.output_path,
			created_at=item.created_at.isoformat(),
		)
		for item in runs
	]


@app.get("/training/runs/{run_id}/analysis", response_model=TrainingRunAnalysisResponse)
def training_run_analysis(run_id: str) -> TrainingRunAnalysisResponse:
	run = STORE.get_training_run(run_id)
	if run is None:
		raise HTTPException(status_code=404, detail=f"Training run not found: {run_id}")

	config = load_runtime_config()
	analysis = build_critical_analysis(
		model=config.llm_model_judge,
		base_url=config.llm_base_url,
		api_key=config.llm_api_key,
		run_payload={
			"run_id": run.run_id,
			"model_name": run.model_name,
			"deterministic_findings": run.deterministic_findings,
			"agent_findings": run.agent_findings,
			"true_positives": run.true_positives,
			"false_positives": run.false_positives,
			"false_negatives": run.false_negatives,
			"precision": run.precision,
			"recall": run.recall,
			"passed_non_regression": run.passed_non_regression,
		},
	)

	return TrainingRunAnalysisResponse(
		run_id=run.run_id,
		model_name=run.model_name,
		analysis=analysis,
	)


def main() -> None:
	host = os.getenv("GRAPHREVIEW_HOST", "0.0.0.0")
	port = int(os.getenv("GRAPHREVIEW_PORT", "8000"))
	uvicorn.run("server.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
	main()
