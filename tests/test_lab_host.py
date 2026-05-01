from pathlib import Path
import tempfile
import unittest

from governed_agent_lab.lab_host import build_codex_runner_contract, collect_lab_host_profile


class LabHostTests(unittest.TestCase):
    def test_collect_lab_host_profile_reports_tools_and_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            profile = collect_lab_host_profile(Path(tmp))

        self.assertIn("hostname", profile)
        self.assertIn("tools", profile)
        self.assertIn("readiness", profile)
        self.assertIn("python", profile["tools"])
        self.assertIn(profile["readiness"]["status"], {"needs-tooling", "ready-with-constraints", "ready-for-local-codex-sandbox"})

    def test_codex_runner_contract_prefers_python_or_uv_commands(self) -> None:
        profile = {
            "hostname": "lab-host",
            "runtime": {"cpu_count": 4, "memory_gb": 8.0},
            "readiness": {"status": "ready-for-local-codex-sandbox", "summary": "Ready."},
            "tools": {
                "python": {"path": "/usr/bin/python3", "available": True},
                "git": {"path": "/usr/bin/git", "available": True},
                "uv": {"path": None, "available": False},
            },
        }

        contract = build_codex_runner_contract(profile)

        self.assertEqual(contract["runner"], "codex")
        self.assertIn("pytest", contract["preferred_commands"]["test"])
        self.assertIn("sandbox-only", contract["prerequisites"][0].lower())


if __name__ == "__main__":
    unittest.main()
