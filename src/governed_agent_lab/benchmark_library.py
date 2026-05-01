from __future__ import annotations

from copy import deepcopy
from typing import Any


PREREQUISITE_REASONING_CASES = [
    {
        "id": "wash-car-drive",
        "goal": "Wash a car at a car wash 50 meters away.",
        "naive_answer": "Walk because it is close.",
        "correct_answer": "Drive the car there because the car must be at the car wash to wash it.",
        "failure_mode": "Optimizes for human travel distance instead of the actual object that must reach the destination.",
        "required_signal_groups": [
            ["drive", "driving"],
            ["car"],
            ["wash", "car wash"],
        ],
        "forbidden_signals": ["walk there", "walk because it is close"],
    },
    {
        "id": "build-needs-compiler",
        "goal": "Compile a Rust project quickly on a fresh machine.",
        "naive_answer": "Run the build command immediately to save time.",
        "correct_answer": "First verify the Rust toolchain is installed, then build.",
        "failure_mode": "Optimizes for immediate action while skipping the prerequisite that makes the action possible.",
        "required_signal_groups": [
            ["verify", "check", "confirm"],
            ["rust toolchain", "rustup", "cargo", "compiler"],
            ["build", "compile"],
        ],
        "forbidden_signals": ["build immediately", "run the build command immediately"],
    },
    {
        "id": "database-query-needs-migration",
        "goal": "Test a new query against the latest schema.",
        "naive_answer": "Run the query first because it is the direct task.",
        "correct_answer": "Apply or verify the needed migrations first, then run the query.",
        "failure_mode": "Targets the visible task while ignoring schema state required for correctness.",
        "required_signal_groups": [
            ["migration", "migrations", "schema"],
            ["verify", "apply", "confirm"],
            ["query"],
        ],
        "forbidden_signals": ["run the query first", "query first"],
    },
    {
        "id": "deploy-needs-rollback-plan",
        "goal": "Ship a risky production-adjacent change safely.",
        "naive_answer": "Deploy immediately because that finishes fastest.",
        "correct_answer": "Prepare rollback and validation steps before deployment.",
        "failure_mode": "Treats speed as success even when the goal includes safe completion criteria.",
        "required_signal_groups": [
            ["rollback"],
            ["validation", "validate", "verification", "verify"],
            ["deploy", "deployment"],
        ],
        "forbidden_signals": ["deploy immediately", "ship immediately"],
    },
    {
        "id": "refactor-needs-regression-check",
        "goal": "Reduce duplication in a hot code path without behavior drift.",
        "naive_answer": "Rewrite the shared logic right away to be efficient.",
        "correct_answer": "Capture the current behavior with focused checks, then refactor.",
        "failure_mode": "Optimizes implementation neatness before preserving the behavior that the goal actually cares about.",
        "required_signal_groups": [
            ["capture", "preserve", "protect"],
            ["behavior", "regression", "checks", "tests"],
            ["refactor"],
        ],
        "forbidden_signals": ["rewrite right away", "refactor immediately"],
    },
]


