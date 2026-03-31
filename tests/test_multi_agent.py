import unittest

from governed_agent_lab.multi_agent import MultiAgentRequest, MultiAgentSystem


class MultiAgentTests(unittest.TestCase):
    def test_multi_agent_system_returns_roles_handoffs_and_gates(self) -> None:
        system = MultiAgentSystem()
        result = system.run(
            MultiAgentRequest(
                goal="Find robust sandboxed strategies",
                domain_label="Trading Strategy",
                constraints="No live deployment",
                blocked_actions=["place live trade"],
            )
        )
        self.assertEqual(result["roles"][0]["role"], "planner")
        self.assertTrue(any(item["role"] == "deployment" for item in result["roles"]))
        self.assertTrue(any(gate["gate"] == "paper-trade-to-deployment" for gate in result["gates"]))
        self.assertTrue(any(handoff["artifact"] == "strategy-specs" for handoff in result["handoffs"]))


if __name__ == "__main__":
    unittest.main()
