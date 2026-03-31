from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .child_projects import ChildProjectBootstrapper, ChildProjectRequest, slugify
from .domain_profiles import DOMAIN_PROFILES
from .multi_agent import MultiAgentRequest, MultiAgentSystem
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
    priority: str = DEFAULT_PRIORITY
    requested_connectors: list[str] | None = None


class MissionControl:
    def __init__(self, storage: Storage, children: ChildProjectBootstrapper) -> None:
        self.storage = storage
        self.children = children
        self.multi_agent = MultiAgentSystem()

    def create_mission(self, request: MissionRequest) -> dict[str, Any]:
        profile = DOMAIN_PROFILES[request.domain]
        mission_name = request.mission_name.strip() or self._default_mission_name(request.goal, profile["label"])
        child_name = self._reserve_child_name(mission_name)
        requested_connectors = self._normalize_connectors(request.requested_connectors)

        child = self.children.create_child(
            ChildProjectRequest(
                name=child_name,
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
        plan = self._build_plan(profile, request, requested_connectors, child, orchestration)
        status = "awaiting-approval" if approvals else "ready"
        summary = (
            f"Mission '{mission_name}' is ready to stand up a governed child workspace for "
            f"{profile['label'].lower()} work."
        )

        mission_id = self.storage.create_mission(
            name=mission_name,
            goal=request.goal,
            domain=request.domain,
            owner=request.owner or "Unassigned",
            priority=request.priority or DEFAULT_PRIORITY,
            status=status,
            constraints=request.constraints,
            child_name=child["name"],
            child_slug=child["slug"],
            child_path=child["path"],
            summary=summary,
            spec=plan["spec"],
            result=plan,
        )

        for approval in approvals:
            self.storage.add_approval(mission_id, **approval)

        artifact_specs = self._write_child_files(
            mission_id=mission_id,
            child_root=Path(child["path"]),
            mission_name=mission_name,
            plan=plan,
            approvals=approvals,
        )
        for artifact in artifact_specs:
            self.storage.add_artifact(mission_id, **artifact)

        status = self.storage.refresh_mission_status(mission_id)
        plan["status"] = status
        self.storage.update_mission_result(mission_id, status=status, result=plan)
        self.storage.add_memory(
            request.domain,
            "mission",
            f"Mission {mission_id} created child workspace '{child['name']}' for goal '{request.goal[:80]}'.",
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
        child: dict[str, str],
        orchestration: dict[str, Any],
    ) -> dict[str, Any]:
        success_definition = (
            "Create a governed child workspace, keep scope narrow, produce reusable artifacts, and avoid "
            "granting more permissions than the goal requires."
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
                "title": "Create governed child workspace",
                "status": "complete",
                "summary": f"Workspace created at {child['path']}.",
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
            "name": child["name"],
            "slug": child["slug"],
            "path": child["path"],
            "goal_path": child["goal_path"],
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
            "next_actions": [
                "Review the mission brief.",
                "Approve or hold requested connectors.",
                "Open the child workspace and begin execution after approvals clear.",
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

        return [
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

    def _mission_brief_markdown(self, mission_id: int, mission_name: str, plan: dict[str, Any]) -> str:
        brief = plan["brief"]
        child = plan["child"]
        return f"""# Mission Brief

## Mission

- ID: {mission_id}
- Name: {mission_name}
- Domain: {brief['domain_label']}
- Owner: {brief['owner']}
- Child Workspace: {child['path']}

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
            "Review these items before activating the child workspace.",
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
