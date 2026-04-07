from __future__ import annotations

TASK_CONFIG: dict[str, object] = {
	"task_id": "logic_review",
	"task_level": "medium",
	"description": "Trace logic bugs using direct dependency context.",
	"default_modules": ["checkout", "auth"],
	"grader": "medium",
	"max_steps": 14,
	"allow_module_override": True,
	"expand_to_dependencies": True,
}
