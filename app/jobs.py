from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from threading import Lock
from .models import JobState

_ALLOWED = {
    JobState.QUEUED: {JobState.PLANNING, JobState.CANCELLED},
    JobState.PLANNING: {JobState.GENERATING_CLIPS, JobState.FAILED, JobState.CANCELLED},
    JobState.GENERATING_CLIPS: {JobState.GENERATING_AUDIO, JobState.FAILED, JobState.CANCELLED},
    JobState.GENERATING_AUDIO: {JobState.ASSEMBLING, JobState.FAILED, JobState.CANCELLED},
    JobState.ASSEMBLING: {JobState.VALIDATING, JobState.FAILED, JobState.CANCELLED},
    JobState.VALIDATING: {JobState.COMPLETED, JobState.FAILED},
    JobState.COMPLETED: set(), JobState.FAILED: set(), JobState.CANCELLED: set(),
}


class JobStore:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db = data_dir / "jobs.db"
        self._lock = Lock()
        with sqlite3.connect(self.db) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, topic TEXT NOT NULL, state TEXT NOT NULL, progress INTEGER NOT NULL, error TEXT, validation TEXT, created REAL DEFAULT (unixepoch()), updated REAL DEFAULT (unixepoch()))")

    def create(self, topic: str) -> dict:
        job = {"id": uuid.uuid4().hex, "topic": topic, "state": JobState.QUEUED.value, "progress": 0, "error": None, "validation": None}
        with self._lock, sqlite3.connect(self.db) as conn:
            conn.execute("INSERT INTO jobs(id,topic,state,progress,error,validation) VALUES(?,?,?,?,?,?)", (job["id"], topic, job["state"], 0, None, None))
        return job

    def get(self, job_id: str) -> dict | None:
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT id,topic,state,progress,error,validation FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row: return None
        item = dict(row)
        item["validation"] = json.loads(item["validation"]) if item["validation"] else None
        return item

    def transition(self, job_id: str, state: JobState) -> dict:
        current = self.get(job_id)
        if not current: raise KeyError(job_id)
        old = JobState(current["state"])
        if state not in _ALLOWED[old]: raise ValueError(f"invalid transition {old.value} -> {state.value}")
        with self._lock, sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE jobs SET state=?, updated=unixepoch() WHERE id=?", (state.value, job_id))
        return self.get(job_id)

    def progress(self, job_id: str, value: int) -> None:
        with self._lock, sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE jobs SET progress=?, updated=unixepoch() WHERE id=?", (max(0, min(100, value)), job_id))

    def fail(self, job_id: str, error: str) -> None:
        with self._lock, sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE jobs SET state=?, error=?, updated=unixepoch() WHERE id=?", (JobState.FAILED.value, error[:1000], job_id))

    def validation(self, job_id: str, value: dict) -> None:
        with self._lock, sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE jobs SET validation=?, updated=unixepoch() WHERE id=?", (json.dumps(value), job_id))