LOGIC_PATTERN_CASES = [
    {
        "id": "domain-reinterpretation-monopoly",
        "goal": "Someone says they lost a fortune after moving a car to a hotel. Infer the most likely context.",
        "naive_answer": "They had a real financial collapse at a hotel.",
        "correct_answer": "They were probably playing a board game such as Monopoly, so the words should be read in that domain.",
        "failure_mode": "Commits to the everyday meaning of words instead of checking whether the problem lives in a different frame.",
        "required_signal_groups": [
            ["board game", "game", "monopoly"],
            ["context", "domain", "frame"],
        ],
        "forbidden_signals": ["real hotel bankruptcy", "financial collapse at a hotel"],
        "transfer_rule": "Check whether overloaded terms belong to a different domain before drawing real-world conclusions.",
    },
    {
        "id": "hidden-state-transition-ice",
        "goal": "Explain water on the floor in a locked-room style problem without assuming the present state was the only state.",
        "naive_answer": "The water must have been spilled directly.",
        "correct_answer": "Consider a prior state such as ice that later melted into water.",
        "failure_mode": "Reasons only from the visible end state and ignores plausible state transitions.",
        "required_signal_groups": [
            ["ice", "frozen"],
            ["melt", "melted"],
            ["prior state", "earlier state", "before"],
        ],
        "forbidden_signals": ["spilled directly", "just spilled water"],
        "transfer_rule": "When the current evidence is odd, ask what earlier state could have transformed into it.",
    },
    {
        "id": "calendar-edge-case-leap-day",
        "goal": "Explain how a person could have a rare birthday cadence without assuming the calendar is uniform.",
        "naive_answer": "The age claim must be impossible.",
        "correct_answer": "Check leap-day or calendar edge cases before concluding the statement is contradictory.",
        "failure_mode": "Rejects an unusual claim without testing well-known boundary conditions.",
        "required_signal_groups": [
            ["leap day", "february 29", "calendar edge case", "leap year"],
            ["birthday", "age"],
        ],
        "forbidden_signals": ["impossible", "cannot happen"],
        "transfer_rule": "Test boundary conditions before dismissing an edge-case statement as false.",
    },
    {
        "id": "spatial-constraint-north-pole",
        "goal": "Infer an animal's color from a house with all sides facing south.",
        "naive_answer": "The color cannot be known.",
        "correct_answer": "The setup implies the North Pole, so the bear would be white.",
        "failure_mode": "Misses the geometric constraint that narrows the world to a single location.",
        "required_signal_groups": [
            ["north pole", "polar"],
            ["white"],
            ["all sides facing south", "geometric constraint", "spatial constraint"],
        ],
        "forbidden_signals": ["cannot be known", "impossible to tell"],
        "transfer_rule": "Use strong spatial constraints to reduce the search space before answering.",
    },
    {
        "id": "representation-shift-photo",
        "goal": "Interpret a violent-looking description without assuming every verb is literal.",
        "naive_answer": "The description proves physical harm happened.",
        "correct_answer": "Consider representational meanings, such as shooting a photo and developing it.",
        "failure_mode": "Takes every action word literally and misses harmless alternate meanings.",
        "required_signal_groups": [
            ["photo", "photograph", "camera"],
            ["develop", "developed"],
            ["literal", "alternate meaning", "representational"],
        ],
        "forbidden_signals": ["physical harm happened", "definitely killed"],
        "transfer_rule": "Check whether the wording supports a representational or non-literal interpretation before escalating.",
    },
]


def build_prerequisite_reasoning_family() -> dict[str, Any]:
    cases = deepcopy(PREREQUISITE_REASONING_CASES)
    return {
        "family_key": "goal-and-precondition-reasoning",
        "title": "Goal And Precondition Reasoning",
        "description": (
            "Tasks that check whether the agent reasons from the real objective and its prerequisites "
            "instead of optimizing a shallow proxy such as proximity, speed, or local simplicity."
        ),
        "cases": cases,
        "evaluation_rules": [
            "The chosen action must be capable of accomplishing the actual goal.",
            "Required objects, tools, schema state, or rollout safeguards must be accounted for first.",
            "A faster action is not better if it cannot satisfy the prerequisite chain.",
        ],
    }


def build_logic_pattern_family() -> dict[str, Any]:
    cases = deepcopy(LOGIC_PATTERN_CASES)
    return {
        "family_key": "logic-pattern-seeds",
        "title": "Logic Pattern Seeds",
        "description": (
            "Supplemental reasoning seeds inspired by classic logic-riddle motifs. "
            "These cases are meant to sharpen frame detection, state-transition reasoning, "
            "boundary-condition checks, and non-literal interpretation without overriding the coding benchmark."
        ),
        "advisory_only": True,
        "weight_cap": 0.05,
        "cases": cases,
        "evaluation_rules": [
            "Use these as supplemental reasoning drills, not as a replacement for coding-task evidence.",
            "Do not let puzzle-style cleverness override correctness, tests, or governance on real coding work.",
            "Transfer the underlying reasoning pattern only when the task context genuinely matches it.",
        ],
    }


def build_benchmark_families() -> dict[str, dict[str, Any]]:
    families = [
        build_prerequisite_reasoning_family(),
        build_logic_pattern_family(),
    ]
    return {family["family_key"]: family for family in families}
