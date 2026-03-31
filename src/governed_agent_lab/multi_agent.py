from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ROLE_ORDER = [
    "planner",
    "research",
    "data",
    "strategy",
    "backtest",
    "risk",
    "review",
    "reporting",
    "paper_trade",
    "deployment",
]


@dataclass
class MultiAgentRequest:
    goal: str
    domain_label: str
    constraints: str
    blocked_actions: list[str]


class MultiAgentSystem:
    def run(self, request: MultiAgentRequest) -> dict[str, Any]:
        planner = self._planner(request)
        research = self._research(request)
        data = self._data(request)
        strategy = self._strategy(request)
        backtest = self._backtest(request)
        risk = self._risk(request)
        review = self._review(request)
        reporting = self._reporting(request)
        paper_trade = self._paper_trade(request)
        deployment = self._deployment(request)
        handoffs = self._handoffs()
        gates = self._gates(risk, review, paper_trade, deployment)

        return {
            "goal": request.goal,
            "domain_label": request.domain_label,
            "roles": [planner, research, data, strategy, backtest, risk, review, reporting, paper_trade, deployment],
            "handoffs": handoffs,
            "gates": gates,
            "separation_rules": [
                "The strategy-producing roles do not deploy.",
                "The deployment role cannot change strategy logic.",
                "Review and risk roles challenge rather than approve by default.",
                "Paper trading is required before any future live promotion.",
            ],
        }

    def _planner(self, request: MultiAgentRequest) -> dict[str, Any]:
        return {
            "role": "planner",
            "purpose": "Decompose the goal and assign work to specialist roles.",
            "workspace_focus": "Translate the user goal into a narrow governed execution brief.",
            "outputs": [
                "research questions",
                "data requirements",
                "strategy-search criteria",
                "review gates",
            ],
            "artifact": "mission-brief",
            "status": "complete",
        }

    def _research(self, request: MultiAgentRequest) -> dict[str, Any]:
        return {
            "role": "research",
            "purpose": "Gather prior art, regime context, and candidate hypotheses.",
            "workspace_focus": f"Investigate the goal '{request.goal[:72]}' using approved read-only inputs.",
            "outputs": [
                "market structure brief",
                "strategy families",
                "evidence and caveats",
            ],
            "artifact": "research-brief",
            "status": "ready",
        }

    def _data(self, request: MultiAgentRequest) -> dict[str, Any]:
        return {
            "role": "data",
            "purpose": "Prepare large historical datasets, features, and validation slices.",
            "workspace_focus": "Shape governed datasets and validation windows for the child workspace.",
            "outputs": [
                "cleaned datasets",
                "feature candidates",
                "train and validation splits",
            ],
            "artifact": "data-spec",
            "status": "ready",
        }

    def _strategy(self, request: MultiAgentRequest) -> dict[str, Any]:
        return {
            "role": "strategy",
            "purpose": "Generate parameterized strategy candidates with money management assumptions.",
            "workspace_focus": "Keep candidate logic simple, reproducible, and comparable.",
            "outputs": [
                "entry and exit rules",
                "position sizing rules",
                "fee and slippage assumptions",
            ],
            "artifact": "strategy-spec",
            "status": "ready",
        }

    def _backtest(self, request: MultiAgentRequest) -> dict[str, Any]:
        return {
            "role": "backtest",
            "purpose": "Run iterative simulations across many parameter combinations.",
            "workspace_focus": "Execute bounded experiments and preserve reproducible run artifacts.",
            "outputs": [
                "performance metrics",
                "drawdown and equity curves",
                "ranked candidate runs",
            ],
            "artifact": "backtest-report",
            "status": "ready",
        }

    def _risk(self, request: MultiAgentRequest) -> dict[str, Any]:
        return {
            "role": "risk",
            "purpose": "Attempt to break candidate strategies by stress, drawdown, and exposure analysis.",
            "workspace_focus": "Search for hidden downside before any promotion step.",
            "outputs": [
                "risk findings",
                "reasons to reject",
                "required safeguards",
            ],
            "artifact": "risk-review",
            "status": "gatekeeper",
        }

    def _review(self, request: MultiAgentRequest) -> dict[str, Any]:
        return {
            "role": "review",
            "purpose": "Challenge assumptions, look for leakage, overfitting, and bad methodology.",
            "workspace_focus": "Force a second pass on method quality and leakage risk.",
            "outputs": [
                "review notes",
                "bias and leakage checks",
                "recommended retests",
            ],
            "artifact": "review-notes",
            "status": "gatekeeper",
        }

    def _reporting(self, request: MultiAgentRequest) -> dict[str, Any]:
        return {
            "role": "reporting",
            "purpose": "Turn winning candidates into charts, rankings, and decision-ready summaries.",
            "workspace_focus": "Package artifacts so the parent can summarize the mission clearly.",
            "outputs": [
                "trend charts",
                "equity curves",
                "ranked strategy recommendations",
            ],
            "artifact": "mission-summary",
            "status": "ready",
        }

    def _paper_trade(self, request: MultiAgentRequest) -> dict[str, Any]:
        return {
            "role": "paper_trade",
            "purpose": "Monitor approved candidates in simulated execution before any real deployment.",
            "workspace_focus": "Remain isolated until governance explicitly permits paper execution.",
            "outputs": [
                "paper trade logs",
                "live-like drift checks",
                "kill switch criteria",
            ],
            "artifact": "paper-trade-log",
            "status": "isolated",
        }

    def _deployment(self, request: MultiAgentRequest) -> dict[str, Any]:
        return {
            "role": "deployment",
            "purpose": "Separate future runtime for paper trading and, later, approved live execution.",
            "workspace_focus": "Stay dormant under current sandbox-only governance.",
            "outputs": [
                "deployment manifests",
                "monitoring hooks",
                "rollback controls",
            ],
            "artifact": "deployment-pack",
            "status": "isolated",
            "blocked_actions": request.blocked_actions,
        }

    def _handoffs(self) -> list[dict[str, Any]]:
        return [
            {"from": "planner", "to": "research", "artifact": "research-brief"},
            {"from": "planner", "to": "data", "artifact": "data-spec"},
            {"from": "research", "to": "strategy", "artifact": "hypothesis-set"},
            {"from": "data", "to": "backtest", "artifact": "clean-dataset-bundle"},
            {"from": "strategy", "to": "backtest", "artifact": "strategy-specs"},
            {"from": "backtest", "to": "risk", "artifact": "ranked-backtest-results"},
            {"from": "backtest", "to": "review", "artifact": "methodology-bundle"},
            {"from": "risk", "to": "reporting", "artifact": "risk-findings"},
            {"from": "review", "to": "reporting", "artifact": "review-findings"},
            {"from": "reporting", "to": "paper_trade", "artifact": "approved-paper-trade-candidate"},
            {"from": "paper_trade", "to": "deployment", "artifact": "paper-trade-promotion-package"},
        ]

    def _gates(self, risk: dict[str, Any], review: dict[str, Any], paper_trade: dict[str, Any], deployment: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {
                "gate": "research-to-backtest",
                "requires": ["clear hypothesis", "clean dataset", "fee assumptions"],
                "human_approval_required": False,
            },
            {
                "gate": "backtest-to-review",
                "requires": ["performance metrics", "drawdown metrics", "reproducible config"],
                "human_approval_required": False,
            },
            {
                "gate": "review-to-paper-trade",
                "requires": [risk["role"], review["role"], "human signoff"],
                "human_approval_required": True,
            },
            {
                "gate": "paper-trade-to-deployment",
                "requires": [paper_trade["role"], deployment["role"], "governance reclassification before live use"],
                "human_approval_required": True,
            },
        ]
