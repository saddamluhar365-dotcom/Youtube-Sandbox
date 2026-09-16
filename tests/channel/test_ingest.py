from pathlib import Path

from app.channel.ingest import PublicChannelIngestor
from app.channel.models import ChannelIdentity
from app.intelligence.db import Database


def _identity() -> ChannelIdentity:
    return ChannelIdentity("UC12345678901234567890", "@Reelios", "https://www.youtube.com/@Reelios")


def _payload(title: str = "Village Recipe", views: int = 1000) -> dict:
    return {
        "title": "Reelios",
        "description": "Food facts",
        "videos": [
            {
                "video_id": "abc123",
                "title": title,
                "description": "A short",
                "published_at": "2026-09-15T10:00:00Z",
                "duration_seconds": 90,
                "view_count": views,
                "like_count": 40,
                "comment_count": 3,
                "is_short": True,
            }
        ],
    }


def test_public_ingestor_persists_channel_and_video_hashes(tmp_path: Path) -> None:
    db = Database(tmp_path / "memory.db")
    result = PublicChannelIngestor(db).ingest(_identity(), _payload())

    assert result.channel.identity.channel_id == _identity().channel_id
    assert result.snapshot_version == 1
    assert result.new_video_ids == ("abc123",)
    assert result.metadata["snapshot_created"] is True

    with db.connection() as conn:
        channel_hash = conn.execute("SELECT data_hash FROM channel_profiles").fetchone()[0]
        video_hash = conn.execute("SELECT data_hash FROM channel_videos").fetchone()[0]
    assert len(channel_hash) == 64
    assert len(video_hash) == 64


def test_public_ingestor_reuses_snapshot_for_unchanged_payload(tmp_path: Path) -> None:
    db = Database(tmp_path / "memory.db")
    ingestor = PublicChannelIngestor(db)
    first = ingestor.ingest(_identity(), _payload())
    second = ingestor.ingest(_identity(), _payload())

    assert second.unchanged_video_ids == ("abc123",)
    assert second.new_video_ids == ()
    assert second.changed_video_ids == ()
    assert second.snapshot_id == first.snapshot_id
    assert second.snapshot_version == first.snapshot_version == 1
    assert second.metadata["incremental_noop"] is True

    with db.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM channel_snapshots").fetchone()[0] == 1


def test_public_ingestor_creates_snapshot_for_changed_video(tmp_path: Path) -> None:
    db = Database(tmp_path / "memory.db")
    ingestor = PublicChannelIngestor(db)
    first = ingestor.ingest(_identity(), _payload(views=1000))
    second = ingestor.ingest(_identity(), _payload(views=1500))

    assert second.changed_video_ids == ("abc123",)
    assert second.snapshot_id != first.snapshot_id
    assert second.snapshot_version == 2
    assert second.metadata["snapshot_created"] is True

    with db.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM channel_snapshots").fetchone()[0] == 2


def test_public_ingestor_adds_new_video_incrementally(tmp_path: Path) -> None:
    db = Database(tmp_path / "memory.db")
    ingestor = PublicChannelIngestor(db)
    first = ingestor.ingest(_identity(), _payload())
    payload = _payload()
    payload["videos"].append(
        {
            "video_id": "def456",
            "title": "New Village Recipe",
            "published_at": "2026-09-16T10:00:00Z",
            "duration_seconds": 90,
            "view_count": 10,
            "like_count": 1,
            "comment_count": 0,
            "is_short": True,
        }
    )
    second = ingestor.ingest(_identity(), payload)

    assert second.new_video_ids == ("def456",)
    assert second.snapshot_id != first.snapshot_id
    assert second.snapshot_version == 2
    assert second.unchanged_video_ids == ("abc123",)

    with db.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM channel_videos").fetchone()[0] == 2
