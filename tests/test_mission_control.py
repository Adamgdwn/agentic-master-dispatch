from pathlib import Path
import tempfile
import unittest

from governed_agent_lab.child_projects import ChildProjectBootstrapper
from governed_agent_lab.mission_control import MissionControl, MissionRequest
from governed_agent_lab.storage import Storage


class MissionControlTests(unittest.TestCase):
    def test_create_mission_bootstraps_child_workspace_and_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            storage = Storage(repo_root / "agent.db")
            control = MissionControl(storage, ChildProjectBootstrapper(repo_root))

            mission = control.create_mission(
                MissionRequest(
                    goal="Design a governed note-taking workflow",
                    domain="research-and-development",
                    owner="Adam Goodwin",
                    mission_name="Notes Lab",
                    requested_connectors=["openai"],
                )
            )

            self.assertEqual(mission["status"], "awaiting-approval")
            self.assertEqual(mission["name"], "Notes Lab")
            self.assertTrue(Path(mission["child_path"]).exists())
            self.assertIsNotNone(mission["project"])
            self.assertIsNotNone(mission["run"])
            self.assertEqual(len(mission["approvals"]), 2)
            self.assertGreaterEqual(len(mission["artifacts"]), 4)
            self.assertTrue(any(item["artifact_type"] == "manifest" for item in mission["artifacts"]))
            self.assertEqual(mission["spec"]["child"]["requested_connectors"], ["openai"])
            self.assertIn("/workspace/runs/", mission["child_path"])

    def test_approving_all_items_moves_mission_to_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            storage = Storage(repo_root / "agent.db")
            control = MissionControl(storage, ChildProjectBootstrapper(repo_root))

            mission = control.create_mission(
                MissionRequest(
                    goal="Study a governed sandbox workflow",
                    domain="research-and-development",
                    requested_connectors=["perplexity"],
                )
            )

            for approval in mission["approvals"]:
                mission = control.decide_approval(approval["id"], "approved")

            self.assertIsNotNone(mission)
            assert mission is not None
            self.assertEqual(mission["status"], "ready")

    def test_same_project_gets_new_isolated_run_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            storage = Storage(repo_root / "agent.db")
            control = MissionControl(storage, ChildProjectBootstrapper(repo_root))

            first = control.create_mission(
                MissionRequest(
                    goal="Explore a governed app concept",
                    domain="research-and-development",
                    project_name="Shared Lab",
                    mission_name="Shared Lab Alpha",
                )
            )
            second = control.create_mission(
                MissionRequest(
                    goal="Iterate on the same governed app concept",
                    domain="research-and-development",
                    project_name="Shared Lab",
                    mission_name="Shared Lab Beta",
                )
            )

            self.assertEqual(first["project"]["id"], second["project"]["id"])
            self.assertEqual(first["project"]["root_path"], second["project"]["root_path"])
            self.assertNotEqual(first["run"]["id"], second["run"]["id"])
            self.assertNotEqual(first["run"]["root_path"], second["run"]["root_path"])
            self.assertNotEqual(first["child_path"], second["child_path"])
            self.assertTrue(Path(first["run"]["root_path"]).exists())
            self.assertTrue(Path(second["run"]["root_path"]).exists())
            self.assertEqual(len(storage.list_projects()), 1)
            self.assertEqual(len(storage.list_runs(project_id=first["project"]["id"])), 2)


if __name__ == "__main__":
    unittest.main()
