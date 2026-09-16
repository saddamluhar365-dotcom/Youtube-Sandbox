from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .schema import SCHEMA_SQL, SCHEMA_VERSION


class Database:
    """Small, local-first SQLite manager used by the intelligence layer."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self._memory = str(path) == ":memory:"
        self._memory_uri = f"file:youtube_sandbox_{id(self)}?mode=memory&cache=shared"
        self._keeper: sqlite3.Connection | None = None
        if self._memory:
            self._keeper = sqlite3.connect(self._memory_uri, uri=True, timeout=30.0)

    def initialize(self) -> None:
        if not self._memory:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as conn:
            conn.executescript(SCHEMA_SQL)
            current = conn.execute(
                "SELECT MAX(version) FROM schema_migrations"
            ).fetchone()[0]
            if current is None:
                conn.execute(
                    "INSERT INTO schema_migrations(version) VALUES (?)",
                    (SCHEMA_VERSION,),
                )
            elif current < SCHEMA_VERSION:
                raise RuntimeError(
                    f"Database migration required: current={current}, "
                    f"application={SCHEMA_VERSION}"
                )

    def schema_version(self) -> int:
        if not self._memory and not self.path.exists():
            return 0
        with self.connection() as conn:
            row = conn.execute(
                "SELECT MAX(version) FROM schema_migrations"
            ).fetchone()
            return int(row[0] or 0)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        if not self._memory:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self.path, timeout=30.0)
        else:
            conn = sqlite3.connect(self._memory_uri, uri=True, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            if not self._memory:
                conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def close(self) -> None:
        if self._keeper is not None:
            self._keeper.close()
            self._keeper = None
