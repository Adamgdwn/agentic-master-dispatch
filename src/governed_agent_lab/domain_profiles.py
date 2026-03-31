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
}
