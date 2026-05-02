from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .coding_loop import CodingOptimizationLoop, CodingOptimizationRequest
from .child_projects import (
    ChildProjectBootstrapper,
    GovernedProjectRequest,
    GovernedRunRequest,
    slugify,
)
from .domain_profiles import DOMAIN_PROFILES
from .lab_host import codex_runner_contract_markdown
from .multi_agent import MultiAgentRequest, MultiAgentSystem
from .sandbox_benchmarks import benchmark_suite_markdown
from .storage import Storage


DEFAULT_PRIORITY = "balanced"
ALLOWED_CONNECTORS = ("openai", "perplexity", "sqlite_readonly", "genspark_bridge")


@dataclass
class MissionRequest:
    goal: str
    domain: str
    constraints: str = ""
    owner: str = ""
    mission_name: str = ""
    project_name: str = ""
    project_kind: str = "project"
    priority: str = DEFAULT_PRIORITY
    requested_connectors: list[str] | None = None


class MissionControl:
    def __init__(self, storage: Storage, children: ChildProjectBootstrapper) -> None:
        self.storage = storage
        self.children = children
        self.multi_agent = MultiAgentSystem()
        self.coding_loop = CodingOptimizationLoop(storage, root_path=self.children.repo_root)

    def create_mission(self, request: MissionRequest) -> dict[str, Any]:
        profile = DOMAIN_PROFILES[request.domain]
        mission_name = request.mission_name.strip() or self._default_mission_name(request.goal, profile["label"])
        project_name = request.project_name.strip() or mission_name
        requested_connectors = self._normalize_connectors(request.requested_connectors)
        project = self._ensure_project_record(request, profile, project_name)
        run_workspace = self.children.create_run_workspace(
            GovernedRunRequest(
                project_slug=project["slug"],
                mission_name=mission_name,
                goal=request.goal,
                domain=request.domain,
                owner=request.owner,
                constraints=request.constraints,
            )
        )

        approvals = self._build_approvals(profile, requested_connectors)
        orchestration = self.multi_agent.run(
            MultiAgentRequest(
                goal=request.goal,
                domain_label=profile["label"],
                constraints=request.constraints,
                blocked_actions=profile["blocked_actions"],
            )
        )
        plan = self._build_plan(profile, request, requested_connectors, project, run_workspace, orchestration)
        status = "awaiting-approval" if approvals else "ready"
        summary = (
            f"Mission '{mission_name}' is ready to stand up a governed run workspace for "
            f"{profile['label'].lower()} work."
        )

        mission_id = self.storage.create_mission(
            project_id=project["id"],
            run_id=None,
            name=mission_name,
            goal=request.goal,
            domain=request.domain,
            owner=request.owner or "Unassigned",
            priority=request.priority or DEFAULT_PRIORITY,
            status=status,
            constraints=request.constraints,
            child_name=run_workspace["name"],
            child_slug=run_workspace["slug"],
            child_path=run_workspace["path"],
            summary=summary,
            spec=plan["spec"],
            result=plan,
        )
        run_summary = (
            f"Run {run_workspace['run_key']} created for mission '{mission_name}' inside project '{project['name']}'."
        )
        run_id = self.storage.create_run(
            project_id=project["id"],
            mission_id=mission_id,
            run_key=run_workspace["run_key"],
            title=mission_name,
            status=status,
            root_path=run_workspace["path"],
            summary=run_summary,
            spec=plan["spec"]["run"],
            result={"phases": plan["phases"], "governance": plan["governance"]},
        )
        self.storage.update_mission_links(mission_id, project_id=project["id"], run_id=run_id)

        if request.domain == "coding-optimization":
            learning_run = self.coding_loop.run(
                CodingOptimizationRequest(goal=request.goal, constraints=request.constraints),
                mission_id=mission_id,
            )
            plan["optimization_lab"] = self._optimization_lab_summary(learning_run)
            summary = (
                f"Mission '{mission_name}' is staging a governed coding optimization loop. "
                f"Recommended pack: {plan['optimization_lab']['recommended_candidate']['title']}."
            )
            self.storage.update_mission_result(mission_id, summary=summary, result=plan)

        for approval in approvals:
            self.storage.add_approval(mission_id, **approval)

        artifact_specs = self._write_child_files(
            mission_id=mission_id,
            child_root=Path(run_workspace["path"]),
            mission_name=mission_name,
            plan=plan,
            approvals=approvals,
        )
        for artifact in artifact_specs:
            self.storage.add_artifact(mission_id, **artifact)

        if plan.get("optimization_lab"):
            recommended = plan["optimization_lab"]["recommended_candidate"]
            outcome_id = self.storage.create_outcome(
                project_id=project["id"],
                run_id=run_id,
                name=f"{mission_name} recommendation",
                status="draft",
                path=str(Path(run_workspace["path"]) / "workspace" / "instruction-candidates.md"),
                summary="Draft outcome generated from the coding optimization recommendation.",
                content={
                    "recommended_candidate": recommended["candidate_key"],
                    "learning_run_id": plan["optimization_lab"]["learning_run_id"],
                },
            )
            project["current_outcome_id"] = outcome_id

        status = self.storage.refresh_mission_status(mission_id)
        plan["status"] = status
        self.storage.update_mission_result(mission_id, status=status, summary=summary, result=plan)
        self.storage.update_run(run_id, status=status, result={"phases": plan["phases"], "governance": plan["governance"]})
        self.storage.add_memory(
            request.domain,
            "mission",
            f"Mission {mission_id} created run workspace '{run_workspace['run_key']}' in project '{project['name']}' for goal '{request.goal[:80]}'.",
            weight=1.4,
        )
        return self.storage.get_mission(mission_id) or {}

    def decide_approval(self, approval_id: int, status: str) -> dict[str, Any] | None:
        mission_id = self.storage.update_approval_status(approval_id, status)
        if mission_id is None:
            return None
        mission = self.storage.get_mission(mission_id)
        if not mission:
            return None

        result = mission["result"]
        result["status"] = mission["status"]
        self.storage.update_mission_result(mission_id, status=mission["status"], result=result)
        return self.storage.get_mission(mission_id)

    def _normalize_connectors(self, connectors: list[str] | None) -> list[str]:
        requested = connectors or []
        return [item for item in requested if item in ALLOWED_CONNECTORS]

    def _ensure_project_record(
        self,
        request: MissionRequest,
        profile: dict[str, Any],
        project_name: str,
    ) -> dict[str, Any]:
        slug = slugify(project_name)
        existing = self.storage.get_project_by_slug(slug)
        if existing is not None:
            return existing

        project_workspace = self.children.ensure_project(
            GovernedProjectRequest(
                name=project_name,
                domain=request.domain,
                owner=request.owner,
                purpose=request.goal,
                constraints=request.constraints,
                kind=request.project_kind or "project",
            )
        )
        project_id = self.storage.create_project(
            name=project_workspace["name"],
            slug=project_workspace["slug"],
            domain=request.domain,
            kind=request.project_kind or "project",
            owner=request.owner or "Unassigned",
            status="active",
            root_path=project_workspace["path"],
            summary=f"Governed project root for {profile['label'].lower()} work.",
            metadata={
                "purpose": request.goal,
                "goal_path": project_workspace["goal_path"],
            },
        )
        return self.storage.get_project(project_id) or {
            "id": project_id,
            "name": project_workspace["name"],
            "slug": project_workspace["slug"],
            "root_path": project_workspace["path"],
            "kind": request.project_kind or "project",
        }

    def _default_mission_name(self, goal: str, domain_label: str) -> str:
        words = re.findall(r"[A-Za-z0-9]+", goal)
        if not words:
            return f"{domain_label} Mission"
        label = " ".join(words[:5]).title()
        return f"{label} Lab"

    def _reserve_child_name(self, base_name: str) -> str:
        candidate = base_name
        child_root = self.children.children_root
        suffix = 2
        while (child_root / slugify(candidate)).exists():
            candidate = f"{base_name} {suffix}"
            suffix += 1
        return candidate

    def _build_approvals(self, profile: dict[str, Any], requested_connectors: list[str]) -> list[dict[str, str]]:
        approvals = [
            {
                "approval_key": "tool-scope-review",
                "title": "Review child tool scope",
                "rationale": "Confirm the child workspace only gets the minimum tool access required for the goal.",
                "required_for": "mission activation",
            }
        ]
        if requested_connectors:
            approvals.append(
                {
                    "approval_key": "connector-access",
                    "title": "Approve requested connectors",
                    "rationale": (
                        "Connector access introduces external APIs or secrets and should be approved explicitly "
                        f"for {profile['label'].lower()} work."
                    ),
                    "required_for": ", ".join(requested_connectors),
                }
            )
        return approvals

    def _build_plan(
        self,
        profile: dict[str, Any],
        request: MissionRequest,
        requested_connectors: list[str],
        project: dict[str, Any],
        run_workspace: dict[str, str],
        orchestration: dict[str, Any],
    ) -> dict[str, Any]:
        success_definition = (
            "Create a governed project-aligned run workspace, keep scope narrow, preserve prior work, "
            "and promote outcomes explicitly instead of overwriting them."
        )
        phases = [
            {
                "id": "intake",
                "title": "Clarify the mission",
                "status": "complete",
                "summary": "The boss agent has captured the goal, owner, constraints, and requested connectors.",
            },
            {
                "id": "child-bootstrap",
                "title": "Create governed run workspace",
                "status": "complete",
                "summary": f"Run workspace created at {run_workspace['path']}.",
            },
            {
                "id": "approval-gate",
                "title": "Collect approvals",
                "status": "active",
                "summary": "The child waits here until connector and tool-scope reviews are complete.",
            },
            {
                "id": "execution",
                "title": "Run in the child workspace",
                "status": "pending",
                "summary": "The child will carry out its assigned work only after the approval gate is cleared.",
            },
            {
                "id": "review",
                "title": "Review outputs",
                "status": "pending",
                "summary": "Artifacts return to the boss agent for summary, handoff, and archive.",
            },
        ]

        child_spec = {
            "name": run_workspace["name"],
            "slug": run_workspace["slug"],
            "path": run_workspace["path"],
            "goal_path": run_workspace["goal_path"],
            "approved_boundary": "sandbox-only A2",
            "requested_connectors": requested_connectors,
            "recommended_roles": ["planner", "research", "review", "reporting"],
        }
        spec = {
            "mission_name": request.mission_name.strip() or self._default_mission_name(request.goal, profile["label"]),
            "domain": request.domain,
            "priority": request.priority or DEFAULT_PRIORITY,
            "success_definition": success_definition,
            "requested_connectors": requested_connectors,
            "project": {
                "id": project["id"],
                "name": project["name"],
                "slug": project["slug"],
                "kind": project["kind"],
                "path": project["root_path"],
                "current_outcome_id": project.get("current_outcome_id"),
            },
            "run": {
                "key": run_workspace["run_key"],
                "name": run_workspace["name"],
                "slug": run_workspace["slug"],
                "path": run_workspace["path"],
                "goal_path": run_workspace["goal_path"],
            },
            "child": child_spec,
        }
        return {
            "status": "draft",
            "brief": {
                "goal": request.goal,
                "domain_label": profile["label"],
                "owner": request.owner or "Unassigned",
                "constraints": request.constraints or "Stay governed, sandbox-only, and evidence-backed.",
                "success_definition": success_definition,
            },
            "spec": spec,
            "phases": phases,
            "orchestration": orchestration,
            "governance": {
                "autonomy_level": "A2",
                "boundary": "sandbox-only",
                "human_review_required_for": [
                    "new connectors",
                    "new secrets",
                    "paid APIs",
                    "external writes",
                    "live execution proposals",
                ],
            },
            "child": child_spec,
            "project": spec["project"],
            "run": spec["run"],
            "next_actions": [
                "Review the mission brief.",
                "Approve or hold requested connectors.",
                "Open the isolated run workspace and begin execution after approvals clear.",
            ],
        }

    def _write_child_files(
        self,
        *,
        mission_id: int,
        child_root: Path,
        mission_name: str,
        plan: dict[str, Any],
        approvals: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        workspace_root = child_root / "workspace"
        artifacts_root = workspace_root / "artifacts"
        artifacts_root.mkdir(parents=True, exist_ok=True)

        mission_brief_path = workspace_root / "mission-brief.md"
        mission_brief_path.write_text(self._mission_brief_markdown(mission_id, mission_name, plan), encoding="utf-8")

        approval_path = workspace_root / "approval-requests.md"
        approval_path.write_text(self._approval_markdown(approvals), encoding="utf-8")

        manifest_path = workspace_root / "mission-manifest.json"
        manifest_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")

        kickoff_path = artifacts_root / "01-kickoff.md"
        kickoff_path.write_text(self._kickoff_markdown(plan), encoding="utf-8")

        artifacts = [
            {
                "artifact_type": "brief",
                "title": "Mission brief",
                "path": str(mission_brief_path),
                "summary": "A human-readable brief for the child workspace.",
                "content": {"mission_name": mission_name, "phase": "intake"},
            },
            {
                "artifact_type": "approval",
                "title": "Approval requests",
                "path": str(approval_path),
                "summary": "The approvals that must clear before the child should run.",
                "content": {"approvals": approvals},
            },
            {
                "artifact_type": "manifest",
                "title": "Mission manifest",
                "path": str(manifest_path),
                "summary": "A machine-readable mission package for the child workspace.",
                "content": {"keys": list(plan.keys())},
            },
            {
                "artifact_type": "kickoff",
                "title": "Kickoff note",
                "path": str(kickoff_path),
                "summary": "A starter note for the child agent explaining what to do first.",
                "content": {"phase": "child-bootstrap"},
            },
        ]

        if plan.get("optimization_lab"):
            optimization = plan["optimization_lab"]
            benchmark_path = workspace_root / "coding-benchmark.json"
            benchmark_path.write_text(json.dumps(optimization["benchmark"], indent=2), encoding="utf-8")

            instructions_path = workspace_root / "instruction-candidates.md"
            instructions_path.write_text(
                self._instruction_candidates_markdown(optimization),
                encoding="utf-8",
            )

            promotion_path = workspace_root / "promotion-gates.md"
            promotion_path.write_text(
                self._promotion_gates_markdown(optimization),
                encoding="utf-8",
            )

            host_profile_path = workspace_root / "lab-host-profile.json"
            host_profile_path.write_text(
                json.dumps(optimization["lab_host_profile"], indent=2),
                encoding="utf-8",
            )

            codex_contract_path = workspace_root / "codex-runner-contract.md"
            codex_contract_path.write_text(
                codex_runner_contract_markdown(
                    optimization["codex_runner_contract"],
                    optimization["lab_host_profile"],
                ),
                encoding="utf-8",
            )

            sandbox_suite_path = workspace_root / "sandbox-benchmark-suite.md"
            sandbox_suite_path.write_text(
                benchmark_suite_markdown(optimization["sandbox_benchmark_suite"]),
                encoding="utf-8",
            )

            artifacts.extend(
                [
                    {
                        "artifact_type": "benchmark",
                        "title": "Coding benchmark suite",
                        "path": str(benchmark_path),
                        "summary": "Sandbox benchmark cases for the coding optimization loop.",
                        "content": {"benchmark_name": optimization["benchmark"]["name"]},
                    },
                    {
                        "artifact_type": "instruction-pack",
                        "title": "Instruction candidates",
                        "path": str(instructions_path),
                        "summary": "Candidate operator instructions for Codex or Claude Code style agents.",
                        "content": {"recommended_candidate": optimization["recommended_candidate"]["candidate_key"]},
                    },
                    {
                        "artifact_type": "promotion-gates",
                        "title": "Promotion gates",
                        "path": str(promotion_path),
                        "summary": "Governance blockers and promotion criteria for any stronger autonomy proposal.",
                        "content": {"learning_run_id": optimization["learning_run_id"]},
                    },
                    {
                        "artifact_type": "lab-host-profile",
                        "title": "Lab host profile",
                        "path": str(host_profile_path),
                        "summary": "A host-level readiness snapshot for local sandbox coding benchmarks.",
                        "content": {"status": optimization["lab_host_profile"]["readiness"]["status"]},
                    },
                    {
                        "artifact_type": "codex-runner-contract",
                        "title": "Codex runner contract",
                        "path": str(codex_contract_path),
                        "summary": "Host-aware execution guidance for Codex on a sandbox lab machine.",
                        "content": {"runner": optimization["codex_runner_contract"]["runner"]},
                    },
                    {
                        "artifact_type": "sandbox-benchmark-suite",
                        "title": "Sandbox benchmark suite",
                        "path": str(sandbox_suite_path),
                        "summary": "Executable local benchmark cases for validating the coding loop on the lab host.",
                        "content": {"suite_key": optimization["sandbox_benchmark_suite"]["suite_key"]},
                    },
                ]
            )

        return artifacts

    def _mission_brief_markdown(self, mission_id: int, mission_name: str, plan: dict[str, Any]) -> str:
        brief = plan["brief"]
        child = plan["child"]
        project = plan["project"]
        run = plan["run"]
        return f"""# Mission Brief

## Mission

- ID: {mission_id}
- Name: {mission_name}
- Domain: {brief['domain_label']}
- Owner: {brief['owner']}
- Project: {project['name']} ({project['kind']})
- Project Root: {project['path']}
- Run Workspace: {run['path']}

## Goal

{brief['goal']}

## Constraints

{brief['constraints']}

## Success Definition

{brief['success_definition']}

## Operating Boundary

- Sandbox-only A2 autonomy
- No production credentials
- No external writes without explicit approval
"""

    def _approval_markdown(self, approvals: list[dict[str, str]]) -> str:
        lines = [
            "# Approval Requests",
            "",
            "Review these items before activating the run workspace.",
            "",
        ]
        for approval in approvals:
            lines.extend(
                [
                    f"## {approval['title']}",
                    "",
                    f"- Status: {approval.get('status', 'pending')}",
                    f"- Required For: {approval['required_for']}",
                    f"- Why: {approval['rationale']}",
                    "",
                ]
            )
        return "\n".join(lines).rstrip() + "\n"

    def _kickoff_markdown(self, plan: dict[str, Any]) -> str:
        lines = [
            "# Kickoff",
            "",
            "Start here once approvals clear.",
            "",
            "## First Moves",
        ]
        for action in plan["next_actions"]:
            lines.append(f"- {action}")
        lines.extend(["", "## Phases"])
        for phase in plan["phases"]:
            lines.append(f"- {phase['title']}: {phase['summary']}")
        return "\n".join(lines) + "\n"

    def _optimization_lab_summary(self, learning_run: dict[str, Any]) -> dict[str, Any]:
        result = learning_run["result"]
        return {
            "learning_run_id": learning_run["id"],
            "status": learning_run["status"],
            "evaluation_mode": result["evaluation_mode"],
            "objective_profile": result["objective_profile"],
            "benchmark": result["benchmark"],
            "lab_host_profile": result["lab_host_profile"],
            "codex_runner_contract": result["codex_runner_contract"],
            "sandbox_benchmark_suite": result["sandbox_benchmark_suite"],
            "recommended_candidate": result["recommended_candidate"],
            "promotion_blockers": result["promotion_blockers"],
            "adoption_path": result["adoption_path"],
            "attempts": learning_run["attempts"],
        }

    def _instruction_candidates_markdown(self, optimization: dict[str, Any]) -> str:
        recommended = optimization["recommended_candidate"]
        lines = [
            "# Instruction Candidates",
            "",
            f"Recommended candidate: {recommended['title']}",
            f"Static readiness score: {recommended['score']['static_readiness']}",
            "",
        ]
        for attempt in optimization["attempts"]:
            lines.extend(
                [
                    f"## {attempt['title']}",
                    "",
                    f"- Candidate Key: {attempt['candidate_key']}",
                    f"- Static Readiness: {attempt['score']['static_readiness']}",
                    "",
                    "### Instruction Pack",
                    "",
                ]
            )
            for item in attempt["instruction_pack"]:
                lines.append(f"- {item}")
            lines.extend(["", "### Strengths", ""])
            for item in attempt["strengths"]:
                lines.append(f"- {item}")
            lines.extend(["", "### Risks", ""])
            for item in attempt["risks"]:
                lines.append(f"- {item}")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def _promotion_gates_markdown(self, optimization: dict[str, Any]) -> str:
        lines = [
            "# Promotion Gates",
            "",
            f"- Learning Run ID: {optimization['learning_run_id']}",
            f"- Evaluation Mode: {optimization['evaluation_mode']}",
            "",
            "## Promotion Blockers",
            "",
        ]
        for blocker in optimization["promotion_blockers"]:
            lines.append(f"- {blocker}")
        lines.extend(["", "## Adoption Path", ""])
        for step in optimization["adoption_path"]:
            lines.append(f"- {step}")
        lines.extend(["", "## Operator Pack", ""])
        for item in optimization["recommended_candidate"]["instruction_pack"]:
            lines.append(f"- {item}")
        return "\n".join(lines).rstrip() + "\n"
