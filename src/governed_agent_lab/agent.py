from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .coding_loop import CodingOptimizationLoop, CodingOptimizationRequest
from .domain_profiles import DOMAIN_PROFILES
from .lab_host import build_codex_runner_contract, collect_lab_host_profile
from .multi_agent import MultiAgentRequest, MultiAgentSystem
from .reporting import sample_strategy_report
from .storage import Storage


PIPELINE_STAGES = [
    "goal",
    "research",
    "train",
    "ethical_outcomes",
    "sandbox_execution",
    "report",
]


@dataclass
class AgentRequest:
    goal: str
    domain: str
    constraints: str


class GovernedAgent:
    def __init__(self, storage: Storage) -> None:
        self.storage = storage
        self.multi_agent = MultiAgentSystem()
        self.coding_loop = CodingOptimizationLoop(storage)

    def run(self, request: AgentRequest) -> dict[str, Any]:
        profile = DOMAIN_PROFILES[request.domain]
        memory = self.storage.list_memories(request.domain, limit=6)
        coding_lab = None
        if request.domain == "coding-optimization":
            coding_lab = self.coding_loop.run(
                CodingOptimizationRequest(goal=request.goal, constraints=request.constraints)
            )
        first_principles = self._first_principles(request.goal, request.constraints, profile)
        research = self._research_brief(profile, memory)
        training = self._learning_plan(profile, memory)
        ethics = self._ethical_review(profile, request.goal)
        sandbox = self._sandbox_execution(profile, request.goal)
        analytics = self._analytics(request.domain, profile, request.goal)
        orchestration = self.multi_agent.run(
            MultiAgentRequest(
                goal=request.goal,
                domain_label=profile["label"],
                constraints=request.constraints,
                blocked_actions=profile["blocked_actions"],
            )
        )
        report = self._report(
            profile,
            request.goal,
            first_principles,
            research,
            training,
            ethics,
            sandbox,
            analytics,
            orchestration,
            coding_lab=coding_lab,
        )
        summary = report["recommendation"]

        task = {
            "pipeline": PIPELINE_STAGES,
            "goal": request.goal,
            "domain": request.domain,
            "constraints": request.constraints,
            "profile": profile,
            "memory_context": memory,
            "first_principles": first_principles,
            "research": research,
            "training": training,
            "ethical_outcomes": ethics,
            "sandbox_execution": sandbox,
            "analytics": analytics,
            "orchestration": orchestration,
            "report": report,
            "coding_lab": coding_lab,
        }
        task_id = self.storage.create_task(
            goal=request.goal,
            domain=request.domain,
            status="completed",
            summary=summary,
            result=task,
        )
        self.storage.add_memory(
            request.domain,
            "lesson",
            f"Task {task_id}: Prefer evidence-backed decomposition for goal '{request.goal[:80]}'.",
            weight=1.2,
        )
        task["id"] = task_id
        return task

    def reinforce(self, task_id: int, rating: int, notes: str) -> None:
        task = self.storage.get_task(task_id)
        if not task:
            return
        weight = 1.5 if rating >= 4 else 0.8
        memory_line = (
            f"Feedback on task {task_id} ({task['domain']}): rating={rating}. "
            f"Keep: {task['summary']}. Notes: {notes or 'No notes provided.'}"
        )
        self.storage.add_feedback(task_id, rating, notes)
        self.storage.add_memory(task["domain"], "feedback", memory_line, weight=weight)

    def _first_principles(self, goal: str, constraints: str, profile: dict[str, Any]) -> dict[str, Any]:
        return {
            "objective": goal,
            "assumptions_to_test": [
                "What outcome matters most?",
                "What can be measured directly?",
                "Which variables are controllable?",
                "What failure modes would invalidate the approach?",
            ],
            "constraints": constraints or "Stay within governance, sandbox-only execution, and reproducibility.",
            "non_goals": profile["blocked_actions"],
        }

    def _research_brief(self, profile: dict[str, Any], memory: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "focus_areas": profile["research_focus"],
            "memory_signals": [item["content"] for item in memory[:3]],
            "sources_strategy": [
                "Use primary sources and direct documentation where possible.",
                "Track assumptions separately from evidence.",
                "Prefer simple hypotheses before complex optimization.",
            ],
        }

    def _learning_plan(self, profile: dict[str, Any], memory: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "loop": [
                "collect evidence",
                "run bounded experiment",
                "measure outcome",
                "capture lesson in memory",
                "adjust next experiment",
            ],
            "persistent_memory": "SQLite-backed lessons and feedback retained across sessions.",
            "bias_controls": [
                "Require explicit evidence statements.",
                "Separate facts, assumptions, and recommendations.",
                "Run ethical review before action recommendations.",
            ],
            "success_metrics": profile["success_metrics"],
        }

    def _ethical_review(self, profile: dict[str, Any], goal: str) -> dict[str, Any]:
        return {
            "checks": [
                "Does the plan stay within sandbox and governance boundaries?",
                "Could the recommendation create financial harm if misunderstood?",
                "Are uncertainty and tradeoffs explained clearly?",
                "Does the workflow avoid protected-class or political targeting?",
            ],
            "decision": "approved-for-sandbox-only",
            "rationale": (
                f"The current plan for '{goal}' is limited to research, evaluation, and "
                "sandbox experimentation. Any external execution remains blocked."
            ),
            "blocked_actions": profile["blocked_actions"],
        }

    def _sandbox_execution(self, profile: dict[str, Any], goal: str) -> dict[str, Any]:
        return {
            "status": "planned",
            "environment": "sandbox",
            "steps": [
                "Create a hypothesis and measurable evaluation criteria.",
                "Implement or refine a prototype strategy.",
                "Run a bounded backtest or simulation.",
                "Record metrics, drawdowns, and failure cases.",
                "Produce a recommendation with confidence and caveats.",
            ],
            "guardrails": [
                "No broker or exchange connectivity.",
                "No real credentials.",
                "No unsandboxed external writes.",
            ],
            "goal": goal,
        }

    def _analytics(self, domain: str, profile: dict[str, Any], goal: str) -> dict[str, Any]:
        if domain == "coding-optimization":
            host_profile = collect_lab_host_profile()
            return {
                "goal_context": goal,
                "domain": profile["label"],
                "reporting_focus": [
                    "goal and precondition reasoning",
                    "regression prevention",
                    "durable implementation choices",
                    "efficiency without behavior drift",
                    "operator-ready instruction packs",
                ],
                "scorecard": [
                    "error elimination",
                    "logical correctness",
                    "efficiency",
                    "durability",
                    "instruction clarity",
                    "governance",
                ],
                "lab_host_status": host_profile["readiness"]["status"],
                "runner_contract_preview": build_codex_runner_contract(host_profile)["preferred_commands"],
            }
        analytics = sample_strategy_report()
        analytics["reporting_focus"] = [
            "trend snapshots",
            "drawdown-aware equity curves",
            "fee-aware backtest summaries",
            "chart-ready series for large datasets",
        ]
        analytics["goal_context"] = goal
        analytics["domain"] = profile["label"]
        return analytics

    def _report(
        self,
        profile: dict[str, Any],
        goal: str,
        first_principles: dict[str, Any],
        research: dict[str, Any],
        training: dict[str, Any],
        ethics: dict[str, Any],
        sandbox: dict[str, Any],
        analytics: dict[str, Any],
        orchestration: dict[str, Any],
        coding_lab: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        recommendation = (
            f"Start with a simple, testable path for '{goal}', validate it against clear "
            "metrics, then iterate through the governed learning loop before promoting any result."
        )
        next_actions = [
            "Clarify the measurable success metric.",
            "Gather evidence against the focus areas.",
            "Build the smallest useful experiment.",
            "Review ethical and governance constraints before any broader use.",
        ]
        explainability: dict[str, Any] = {
            "first_principles": first_principles,
            "research_focus": research["focus_areas"],
            "learning_loop": training["loop"],
            "ethics_decision": ethics["decision"],
            "sandbox_status": sandbox["status"],
            "gates": orchestration["gates"],
        }
        if coding_lab is not None:
            candidate = coding_lab["result"]["recommended_candidate"]
            recommendation = (
                f"Use the sandbox candidate '{candidate['title']}' as the current coding instruction pack, "
                "run real repo benchmarks next, and keep autonomy at A2 until governance approves promotion."
            )
            next_actions = coding_lab["result"]["adoption_path"][:4]
            explainability["recommended_instruction_pack"] = candidate
            explainability["promotion_blockers"] = coding_lab["result"]["promotion_blockers"]
        return {
            "recommendation": recommendation,
            "next_actions": next_actions,
            "explainability": explainability,
            "project_type": profile["label"],
            "reporting": analytics,
        }
