from pathlib import Path

from app.intelligence.db import Database


def test_database_initializes_schema_idempotently(tmp_path: Path) -> None:
    db = Database(tmp_path / "memory.db")

    db.initialize()
    first_version = db.schema_version()
    assert first_version >= 1

    with db.connection() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert "schema_migrations" in tables
    assert "channel_profiles" in tables
    assert "channel_snapshots" in tables
    assert "channel_videos" in tables
    assert "recipes" in tables
    assert "knowledge_records" in tables
    assert "creative_projects" in tables

    db.initialize()
    assert db.schema_version() == first_version


def test_database_connection_enables_foreign_keys_and_wal(tmp_path: Path) -> None:
    db = Database(tmp_path / "memory.db")
    db.initialize()

    with db.connection() as conn:
        foreign_keys = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]

    assert foreign_keys == 1
    assert str(journal_mode).lower() == "wal"
