from __future__ import annotations

DOMAIN_PROFILES = {
    "trading-strategy": {
        "label": "Trading Strategy",
        "objective": "Research and evaluate trading strategies in sandboxed environments.",
        "research_focus": [
            "market structure",
            "strategy families",
            "risk controls",
            "backtesting assumptions",
            "failure modes",
        ],
        "success_metrics": [
            "clear hypothesis",
            "reproducible experiment design",
            "risk-aware evaluation",
            "human-readable recommendation",
        ],
        "blocked_actions": [
            "place live trade",
            "connect to broker",
            "move money",
            "use production credentials",
        ],
    },
    "research-and-development": {
        "label": "Research And Development",
        "objective": "Investigate a goal, synthesize evidence, prototype safely, and recommend next steps.",
        "research_focus": [
            "goal decomposition",
            "state of the art",
            "constraints",
            "prototype options",
            "evaluation design",
        ],
        "success_metrics": [
            "first-principles reasoning",
            "evidence-backed options",
            "safe prototype plan",
            "clear recommendation",
        ],
        "blocked_actions": [
            "unsafe external writes",
            "credential misuse",
            "production deployment without review",
        ],
    },
    "coding-optimization": {
        "label": "Coding Optimization",
        "objective": "Improve AI coding behavior through governed sandbox evaluation, feedback capture, and reusable instructions.",
        "research_focus": [
            "failure reproduction",
            "goal and precondition reasoning",
            "regression prevention",
            "durable implementation patterns",
            "efficiency improvements",
            "operator guidance for coding agents",
        ],
        "success_metrics": [
            "fewer repeated errors",
            "correct reasoning about goals and prerequisites",
            "durable code changes",
            "evidence-backed efficiency gains",
            "clear reusable instructions for coding agents",
        ],
        "blocked_actions": [
            "autonomy increase without review",
            "unreviewed prompt or model promotion",
            "unsafe external writes",
            "production deployment without review",
        ],
    },
}
