from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .reporting import load_price_series, sample_strategy_report, summarize_backtest, summarize_price_series

from .agent import AgentRequest, GovernedAgent
from .benchmark_runner import BenchmarkEvaluationRequest, BenchmarkRunner
from .child_projects import ChildProjectBootstrapper, ChildProjectRequest
from .connectors import connector_statuses, load_local_env, probe_connector
from .domain_profiles import DOMAIN_PROFILES
from .lab_host import build_codex_runner_contract, collect_lab_host_profile
from .mission_control import MissionControl, MissionRequest
from .sandbox_benchmarks import build_lab_host_benchmark_executor
from .storage import Storage

REPO_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = REPO_ROOT / "web"
DATA_DIR = REPO_ROOT / "data"
CONFIG_DIR = REPO_ROOT / "config"
REPORTS_DIR = REPO_ROOT / "data" / "reports"


class App:
    def __init__(self) -> None:
        self.loaded_env = load_local_env(CONFIG_DIR / "secrets.local.env")
        self.storage = Storage(DATA_DIR / "agent.db")
        self.children = ChildProjectBootstrapper(REPO_ROOT)
        self.agent = GovernedAgent(self.storage)
        self.benchmarks = BenchmarkRunner()
        self.missions = MissionControl(self.storage, self.children)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        self._seed_memory()

    def _seed_memory(self) -> None:
        if self.storage.list_all_memories(limit=1):
            return
        self.storage.add_memory(
            "trading-strategy",
            "policy",
            "Default to simple hypotheses, risk controls first, and sandbox-only execution.",
            weight=2.0,
        )
        self.storage.add_memory(
            "research-and-development",
            "policy",
            "Start with first principles, test assumptions early, and preserve reusable lessons.",
            weight=2.0,
        )

    def reload_env(self) -> dict[str, str]:
        self.loaded_env = load_local_env(CONFIG_DIR / "secrets.local.env")
        return self.loaded_env

    def lab_host_profile(self) -> dict[str, object]:
        return collect_lab_host_profile(REPO_ROOT)

    def sandbox_benchmark_executor(self):
        profile = self.lab_host_profile()
        contract = build_codex_runner_contract(profile)
        return build_lab_host_benchmark_executor(
            REPO_ROOT,
            test_command=contract["preferred_commands"]["test"],
        )


APP = App()


class RequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8"))

    def _benchmark_family_payload(self, family_key: str | None = None) -> tuple[dict[str, object], int]:
        if family_key is None:
            return {
                "families": APP.benchmarks.list_families(),
                "evaluations": APP.storage.list_benchmark_evaluations(limit=20),
            }, HTTPStatus.OK
        try:
            family = APP.benchmarks.get_family(family_key)
        except ValueError:
            return {"error": "Benchmark family not found"}, HTTPStatus.NOT_FOUND
        return {
            "family": family,
            "evaluations": APP.storage.list_benchmark_evaluations(
                family_key=family_key,
                limit=20,
            ),
        }, HTTPStatus.OK

    def _run_benchmark_evaluation(
        self,
        body: dict[str, object],
        family_key_override: str | None = None,
    ) -> tuple[dict[str, object], int]:
        family_key = family_key_override or str(body.get("family_key", "")).strip()
        case_id = str(body.get("case_id", "")).strip()
        answer = str(body.get("answer", "")).strip()
        if not family_key or not case_id or not answer:
            return {"error": "family_key, case_id, and answer are required"}, HTTPStatus.BAD_REQUEST
        try:
            result = APP.benchmarks.evaluate(
                BenchmarkEvaluationRequest(
                    family_key=family_key,
                    case_id=case_id,
                    answer=answer,
                )
            )
        except ValueError as exc:
            return {"error": str(exc)}, HTTPStatus.BAD_REQUEST
        evaluation_id = APP.storage.add_benchmark_evaluation(
            family_key=result["family_key"],
            case_id=result["case_id"],
            score=result["score"],
            passed=result["passed"],
            answer=result["answer"],
            result=result,
        )
        return {"evaluation_id": evaluation_id, "result": result}, HTTPStatus.CREATED

    def _lab_host_benchmark_payload(self) -> dict[str, object]:
        suite = APP.sandbox_benchmark_executor().list_suite()
        recent_runs = APP.storage.list_sandbox_benchmark_runs(limit=20)
        return {
            "suite": suite,
            "recent_runs": recent_runs,
        }

    def _run_lab_host_benchmarks(self, body: dict[str, object]) -> tuple[dict[str, object], int]:
        raw_case_ids = body.get("case_ids", [])
        case_ids = raw_case_ids if isinstance(raw_case_ids, list) else []
        try:
            run = APP.sandbox_benchmark_executor().run(
                [str(item).strip() for item in case_ids if str(item).strip()]
            )
        except ValueError as exc:
            return {"error": str(exc)}, HTTPStatus.BAD_REQUEST

        for result in run["results"]:
            APP.storage.add_sandbox_benchmark_run(
                run_group=run["run_group"],
                suite_key=run["suite"]["suite_key"],
                case_id=result["case_id"],
                title=result["title"],
                command=result["command"],
                status=result["status"],
                passed=result["passed"],
                exit_code=result["exit_code"],
                duration_seconds=result["duration_seconds"],
                stdout=result["stdout"],
                stderr=result["stderr"],
                result=result,
            )
        run["stored_results"] = APP.storage.list_sandbox_benchmark_runs(run_group=run["run_group"], limit=20)
        return run, HTTPStatus.CREATED

    def _compose_exploration_constraints(self, body: dict[str, object]) -> str:
        sections = [
            ("Hard Constraints", str(body.get("hard_constraints", "")).strip()),
            ("Available Environment", str(body.get("available_environment", "")).strip()),
            ("Evidence Requirements", str(body.get("evidence_requirements", "")).strip()),
            (
                "Operator Hunches",
                str(body.get("operator_hunches", "")).strip(),
            ),
            (
                "Disallowed Assumptions",
                str(body.get("disallowed_assumptions", "")).strip(),
            ),
        ]
        lines: list[str] = []
        for title, content in sections:
            if not content:
                continue
            if title == "Operator Hunches":
                content = (
                    "Treat these as operator hypotheses for exploration, not as the scoring rule unless later approved.\n"
                    + content
                )
            lines.append(f"{title}:")
            lines.append(content)
            lines.append("")
        return "\n".join(lines).strip()

    def _exploration_preview(self, body: dict[str, object]) -> tuple[dict[str, object], int]:
        goal = str(body.get("goal", "")).strip()
        if not goal:
            return {"error": "Goal is required"}, HTTPStatus.BAD_REQUEST
        domain = str(body.get("domain", "coding-optimization")).strip() or "coding-optimization"
        if domain not in DOMAIN_PROFILES:
            return {"error": "Unknown domain"}, HTTPStatus.BAD_REQUEST

        structured_constraints = self._compose_exploration_constraints(body)
        objective_profile = APP.missions.coding_loop.preview_objective_profile(
            goal,
            structured_constraints,
            host_profile=APP.lab_host_profile(),
        )
        unresolved = []
        if not str(body.get("hard_constraints", "")).strip():
            unresolved.append("No hard constraints were provided yet.")
        if not str(body.get("evidence_requirements", "")).strip():
            unresolved.append("Evidence requirements are still open-ended.")
        if not str(body.get("disallowed_assumptions", "")).strip():
            unresolved.append("Disallowed assumptions are not yet explicit.")

        return {
            "preview": {
                "domain": domain,
                "objective_profile": objective_profile,
                "mission_packet": {
                    "project_name": str(body.get("project_name", "")).strip(),
                    "project_kind": str(body.get("project_kind", "project")).strip() or "project",
                    "goal": goal,
                    "domain": domain,
                    "constraints": structured_constraints,
                },
                "bias_controls": [
                    "Keep operator hunches separate from the core mission statement.",
                    "Require measurable dimensions before claiming one option is best.",
                    "Treat unresolved assumptions as review items, not silent defaults.",
                ],
                "unresolved_questions": unresolved,
            }
        }, HTTPStatus.OK

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/state":
            missions = APP.storage.list_missions()
            pending_approvals = APP.storage.list_approvals(status="pending", limit=50)
            self._send_json(
                {
                    "project": {
                        "name": "Governed Agent Lab",
                        "risk_tier": "high",
                        "autonomy_level": "A2",
                        "scope": "Mission intake, governed child workspaces, approvals, sandbox execution",
                        "launcher": str(REPO_ROOT / "GovernedAgentLab.command"),
                    },
                    "domains": DOMAIN_PROFILES,
                    "missions": missions,
                    "pending_approvals": pending_approvals,
                    "tasks": APP.storage.list_tasks(),
                    "memories": APP.storage.list_all_memories(),
                    "feedback": APP.storage.list_feedback(),
                    "learning_runs": APP.storage.list_learning_runs(),
                    "projects": APP.storage.list_projects(),
                    "runs": APP.storage.list_runs(limit=50),
                    "outcomes": APP.storage.list_outcomes(limit=50),
                    "benchmark_evaluations": APP.storage.list_benchmark_evaluations(limit=20),
                    "sandbox_benchmark_runs": APP.storage.list_sandbox_benchmark_runs(limit=20),
                    "lab_host": APP.lab_host_profile(),
                    "children": APP.children.list_children(),
                    "connectors": connector_statuses(REPO_ROOT / "config" / "tool-profiles.toml"),
                    "loaded_env_keys": sorted(APP.loaded_env.keys()),
                }
            )
            return
        if parsed.path.startswith("/api/missions/"):
            mission_id = parsed.path.rsplit("/", 1)[-1]
            if mission_id.isdigit():
                mission = APP.storage.get_mission(int(mission_id))
                if mission:
                    self._send_json({"mission": mission})
                    return
            self._send_json({"error": "Mission not found"}, status=404)
            return
        if parsed.path == "/api/reporting/sample":
            payload = sample_strategy_report()
            self._send_json({"report": payload})
            return
        if parsed.path.startswith("/api/tasks/"):
            task_id = parsed.path.rsplit("/", 1)[-1]
            if task_id.isdigit():
                task = APP.storage.get_task(int(task_id))
                if task:
                    self._send_json({"task": task})
                    return
            self._send_json({"error": "Task not found"}, status=404)
            return
        if parsed.path == "/api/benchmarks/prerequisite-reasoning":
            payload, status = self._benchmark_family_payload("goal-and-precondition-reasoning")
            self._send_json(payload, status=status)
            return
        if parsed.path == "/api/lab-host/profile":
            self._send_json({"profile": APP.lab_host_profile()})
            return
        if parsed.path == "/api/lab-host/benchmarks":
            self._send_json(self._lab_host_benchmark_payload())
            return
        if parsed.path == "/api/benchmarks":
            payload, status = self._benchmark_family_payload()
            self._send_json(payload, status=status)
            return
        if parsed.path.startswith("/api/benchmarks/"):
            family_key = parsed.path.rsplit("/", 1)[-1]
            payload, status = self._benchmark_family_payload(family_key)
            self._send_json(payload, status=status)
            return
        return super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/tasks":
            body = self._read_json()
            goal = body.get("goal", "").strip()
            domain = body.get("domain", "research-and-development").strip()
            constraints = body.get("constraints", "").strip()
            if not goal:
                self._send_json({"error": "Goal is required"}, status=HTTPStatus.BAD_REQUEST)
                return
            if domain not in DOMAIN_PROFILES:
                self._send_json({"error": "Unknown domain"}, status=HTTPStatus.BAD_REQUEST)
                return
            task = APP.agent.run(AgentRequest(goal=goal, domain=domain, constraints=constraints))
            self._send_json({"task": task}, status=HTTPStatus.CREATED)
            return
        if parsed.path == "/api/missions":
            body = self._read_json()
            goal = body.get("goal", "").strip()
            domain = body.get("domain", "research-and-development").strip()
            if not goal:
                self._send_json({"error": "Goal is required"}, status=HTTPStatus.BAD_REQUEST)
                return
            if domain not in DOMAIN_PROFILES:
                self._send_json({"error": "Unknown domain"}, status=HTTPStatus.BAD_REQUEST)
                return
            mission = APP.missions.create_mission(
                MissionRequest(
                    goal=goal,
                    domain=domain,
                    constraints=body.get("constraints", "").strip(),
                    owner=body.get("owner", "").strip(),
                    mission_name=body.get("mission_name", "").strip(),
                    project_name=body.get("project_name", "").strip(),
                    project_kind=body.get("project_kind", "project").strip() or "project",
                    priority=body.get("priority", "balanced").strip() or "balanced",
                    requested_connectors=body.get("requested_connectors", []),
                )
            )
            self._send_json({"mission": mission}, status=HTTPStatus.CREATED)
            return
        if parsed.path == "/api/exploration/preview":
            payload, status = self._exploration_preview(self._read_json())
            self._send_json(payload, status=status)
            return
        if parsed.path == "/api/children":
            body = self._read_json()
            if not body.get("name", "").strip() or not body.get("goal", "").strip():
                self._send_json({"error": "Name and goal are required"}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                child = APP.children.create_child(
                    ChildProjectRequest(
                        name=body.get("name", "").strip(),
                        goal=body.get("goal", "").strip(),
                        domain=body.get("domain", "research-and-development").strip(),
                        owner=body.get("owner", "").strip(),
                        constraints=body.get("constraints", "").strip(),
                    )
                )
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            except FileExistsError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.CONFLICT)
                return
            self._send_json({"child": child}, status=HTTPStatus.CREATED)
            return
        if parsed.path == "/api/reporting/price-series":
            body = self._read_json()
            csv_path = body.get("csv_path", "").strip()
            window = int(body.get("window", 20))
            if not csv_path:
                self._send_json({"error": "csv_path is required"}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                series = load_price_series(Path(csv_path))
                report = summarize_price_series(series, window=window)
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            self._send_json({"report": report})
            return
        if parsed.path == "/api/reporting/backtest":
            body = self._read_json()
            trade_pnls = body.get("trade_pnls", [])
            fees = body.get("fees")
            starting_capital = float(body.get("starting_capital", 10000.0))
            try:
                report = summarize_backtest(trade_pnls, fees=fees, starting_capital=starting_capital)
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            self._send_json({"report": report})
            return
        if parsed.path == "/api/connectors/reload":
            loaded = APP.reload_env()
            self._send_json({"ok": True, "loaded_env_keys": sorted(loaded.keys())})
            return
        if parsed.path == "/api/connectors/test":
            body = self._read_json()
            connector_key = body.get("connector", "").strip()
            if not connector_key:
                self._send_json({"error": "Connector key is required"}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                result = probe_connector(connector_key)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            self._send_json({"result": result})
            return
        if parsed.path == "/api/benchmarks/prerequisite-reasoning/evaluate":
            payload, status = self._run_benchmark_evaluation(
                self._read_json(),
                family_key_override="goal-and-precondition-reasoning",
            )
            self._send_json(payload, status=status)
            return
        if parsed.path == "/api/benchmarks/evaluate":
            payload, status = self._run_benchmark_evaluation(self._read_json())
            self._send_json(payload, status=status)
            return
        if parsed.path == "/api/lab-host/benchmarks/run":
            payload, status = self._run_lab_host_benchmarks(self._read_json())
            self._send_json(payload, status=status)
            return
        if parsed.path.startswith("/api/approvals/"):
            pieces = parsed.path.split("/")
            if len(pieces) >= 4 and pieces[3].isdigit():
                approval_id = int(pieces[3])
                body = self._read_json()
                status = body.get("status", "").strip()
                if status not in {"pending", "approved", "rejected"}:
                    self._send_json({"error": "Status must be pending, approved, or rejected"}, status=HTTPStatus.BAD_REQUEST)
                    return
                mission = APP.missions.decide_approval(approval_id, status)
                if mission is None:
                    self._send_json({"error": "Approval not found"}, status=HTTPStatus.NOT_FOUND)
                    return
                self._send_json({"mission": mission})
                return
            self._send_json({"error": "Invalid approval id"}, status=HTTPStatus.BAD_REQUEST)
            return
        if parsed.path.startswith("/api/tasks/") and parsed.path.endswith("/feedback"):
            pieces = parsed.path.split("/")
            if len(pieces) >= 4 and pieces[3].isdigit():
                task_id = int(pieces[3])
                body = self._read_json()
                rating = int(body.get("rating", 0))
                notes = body.get("notes", "").strip()
                if rating < 1 or rating > 5:
                    self._send_json({"error": "Rating must be between 1 and 5"}, status=HTTPStatus.BAD_REQUEST)
                    return
                APP.agent.reinforce(task_id=task_id, rating=rating, notes=notes)
                self._send_json({"ok": True})
                return
            self._send_json({"error": "Invalid task id"}, status=HTTPStatus.BAD_REQUEST)
            return
        self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, fmt: str, *args) -> None:
        if os.environ.get("AGENT_SERVER_QUIET") == "1":
            return
        super().log_message(fmt, *args)


def create_server(host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), RequestHandler)


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = create_server(host=host, port=port)
    print(f"Serving Governed Agent Lab UI at http://{host}:{port}")
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
