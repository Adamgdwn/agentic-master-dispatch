from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class Storage:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _column_names(self, conn: sqlite3.Connection, table_name: str) -> set[str]:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {str(row["name"]) for row in rows}

    def _ensure_column(
        self,
        conn: sqlite3.Connection,
        table_name: str,
        column_name: str,
        definition: str,
    ) -> None:
        if column_name in self._column_names(conn, table_name):
            return
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    goal TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    status TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    content TEXT NOT NULL,
                    weight REAL NOT NULL DEFAULT 1.0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    rating INTEGER NOT NULL,
                    notes TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(task_id) REFERENCES tasks(id)
                );

                CREATE TABLE IF NOT EXISTS missions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    run_id INTEGER,
                    name TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL,
                    constraints TEXT NOT NULL,
                    child_name TEXT NOT NULL,
                    child_slug TEXT NOT NULL,
                    child_path TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    spec_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES projects(id),
                    FOREIGN KEY(run_id) REFERENCES mission_runs(id)
                );

                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    slug TEXT NOT NULL UNIQUE,
                    domain TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    status TEXT NOT NULL,
                    root_path TEXT NOT NULL,
                    current_outcome_id INTEGER,
                    summary TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS mission_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    mission_id INTEGER,
                    run_key TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    root_path TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    spec_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES projects(id),
                    FOREIGN KEY(mission_id) REFERENCES missions(id)
                );

                CREATE TABLE IF NOT EXISTS outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    run_id INTEGER,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    path TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    content_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES projects(id),
                    FOREIGN KEY(run_id) REFERENCES mission_runs(id)
                );

                CREATE TABLE IF NOT EXISTS approvals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mission_id INTEGER NOT NULL,
                    approval_key TEXT NOT NULL,
                    title TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    required_for TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    decided_at TEXT,
                    FOREIGN KEY(mission_id) REFERENCES missions(id)
                );

                CREATE TABLE IF NOT EXISTS artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mission_id INTEGER NOT NULL,
                    artifact_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    path TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    content_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(mission_id) REFERENCES missions(id)
                );

                CREATE TABLE IF NOT EXISTS learning_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mission_id INTEGER,
                    domain TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    evaluation_mode TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    recommended_candidate TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(mission_id) REFERENCES missions(id)
                );

                CREATE TABLE IF NOT EXISTS learning_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    candidate_key TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    score_json TEXT NOT NULL,
                    instruction_pack_json TEXT NOT NULL,
                    strengths_json TEXT NOT NULL,
                    risks_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(run_id) REFERENCES learning_runs(id)
                );

                CREATE TABLE IF NOT EXISTS benchmark_evaluations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    family_key TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    score REAL NOT NULL,
                    passed INTEGER NOT NULL,
                    answer TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS sandbox_benchmark_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_group TEXT NOT NULL,
                    suite_key TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    command_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    passed INTEGER NOT NULL,
                    exit_code INTEGER,
                    duration_seconds REAL NOT NULL,
                    stdout_text TEXT NOT NULL,
                    stderr_text TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            self._ensure_column(conn, "missions", "project_id", "INTEGER")
            self._ensure_column(conn, "missions", "run_id", "INTEGER")

    def create_task(
        self, goal: str, domain: str, status: str, summary: str, result: dict[str, Any]
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO tasks (goal, domain, status, summary, result_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (goal, domain, status, summary, json.dumps(result)),
            )
            return int(cursor.lastrowid)

    def list_tasks(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, goal, domain, status, summary, created_at FROM tasks ORDER BY id DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_task(self, task_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
        if not row:
            return None
        task = dict(row)
        task["result"] = json.loads(task.pop("result_json"))
        return task

    def add_memory(self, domain: str, kind: str, content: str, weight: float = 1.0) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO memories (domain, kind, content, weight)
                VALUES (?, ?, ?, ?)
                """,
                (domain, kind, content, weight),
            )

    def list_memories(self, domain: str, limit: int = 8) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, domain, kind, content, weight, created_at
                FROM memories
                WHERE domain = ?
                ORDER BY weight DESC, id DESC
                LIMIT ?
                """,
                (domain, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_all_memories(self, limit: int = 16) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, domain, kind, content, weight, created_at
                FROM memories
                ORDER BY weight DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def add_feedback(self, task_id: int, rating: int, notes: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO feedback (task_id, rating, notes) VALUES (?, ?, ?)",
                (task_id, rating, notes),
            )

    def list_feedback(self, limit: int = 12) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT feedback.id, task_id, rating, notes, feedback.created_at, tasks.goal
                FROM feedback
                JOIN tasks ON tasks.id = feedback.task_id
                ORDER BY feedback.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_project(
        self,
        *,
        name: str,
        slug: str,
        domain: str,
        kind: str,
        owner: str,
        status: str,
        root_path: str,
        summary: str,
        metadata: dict[str, Any],
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO projects (
                    name, slug, domain, kind, owner, status, root_path,
                    summary, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    slug,
                    domain,
                    kind,
                    owner,
                    status,
                    root_path,
                    summary,
                    json.dumps(metadata),
                ),
            )
            return int(cursor.lastrowid)

    def get_project_by_slug(self, slug: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM projects WHERE slug = ?", (slug,)).fetchone()
        if not row:
            return None
        return self._project_record(dict(row))

    def get_project(self, project_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not row:
            return None
        return self._project_record(dict(row))

    def list_projects(self, limit: int = 24) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    id, name, slug, domain, kind, owner, status, root_path,
                    current_outcome_id, summary, metadata_json, created_at, updated_at
                FROM projects
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._project_record(dict(row)) for row in rows]

    def update_project(
        self,
        project_id: int,
        *,
        status: str | None = None,
        summary: str | None = None,
        current_outcome_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        fields: list[str] = []
        params: list[Any] = []
        if status is not None:
            fields.append("status = ?")
            params.append(status)
        if summary is not None:
            fields.append("summary = ?")
            params.append(summary)
        if current_outcome_id is not None:
            fields.append("current_outcome_id = ?")
            params.append(current_outcome_id)
        if metadata is not None:
            fields.append("metadata_json = ?")
            params.append(json.dumps(metadata))
        fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(project_id)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE projects SET {', '.join(fields)} WHERE id = ?",
                tuple(params),
            )

    def _project_record(self, project: dict[str, Any]) -> dict[str, Any]:
        project["metadata"] = json.loads(project.pop("metadata_json"))
        if project.get("current_outcome_id"):
            project["current_outcome"] = self.get_outcome(int(project["current_outcome_id"]))
        else:
            project["current_outcome"] = None
        return project

    def create_mission(
        self,
        *,
        project_id: int | None,
        run_id: int | None,
        name: str,
        goal: str,
        domain: str,
        owner: str,
        priority: str,
        status: str,
        constraints: str,
        child_name: str,
        child_slug: str,
        child_path: str,
        summary: str,
        spec: dict[str, Any],
        result: dict[str, Any],
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO missions (
                    project_id, run_id, name, goal, domain, owner, priority, status, constraints,
                    child_name, child_slug, child_path, summary, spec_json, result_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    run_id,
                    name,
                    goal,
                    domain,
                    owner,
                    priority,
                    status,
                    constraints,
                    child_name,
                    child_slug,
                    child_path,
                    summary,
                    json.dumps(spec),
                    json.dumps(result),
                ),
            )
            return int(cursor.lastrowid)

    def list_missions(self, limit: int = 24) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    missions.id,
                    missions.project_id,
                    missions.run_id,
                    missions.name,
                    goal,
                    domain,
                    owner,
                    priority,
                    missions.status,
                    constraints,
                    child_name,
                    child_slug,
                    child_path,
                    missions.summary,
                    missions.created_at,
                    missions.updated_at,
                    projects.name AS project_name,
                    projects.kind AS project_kind,
                    mission_runs.run_key
                FROM missions
                LEFT JOIN projects ON projects.id = missions.project_id
                LEFT JOIN mission_runs ON mission_runs.id = missions.run_id
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_mission(self, mission_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM missions WHERE id = ?", (mission_id,)).fetchone()
        if not row:
            return None
        mission = dict(row)
        mission["spec"] = json.loads(mission.pop("spec_json"))
        mission["result"] = json.loads(mission.pop("result_json"))
        mission["approvals"] = self.list_approvals(mission_id=mission_id)
        mission["artifacts"] = self.list_artifacts(mission_id=mission_id)
        mission["project"] = self.get_project(int(mission["project_id"])) if mission.get("project_id") else None
        mission["run"] = self.get_run(int(mission["run_id"])) if mission.get("run_id") else None
        return mission

    def update_mission_links(
        self,
        mission_id: int,
        *,
        project_id: int | None = None,
        run_id: int | None = None,
    ) -> None:
        fields: list[str] = []
        params: list[Any] = []
        if project_id is not None:
            fields.append("project_id = ?")
            params.append(project_id)
        if run_id is not None:
            fields.append("run_id = ?")
            params.append(run_id)
        if not fields:
            return
        fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(mission_id)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE missions SET {', '.join(fields)} WHERE id = ?",
                tuple(params),
            )

    def add_approval(
        self,
        mission_id: int,
        *,
        approval_key: str,
        title: str,
        rationale: str,
        required_for: str,
        status: str = "pending",
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO approvals (mission_id, approval_key, title, rationale, required_for, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (mission_id, approval_key, title, rationale, required_for, status),
            )
            return int(cursor.lastrowid)

    def list_approvals(
        self,
        mission_id: int | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        query = """
            SELECT
                approvals.id,
                mission_id,
                approval_key,
                title,
                rationale,
                required_for,
                approvals.status,
                approvals.created_at,
                approvals.decided_at,
                missions.name AS mission_name
            FROM approvals
            JOIN missions ON missions.id = approvals.mission_id
        """
        conditions: list[str] = []
        params: list[Any] = []
        if mission_id is not None:
            conditions.append("mission_id = ?")
            params.append(mission_id)
        if status is not None:
            conditions.append("approvals.status = ?")
            params.append(status)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY approvals.id DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(row) for row in rows]

    def update_approval_status(self, approval_id: int, status: str) -> int | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT mission_id FROM approvals WHERE id = ?",
                (approval_id,),
            ).fetchone()
            if not row:
                return None
            decided_at = None if status == "pending" else "CURRENT_TIMESTAMP"
            if decided_at is None:
                conn.execute(
                    """
                    UPDATE approvals
                    SET status = ?, decided_at = NULL
                    WHERE id = ?
                    """,
                    (status, approval_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE approvals
                    SET status = ?, decided_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (status, approval_id),
                )
            mission_id = int(row["mission_id"])
        self.refresh_mission_status(mission_id)
        return mission_id

    def add_artifact(
        self,
        mission_id: int,
        *,
        artifact_type: str,
        title: str,
        path: str,
        summary: str,
        content: dict[str, Any],
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO artifacts (mission_id, artifact_type, title, path, summary, content_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (mission_id, artifact_type, title, path, summary, json.dumps(content)),
            )
            return int(cursor.lastrowid)

    def list_artifacts(self, mission_id: int | None = None, limit: int = 100) -> list[dict[str, Any]]:
        query = """
            SELECT id, mission_id, artifact_type, title, path, summary, content_json, created_at
            FROM artifacts
        """
        params: list[Any] = []
        if mission_id is not None:
            query += " WHERE mission_id = ?"
            params.append(mission_id)
        query += " ORDER BY id ASC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        artifacts: list[dict[str, Any]] = []
        for row in rows:
            artifact = dict(row)
            artifact["content"] = json.loads(artifact.pop("content_json"))
            artifacts.append(artifact)
        return artifacts

    def update_mission_result(
        self,
        mission_id: int,
        *,
        status: str | None = None,
        summary: str | None = None,
        result: dict[str, Any] | None = None,
    ) -> None:
        fields: list[str] = []
        params: list[Any] = []
        if status is not None:
            fields.append("status = ?")
            params.append(status)
        if summary is not None:
            fields.append("summary = ?")
            params.append(summary)
        if result is not None:
            fields.append("result_json = ?")
            params.append(json.dumps(result))
        fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(mission_id)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE missions SET {', '.join(fields)} WHERE id = ?",
                tuple(params),
            )

    def create_run(
        self,
        *,
        project_id: int,
        mission_id: int | None,
        run_key: str,
        title: str,
        status: str,
        root_path: str,
        summary: str,
        spec: dict[str, Any],
        result: dict[str, Any],
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO mission_runs (
                    project_id, mission_id, run_key, title, status, root_path,
                    summary, spec_json, result_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    mission_id,
                    run_key,
                    title,
                    status,
                    root_path,
                    summary,
                    json.dumps(spec),
                    json.dumps(result),
                ),
            )
            return int(cursor.lastrowid)

    def list_runs(
        self,
        *,
        project_id: int | None = None,
        mission_id: int | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        query = """
            SELECT
                id, project_id, mission_id, run_key, title, status, root_path,
                summary, spec_json, result_json, created_at, updated_at
            FROM mission_runs
        """
        conditions: list[str] = []
        params: list[Any] = []
        if project_id is not None:
            conditions.append("project_id = ?")
            params.append(project_id)
        if mission_id is not None:
            conditions.append("mission_id = ?")
            params.append(mission_id)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._run_record(dict(row)) for row in rows]

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM mission_runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            return None
        return self._run_record(dict(row))

    def update_run(
        self,
        run_id: int,
        *,
        mission_id: int | None = None,
        status: str | None = None,
        summary: str | None = None,
        result: dict[str, Any] | None = None,
    ) -> None:
        fields: list[str] = []
        params: list[Any] = []
        if mission_id is not None:
            fields.append("mission_id = ?")
            params.append(mission_id)
        if status is not None:
            fields.append("status = ?")
            params.append(status)
        if summary is not None:
            fields.append("summary = ?")
            params.append(summary)
        if result is not None:
            fields.append("result_json = ?")
            params.append(json.dumps(result))
        fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(run_id)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE mission_runs SET {', '.join(fields)} WHERE id = ?",
                tuple(params),
            )

    def _run_record(self, run: dict[str, Any]) -> dict[str, Any]:
        run["spec"] = json.loads(run.pop("spec_json"))
        run["result"] = json.loads(run.pop("result_json"))
        return run

    def create_outcome(
        self,
        *,
        project_id: int,
        run_id: int | None,
        name: str,
        status: str,
        path: str,
        summary: str,
        content: dict[str, Any],
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO outcomes (
                    project_id, run_id, name, status, path, summary, content_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    run_id,
                    name,
                    status,
                    path,
                    summary,
                    json.dumps(content),
                ),
            )
            return int(cursor.lastrowid)

    def list_outcomes(
        self,
        *,
        project_id: int | None = None,
        run_id: int | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        query = """
            SELECT
                id, project_id, run_id, name, status, path, summary, content_json,
                created_at, updated_at
            FROM outcomes
        """
        conditions: list[str] = []
        params: list[Any] = []
        if project_id is not None:
            conditions.append("project_id = ?")
            params.append(project_id)
        if run_id is not None:
            conditions.append("run_id = ?")
            params.append(run_id)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._outcome_record(dict(row)) for row in rows]

    def get_outcome(self, outcome_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM outcomes WHERE id = ?", (outcome_id,)).fetchone()
        if not row:
            return None
        return self._outcome_record(dict(row))

    def promote_outcome(self, project_id: int, outcome_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE outcomes
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE project_id = ? AND id = ?
                """,
                ("promoted", project_id, outcome_id),
            )
        self.update_project(project_id, current_outcome_id=outcome_id)

    def _outcome_record(self, outcome: dict[str, Any]) -> dict[str, Any]:
        outcome["content"] = json.loads(outcome.pop("content_json"))
        return outcome

    def create_learning_run(
        self,
        *,
        mission_id: int | None,
        domain: str,
        goal: str,
        status: str,
        evaluation_mode: str,
        summary: str,
        recommended_candidate: str,
        result: dict[str, Any],
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO learning_runs (
                    mission_id, domain, goal, status, evaluation_mode, summary,
                    recommended_candidate, result_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mission_id,
                    domain,
                    goal,
                    status,
                    evaluation_mode,
                    summary,
                    recommended_candidate,
                    json.dumps(result),
                ),
            )
            return int(cursor.lastrowid)

    def add_learning_attempt(
        self,
        run_id: int,
        *,
        candidate_key: str,
        title: str,
        summary: str,
        score: dict[str, Any],
        instruction_pack: list[str],
        strengths: list[str],
        risks: list[str],
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO learning_attempts (
                    run_id, candidate_key, title, summary, score_json,
                    instruction_pack_json, strengths_json, risks_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    candidate_key,
                    title,
                    summary,
                    json.dumps(score),
                    json.dumps(instruction_pack),
                    json.dumps(strengths),
                    json.dumps(risks),
                ),
            )
            return int(cursor.lastrowid)

    def list_learning_runs(self, mission_id: int | None = None, limit: int = 24) -> list[dict[str, Any]]:
        query = """
            SELECT
                id, mission_id, domain, goal, status, evaluation_mode, summary,
                recommended_candidate, created_at
            FROM learning_runs
        """
        params: list[Any] = []
        if mission_id is not None:
            query += " WHERE mission_id = ?"
            params.append(mission_id)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(row) for row in rows]

    def list_learning_attempts(self, run_id: int, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    id, run_id, candidate_key, title, summary, score_json,
                    instruction_pack_json, strengths_json, risks_json, created_at
                FROM learning_attempts
                WHERE run_id = ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (run_id, limit),
            ).fetchall()
        attempts = []
        for row in rows:
            attempt = dict(row)
            attempt["score"] = json.loads(attempt.pop("score_json"))
            attempt["instruction_pack"] = json.loads(attempt.pop("instruction_pack_json"))
            attempt["strengths"] = json.loads(attempt.pop("strengths_json"))
            attempt["risks"] = json.loads(attempt.pop("risks_json"))
            attempts.append(attempt)
        return attempts

    def get_learning_run(self, run_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM learning_runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            return None
        learning_run = dict(row)
        learning_run["result"] = json.loads(learning_run.pop("result_json"))
        learning_run["attempts"] = self.list_learning_attempts(run_id)
        return learning_run

    def add_benchmark_evaluation(
        self,
        *,
        family_key: str,
        case_id: str,
        score: float,
        passed: bool,
        answer: str,
        result: dict[str, Any],
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO benchmark_evaluations (
                    family_key, case_id, score, passed, answer, result_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    family_key,
                    case_id,
                    score,
                    1 if passed else 0,
                    answer,
                    json.dumps(result),
                ),
            )
            return int(cursor.lastrowid)

    def list_benchmark_evaluations(
        self,
        family_key: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        query = """
            SELECT id, family_key, case_id, score, passed, answer, result_json, created_at
            FROM benchmark_evaluations
        """
        params: list[Any] = []
        if family_key is not None:
            query += " WHERE family_key = ?"
            params.append(family_key)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        evaluations = []
        for row in rows:
            evaluation = dict(row)
            evaluation["passed"] = bool(evaluation["passed"])
            evaluation["result"] = json.loads(evaluation.pop("result_json"))
            evaluations.append(evaluation)
        return evaluations

    def add_sandbox_benchmark_run(
        self,
        *,
        run_group: str,
        suite_key: str,
        case_id: str,
        title: str,
        command: list[str],
        status: str,
        passed: bool,
        exit_code: int | None,
        duration_seconds: float,
        stdout: str,
        stderr: str,
        result: dict[str, Any],
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sandbox_benchmark_runs (
                    run_group, suite_key, case_id, title, command_json,
                    status, passed, exit_code, duration_seconds, stdout_text,
                    stderr_text, result_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_group,
                    suite_key,
                    case_id,
                    title,
                    json.dumps(command),
                    status,
                    1 if passed else 0,
                    exit_code,
                    duration_seconds,
                    stdout,
                    stderr,
                    json.dumps(result),
                ),
            )
            return int(cursor.lastrowid)

    def list_sandbox_benchmark_runs(
        self,
        run_group: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        query = """
            SELECT
                id, run_group, suite_key, case_id, title, command_json, status,
                passed, exit_code, duration_seconds, stdout_text, stderr_text,
                result_json, created_at
            FROM sandbox_benchmark_runs
        """
        params: list[Any] = []
        if run_group is not None:
            query += " WHERE run_group = ?"
            params.append(run_group)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        runs = []
        for row in rows:
            run = dict(row)
            run["command"] = json.loads(run.pop("command_json"))
            run["passed"] = bool(run["passed"])
            run["stdout"] = run.pop("stdout_text")
            run["stderr"] = run.pop("stderr_text")
            run["result"] = json.loads(run.pop("result_json"))
            runs.append(run)
        return runs

    def refresh_mission_status(self, mission_id: int) -> str:
        approvals = self.list_approvals(mission_id=mission_id)
        if not approvals:
            status = "ready"
        else:
            statuses = {item["status"] for item in approvals}
            if "rejected" in statuses:
                status = "blocked"
            elif statuses == {"approved"}:
                status = "ready"
            else:
                status = "awaiting-approval"

        with self._connect() as conn:
            conn.execute(
                """
                UPDATE missions
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, mission_id),
            )
        return status
