from __future__ import annotations

import os
import platform
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any


DEFAULT_TOOL_PROBES = {
    "codex": ["codex", "--version"],
    "claude": ["claude", "--version"],
    "git": ["git", "--version"],
    "node": ["node", "--version"],
    "npm": ["npm", "--version"],
    "python": [sys.executable, "--version"],
    "pytest": ["pytest", "--version"],
    "uv": ["uv", "--version"],
}


def collect_lab_host_profile(root_path: Path | None = None) -> dict[str, Any]:
    root = (root_path or Path.cwd()).resolve()
    disk = shutil.disk_usage(root)
    tools = {name: _probe_tool(name, command) for name, command in DEFAULT_TOOL_PROBES.items()}
    cpu_count = os.cpu_count() or 1
    memory_gb = _memory_gb()
    readiness = _readiness_summary(tools, cpu_count, memory_gb)

    return {
        "hostname": socket.gethostname(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python_version": platform.python_version(),
        },
        "workspace": {
            "root_path": str(root),
            "disk_total_gb": round(disk.total / (1024 ** 3), 1),
            "disk_free_gb": round(disk.free / (1024 ** 3), 1),
        },
        "runtime": {
            "cpu_count": cpu_count,
            "memory_gb": memory_gb,
            "shell": os.environ.get("SHELL", ""),
            "virtual_env": os.environ.get("VIRTUAL_ENV", ""),
        },
        "tools": tools,
        "readiness": readiness,
        "governance_boundary": {
            "autonomy_level": "A2",
            "execution_mode": "sandbox-only",
            "notes": [
                "Local host profiling is allowed for sandbox benchmark preparation.",
                "Host access does not grant approval for external writes or autonomy escalation.",
            ],
        },
    }


def build_codex_runner_contract(profile: dict[str, Any]) -> dict[str, Any]:
    tools = profile.get("tools", {})
    readiness = profile.get("readiness", {})
    cpu_count = int(profile.get("runtime", {}).get("cpu_count", 1))
    memory_gb = float(profile.get("runtime", {}).get("memory_gb", 0.0))
    parallelism = max(1, min(cpu_count, 4))

    test_command = _preferred_test_command(tools)
    install_command = _preferred_install_command(tools)
    benchmark_steps = [
        "Read the mission brief, benchmark suite, and promotion gates before editing.",
        "Reproduce the failure or baseline behavior with the smallest trustworthy command.",
        f"Run targeted verification with `{test_command}` after each meaningful code change.",
        "Capture failed reasoning patterns as benchmark updates instead of silent prompt drift.",
        "Finish with a concise risk summary, verification notes, and reusable operator guidance.",
    ]
    if install_command:
        benchmark_steps.insert(1, f"Use `{install_command}` when dependencies need a local refresh.")

    host_tuning = [
        f"Keep concurrent tool work modest; this host is sized for about {parallelism} parallel local tasks.",
        "Prefer targeted tests and narrow searches over full-repo churn when iterating.",
    ]
    if memory_gb and memory_gb < 8.0:
        host_tuning.append("Avoid memory-hungry sweeps or large multi-process test fans on this host.")
    else:
        host_tuning.append("Use the available memory budget for focused local benchmarks, not speculative rewrites.")

    return {
        "runner": "codex",
        "status": readiness.get("status", "unknown"),
        "summary": readiness.get("summary", ""),
        "prerequisites": [
            "Stay within sandbox-only A2 autonomy.",
            "Do not use external credentials, production systems, or unsandboxed writes.",
            "Treat prompt, model, tool, and autonomy changes as promotion proposals.",
        ],
        "preferred_commands": {
            "test": test_command,
            "install": install_command,
            "python": _tool_path_or_default(tools, "python", sys.executable),
            "git": _tool_path_or_default(tools, "git", "git"),
        },
        "host_tuning": host_tuning,
        "execution_loop": benchmark_steps,
        "artifact_requirements": [
            "Record the commands used for reproduction and verification.",
            "Preserve benchmark outcomes, especially failed prerequisite reasoning cases.",
            "Write operator-facing instructions that another coding agent can reuse.",
        ],
        "promotion_blockers": [
            "No autonomy increase without governance review.",
            "No deployment-target change without review.",
            "No external-write tooling outside the approved sandbox boundary.",
        ],
    }


