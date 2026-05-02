from pathlib import Path
import tempfile
import unittest

from governed_agent_lab.coding_loop import CodingOptimizationLoop, CodingOptimizationRequest
from governed_agent_lab.child_projects import ChildProjectBootstrapper
from governed_agent_lab.mission_control import MissionControl, MissionRequest
from governed_agent_lab.storage import Storage


class CodingLoopTests(unittest.TestCase):
    def test_coding_loop_creates_learning_run_with_instruction_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            storage = Storage(Path(tmp) / "agent.db")
            loop = CodingOptimizationLoop(
                storage,
                host_profiler=lambda: {
                    "hostname": "chuwi-lab",
                    "runtime": {"cpu_count": 4, "memory_gb": 8.0},
                    "readiness": {
                        "status": "ready-for-local-codex-sandbox",
                        "summary": "Ready for local Codex sandbox work.",
                    },
                    "tools": {
                        "python": {"path": "/usr/bin/python3", "available": True},
                        "git": {"path": "/usr/bin/git", "available": True},
                        "uv": {"path": None, "available": False},
                    },
                },
            )

            learning_run = loop.run(
                CodingOptimizationRequest(
                    goal="Improve AI coder durability and reduce regression risk",
                    constraints="Keep all optimization inside sandbox-only governance.",
                )
            )

            self.assertEqual(learning_run["status"], "ready-for-sandbox")
            self.assertEqual(learning_run["result"]["evaluation_mode"], "static-readiness")
            self.assertGreaterEqual(len(learning_run["attempts"]), 4)
            self.assertTrue(learning_run["result"]["recommended_candidate"]["instruction_pack"])
            self.assertIn("A2", learning_run["summary"])
            self.assertEqual(
                learning_run["result"]["objective_profile"]["mode"],
                "capability-optimization",
            )
            self.assertIn("benchmark_history", learning_run["result"])
            benchmark_cases = learning_run["result"]["benchmark"]["cases"]
            self.assertTrue(any(case["id"] == "goal-and-precondition-reasoning" for case in benchmark_cases))
            benchmark_families = learning_run["result"]["benchmark"]["families"]
            self.assertTrue(
                any(family["family_key"] == "goal-and-precondition-reasoning" for family in benchmark_families)
            )
            self.assertTrue(
                any(family["family_key"] == "logic-pattern-seeds" for family in benchmark_families)
            )
            self.assertEqual(
                learning_run["result"]["lab_host_profile"]["readiness"]["status"],
                "ready-for-local-codex-sandbox",
            )
            self.assertEqual(
                learning_run["result"]["codex_runner_contract"]["runner"],
                "codex",
            )
            self.assertEqual(
                learning_run["result"]["sandbox_benchmark_suite"]["suite_key"],
                "lab-host-coding-sandbox",
            )
            prerequisite_family = next(
                family for family in benchmark_families if family["family_key"] == "goal-and-precondition-reasoning"
            )
            self.assertGreaterEqual(len(prerequisite_family["cases"]), 5)
            self.assertTrue(
                any(case["id"] == "wash-car-drive" for case in prerequisite_family["cases"])
            )
            logic_family = next(
                family for family in benchmark_families if family["family_key"] == "logic-pattern-seeds"
            )
            self.assertTrue(logic_family["advisory_only"])
            self.assertIn(
                "logical_correctness",
                learning_run["result"]["recommended_candidate"]["score"],
            )
            self.assertIn(
                "logical_correctness_min",
                learning_run["result"]["benchmark"]["score_gates"],
            )
            self.assertTrue(learning_run["result"]["supplemental_reasoning_seeds"])
            self.assertIn(
                "selection_score",
                learning_run["result"]["recommended_candidate"]["score"],
            )

    def test_tradeoff_goal_builds_neutral_objective_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            storage = Storage(Path(tmp) / "agent.db")
            loop = CodingOptimizationLoop(
                storage,
                host_profiler=lambda: {
                    "hostname": "chuwi-lab",
                    "runtime": {"cpu_count": 4, "memory_gb": 8.0},
                    "readiness": {
                        "status": "ready-for-local-codex-sandbox",
                        "summary": "Ready for local Codex sandbox work.",
                    },
                    "tools": {
                        "python": {"path": "/usr/bin/python3", "available": True},
                        "git": {"path": "/usr/bin/git", "available": True},
                        "uv": {"path": None, "available": False},
                    },
                },
            )

            learning_run = loop.run(
                CodingOptimizationRequest(
                    goal="Better independent coding capabilities with less compute",
                    constraints="Stay inside sandbox-only governance.",
                )
            )

            objective = learning_run["result"]["objective_profile"]
            self.assertEqual(objective["mode"], "tradeoff-optimization")
            self.assertEqual(objective["gain_target"]["phrase"], "better independent coding capabilities")
            self.assertEqual(objective["cost_target"]["phrase"], "compute")
            self.assertIn("logical_correctness", objective["gain_target"]["derived_metrics"])
            self.assertIn("efficiency", objective["cost_target"]["derived_metrics"])
            self.assertEqual(
                learning_run["result"]["recommended_candidate"]["score"]["selection_score"],
                max(item["score"]["selection_score"] for item in learning_run["attempts"]),
            )

    def test_benchmark_history_penalizes_shortcut_heavy_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            storage = Storage(Path(tmp) / "agent.db")
            storage.add_benchmark_evaluation(
                family_key="goal-and-precondition-reasoning",
                case_id="wash-car-drive",
                score=20.0,
                passed=False,
                answer="Walk there because it is close.",
                result={"case_id": "wash-car-drive", "passed": False},
            )
            storage.add_benchmark_evaluation(
                family_key="logic-pattern-seeds",
                case_id="domain-reinterpretation-monopoly",
                score=30.0,
                passed=False,
                answer="It must be real bankruptcy.",
                result={"case_id": "domain-reinterpretation-monopoly", "passed": False},
            )
            loop = CodingOptimizationLoop(
                storage,
                host_profiler=lambda: {
                    "hostname": "chuwi-lab",
                    "runtime": {"cpu_count": 4, "memory_gb": 8.0},
                    "readiness": {
                        "status": "ready-for-local-codex-sandbox",
                        "summary": "Ready for local Codex sandbox work.",
                    },
                    "tools": {
                        "python": {"path": "/usr/bin/python3", "available": True},
                        "git": {"path": "/usr/bin/git", "available": True},
                        "uv": {"path": None, "available": False},
                    },
                },
            )

            learning_run = loop.run(
                CodingOptimizationRequest(
                    goal="Improve AI coder logic and reliability",
                    constraints="Stay inside sandbox-only governance.",
                )
            )

            attempts = {item["candidate_key"]: item for item in learning_run["attempts"]}
            self.assertLess(
                attempts["efficiency-first"]["score"]["benchmark_history_adjustment"],
                attempts["balanced-governed"]["score"]["benchmark_history_adjustment"],
            )
            self.assertTrue(
                any("shortcut risk" in item.lower() for item in attempts["efficiency-first"]["risks"])
            )

    def test_coding_optimization_mission_writes_extra_lab_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            storage = Storage(repo_root / "agent.db")
            control = MissionControl(storage, ChildProjectBootstrapper(repo_root))

            mission = control.create_mission(
                MissionRequest(
                    goal="Design a sandbox loop that improves AI coding behavior",
                    domain="coding-optimization",
                    mission_name="Coder Lab",
                    constraints="No autonomy increase without review",
                )
            )

            artifact_types = {item["artifact_type"] for item in mission["artifacts"]}
            self.assertIn("benchmark", artifact_types)
            self.assertIn("instruction-pack", artifact_types)
            self.assertIn("promotion-gates", artifact_types)
            self.assertIn("lab-host-profile", artifact_types)
            self.assertIn("codex-runner-contract", artifact_types)
            self.assertIn("sandbox-benchmark-suite", artifact_types)
            self.assertEqual(
                mission["result"]["optimization_lab"]["objective_profile"]["mode"],
                "capability-optimization",
            )
            learning_runs = storage.list_learning_runs()
            self.assertEqual(len(learning_runs), 1)
            self.assertEqual(learning_runs[0]["mission_id"], mission["id"])
            outcomes = storage.list_outcomes(project_id=mission["project"]["id"])
            self.assertEqual(len(outcomes), 1)
            self.assertEqual(outcomes[0]["status"], "draft")


if __name__ == "__main__":
    unittest.main()
