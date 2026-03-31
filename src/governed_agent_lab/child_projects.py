from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .domain_profiles import DOMAIN_PROFILES

CHILDREN_DIRNAME = "children"


def slugify(value: str) -> str:
    lowered = value.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "child-agent"


@dataclass
class ChildProjectRequest:
    name: str
    goal: str
    domain: str
    owner: str
    constraints: str


class ChildProjectBootstrapper:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.children_root = self.repo_root / CHILDREN_DIRNAME

    def list_children(self) -> list[dict[str, str]]:
        if not self.children_root.exists():
            return []
        children = []
        for project in sorted(self.children_root.iterdir()):
            if project.is_dir():
                children.append(
                    {
                        "name": project.name,
                        "path": str(project),
                        "project_control": str(project / "project-control.yaml"),
                    }
                )
        return children

    def create_child(self, request: ChildProjectRequest) -> dict[str, str]:
        if not request.name.strip() or not request.goal.strip():
            raise ValueError("Name and goal are required")
        if request.domain not in DOMAIN_PROFILES:
            raise ValueError("Unknown domain")

        profile = DOMAIN_PROFILES[request.domain]
        slug = slugify(request.name)
        child_root = self.children_root / slug
        if child_root.exists():
            raise FileExistsError(f"Child project already exists: {slug}")

        self._make_dirs(child_root)
        self._write(child_root / "README.md", self._readme(request, profile))
        self._write(child_root / "AGENTS.md", self._agents())
        self._write(child_root / "project-control.yaml", self._project_control(request, slug, profile))
        self._write(child_root / "docs/architecture.md", self._architecture(request, profile))
        self._write(child_root / "docs/deployment-guide.md", self._deployment())
        self._write(child_root / "docs/runbook.md", self._runbook())
        self._write(child_root / "docs/CHANGELOG.md", self._changelog())
        self._write(child_root / "config/secrets.example.env", self._secrets_example())
        self._write(child_root / "config/tool-profiles.toml", self._tool_profiles())
        self._write(child_root / "docs/agent-inventory.md", self._agent_inventory(request))
        self._write(child_root / "docs/model-registry.md", self._model_registry())
        self._write(child_root / "docs/prompt-register.md", self._prompt_register(request))
        self._write(child_root / "docs/tool-permission-matrix.md", self._tool_matrix())
        self._write(child_root / "docs/evaluation-approach.md", self._evaluation())
        self._write(child_root / "docs/human-oversight-rules.md", self._oversight())
        self._write(child_root / "docs/risks/risk-register.md", self._risk_register(request))
        self._write(child_root / "scripts/governance-check.sh", self._governance_check())
        self._write(child_root / "scripts/governance-preflight.sh", self._governance_preflight())
        self._write(child_root / "workspace/goal.md", self._goal_brief(request, profile))

        return {
            "name": request.name,
            "slug": slug,
            "path": str(child_root),
            "goal_path": str(child_root / "workspace/goal.md"),
        }

    def _make_dirs(self, root: Path) -> None:
        for rel in [
            "config",
            "docs",
            "docs/risks",
            "scripts",
            "tools",
            "workspace",
            "workspace/artifacts",
            "workspace/approvals",
            "src",
            "tests",
        ]:
            (root / rel).mkdir(parents=True, exist_ok=True)

    def _write(self, path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")
        if path.suffix in {".sh", ".command"}:
            path.chmod(0o755)

    def _readme(self, request: ChildProjectRequest, profile: dict[str, object]) -> str:
        return f"""# {request.name}

## Purpose

This child agent workspace was spawned from Governed Agent Lab. Its purpose is to pursue the goal below inside governed, sandbox-first boundaries.

## Goal

{request.goal}

## Status

- Owner: {request.owner or 'Unassigned'}
- Technical lead: Governed Agent Lab
- Domain: {profile['label']}
- Risk tier: High
- Production status: Not approved for production or money movement
- Maximum approved autonomy: A2 in sandboxed environments only

## Quick Start

1. Run `bash scripts/governance-preflight.sh`
2. Review `project-control.yaml`
3. Configure connector env vars from `config/secrets.example.env` as needed
4. Use `workspace/goal.md` as the active working brief

## Parentage

This project inherits governance conventions from the parent lab. New tools, model changes, or expanded autonomy require local documentation and review before use.
"""

    def _agents(self) -> str:
        return """# Agent Instructions

Before making substantial code or configuration changes in this repository:

1. run the governance preflight check
2. review `project-control.yaml`
3. review `docs/tool-permission-matrix.md` and `docs/human-oversight-rules.md`
4. stay within sandbox-only A2 autonomy unless governance is explicitly updated
5. review `config/tool-profiles.toml` before enabling connectors
6. document any tool, model, or prompt changes before broadening the child agent

## Preflight

```bash
bash scripts/governance-preflight.sh
```
"""

    def _project_control(self, request: ChildProjectRequest, slug: str, profile: dict[str, object]) -> str:
        notes = (
            "Child project created by Governed Agent Lab. "
            "External tool downloads are disabled by default and require explicit approval."
        )
        purpose = f"Child agent for {profile['label']} work on the goal '{request.goal[:80]}'"
        return f"""project_name: {slug}
project_type: agent
risk_tier: high
repository_model: single-repo
owner:
  name: {request.owner or 'Unassigned'}
  role: owner
technical_lead:
  name: Governed Agent Lab
  role: technical-lead
status: active
environments:
  - dev
  - sandbox
data_classification:
  handles_sensitive_data: false
  handles_money: false
  notes: "{notes}"
controls:
  required_docs:
    - README.md
    - docs/architecture.md
    - docs/deployment-guide.md
    - docs/runbook.md
    - docs/CHANGELOG.md
    - docs/risks/risk-register.md
    - docs/agent-inventory.md
    - docs/model-registry.md
    - docs/prompt-register.md
    - docs/tool-permission-matrix.md
    - docs/evaluation-approach.md
    - docs/human-oversight-rules.md
  machine_enforcement:
    - required-file-check
    - governance-preflight
    - tool-permission-review
    - sandbox-only-execution-check
exceptions: []
agent_controls:
  applicable: true
  autonomy_level: A2
  intended_purpose: "{purpose}"
  disallowed_actions:
    - "Placing live trades or moving money"
    - "Using production credentials"
    - "Installing or downloading tools without documented approval"
    - "Changing autonomy level without governance review"
  approved_tool_classes:
    - local sandbox execution
    - repository-local file editing
    - approved read-only research tools
  escalation_path: "Escalate to the owner before enabling new tools, network downloads, external writes, or production access."
  human_oversight: "Human review required before changing child scope or enabling new tools."
  rollback_disable: "Disable new tools, revert to advisory mode, and rerun preflight."
  model_registry:
    - docs/model-registry.md
  prompt_registry:
    - docs/prompt-register.md
"""

    def _architecture(self, request: ChildProjectRequest, profile: dict[str, object]) -> str:
        return f"""# Architecture Overview

## Summary

This child workspace focuses on {profile['label']} under the goal below:

{request.goal}

## Components

- Goal brief in `workspace/goal.md`
- Experiment code in `src/`
- Validation in `tests/`
- Governance records in `docs/`

## Data Flow

Inputs should remain governed, minimal, and reproducible. External write access is out of scope until documented and approved.
"""

    def _deployment(self) -> str:
        return """# Deployment Guide

## Environments

- `dev`
- `sandbox`

No production deployment is approved for this child workspace by default.
"""

    def _runbook(self) -> str:
        return """# Runbook

## Purpose

Operate this child agent only inside approved sandbox boundaries.

## Recovery

1. Stop running tasks.
2. Disable any newly added tools.
3. Re-run governance preflight.
4. Review docs before resuming.
"""

    def _changelog(self) -> str:
        return """# Change Log

## Unreleased

- Child workspace bootstrapped from Governed Agent Lab.
"""

    def _secrets_example(self) -> str:
        return """# Child-level connector secrets. Keep real values out of git.

OPENAI_API_KEY=
PERPLEXITY_API_KEY=
GENSPARK_BRIDGE_URL=http://127.0.0.1:8787
GENSPARK_BRIDGE_TOKEN=
SQLITE_DB_PATH=
"""

    def _tool_profiles(self) -> str:
        return """[[connector]]
key = "openai"
enabled = false
mode = "api"
access = "narrow"
notes = "Enable only if this child truly needs it."

[[connector]]
key = "perplexity"
enabled = false
mode = "api"
access = "read-only"
notes = "Enable for external research only."

[[connector]]
key = "genspark_bridge"
enabled = false
mode = "bridge"
access = "narrow"
notes = "Prefer a local bridge token over raw login access."

[[connector]]
key = "sqlite_readonly"
enabled = false
mode = "local"
access = "read-only"
notes = "Use approved research snapshots only."
"""

    def _agent_inventory(self, request: ChildProjectRequest) -> str:
        return f"""# Agent Inventory

| Agent ID | Name | Purpose | Autonomy | Model | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- |
| AG-001 | {request.name} | Child agent spawned for a specific governed goal. | A2 | See model registry | {request.owner or 'Unassigned'} | Draft |
"""

    def _model_registry(self) -> str:
        return """# Model Registry

| Model ID | Provider | Version | Purpose | Approved For | Owner | Last Reviewed |
| --- | --- | --- | --- | --- | --- | --- |
| M-001 | TBD | TBD | Goal-specific research and sandbox orchestration | Child workspace tasks only | TBD | 2026-03-22 |
"""

    def _prompt_register(self, request: ChildProjectRequest) -> str:
        return f"""# Prompt Register

| Prompt ID | Agent | Purpose | Current Version | Change Type | Last Reviewed |
| --- | --- | --- | --- | --- | --- |
| P-001 | {request.name} | Goal intake and execution guidance for the child workspace | v1 | Initial child bootstrap | 2026-03-22 |
"""

    def _tool_matrix(self) -> str:
        return """# Tool Permission Matrix

| Tool | Purpose | Allowed Actions | Prohibited Actions | Approval Required | Notes |
| --- | --- | --- | --- | --- | --- |
| Local shell tools | Build and test child workspace code | Read, local writes, local execution | Destructive system actions | No for normal repo work | Stay in repo boundary |
| Network downloads | Fetch dependencies or external tooling | None by default | Any download or install without review | Yes | Add entries before enabling |
| API connectors | Approved SaaS or model APIs | Calls through documented wrappers and env vars | Raw password sharing, unmanaged browser sessions, production writes | Yes | Keep access narrow and auditable |
| External APIs | Goal-specific integrations | Read-only only if documented | Writes, account actions, production access | Yes | Must be added before use |
"""

    def _evaluation(self) -> str:
        return """# Evaluation Approach

## Objectives

- Instruction adherence
- Scope control
- Tool-use correctness
- Reproducible outputs
- Clear escalation when new permissions are needed
"""

    def _oversight(self) -> str:
        return """# Human Oversight Rules

## Mandatory Review

- New tools
- Any download or install step
- Any external write
- Any autonomy increase
- Any production credential or account access
"""

    def _risk_register(self, request: ChildProjectRequest) -> str:
        return f"""# Risk Register

## Current Risk Classification

- Tier: High
- Owner: {request.owner or 'Unassigned'}
- Last reviewed: 2026-03-22

## Key Risks

| ID | Risk | Likelihood | Impact | Controls | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- |
| R-001 | Goal drift causes the child workspace to exceed its approved scope. | Medium | High | Keep `workspace/goal.md` current and review before changes. | {request.owner or 'Unassigned'} | Open |
| R-002 | Tools are added without documenting permissions. | Medium | High | Update tool matrix before adoption and rerun preflight. | {request.owner or 'Unassigned'} | Open |
| R-003 | Work expands toward production before governance is updated. | Medium | Critical | Keep sandbox-only controls and escalate before deployment changes. | {request.owner or 'Unassigned'} | Open |
"""

    def _goal_brief(self, request: ChildProjectRequest, profile: dict[str, object]) -> str:
        return f"""# Goal Brief

## Child Agent

- Name: {request.name}
- Domain: {profile['label']}
- Owner: {request.owner or 'Unassigned'}

## Goal

{request.goal}

## Constraints

{request.constraints or 'Stay simple, governed, sandbox-first, and evidence-backed.'}
"""

    def _governance_check(self) -> str:
        return """#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 /path/to/project"
  exit 1
fi

project_path="$1"
errors=0
warnings=0

pass() {
  echo "PASS: $1"
}

warn() {
  echo "WARN: $1"
  warnings=$((warnings + 1))
}

fail() {
  echo "FAIL: $1"
  errors=$((errors + 1))
}

require_file() {
  local rel_path="$1"
  if [[ -f "${project_path}/${rel_path}" ]]; then
    pass "Found ${rel_path}"
  else
    fail "Missing required file ${rel_path}"
  fi
}

require_file "README.md"
require_file "project-control.yaml"
require_file "docs/architecture.md"
require_file "docs/risks/risk-register.md"
require_file "docs/agent-inventory.md"
require_file "docs/model-registry.md"
require_file "docs/prompt-register.md"
require_file "docs/tool-permission-matrix.md"
require_file "docs/evaluation-approach.md"
require_file "docs/human-oversight-rules.md"
require_file "docs/deployment-guide.md"
require_file "docs/runbook.md"
require_file "AGENTS.md"

if [[ ${errors} -gt 0 ]]; then
  echo
  echo "Governance check failed with ${errors} error(s) and ${warnings} warning(s)."
  exit 1
fi

echo
echo "Governance check passed with ${warnings} warning(s)."
"""

    def _governance_preflight(self) -> str:
        return """#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bash "${repo_root}/scripts/governance-check.sh" "${repo_root}"
"""