def codex_runner_contract_markdown(contract: dict[str, Any], profile: dict[str, Any]) -> str:
    lines = [
        "# Codex Runner Contract",
        "",
        f"- Host: {profile['hostname']}",
        f"- Status: {contract['status']}",
        f"- Summary: {contract['summary']}",
        "",
        "## Preferred Commands",
        "",
    ]
    for key, value in contract["preferred_commands"].items():
        if value:
            lines.append(f"- {key.title()}: `{value}`")
    lines.extend(["", "## Host Tuning", ""])
    for item in contract["host_tuning"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Execution Loop", ""])
    for item in contract["execution_loop"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Artifact Requirements", ""])
    for item in contract["artifact_requirements"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Promotion Blockers", ""])
    for item in contract["promotion_blockers"]:
        lines.append(f"- {item}")
    return "\n".join(lines).rstrip() + "\n"


def _probe_tool(name: str, command: list[str]) -> dict[str, Any]:
    executable = shutil.which(command[0]) if command[0] != sys.executable else sys.executable
    if executable is None:
        return {
            "name": name,
            "available": False,
            "path": None,
            "version": None,
        }
    version = _command_output([executable, *command[1:]])
    return {
        "name": name,
        "available": True,
        "path": executable,
        "version": version,
    }


def _command_output(command: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=2.0,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    output = (completed.stdout or completed.stderr).strip()
    return output.splitlines()[0] if output else None


def _memory_gb() -> float:
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                parts = line.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    kib = int(parts[1])
                    return round(kib / (1024 ** 2), 1)
    if hasattr(os, "sysconf") and "SC_PAGE_SIZE" in os.sysconf_names and "SC_PHYS_PAGES" in os.sysconf_names:
        page_size = os.sysconf("SC_PAGE_SIZE")
        phys_pages = os.sysconf("SC_PHYS_PAGES")
        if isinstance(page_size, int) and isinstance(phys_pages, int) and page_size > 0 and phys_pages > 0:
            return round((page_size * phys_pages) / (1024 ** 3), 1)
    return 0.0


def _readiness_summary(tools: dict[str, dict[str, Any]], cpu_count: int, memory_gb: float) -> dict[str, Any]:
    required = ["codex", "git", "python"]
    missing = [name for name in required if not tools.get(name, {}).get("available")]
    warnings = []
    if memory_gb and memory_gb < 4.0:
        warnings.append("Very low memory for iterative coding benchmarks.")
    if cpu_count <= 2:
        warnings.append("Limited CPU parallelism; prefer narrow test runs.")

    if missing:
        return {
            "status": "needs-tooling",
            "missing_tools": missing,
            "warnings": warnings,
            "summary": "This host is missing one or more required tools for Codex benchmark work.",
        }
    status = "ready-for-local-codex-sandbox"
    if warnings:
        status = "ready-with-constraints"
    return {
        "status": status,
        "missing_tools": [],
        "warnings": warnings,
        "summary": "This host can run local Codex-oriented sandbox coding benchmarks.",
    }


def _preferred_test_command(tools: dict[str, dict[str, Any]]) -> str:
    if tools.get("uv", {}).get("available"):
        return "uv run pytest"
    python_path = _tool_path_or_default(tools, "python", sys.executable)
    return f"{python_path} -m pytest"


def _preferred_install_command(tools: dict[str, dict[str, Any]]) -> str:
    if tools.get("uv", {}).get("available"):
        return "uv sync"
    python_path = _tool_path_or_default(tools, "python", sys.executable)
    return f"{python_path} -m pip install -r requirements.txt"


def _tool_path_or_default(tools: dict[str, dict[str, Any]], key: str, default: str) -> str:
    return str(tools.get(key, {}).get("path") or default)
