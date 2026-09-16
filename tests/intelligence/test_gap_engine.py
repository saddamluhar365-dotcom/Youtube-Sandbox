from pathlib import Path

from app.intelligence.db import Database
from app.intelligence.gap_engine import GapEngine


def test_gap_engine_builds_observed_patterns_without_fabrication(tmp_path: Path) -> None:
    db = Database(tmp_path / "memory.db")
    db.initialize()
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO channel_profiles(channel_id, channel_handle, title) VALUES (?, ?, ?)",
            ("UC12345678901234567890", "@Reelios", "Reelios"),
        )
        rows = [
            ("v1", "UC12345678901234567890", "Village Potato Story", "food", 90, 1000),
            ("v2", "UC12345678901234567890", "Village Potato ASMR", "food", 90, 3000),
            ("v3", "UC12345678901234567890", "Raw Mango Mystery", "food", 90, 500),
        ]
        for video_id, channel_id, title, topic, duration, views in rows:
            conn.execute(
                """INSERT INTO channel_videos
                (video_id, channel_id, title, duration_seconds, view_count, data_hash)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (video_id, channel_id, title, duration, views, video_id * 64),
            )
            conn.execute(
                "INSERT INTO video_topics(video_id, topic, confidence) VALUES (?, ?, ?)",
                (video_id, topic, 0.9),
            )

    result = GapEngine(db).analyze("UC12345678901234567890")

    assert result.status == "observed"
    assert result.sample_size == 3
    assert result.top_topics
    assert all(item.evidence_type == "observed_data" for item in result.patterns)
    assert all(item.sample_size == 3 for item in result.patterns)


def test_gap_engine_reports_insufficient_data(tmp_path: Path) -> None:
    db = Database(tmp_path / "memory.db")
    db.initialize()
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO channel_profiles(channel_id, channel_handle) VALUES (?, ?)",
            ("UC12345678901234567890", "@Reelios"),
        )

    result = GapEngine(db).analyze("UC12345678901234567890")
    assert result.status == "INSUFFICIENT_DATA"
    assert result.sample_size == 0
    assert result.patterns == ()
