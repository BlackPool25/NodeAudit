from __future__ import annotations

import argparse
import ast
import os
from pathlib import Path

from pydantic import BaseModel

from db.schema import EdgeType
from db.store import Store
from parser.linter import run_linters
from parser.summarizer import summarize_module


_SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
}


def _iter_python_files(target_dir: Path) -> list[Path]:
    max_files = int(os.getenv("GRAPHREVIEW_MAX_FILES", "5000"))
    py_files: list[Path] = []
    for path in sorted(target_dir.rglob("*.py")):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        py_files.append(path)
        if len(py_files) >= max_files:
            break
    return py_files


class ImportRef(BaseModel):
    target_module: str
    import_line: str
    scope: str = "module_level"
    weight: float = 1.0
    edge_type: EdgeType = EdgeType.EXPLICIT_IMPORT


class ParsedModule(BaseModel):
    module_id: str
    raw_code: str
    function_signatures: list[str]
    classes: list[str]
    imports: list[ImportRef]
    constants: list[str]
    dependencies: list[str]


class _Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.function_signatures: list[str] = []
        self.classes: list[str] = []
        self.constants: list[str] = []
        self.imports: list[tuple[str, str, str]] = []
        self._scope_stack: list[str] = []

    @property
    def _scope(self) -> str:
        return "function_level" if self._scope_stack else "module_level"

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        args: list[str] = []
        for arg in node.args.args:
            if arg.annotation is not None:
                args.append(f"{arg.arg}: {ast.unparse(arg.annotation)}")
            else:
                args.append(arg.arg)
        returns = ast.unparse(node.returns) if node.returns is not None else "None"
        self.function_signatures.append(f"{node.name}({', '.join(args)})->{returns}")
        self._scope_stack.append(node.name)
        try:
            self.generic_visit(node)
        finally:
            self._scope_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        fake = ast.FunctionDef(
            name=node.name,
            args=node.args,
            body=node.body,
            decorator_list=node.decorator_list,
            returns=node.returns,
            type_comment=node.type_comment,
        )
        self.visit_FunctionDef(fake)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.classes.append(node.name)
        self._scope_stack.append(node.name)
        try:
            self.generic_visit(node)
        finally:
            self._scope_stack.pop()

    def visit_Import(self, node: ast.Import) -> None:
        line = ast.get_source_segment(self._source, node) or "import"
        for alias in node.names:
            self.imports.append((alias.name, line, self._scope))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        level = node.level or 0
        dotted = "." * level + module
        line = ast.get_source_segment(self._source, node) or "from"
        self.imports.append((dotted, line, self._scope))

    def visit_Assign(self, node: ast.Assign) -> None:
        if isinstance(node.value, ast.Constant):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    self.constants.append(target.id)
        self.generic_visit(node)

    def parse(self, tree: ast.AST, source: str) -> None:
        self._source = source
        self.visit(tree)


def _to_module_id(path: Path, root: Path) -> str:
    rel = path.resolve().relative_to(root.resolve())
    return str(rel.with_suffix("")).replace("/", ".")


def _resolve_relative_import(current_module: str, ref: str) -> str:
    if not ref.startswith("."):
        return ref
    dots = len(ref) - len(ref.lstrip("."))
    suffix = ref.lstrip(".")
    parts = current_module.split(".")
    base = parts[:-dots] if dots <= len(parts) else []
    if suffix:
        base.append(suffix)
    return ".".join(part for part in base if part)


def parse_python_file(path: Path, root_dir: Path) -> ParsedModule:
    source = path.read_text(encoding="utf-8")
    module_id = _to_module_id(path, root_dir)
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ParsedModule(
            module_id=module_id,
            raw_code=source,
            function_signatures=[],
            classes=[],
            imports=[],
            constants=[],
            dependencies=[],
        )

    visitor = _Visitor()
    visitor.parse(tree, source)

    imports = [
        ImportRef(
            target_module=_resolve_relative_import(module_id, name),
            import_line=line,
            scope=scope,
            weight=0.5 if scope == "function_level" else 1.0,
            edge_type=EdgeType.EXPLICIT_IMPORT,
        )
        for name, line, scope in visitor.imports
    ]

    dependencies = [imp.target_module for imp in imports if imp.target_module]

    return ParsedModule(
        module_id=module_id,
        raw_code=source,
        function_signatures=visitor.function_signatures,
        classes=visitor.classes,
        imports=imports,
        constants=visitor.constants,
        dependencies=dependencies,
    )


def parse_directory(target_dir: Path, db_path: str | None = None) -> Store:
    target_dir = target_dir.resolve()
    store = Store(source_root=str(target_dir), db_path=db_path)
    store.clear_source_graph()

    py_files = _iter_python_files(target_dir)
    parsed_modules = [parse_python_file(py_file, target_dir) for py_file in py_files]
    known_module_ids = {parsed.module_id for parsed in parsed_modules}

    for py_file, parsed in zip(py_files, parsed_modules):
        issues = run_linters(py_file)
        summary = summarize_module(parsed, issues)

        dep_reason = "Imports used by module-level and callable logic"
        store.upsert_node(
            module_id=parsed.module_id,
            raw_code=parsed.raw_code,
            ast_summary=summary,
            dependency_reason=dep_reason,
        )
        store.replace_findings_for_module(
            parsed.module_id,
            [issue.model_dump() for issue in issues],
        )
        for imported in parsed.imports:
            if imported.target_module and imported.target_module in known_module_ids:
                store.upsert_edge(
                    source_module_id=parsed.module_id,
                    target_module_id=imported.target_module,
                    edge_type=imported.edge_type,
                    import_line=imported.import_line,
                    weight=imported.weight,
                )

    return store


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parse Python codebase into SQLite graph")
    parser.add_argument("target", help="Path to target codebase")
    parser.add_argument("--db-path", default=None, help="Path to SQLite database")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    target_dir = Path(args.target)
    store = parse_directory(target_dir=target_dir, db_path=args.db_path)
    snapshot = store.get_full_graph()
    print(
        f"Populated DB for {target_dir} with "
        f"{len(snapshot.nodes)} nodes and {len(snapshot.edges)} edges"
    )


if __name__ == "__main__":
    main()
