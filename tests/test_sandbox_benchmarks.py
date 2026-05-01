from pathlib import Path
import tempfile
import unittest

from governed_agent_lab.sandbox_benchmarks import SandboxBenchmarkCase, SandboxBenchmarkExecutor


class SandboxBenchmarkTests(unittest.TestCase):
    def test_executor_runs_selected_cases_and_reports_pass_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            executor = SandboxBenchmarkExecutor(
                root,
                cases=[
                    SandboxBenchmarkCase(
                        id="pass",
                        title="Pass",
                        description="A passing command.",
                        command=["bash", "-lc", "printf ok"],
                        timeout_seconds=5,
                    ),
                    SandboxBenchmarkCase(
                        id="fail",
                        title="Fail",
                        description="A failing command.",
                        command=["bash", "-lc", "exit 2"],
                        timeout_seconds=5,
                    ),
                ],
            )

            run = executor.run(["pass", "fail"])

        self.assertEqual(len(run["results"]), 2)
        self.assertTrue(any(item["passed"] for item in run["results"]))
        self.assertTrue(any(not item["passed"] for item in run["results"]))

    def test_executor_rejects_unknown_case(self) -> None:
        executor = SandboxBenchmarkExecutor(Path.cwd(), cases=[])
        with self.assertRaises(ValueError):
            executor.run(["missing"])


if __name__ == "__main__":
    unittest.main()
