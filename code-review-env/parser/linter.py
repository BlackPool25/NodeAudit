from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
import subprocess
from pathlib import Path
import sys

from pydantic import BaseModel


class LinterIssue(BaseModel):
    tool: str
    line: int
    severity: str
    code: str
    message: str


_PYLINT_SEVERITY_MAP = {
    "fatal": "high",
    "error": "high",
    "warning": "medium",
    "refactor": "low",
    "convention": "low",
    "info": "low",
}

_BANDIT_SEVERITY_MAP = {
    "high": "high",
    "medium": "medium",
    "low": "low",
}


def _timeout_seconds() -> int:
    return int(os.getenv("GRAPHREVIEW_LINTER_TIMEOUT_SECONDS", "20"))


def run_pylint(path: Path) -> list[LinterIssue]:
    cmd = [
        sys.executable,
        "-m",
        "pylint",
        str(path),
        "--output-format=json2",
        "--score=n",
        "--reports=n",
        "--errors-only",
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=_timeout_seconds(),
        )
    except subprocess.TimeoutExpired:
        return []

    payload = (proc.stdout or "").strip()
    if not payload:
        return []

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []

    messages = data.get("messages", []) if isinstance(data, dict) else []
    issues: list[LinterIssue] = []
    for message in messages:
        severity = _PYLINT_SEVERITY_MAP.get(str(message.get("type", "")).lower(), "low")
        issues.append(
            LinterIssue(
                tool="pylint",
                line=int(message.get("line", 0)),
                severity=severity,
                code=str(message.get("messageId", "PL0000")),
                message=str(message.get("message", "")),
            )
        )
    return issues


def run_bandit(path: Path) -> list[LinterIssue]:
    cmd = [sys.executable, "-m", "bandit", "-q", "-f", "json", str(path)]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=_timeout_seconds(),
        )
    except subprocess.TimeoutExpired:
        return []

    payload = (proc.stdout or "").strip()
    if not payload:
        return []

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []

    results = data.get("results", []) if isinstance(data, dict) else []
    issues: list[LinterIssue] = []
    for item in results:
        raw_sev = str(item.get("issue_severity", "LOW")).lower()
        issues.append(
            LinterIssue(
                tool="bandit",
                line=int(item.get("line_number", 0)),
                severity=_BANDIT_SEVERITY_MAP.get(raw_sev, "low"),
                code=str(item.get("test_id", "B000")),
                message=str(item.get("issue_text", "")),
            )
        )
    return issues


def run_pyright(path: Path) -> list[LinterIssue]:
    pyright_bin = str((Path(sys.executable).resolve().parent / "pyright"))
    cmd = [pyright_bin if Path(pyright_bin).exists() else "pyright", "--strict", "--outputjson", str(path)]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=_timeout_seconds(),
        )
    except FileNotFoundError:
        # Optional dependency in lightweight/docker environments.
        return []
    except subprocess.TimeoutExpired:
        return []
    payload = (proc.stdout or "").strip()
    if not payload:
        return []

    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return []

    issues: list[LinterIssue] = []
    for item in parsed.get("generalDiagnostics", []):
        if not isinstance(item, dict):
            continue
        if str(item.get("severity") or "").lower() != "error":
            continue
        line = int(((item.get("range") or {}).get("start") or {}).get("line") or 0) + 1
        issues.append(
            LinterIssue(
                tool="pyright",
                line=line,
                severity="high",
                code=str(item.get("rule") or "PYRIGHT"),
                message=str(item.get("message") or ""),
            )
        )
    return issues


def run_linters(path: Path) -> list[LinterIssue]:
    with ThreadPoolExecutor(max_workers=3) as pool:
        py_future = pool.submit(run_pylint, path)
        ba_future = pool.submit(run_bandit, path)
        fl_future = pool.submit(run_pyright, path)

        issues = py_future.result()
        issues.extend(ba_future.result())
        issues.extend(fl_future.result())

    return sorted(issues, key=lambda item: (item.line, item.tool, item.code, item.message))
