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
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
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
                """
            )

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

    def create_mission(
        self,
        *,
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
                    name, goal, domain, owner, priority, status, constraints,
                    child_name, child_slug, child_path, summary, spec_json, result_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
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
                    id, name, goal, domain, owner, priority, status, constraints,
                    child_name, child_slug, child_path, summary, created_at, updated_at
                FROM missions
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
        return mission

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
