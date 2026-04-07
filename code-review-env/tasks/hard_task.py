from __future__ import annotations

TASK_CONFIG: dict[str, object] = {
	"task_id": "cascade_review",
	"task_level": "hard",
	"description": "Attribute cascading dependency failures to their root cause.",
	"default_modules": ["checkout", "auth", "config"],
	"grader": "hard",
	"max_steps": 20,
	"allow_module_override": True,
	"expand_to_dependencies": True,
}
