from pathlib import Path
import tempfile
import unittest

from governed_agent_lab.benchmark_runner import BenchmarkEvaluationRequest, BenchmarkRunner
from governed_agent_lab.storage import Storage


class BenchmarkRunnerTests(unittest.TestCase):
    def test_prerequisite_reasoning_runner_passes_correct_answer(self) -> None:
        runner = BenchmarkRunner()
        result = runner.evaluate(
            BenchmarkEvaluationRequest(
                family_key="goal-and-precondition-reasoning",
                case_id="wash-car-drive",
                answer="Drive the car there because the car has to be at the car wash to wash it.",
            )
        )
        self.assertTrue(result["passed"])
        self.assertGreaterEqual(result["score"], 85.0)

    def test_prerequisite_reasoning_runner_fails_naive_answer(self) -> None:
        runner = BenchmarkRunner()
        result = runner.evaluate(
            BenchmarkEvaluationRequest(
                family_key="goal-and-precondition-reasoning",
                case_id="wash-car-drive",
                answer="Walk there because it is close.",
            )
        )
        self.assertFalse(result["passed"])
        self.assertLess(result["score"], 85.0)
        self.assertTrue(any("Missing required reasoning signals" in item for item in result["findings"]))

    def test_benchmark_evaluation_storage_round_trip(self) -> None:
        runner = BenchmarkRunner()
        result = runner.evaluate(
            BenchmarkEvaluationRequest(
                family_key="goal-and-precondition-reasoning",
                case_id="build-needs-compiler",
                answer="First verify the Rust toolchain is installed, then run the build.",
            )
        )
        with tempfile.TemporaryDirectory() as tmp:
            storage = Storage(Path(tmp) / "agent.db")
            evaluation_id = storage.add_benchmark_evaluation(
                family_key=result["family_key"],
                case_id=result["case_id"],
                score=result["score"],
                passed=result["passed"],
                answer=result["answer"],
                result=result,
            )
            evaluations = storage.list_benchmark_evaluations(
                family_key="goal-and-precondition-reasoning",
            )
            self.assertEqual(evaluation_id, evaluations[0]["id"])
            self.assertTrue(evaluations[0]["passed"])
            self.assertEqual(evaluations[0]["result"]["case_id"], "build-needs-compiler")

    def test_logic_pattern_family_is_available_and_passes_contextual_answer(self) -> None:
        runner = BenchmarkRunner()
        family = runner.get_family("logic-pattern-seeds")
        self.assertTrue(family["advisory_only"])
        result = runner.evaluate(
            BenchmarkEvaluationRequest(
                family_key="logic-pattern-seeds",
                case_id="domain-reinterpretation-monopoly",
                answer="This sounds like Monopoly or another board game, so the words should be read in that game context.",
            )
        )
        self.assertTrue(result["passed"])

    def test_family_reads_are_defensive_copies(self) -> None:
        runner = BenchmarkRunner()

        family = runner.get_family("goal-and-precondition-reasoning")
        family["cases"].append({"id": "mutated"})

        family_again = runner.get_family("goal-and-precondition-reasoning")
        self.assertFalse(any(case["id"] == "mutated" for case in family_again["cases"]))


if __name__ == "__main__":
    unittest.main()
