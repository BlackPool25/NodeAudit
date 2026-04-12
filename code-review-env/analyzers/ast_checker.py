from __future__ import annotations

import ast
import dataclasses
from pathlib import Path


@dataclasses.dataclass(frozen=True)
class ASTFinding:
    file: str
    line: int
    rule: str
    message: str
    severity: str


_MUTABLE_DEFAULT_NODES = (ast.List, ast.Dict, ast.Set)


def _load_tree(filepath: Path) -> ast.AST:
    return ast.parse(filepath.read_text(encoding="utf-8"), filename=str(filepath))


def _is_optional_annotation(node: ast.AST | None) -> bool:
    if node is None:
        return False
    if isinstance(node, ast.Subscript):
        if isinstance(node.value, ast.Name) and node.value.id == "Optional":
            return True
        if isinstance(node.value, ast.Attribute) and node.value.attr == "Optional":
            return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        if isinstance(node.right, ast.Constant) and node.right.value is None:
            return True
        if isinstance(node.left, ast.Constant) and node.left.value is None:
            return True
    return False


def check_mutable_defaults(tree: ast.AST, filepath: str) -> list[ASTFinding]:
    findings: list[ASTFinding] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        defaults = list(node.args.defaults) + [d for d in node.args.kw_defaults if d is not None]
        for default in defaults:
            if isinstance(default, _MUTABLE_DEFAULT_NODES):
                findings.append(
                    ASTFinding(
                        file=filepath,
                        line=int(getattr(default, "lineno", node.lineno)),
                        rule="mutable_default_arg",
                        message="Mutable default argument can leak state across calls",
                        severity="high",
                    )
                )
    return findings


def check_bare_except(tree: ast.AST, filepath: str) -> list[ASTFinding]:
    findings: list[ASTFinding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if node.type is None:
            findings.append(
                ASTFinding(
                    file=filepath,
                    line=int(node.lineno),
                    rule="bare_except",
                    message="Bare except catches unexpected errors and hides root causes",
                    severity="high",
                )
            )
    return findings


def check_none_comparison(tree: ast.AST, filepath: str) -> list[ASTFinding]:
    findings: list[ASTFinding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        if not any(isinstance(op, (ast.Eq, ast.NotEq)) for op in node.ops):
            continue
        comparators = [node.left, *node.comparators]
        if any(isinstance(comp, ast.Constant) and comp.value is None for comp in comparators):
            findings.append(
                ASTFinding(
                    file=filepath,
                    line=int(node.lineno),
                    rule="none_equality_check",
                    message="Use 'is None' / 'is not None' instead of == None comparisons",
                    severity="medium",
                )
            )
    return findings


def _collect_optional_returning_functions(tree: ast.AST) -> set[str]:
    optional_functions: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        if _is_optional_annotation(node.returns):
            optional_functions.add(node.name)
            continue

        has_none_return = False
        has_value_return = False
        for child in ast.walk(node):
            if not isinstance(child, ast.Return):
                continue
            if child.value is None:
                has_none_return = True
            elif isinstance(child.value, ast.Constant) and child.value.value is None:
                has_none_return = True
            else:
                has_value_return = True
        if has_none_return and has_value_return:
            optional_functions.add(node.name)
    return optional_functions


def check_unchecked_optional_returns(tree: ast.AST, filepath: str) -> list[ASTFinding]:
    findings: list[ASTFinding] = []
    optional_functions = _collect_optional_returning_functions(tree)
    if not optional_functions:
        return findings

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        if not isinstance(node.targets[0], ast.Name):
            continue
        if not isinstance(node.value, ast.Call):
            continue
        if not isinstance(node.value.func, ast.Name):
            continue
        if node.value.func.id not in optional_functions:
            continue

        var_name = node.targets[0].id
        parent_body = _find_parent_body(tree, node)
        if parent_body is None:
            continue
        index = parent_body.index(node)
        for next_node in parent_body[index + 1 : index + 4]:
            if isinstance(next_node, ast.If) and _is_none_guard(next_node.test, var_name):
                break
            if _uses_name_without_guard(next_node, var_name):
                findings.append(
                    ASTFinding(
                        file=filepath,
                        line=int(getattr(next_node, "lineno", node.lineno)),
                        rule="unchecked_optional_return",
                        message=(
                            f"Result of optional-returning call '{node.value.func.id}' is used without a None guard"
                        ),
                        severity="high",
                    )
                )
                break
    return findings


def check_missing_dunder_all(tree: ast.AST, filepath: str) -> list[ASTFinding]:
    path = Path(filepath)
    if path.name.startswith("_"):
        return []

    has_public_defs = False
    has_dunder_all = False

    for node in tree.body if isinstance(tree, ast.Module) else []:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    has_dunder_all = True
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not node.name.startswith("_"):
            has_public_defs = True

    if has_public_defs and not has_dunder_all:
        return [
            ASTFinding(
                file=filepath,
                line=1,
                rule="missing_dunder_all",
                message="Public module exports are missing __all__ declaration",
                severity="medium",
            )
        ]
    return []


def _find_parent_body(tree: ast.AST, target: ast.AST) -> list[ast.stmt] | None:
    for node in ast.walk(tree):
        for field_name in ("body", "orelse", "finalbody"):
            body = getattr(node, field_name, None)
            if not isinstance(body, list):
                continue
            if target in body:
                return body
    return None


def _is_none_guard(test: ast.AST, var_name: str) -> bool:
    if not isinstance(test, ast.Compare):
        return False
    if len(test.ops) != 1 or len(test.comparators) != 1:
        return False
    op = test.ops[0]
    left = test.left
    right = test.comparators[0]
    if not isinstance(left, ast.Name) or left.id != var_name:
        return False
    if not isinstance(right, ast.Constant) or right.value is not None:
        return False
    return isinstance(op, (ast.Is, ast.IsNot))


def _uses_name_without_guard(node: ast.AST, var_name: str) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Attribute) and isinstance(child.value, ast.Name) and child.value.id == var_name:
            return True
        if isinstance(child, ast.Subscript) and isinstance(child.value, ast.Name) and child.value.id == var_name:
            return True
    return False


def run_all(filepath: str | Path) -> list[ASTFinding]:
    path = Path(filepath)
    try:
        tree = _load_tree(path)
    except (OSError, SyntaxError):
        return []

    filename = str(path)
    findings = []
    findings.extend(check_mutable_defaults(tree, filename))
    findings.extend(check_bare_except(tree, filename))
    findings.extend(check_none_comparison(tree, filename))
    findings.extend(check_unchecked_optional_returns(tree, filename))
    findings.extend(check_missing_dunder_all(tree, filename))
    return findings


def run_all_checks(filepath: str | Path) -> list[ASTFinding]:
    return run_all(filepath)
