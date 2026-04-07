from __future__ import annotations

from dataclasses import dataclass

from graph.graph_manager import GraphManager
from tasks.easy_task import TASK_CONFIG as EASY_TASK
from tasks.hard_task import TASK_CONFIG as HARD_TASK
from tasks.medium_task import TASK_CONFIG as MEDIUM_TASK


@dataclass(frozen=True)
class TaskSpec:
	task_id: str
	task_level: str
	description: str
	default_modules: list[str]
	grader: str
	max_steps: int
	allow_module_override: bool
	expand_to_dependencies: bool


def _to_spec(config: dict[str, object]) -> TaskSpec:
	return TaskSpec(
		task_id=str(config["task_id"]),
		task_level=str(config["task_level"]),
		description=str(config["description"]),
		default_modules=[str(item) for item in list(config["default_modules"])],
		grader=str(config["grader"]),
		max_steps=int(config["max_steps"]),
		allow_module_override=bool(config["allow_module_override"]),
		expand_to_dependencies=bool(config["expand_to_dependencies"]),
	)


TASK_REGISTRY: dict[str, TaskSpec] = {
	"style_review": _to_spec(EASY_TASK),
	"logic_review": _to_spec(MEDIUM_TASK),
	"cascade_review": _to_spec(HARD_TASK),
}


def list_tasks() -> list[TaskSpec]:
	return [TASK_REGISTRY[key] for key in sorted(TASK_REGISTRY)]


def get_task(task_id: str) -> TaskSpec:
	if task_id not in TASK_REGISTRY:
		raise ValueError(f"Unknown task_id: {task_id}")
	return TASK_REGISTRY[task_id]


def resolve_task_modules(
	task: TaskSpec,
	graph_manager: GraphManager,
	module_override: list[str] | None = None,
) -> list[str]:
	graph = graph_manager.load_graph()
	available = set(graph.nodes())
	base_modules = task.default_modules

	if module_override:
		if not task.allow_module_override:
			raise ValueError(f"Task {task.task_id} does not allow module_override")
		requested: list[str] = []
		for module in module_override:
			try:
				requested.append(graph_manager.resolve_module_id(module))
			except ValueError:
				continue
		if not requested:
			raise ValueError("module_override does not include any known module ids")
		base_modules = sorted(set(requested))

	if not task.expand_to_dependencies:
		return [module for module in base_modules if module in available]

	expanded: set[str] = set()
	for module_id in base_modules:
		if module_id not in available:
			continue
		expanded.add(module_id)
		expanded.update(graph.successors(module_id))
		expanded.update(graph.predecessors(module_id))

	# Dependency-aware policy: prefer leaves first and keep deterministic ordering.
	traversal_rank = {node: idx for idx, node in enumerate(graph_manager.traversal_order())}
	return sorted(expanded, key=lambda node: (int(traversal_rank.get(node, 10_000)), node))
