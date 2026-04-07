from __future__ import annotations

import json
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


def run_pylint(path: Path) -> list[LinterIssue]:
    cmd = [
        sys.executable,
        "-m",
        "pylint",
        str(path),
        "--output-format=json2",
        "--score=n",
        "--reports=n",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)

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
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)

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


def run_pyflakes(path: Path) -> list[LinterIssue]:
    cmd = [sys.executable, "-m", "pyflakes", str(path)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    payload = (proc.stdout or "").strip()
    if not payload:
        return []

    issues: list[LinterIssue] = []
    for raw_line in payload.splitlines():
        line = 0
        message = raw_line.strip()
        if ":" in raw_line:
            parts = raw_line.split(":", 3)
            if len(parts) >= 3 and parts[1].isdigit():
                line = int(parts[1])
                message = parts[3].strip() if len(parts) == 4 else message
        issues.append(
            LinterIssue(
                tool="pyflakes",
                line=line,
                severity="medium",
                code="PYF000",
                message=message,
            )
        )
    return issues


def run_linters(path: Path) -> list[LinterIssue]:
    issues = run_pylint(path)
    issues.extend(run_bandit(path))
    issues.extend(run_pyflakes(path))
    return issues
