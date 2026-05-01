from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .benchmark_library import build_benchmark_families


def _normalize_text(value: str) -> str:
    lowered = value.lower()
    normalized = re.sub(r"[^a-z0-9\s]+", " ", lowered)
    return re.sub(r"\s+", " ", normalized).strip()


def _contains_signal(text: str, signal: str) -> bool:
    pattern = r"\b" + re.escape(signal.lower()) + r"\b"
    return re.search(pattern, text) is not None


@dataclass
class BenchmarkEvaluationRequest:
    family_key: str
    case_id: str
    answer: str


class BenchmarkRunner:
    def __init__(self) -> None:
        self.families = build_benchmark_families()

    def list_families(self) -> list[dict[str, Any]]:
        return [deepcopy(family) for family in self.families.values()]

    def get_family(self, family_key: str) -> dict[str, Any]:
        family = self.families.get(family_key)
        if family is None:
            raise ValueError(f"Unknown benchmark family: {family_key}")
        return deepcopy(family)

    def evaluate(self, request: BenchmarkEvaluationRequest) -> dict[str, Any]:
        family = self.get_family(request.family_key)
        case = self._get_case(family, request.case_id)
        normalized_answer = _normalize_text(request.answer)

        matched_groups = []
        missing_groups = []
        for signals in case["required_signal_groups"]:
            hit = next((signal for signal in signals if _contains_signal(normalized_answer, signal)), None)
            if hit is None:
                missing_groups.append(signals)
            else:
                matched_groups.append(hit)

        forbidden_hits = [
            signal for signal in case.get("forbidden_signals", [])
            if _contains_signal(normalized_answer, signal)
        ]

        score = 100.0
        if missing_groups:
            score -= min(60.0, 20.0 * len(missing_groups))
        if forbidden_hits:
            score -= min(30.0, 15.0 * len(forbidden_hits))
        if len(normalized_answer.split()) < 4:
            score -= 10.0
        score = max(0.0, round(score, 1))

        passed = not missing_groups and not forbidden_hits and score >= 85.0
        findings = []
        if matched_groups:
            findings.append(
                "Matched prerequisite signals: " + ", ".join(matched_groups) + "."
            )
        if missing_groups:
            findings.append(
                "Missing required reasoning signals: "
                + "; ".join("/".join(group) for group in missing_groups)
                + "."
            )
        if forbidden_hits:
            findings.append(
                "Included forbidden shortcut reasoning: " + ", ".join(forbidden_hits) + "."
            )
        if not findings:
            findings.append("No strong reasoning signals were detected.")

        return {
            "family_key": request.family_key,
            "case_id": request.case_id,
            "goal": case["goal"],
            "answer": request.answer,
            "score": score,
            "passed": passed,
            "expected_answer": case["correct_answer"],
            "failure_mode": case["failure_mode"],
            "findings": findings,
        }

    def _get_case(self, family: dict[str, Any], case_id: str) -> dict[str, Any]:
        for case in family["cases"]:
            if case["id"] == case_id:
                return case
        raise ValueError(f"Unknown benchmark case: {case_id}")
