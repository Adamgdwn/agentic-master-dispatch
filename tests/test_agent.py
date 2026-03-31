from pathlib import Path
import os
import sqlite3
import tempfile
import unittest

from governed_agent_lab.agent import AgentRequest, GovernedAgent
from governed_agent_lab.child_projects import ChildProjectBootstrapper, ChildProjectRequest
from governed_agent_lab.connectors import load_local_env, test_connector
from governed_agent_lab.storage import Storage


class AgentTests(unittest.TestCase):
    def test_agent_cycle_creates_report_and_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            storage = Storage(Path(tmp) / "agent.db")
            agent = GovernedAgent(storage)
            task = agent.run(
                AgentRequest(
                    goal="Research a volatility breakout strategy",
                    domain="trading-strategy",
                    constraints="Focus on simple and reproducible ideas",
                )
            )
            self.assertEqual(task["report"]["project_type"], "Trading Strategy")
            self.assertEqual(task["ethical_outcomes"]["decision"], "approved-for-sandbox-only")
            self.assertTrue(storage.list_memories("trading-strategy"))
            self.assertIn("roles", task["orchestration"])
            self.assertIn("gates", task["orchestration"])

    def test_child_workspace_bootstrap_creates_governed_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bootstrapper = ChildProjectBootstrapper(Path(tmp))
            child = bootstrapper.create_child(
                ChildProjectRequest(
                    name="Market Structure Lab",
                    goal="Study market structure hypotheses in a sandbox.",
                    domain="research-and-development",
                    owner="Adam Goodwin",
                    constraints="No downloads without approval",
                )
            )
            child_root = Path(child["path"])
            self.assertTrue((child_root / "project-control.yaml").exists())
            self.assertTrue((child_root / "docs/tool-permission-matrix.md").exists())
            self.assertTrue((child_root / "workspace/goal.md").exists())
            self.assertTrue((child_root / "config/secrets.example.env").exists())
            self.assertTrue((child_root / "config/tool-profiles.toml").exists())

    def test_load_local_env_sets_missing_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / "secrets.local.env"
            env_file.write_text("OPENAI_API_KEY=test-key\n# comment\nEMPTY=\n", encoding="utf-8")
            os.environ.pop("OPENAI_API_KEY", None)
            loaded = load_local_env(env_file)
            self.assertEqual(loaded["OPENAI_API_KEY"], "test-key")
            self.assertEqual(os.environ["OPENAI_API_KEY"], "test-key")

    def test_sqlite_connector_test_works_with_read_only_db(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "sample.db"
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE sample (id INTEGER)")
            conn.execute("INSERT INTO sample (id) VALUES (1)")
            conn.commit()
            conn.close()

            os.environ["SQLITE_DB_PATH"] = str(db_path)
            result = test_connector("sqlite_readonly")
            self.assertTrue(result["ok"])


if __name__ == "__main__":
    unittest.main()
