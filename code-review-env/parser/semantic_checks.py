from __future__ import annotations

import ast
from dataclasses import dataclass


@dataclass(frozen=True)
class SemanticIssue:
    line: int
    severity: str
    message: str
    stage: str


def _build_undirected_graph(tree: ast.AST) -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = {}

    def ensure(node: str) -> None:
        adjacency.setdefault(node, set())

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        var_name = target.id
        value = node.value
        if not isinstance(value, ast.Call):
            continue
        if not isinstance(value.func, ast.Name) or value.func.id != "Node":
            continue

        ensure(var_name)
        if len(value.args) >= 3 and isinstance(value.args[2], ast.List):
            for item in value.args[2].elts:
                if isinstance(item, ast.Name):
                    ensure(item.id)
                    adjacency[var_name].add(item.id)
                    adjacency[item.id].add(var_name)

    return adjacency


def _connected(adjacency: dict[str, set[str]], left: str, right: str) -> bool:
    if left == right:
        return True
    if left not in adjacency or right not in adjacency:
        return False

    seen = {left}
    stack = [left]
    while stack:
        current = stack.pop()
        for neighbor in adjacency.get(current, set()):
            if neighbor in seen:
                continue
            if neighbor == right:
                return True
            seen.add(neighbor)
            stack.append(neighbor)
    return False


def detect_semantic_issues(raw_code: str) -> list[SemanticIssue]:
    try:
        tree = ast.parse(raw_code)
    except SyntaxError:
        return []

    lines = raw_code.splitlines()
    adjacency = _build_undirected_graph(tree)
    issues: list[SemanticIssue] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not isinstance(test, ast.Call):
            continue
        if not isinstance(test.func, ast.Name) or test.func.id != "breadth_first_search":
            continue
        if len(test.args) < 2:
            continue
        if not isinstance(test.args[0], ast.Name) or not isinstance(test.args[1], ast.Name):
            continue

        src = test.args[0].id
        dst = test.args[1].id
        line_no = int(getattr(node, "lineno", 1))
        context_start = max(0, line_no - 4)
        context = "\n".join(lines[context_start:line_no]).lower()

        if "unconnected" in context and _connected(adjacency, src, dst):
            issues.append(
                SemanticIssue(
                    line=line_no,
                    severity="medium",
                    stage="medium",
                    message=(
                        f"Comment claims unconnected nodes, but '{src}' and '{dst}' belong to the same undirected"
                        " component. Test intent is misleading and can hide logical regressions."
                    ),
                )
            )

    return issues
