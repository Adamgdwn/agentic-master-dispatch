from __future__ import annotations

import json
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MAX_OUTPUT_CHARS = 4000


@dataclass(frozen=True)
class SandboxBenchmarkCase:
    id: str
    title: str
    description: str
    command: list[str]
    timeout_seconds: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "command": self.command,
            "timeout_seconds": self.timeout_seconds,
        }


class SandboxBenchmarkExecutor:
    def __init__(self, root_path: Path, cases: list[SandboxBenchmarkCase] | None = None) -> None:
        self.root_path = root_path
        self.cases = cases or []

    def list_suite(self) -> dict[str, Any]:
        return {
            "suite_key": "lab-host-coding-sandbox",
            "title": "Lab Host Coding Sandbox",
            "root_path": str(self.root_path),
            "cases": [case.to_dict() for case in self.cases],
        }

    def run(self, case_ids: list[str] | None = None) -> dict[str, Any]:
        selected = self._selected_cases(case_ids)
        run_group = f"lab-run-{uuid.uuid4().hex[:12]}"
        results = [self._run_case(run_group, case) for case in selected]
        passed = all(item["passed"] for item in results)
        return {
            "run_group": run_group,
            "suite": self.list_suite(),
            "results": results,
            "passed": passed,
        }

    def _selected_cases(self, case_ids: list[str] | None) -> list[SandboxBenchmarkCase]:
        if not case_ids:
            return list(self.cases)
        requested = set(case_ids)
        selected = [case for case in self.cases if case.id in requested]
        missing = requested - {case.id for case in selected}
        if missing:
            raise ValueError(f"Unknown sandbox benchmark case ids: {', '.join(sorted(missing))}")
        return selected

    def _run_case(self, run_group: str, case: SandboxBenchmarkCase) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                case.command,
                cwd=self.root_path,
                capture_output=True,
                text=True,
                timeout=case.timeout_seconds,
                check=False,
            )
            duration = round(time.perf_counter() - started, 3)
            stdout = _trim_output(completed.stdout)
            stderr = _trim_output(completed.stderr)
            passed = completed.returncode == 0
            status = "passed" if passed else "failed"
            return {
                "run_group": run_group,
                "case_id": case.id,
                "title": case.title,
                "command": case.command,
                "passed": passed,
                "status": status,
                "exit_code": completed.returncode,
                "duration_seconds": duration,
                "stdout": stdout,
                "stderr": stderr,
            }
        except subprocess.TimeoutExpired as exc:
            duration = round(time.perf_counter() - started, 3)
            stdout = _trim_output(exc.stdout or "")
            stderr = _trim_output(exc.stderr or "")
            return {
                "run_group": run_group,
                "case_id": case.id,
                "title": case.title,
                "command": case.command,
                "passed": False,
                "status": "timed-out",
                "exit_code": None,
                "duration_seconds": duration,
                "stdout": stdout,
                "stderr": stderr,
            }


def build_lab_host_benchmark_executor(
    root_path: Path,
    *,
    test_command: str,
) -> SandboxBenchmarkExecutor:
    cases = [
        SandboxBenchmarkCase(
            id="governance-preflight",
            title="Governance Preflight",
            description="Verify the governed project metadata and required documentation are intact.",
            command=["bash", "scripts/governance-preflight.sh"],
            timeout_seconds=30,
        ),
        SandboxBenchmarkCase(
            id="coding-loop-stack",
            title="Coding Loop Stack",
            description="Run the focused benchmark, lab-host, mission, and server tests that back the coding loop.",
            command=_shell_command_from_string(
                f"{test_command} tests/test_benchmark_runner.py tests/test_coding_loop.py tests/test_lab_host.py tests/test_server.py"
            ),
            timeout_seconds=120,
        ),
        SandboxBenchmarkCase(
            id="full-unit-suite",
            title="Full Unit Suite",
            description="Run the full local unit test suite for a broader regression signal.",
            command=_shell_command_from_string(test_command),
            timeout_seconds=240,
        ),
    ]
    return SandboxBenchmarkExecutor(root_path=root_path, cases=cases)


def benchmark_suite_markdown(suite: dict[str, Any]) -> str:
    lines = [
        "# Sandbox Benchmark Suite",
        "",
        f"- Suite: {suite['title']}",
        f"- Root Path: {suite['root_path']}",
        "",
    ]
    for case in suite["cases"]:
        lines.extend(
            [
                f"## {case['title']}",
                "",
                f"- Case ID: {case['id']}",
                f"- Timeout: {case['timeout_seconds']}s",
                f"- Command: `{_command_string(case['command'])}`",
                "",
                case["description"],
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _shell_command_from_string(command: str) -> list[str]:
    return ["bash", "-lc", command]


def _command_string(command: list[str]) -> str:
    return " ".join(json.dumps(part) if " " in part else part for part in command)


def _trim_output(output: str) -> str:
    text = output.strip()
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[:MAX_OUTPUT_CHARS] + "\n...[truncated]"
