from __future__ import annotations

TASK_CONFIG: dict[str, object] = {
	"task_id": "style_review",
	"task_level": "easy",
	"description": "Find style/lint issues for a focused module review.",
	"default_modules": ["cart"],
	"grader": "easy",
	"max_steps": 8,
	"allow_module_override": True,
	"expand_to_dependencies": False,
}
