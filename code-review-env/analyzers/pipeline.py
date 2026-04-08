from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AnalyzerFindingRecord:
    analyzer: str
    module_id: str
    line: int
    severity: str
    rule_id: str
    message: str
    evidence: str = ""


@dataclass(frozen=True)
class AnalyzerRunSummary:
    analyzer: str
    findings: int
    status: str
    command: str
    command_hash: str
    analyzer_version: str
    error_message: str | None = None


class AnalyzerPipeline:
    """Run deterministic analyzers and normalize outputs into shared finding records."""

    def __init__(self, target_dir: Path, timeout_seconds: int = 45) -> None:
        self.target_dir = target_dir.resolve()
        self.timeout_seconds = timeout_seconds

    def run_all(self) -> tuple[list[AnalyzerFindingRecord], list[AnalyzerRunSummary]]:
        findings: list[AnalyzerFindingRecord] = []
        summaries: list[AnalyzerRunSummary] = []
        semgrep_enabled = os.getenv("GRAPHREVIEW_SEMGREP_ENABLED", "true").strip().lower() == "true"
        runners = [
            self._run_pylint,
            self._run_pyflakes,
            self._run_bandit,
            self._run_mypy,
            self._run_pyright,
            self._run_vulture,
        ]
        if semgrep_enabled:
            runners.append(self._run_semgrep)
        for runner in runners:
            records, summary = runner()
            findings.extend(records)
            summaries.append(summary)
        return findings, summaries

    def _run_mypy(self) -> tuple[list[AnalyzerFindingRecord], AnalyzerRunSummary]:
        cmd = [
            sys.executable,
            "-m",
            "mypy",
            str(self.target_dir),
            "--output",
            "json",
            "--show-error-codes",
            "--hide-error-context",
            "--no-color-output",
            "--no-error-summary",
        ]
        return self._run_with_parser("mypy", cmd, self._parse_mypy)

    def _run_pylint(self) -> tuple[list[AnalyzerFindingRecord], AnalyzerRunSummary]:
        cmd = [
            sys.executable,
            "-m",
            "pylint",
            str(self.target_dir),
            "--output-format=json2",
            "--score=n",
            "--reports=n",
        ]
        return self._run_with_parser("pylint", cmd, self._parse_pylint)

    def _run_pyflakes(self) -> tuple[list[AnalyzerFindingRecord], AnalyzerRunSummary]:
        cmd = [sys.executable, "-m", "pyflakes", str(self.target_dir)]
        return self._run_with_parser("pyflakes", cmd, self._parse_pyflakes)

    def _run_bandit(self) -> tuple[list[AnalyzerFindingRecord], AnalyzerRunSummary]:
        cmd = [sys.executable, "-m", "bandit", "-r", "-q", "-f", "json", str(self.target_dir)]
        return self._run_with_parser("bandit", cmd, self._parse_bandit)

    def _run_pyright(self) -> tuple[list[AnalyzerFindingRecord], AnalyzerRunSummary]:
        cmd = ["pyright", "--outputjson", str(self.target_dir)]
        return self._run_with_parser("pyright", cmd, self._parse_pyright)

    def _run_semgrep(self) -> tuple[list[AnalyzerFindingRecord], AnalyzerRunSummary]:
        rules_dir = self.target_dir / "semgrep_rules"
        if not rules_dir.exists():
            rules_dir = Path(__file__).resolve().parents[1] / "semgrep_rules"

        cmd = [
            "semgrep",
            "--json",
            "--config",
            str(rules_dir),
            str(self.target_dir),
        ]
        return self._run_with_parser("semgrep", cmd, self._parse_semgrep)

    def _run_vulture(self) -> tuple[list[AnalyzerFindingRecord], AnalyzerRunSummary]:
        cmd = [sys.executable, "-m", "vulture", str(self.target_dir), "--sort-by-size", "--json"]
        return self._run_with_parser("vulture", cmd, self._parse_vulture)

    def _run_with_parser(
        self,
        analyzer: str,
        cmd: list[str],
        parser: callable,
    ) -> tuple[list[AnalyzerFindingRecord], AnalyzerRunSummary]:
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.target_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except FileNotFoundError:
            return [], AnalyzerRunSummary(
                analyzer=analyzer,
                findings=0,
                status="missing",
                command=" ".join(cmd),
                command_hash=self._command_hash(cmd),
                analyzer_version="",
                error_message="executable not found",
            )
        except subprocess.TimeoutExpired:
            return [], AnalyzerRunSummary(
                analyzer=analyzer,
                findings=0,
                status="timeout",
                command=" ".join(cmd),
                command_hash=self._command_hash(cmd),
                analyzer_version=self._resolve_version(cmd),
                error_message="timed out",
            )

        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()
        analyzer_version = self._resolve_version(cmd)
        command = " ".join(cmd)
        command_hash = self._command_hash(cmd)
        if not stdout:
            # pyflakes emits diagnostics on stderr.
            if analyzer == "pyflakes" and stderr:
                stdout = stderr
            else:
                return [], AnalyzerRunSummary(
                    analyzer=analyzer,
                    findings=0,
                    status="ok" if proc.returncode == 0 else "no-output",
                    command=command,
                    command_hash=command_hash,
                    analyzer_version=analyzer_version,
                    error_message=stderr or None,
                )

        try:
            records = parser(stdout)
            status = "ok"
            if proc.returncode not in {0, 1} and analyzer not in {"pylint", "pyflakes", "bandit", "vulture", "mypy", "pyright", "semgrep"}:
                status = "no-output"
            return records, AnalyzerRunSummary(
                analyzer=analyzer,
                findings=len(records),
                status=status,
                command=command,
                command_hash=command_hash,
                analyzer_version=analyzer_version,
                error_message=stderr or None,
            )
        except Exception as exc:  # pragma: no cover
            return [], AnalyzerRunSummary(
                analyzer=analyzer,
                findings=0,
                status="parse-error",
                command=command,
                command_hash=command_hash,
                analyzer_version=analyzer_version,
                error_message=str(exc),
            )

    def _resolve_version(self, cmd: list[str]) -> str:
        if not cmd:
            return ""
        exe = cmd[0]
        if exe == sys.executable and len(cmd) >= 3 and cmd[1] == "-m":
            module = cmd[2]
            version_cmd = [sys.executable, "-m", module, "--version"]
        else:
            version_cmd = [exe, "--version"]
        try:
            proc = subprocess.run(
                version_cmd,
                cwd=str(self.target_dir),
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
        except Exception:
            return ""
        value = (proc.stdout or proc.stderr or "").strip().splitlines()
        return value[0][:160] if value else ""

    @staticmethod
    def _command_hash(cmd: list[str]) -> str:
        payload = " ".join(cmd)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _normalize_module(self, file_path: str) -> str:
        rel = Path(file_path)
        if rel.is_absolute():
            try:
                rel = rel.relative_to(self.target_dir)
            except ValueError:
                rel = rel.name
        module = str(rel).replace("\\", "/")
        if module.endswith(".py"):
            module = module[:-3]
        return module

    def _parse_mypy(self, text: str) -> list[AnalyzerFindingRecord]:
        parsed = json.loads(text)
        records: list[AnalyzerFindingRecord] = []
        if not isinstance(parsed, list):
            return records
        for item in parsed:
            if not isinstance(item, dict):
                continue
            file_path = str(item.get("file") or "")
            line = int(item.get("line") or 1)
            message = str(item.get("message") or "")
            code = str(item.get("code") or "mypy")
            severity = "high" if str(item.get("severity") or "error").lower() == "error" else "medium"
            records.append(
                AnalyzerFindingRecord(
                    analyzer="mypy",
                    module_id=self._normalize_module(file_path),
                    line=max(line, 1),
                    severity=severity,
                    rule_id=code,
                    message=message,
                    evidence="",
                )
            )
        return records

    def _parse_pylint(self, text: str) -> list[AnalyzerFindingRecord]:
        parsed = json.loads(text)
        messages = parsed.get("messages", []) if isinstance(parsed, dict) else []
        records: list[AnalyzerFindingRecord] = []
        for item in messages:
            if not isinstance(item, dict):
                continue
            module_id = self._normalize_module(str(item.get("path") or item.get("abspath") or ""))
            line = int(item.get("line") or 1)
            raw_type = str(item.get("type") or "warning").lower()
            severity = "low"
            if raw_type in {"fatal", "error"}:
                severity = "high"
            elif raw_type == "warning":
                severity = "medium"
            records.append(
                AnalyzerFindingRecord(
                    analyzer="pylint",
                    module_id=module_id,
                    line=max(line, 1),
                    severity=severity,
                    rule_id=str(item.get("messageId") or "pylint"),
                    message=str(item.get("message") or ""),
                    evidence=str(item.get("symbol") or ""),
                )
            )
        return records

    def _parse_pyflakes(self, text: str) -> list[AnalyzerFindingRecord]:
        records: list[AnalyzerFindingRecord] = []
        for raw_line in text.splitlines():
            stripped = raw_line.strip()
            if not stripped:
                continue
            parts = stripped.split(":", 3)
            if len(parts) < 3:
                continue
            module_id = self._normalize_module(parts[0].strip())
            line = int(parts[1]) if parts[1].isdigit() else 1
            message = parts[3].strip() if len(parts) == 4 else stripped
            records.append(
                AnalyzerFindingRecord(
                    analyzer="pyflakes",
                    module_id=module_id,
                    line=max(line, 1),
                    severity="medium",
                    rule_id="PYF000",
                    message=message,
                    evidence="",
                )
            )
        return records

    def _parse_bandit(self, text: str) -> list[AnalyzerFindingRecord]:
        parsed = json.loads(text)
        results = parsed.get("results", []) if isinstance(parsed, dict) else []
        records: list[AnalyzerFindingRecord] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            severity_raw = str(item.get("issue_severity") or "LOW").lower()
            severity = "low"
            if severity_raw == "high":
                severity = "high"
            elif severity_raw == "medium":
                severity = "medium"
            records.append(
                AnalyzerFindingRecord(
                    analyzer="bandit",
                    module_id=self._normalize_module(str(item.get("filename") or "")),
                    line=max(int(item.get("line_number") or 1), 1),
                    severity=severity,
                    rule_id=str(item.get("test_id") or "bandit"),
                    message=str(item.get("issue_text") or ""),
                    evidence=str(item.get("code") or ""),
                )
            )
        return records

    def _parse_pyright(self, text: str) -> list[AnalyzerFindingRecord]:
        parsed = json.loads(text)
        diagnostics = parsed.get("generalDiagnostics", []) if isinstance(parsed, dict) else []
        records: list[AnalyzerFindingRecord] = []
        for item in diagnostics:
            if not isinstance(item, dict):
                continue
            file_path = str(item.get("file") or "")
            severity_raw = str(item.get("severity") or "warning").lower()
            severity = "high" if severity_raw == "error" else "medium"
            message = str(item.get("message") or "")
            rule = str(item.get("rule") or "pyright")
            line = int(((item.get("range") or {}).get("start") or {}).get("line") or 0) + 1
            records.append(
                AnalyzerFindingRecord(
                    analyzer="pyright",
                    module_id=self._normalize_module(file_path),
                    line=max(line, 1),
                    severity=severity,
                    rule_id=rule,
                    message=message,
                    evidence="",
                )
            )
        return records

    def _parse_semgrep(self, text: str) -> list[AnalyzerFindingRecord]:
        parsed = json.loads(text)
        results = parsed.get("results", []) if isinstance(parsed, dict) else []
        records: list[AnalyzerFindingRecord] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path") or "")
            extra = item.get("extra") or {}
            severity_raw = str(extra.get("severity") or "WARNING").lower()
            severity = "high" if severity_raw == "error" else "medium"
            start_line = int(((item.get("start") or {}).get("line") or 1))
            message = str(extra.get("message") or "")
            rule_id = str(item.get("check_id") or "semgrep")
            evidence = str(extra.get("lines") or "")
            records.append(
                AnalyzerFindingRecord(
                    analyzer="semgrep",
                    module_id=self._normalize_module(path),
                    line=max(start_line, 1),
                    severity=severity,
                    rule_id=rule_id,
                    message=message,
                    evidence=evidence,
                )
            )
        return records

    def _parse_vulture(self, text: str) -> list[AnalyzerFindingRecord]:
        parsed = json.loads(text)
        issues = parsed if isinstance(parsed, list) else []
        records: list[AnalyzerFindingRecord] = []
        for item in issues:
            if not isinstance(item, dict):
                continue
            module_id = self._normalize_module(str(item.get("filename") or ""))
            line = int(item.get("lineno") or 1)
            confidence = int(item.get("confidence") or 60)
            severity = "medium" if confidence >= 70 else "low"
            rule_id = str(item.get("type") or "vulture")
            message = str(item.get("message") or item.get("name") or "Unused code candidate")
            records.append(
                AnalyzerFindingRecord(
                    analyzer="vulture",
                    module_id=module_id,
                    line=max(line, 1),
                    severity=severity,
                    rule_id=rule_id,
                    message=message,
                    evidence="",
                )
            )
        return records
