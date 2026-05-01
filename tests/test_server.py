import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from governed_agent_lab.benchmark_runner import BenchmarkRunner
from governed_agent_lab.sandbox_benchmarks import SandboxBenchmarkCase, SandboxBenchmarkExecutor
from governed_agent_lab.server import create_server
from governed_agent_lab.storage import Storage


class ServerBenchmarkTests(unittest.TestCase):
    def _request_json(
        self,
        conn: http.client.HTTPConnection,
        method: str,
        path: str,
        body: dict | None = None,
    ) -> tuple[int, dict]:
        payload = None if body is None else json.dumps(body)
        headers = {"Content-Type": "application/json"} if body is not None else {}
        conn.request(method, path, body=payload, headers=headers)
        response = conn.getresponse()
        data = response.read().decode("utf-8")
        return response.status, json.loads(data)

    def test_benchmark_endpoints_list_and_evaluate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = SimpleNamespace(
                storage=Storage(Path(tmp) / "agent.db"),
                benchmarks=BenchmarkRunner(),
                lab_host_profile=lambda: {
                    "hostname": "chuwi-lab",
                    "readiness": {"status": "ready-for-local-codex-sandbox", "summary": "Ready."},
                },
                sandbox_benchmark_executor=lambda: SandboxBenchmarkExecutor(
                    Path(tmp),
                    cases=[
                        SandboxBenchmarkCase(
                            id="quick-pass",
                            title="Quick Pass",
                            description="Fast passing command.",
                            command=["bash", "-lc", "printf ok"],
                            timeout_seconds=5,
                        )
                    ],
                ),
            )
            with patch("governed_agent_lab.server.APP", app):
                server = create_server(host="127.0.0.1", port=0)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                host, port = server.server_address
                conn = http.client.HTTPConnection(host, port, timeout=5)
                try:
                    status, payload = self._request_json(conn, "GET", "/api/benchmarks")
                    self.assertEqual(status, 200)
                    self.assertTrue(
                        any(item["family_key"] == "goal-and-precondition-reasoning" for item in payload["families"])
                    )

                    status, payload = self._request_json(
                        conn,
                        "POST",
                        "/api/benchmarks/evaluate",
                        {
                            "family_key": "goal-and-precondition-reasoning",
                            "case_id": "wash-car-drive",
                            "answer": "Drive the car there because the car must be at the car wash.",
                        },
                    )
                    self.assertEqual(status, 201)
                    self.assertTrue(payload["result"]["passed"])

                    status, payload = self._request_json(conn, "GET", "/api/benchmarks/goal-and-precondition-reasoning")
                    self.assertEqual(status, 200)
                    self.assertTrue(payload["evaluations"])

                    status, payload = self._request_json(conn, "GET", "/api/lab-host/profile")
                    self.assertEqual(status, 200)
                    self.assertEqual(payload["profile"]["hostname"], "chuwi-lab")

                    status, payload = self._request_json(conn, "GET", "/api/lab-host/benchmarks")
                    self.assertEqual(status, 200)
                    self.assertEqual(payload["suite"]["suite_key"], "lab-host-coding-sandbox")

                    status, payload = self._request_json(conn, "POST", "/api/lab-host/benchmarks/run", {})
                    self.assertEqual(status, 201)
                    self.assertTrue(payload["passed"])
                    self.assertTrue(payload["stored_results"])
                finally:
                    conn.close()
                    server.shutdown()
                    server.server_close()
                    thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
