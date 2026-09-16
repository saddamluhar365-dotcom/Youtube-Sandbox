from pathlib import Path

from app.channel.ingest import PublicChannelIngestor
from app.channel.models import ChannelIdentity
from app.intelligence.db import Database


def test_public_ingestor_persists_channel_and_video_hashes(tmp_path: Path) -> None:
    db = Database(tmp_path / "memory.db")
    identity = ChannelIdentity("UC12345678901234567890", "@Reelios", "https://www.youtube.com/@Reelios")
    payload = {
        "title": "Reelios",
        "description": "Food facts",
        "videos": [
            {
                "video_id": "abc123",
                "title": "Village Recipe",
                "description": "A short",
                "published_at": "2026-09-15T10:00:00Z",
                "duration_seconds": 90,
                "view_count": 1000,
                "like_count": 40,
                "comment_count": 3,
                "is_short": True,
            }
        ],
    }
    result = PublicChannelIngestor(db).ingest(identity, payload)
    assert result.channel.identity.channel_id == identity.channel_id
    assert result.snapshot_version == 1
    assert result.new_video_ids == ("abc123",)

    with db.connection() as conn:
        channel_hash = conn.execute("SELECT data_hash FROM channel_profiles").fetchone()[0]
        video_hash = conn.execute("SELECT data_hash FROM channel_videos").fetchone()[0]
    assert len(channel_hash) == 64
    assert len(video_hash) == 64


def test_public_ingestor_marks_unchanged_video(tmp_path: Path) -> None:
    db = Database(tmp_path / "memory.db")
    identity = ChannelIdentity("UC12345678901234567890", "@Reelios", "https://www.youtube.com/@Reelios")
    payload = {"title": "Reelios", "videos": [{"video_id": "abc123", "title": "Same"}]}
    ingestor = PublicChannelIngestor(db)
    ingestor.ingest(identity, payload)
    result = ingestor.ingest(identity, payload)
    assert result.unchanged_video_ids == ("abc123",)
    assert result.new_video_ids == ()
