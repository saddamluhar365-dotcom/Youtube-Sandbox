from __future__ import annotations

from typing import Any

from app.intelligence.db import Database

from .ingest import PublicChannelIngestor
from .models import ChannelIdentity, ChannelSyncResult


class ChannelStore:
    """Persistence facade for channel snapshots and incremental sync state."""

    def __init__(self, db: Database):
        self.db = db
        self.db.initialize()
        self._ingestor = PublicChannelIngestor(db)

    def save_snapshot(self, identity: ChannelIdentity, payload: dict[str, Any]) -> str:
        """Persist a public snapshot and return its reused or newly-created snapshot ID."""
        return self._ingestor.ingest(identity, payload).snapshot_id

    def save_and_sync(self, identity: ChannelIdentity, payload: dict[str, Any]) -> ChannelSyncResult:
        """Persist a payload and return the full incremental classification."""
        return self._ingestor.ingest(identity, payload)

    def get_latest_snapshot(self, channel_id: str) -> dict[str, Any] | None:
        with self.db.connection() as conn:
            row = conn.execute(
                """
                SELECT snapshot_id, channel_id, snapshot_version, data_hash, video_count
                FROM channel_snapshots
                WHERE channel_id = ?
                ORDER BY snapshot_version DESC
                LIMIT 1
                """,
                (channel_id,),
            ).fetchone()
            if row is None:
                return None
            return {
                "snapshot_id": row[0],
                "channel_id": row[1],
                "snapshot_version": int(row[2]),
                "data_hash": row[3],
                "video_count": int(row[4]),
            }

    def get_video_hash(self, video_id: str) -> str | None:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT data_hash FROM channel_videos WHERE video_id = ?",
                (video_id,),
            ).fetchone()
            return None if row is None else str(row[0])

    def get_sync_metadata(self, channel_id: str) -> dict[str, Any] | None:
        with self.db.connection() as conn:
            row = conn.execute(
                """
                SELECT channel_handle, channel_url, last_seen_at, last_sync_at, data_hash
                FROM channel_profiles
                WHERE channel_id = ?
                """,
                (channel_id,),
            ).fetchone()
            if row is None:
                return None
            return {
                "channel_handle": row[0],
                "channel_url": row[1],
                "last_seen_at": row[2],
                "last_sync_at": row[3],
                "data_hash": row[4],
            }
