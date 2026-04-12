from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from analyzers.ast_checker import ASTFinding, run_all_checks


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

    def __init__(self, target_dir: Path, timeout_seconds: int = 60) -> None:
        self.target_dir = target_dir.resolve()
        self.timeout_seconds = timeout_seconds

    def run_all(self) -> tuple[list[AnalyzerFindingRecord], list[AnalyzerRunSummary]]:
        findings: list[AnalyzerFindingRecord] = []
        summaries: list[AnalyzerRunSummary] = []
        runners = [
            self._run_pyright,
            self._run_pysa,
            self._run_bandit,
            self._run_pylint,
            self._run_radon,
            self._run_ast_checks,
        ]
        for runner in runners:
            records, summary = runner()
            findings.extend(records)
            summaries.append(summary)
        return findings, summaries

    def _run_pyright(self) -> tuple[list[AnalyzerFindingRecord], AnalyzerRunSummary]:
        cmd = [self._resolve_pyright_bin(), "--strict", "--outputjson", str(self.target_dir)]
        return self._run_with_parser("pyright", cmd, self._parse_pyright)

    def _resolve_pyright_bin(self) -> str:
        env_bin = Path(sys.executable).resolve().parent / "pyright"
        if env_bin.exists():
            return str(env_bin)
        explicit = os.getenv("GRAPHREVIEW_PYRIGHT_BIN", "").strip()
        if explicit:
            return explicit
        return "pyright"

    def _run_pysa(self) -> tuple[list[AnalyzerFindingRecord], AnalyzerRunSummary]:
        cmd = ["pyre", "--noninteractive", "analyze", "--output", "json"]
        return self._run_with_parser("pysa", cmd, self._parse_pysa)

    def _run_bandit(self) -> tuple[list[AnalyzerFindingRecord], AnalyzerRunSummary]:
        cmd = [sys.executable, "-m", "bandit", "-r", "-q", "-f", "json", str(self.target_dir)]
        return self._run_with_parser("bandit", cmd, self._parse_bandit)

    def _run_pylint(self) -> tuple[list[AnalyzerFindingRecord], AnalyzerRunSummary]:
        cmd = [
            sys.executable,
            "-m",
            "pylint",
            str(self.target_dir),
            "--output-format=json2",
            "--score=n",
            "--reports=n",
            "--errors-only",
        ]
        return self._run_with_parser("pylint", cmd, self._parse_pylint)

    def _run_radon(self) -> tuple[list[AnalyzerFindingRecord], AnalyzerRunSummary]:
        cmd = [sys.executable, "-m", "radon", "cc", "-j", "-s", str(self.target_dir)]
        return self._run_with_parser("radon", cmd, self._parse_radon)

    def _run_ast_checks(self) -> tuple[list[AnalyzerFindingRecord], AnalyzerRunSummary]:
        cmd = ["python-ast-checker", str(self.target_dir)]
        py_files = sorted(path for path in self.target_dir.rglob("*.py") if path.is_file())
        records: list[AnalyzerFindingRecord] = []

        for py_file in py_files:
            if any(part.startswith(".") for part in py_file.parts):
                continue
            for finding in run_all_checks(py_file):
                records.append(self._ast_to_record(finding))

        return (
            records,
            AnalyzerRunSummary(
                analyzer="ast",
                findings=len(records),
                status="ok",
                command=" ".join(cmd),
                command_hash=self._command_hash(cmd),
                analyzer_version="builtin",
                error_message=None,
            ),
        )

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

        if not stdout and analyzer in {"pysa"} and stderr:
            stdout = stderr

        if not stdout:
            return [], AnalyzerRunSummary(
                analyzer=analyzer,
                findings=0,
                status="ok" if proc.returncode in {0, 1, 2} else "no-output",
                command=command,
                command_hash=command_hash,
                analyzer_version=analyzer_version,
                error_message=stderr or None,
            )

        try:
            records = parser(stdout)
            return records, AnalyzerRunSummary(
                analyzer=analyzer,
                findings=len(records),
                status="ok" if proc.returncode in {0, 1, 2} else "no-output",
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
            version_cmd = [sys.executable, "-m", cmd[2], "--version"]
        elif exe == "pyre":
            version_cmd = ["pyre", "--version"]
        elif exe == "pyright":
            version_cmd = ["pyright", "--version"]
        else:
            version_cmd = [exe, "--version"]

        try:
            proc = subprocess.run(
                version_cmd,
                cwd=str(self.target_dir),
                capture_output=True,
                text=True,
                timeout=10,
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

    def _ast_to_record(self, finding: ASTFinding) -> AnalyzerFindingRecord:
        return AnalyzerFindingRecord(
            analyzer="ast",
            module_id=self._normalize_module(finding.file),
            line=max(int(finding.line), 1),
            severity=finding.severity,
            rule_id=finding.rule,
            message=finding.message,
            evidence="",
        )

    def _parse_pyright(self, text: str) -> list[AnalyzerFindingRecord]:
        parsed = json.loads(text)
        diagnostics = parsed.get("generalDiagnostics", []) if isinstance(parsed, dict) else []
        records: list[AnalyzerFindingRecord] = []
        for item in diagnostics:
            if not isinstance(item, dict):
                continue
            if str(item.get("severity", "")).lower() != "error":
                continue
            file_path = str(item.get("file") or "")
            message = str(item.get("message") or "")
            rule = str(item.get("rule") or "pyright-error")
            line = int(((item.get("range") or {}).get("start") or {}).get("line") or 0) + 1
            records.append(
                AnalyzerFindingRecord(
                    analyzer="pyright",
                    module_id=self._normalize_module(file_path),
                    line=max(line, 1),
                    severity="high",
                    rule_id=rule,
                    message=message,
                    evidence="",
                )
            )
        return records
    def _parse_pysa(self, text: str) -> list[AnalyzerFindingRecord]:
        parsed = json.loads(text)
        issues: list[dict[str, object]] = []
        if isinstance(parsed, dict):
            issues = list(parsed.get("issues", []))
        elif isinstance(parsed, list):
            issues = [item for item in parsed if isinstance(item, dict)]

        records: list[AnalyzerFindingRecord] = []
        for issue in issues:
            path = str(issue.get("path") or issue.get("filename") or "")
            line = int(issue.get("line") or issue.get("line_number") or 1)
            code = str(issue.get("code") or issue.get("name") or "pysa")
            message = str(issue.get("description") or issue.get("message") or "Taint flow issue")
            records.append(
                AnalyzerFindingRecord(
                    analyzer="pysa",
                    module_id=self._normalize_module(path),
                    line=max(line, 1),
                    severity="high",
                    rule_id=code,
                    message=message,
                    evidence=str(issue.get("define") or issue.get("callable") or ""),
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

    def _parse_pylint(self, text: str) -> list[AnalyzerFindingRecord]:
        parsed = json.loads(text)
        messages = parsed.get("messages", []) if isinstance(parsed, dict) else []
        records: list[AnalyzerFindingRecord] = []
        for item in messages:
            if not isinstance(item, dict):
                continue
            msg_type = str(item.get("type") or "").lower()
            if msg_type not in {"fatal", "error"}:
                continue
            records.append(
                AnalyzerFindingRecord(
                    analyzer="pylint",
                    module_id=self._normalize_module(str(item.get("path") or item.get("abspath") or "")),
                    line=max(int(item.get("line") or 1), 1),
                    severity="high",
                    rule_id=str(item.get("messageId") or "pylint-error"),
                    message=str(item.get("message") or ""),
                    evidence=str(item.get("symbol") or ""),
                )
            )
        return records

    def _parse_radon(self, text: str) -> list[AnalyzerFindingRecord]:
        parsed = json.loads(text)
        records: list[AnalyzerFindingRecord] = []
        if not isinstance(parsed, dict):
            return records

        for file_path, blocks in parsed.items():
            if not isinstance(blocks, list):
                continue
            for block in blocks:
                if not isinstance(block, dict):
                    continue
                complexity = int(block.get("complexity") or 0)
                if complexity <= 10:
                    continue
                name = str(block.get("name") or block.get("type") or "block")
                line = int(block.get("lineno") or 1)
                records.append(
                    AnalyzerFindingRecord(
                        analyzer="radon",
                        module_id=self._normalize_module(file_path),
                        line=max(line, 1),
                        severity="medium" if complexity < 15 else "high",
                        rule_id="CC_HIGH",
                        message=f"Cyclomatic complexity {complexity} in {name} exceeds threshold 10",
                        evidence=f"complexity={complexity}",
                    )
                )
        return records


def run_pipeline(target_dir: str | Path) -> list[AnalyzerFindingRecord]:
    pipeline = AnalyzerPipeline(target_dir=Path(target_dir))
    findings, _ = pipeline.run_all()
    return findings
