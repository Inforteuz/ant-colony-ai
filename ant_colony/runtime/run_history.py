"""Persistent local history for completed and in-progress orchestration runs."""
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


PERSISTED_EVENT_TYPES = {
    "pm_plan_ready",
    "qa_verified",
    "security_report",
    "role_evaluation",
    "orchestration_completed",
    "orchestration_failed",
    "orchestration_cancelled",
}


class RunHistory:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    job_id TEXT PRIMARY KEY,
                    task TEXT NOT NULL,
                    language TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    finished_at REAL,
                    project_dir TEXT,
                    final_score REAL,
                    plan_json TEXT,
                    final_json TEXT,
                    updated_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS run_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY(job_id) REFERENCES runs(job_id)
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs(created_at DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_run_events_job_id ON run_events(job_id, id)")

    def start_run(self, job_id: str, task: str, language: str, created_at: float) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO runs(job_id, task, language, status, created_at, updated_at)
                VALUES (?, ?, ?, 'running', ?, ?)
                """,
                (job_id, task, language, created_at, created_at),
            )

    def record_event(self, job_id: str, event: Dict[str, Any]) -> None:
        if event.get("type") not in PERSISTED_EVENT_TYPES:
            return
        now = time.time()
        payload = json.dumps(event, ensure_ascii=False, default=str)
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO run_events(job_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?)",
                (job_id, event["type"], payload, now),
            )
            if event["type"] == "pm_plan_ready":
                conn.execute(
                    "UPDATE runs SET plan_json = ?, updated_at = ? WHERE job_id = ?",
                    (payload, now, job_id),
                )

    def finish_run(self, job_id: str, status: str, finished_at: float,
                   final_event: Optional[Dict[str, Any]]) -> None:
        final_event = final_event or {}
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE runs
                SET status = ?, finished_at = ?, project_dir = ?, final_score = ?,
                    final_json = ?, updated_at = ?
                WHERE job_id = ?
                """,
                (
                    status,
                    finished_at,
                    final_event.get("project_dir"),
                    final_event.get("final_score"),
                    json.dumps(final_event, ensure_ascii=False, default=str) if final_event else None,
                    finished_at,
                    job_id,
                ),
            )

    def list_runs(self, limit: int = 20) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 100))
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT job_id, task, language, status, created_at, finished_at,
                       project_dir, final_score,
                       CASE
                           WHEN finished_at IS NOT NULL THEN ROUND(MAX(0, finished_at - created_at), 2)
                           ELSE NULL
                       END AS duration_s
                FROM runs ORDER BY created_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_run(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock, self._connect() as conn:
            run = conn.execute("SELECT * FROM runs WHERE job_id = ?", (job_id,)).fetchone()
            if not run:
                return None
            events = conn.execute(
                "SELECT event_type, payload_json, created_at FROM run_events WHERE job_id = ? ORDER BY id",
                (job_id,),
            ).fetchall()
        result = dict(run)
        if result.get("finished_at") is not None:
            result["duration_s"] = round(max(0, result["finished_at"] - result["created_at"]), 2)
        else:
            result["duration_s"] = None
        for key in ("plan_json", "final_json"):
            if result.get(key):
                result[key[:-5]] = json.loads(result.pop(key))
            else:
                result[key[:-5]] = None
                result.pop(key, None)
        result["events"] = [
            {"type": row["event_type"], "created_at": row["created_at"],
             "payload": json.loads(row["payload_json"])}
            for row in events
        ]
        return result
