from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.intelligence.db import Database

from .models import ChannelIdentity, ChannelSyncResult, PublicChannel, PublicVideo


def _hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class PublicChannelIngestor:
    """Persist normalized public channel payloads with incremental snapshot reuse."""

    def __init__(self, db: Database):
        self.db = db
        self.db.initialize()

    def ingest(self, identity: ChannelIdentity, payload: dict[str, Any]) -> ChannelSyncResult:
        videos = tuple(self._video(item) for item in payload.get("videos", []))
        channel_payload = {
            "channel_id": identity.channel_id,
            "handle": identity.channel_handle,
            "url": identity.channel_url,
            "title": payload.get("title") or identity.title,
            "description": payload.get("description", ""),
            "country": payload.get("country"),
            "custom_url": payload.get("custom_url"),
            "published_at": payload.get("published_at"),
            "videos": [self._video_dict(video) for video in videos],
        }
        channel_hash = _hash(channel_payload)
        video_hashes = {video.video_id: _hash(self._video_dict(video)) for video in videos}
        now = _utcnow()

        with self.db.connection() as conn:
            old_channel = conn.execute(
                "SELECT data_hash FROM channel_profiles WHERE channel_id = ?",
                (identity.channel_id,),
            ).fetchone()
            channel_changed = old_channel is None or old_channel[0] != channel_hash

            classifications = self._classify_videos(conn, video_hashes)
            has_video_changes = bool(classifications[0] or classifications[1])
            snapshot_needed = channel_changed or has_video_changes

            conn.execute(
                """
                INSERT INTO channel_profiles
                (channel_id, channel_handle, channel_url, title, description, country,
                 custom_url, published_at, last_seen_at, last_sync_at, data_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(channel_id) DO UPDATE SET
                    channel_handle=excluded.channel_handle,
                    channel_url=excluded.channel_url,
                    title=excluded.title,
                    description=excluded.description,
                    country=excluded.country,
                    custom_url=excluded.custom_url,
                    published_at=excluded.published_at,
                    last_seen_at=excluded.last_seen_at,
                    last_sync_at=excluded.last_sync_at,
                    data_hash=excluded.data_hash
                """,
                (
                    identity.channel_id,
                    identity.channel_handle,
                    identity.channel_url,
                    channel_payload["title"],
                    channel_payload["description"],
                    channel_payload["country"],
                    channel_payload["custom_url"],
                    channel_payload["published_at"],
                    now,
                    now,
                    channel_hash,
                ),
            )

            latest_snapshot = conn.execute(
                """
                SELECT snapshot_id, snapshot_version
                FROM channel_snapshots
                WHERE channel_id = ?
                ORDER BY snapshot_version DESC
                LIMIT 1
                """,
                (identity.channel_id,),
            ).fetchone()

            if snapshot_needed or latest_snapshot is None:
                snapshot_version = int(latest_snapshot[1] if latest_snapshot else 0) + 1
                snapshot_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO channel_snapshots
                    (snapshot_id, channel_id, snapshot_version, data_hash, video_count)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (snapshot_id, identity.channel_id, snapshot_version, channel_hash, len(videos)),
                )
            else:
                snapshot_id = str(latest_snapshot[0])
                snapshot_version = int(latest_snapshot[1])

            new_ids, changed_ids, unchanged_ids = classifications
            for video in videos:
                conn.execute(
                    """
                    INSERT INTO channel_videos
                    (video_id, channel_id, snapshot_id, title, description, published_at,
                     duration_seconds, is_short, view_count, like_count, comment_count,
                     thumbnail_url, data_hash, last_seen_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(video_id) DO UPDATE SET
                        snapshot_id=excluded.snapshot_id,
                        title=excluded.title,
                        description=excluded.description,
                        published_at=excluded.published_at,
                        duration_seconds=excluded.duration_seconds,
                        is_short=excluded.is_short,
                        view_count=excluded.view_count,
                        like_count=excluded.like_count,
                        comment_count=excluded.comment_count,
                        thumbnail_url=excluded.thumbnail_url,
                        data_hash=excluded.data_hash,
                        last_seen_at=excluded.last_seen_at
                    """,
                    (
                        video.video_id,
                        identity.channel_id,
                        snapshot_id,
                        video.title,
                        video.description,
                        video.published_at,
                        video.duration_seconds,
                        int(video.is_short),
                        video.view_count,
                        video.like_count,
                        video.comment_count,
                        video.thumbnail_url,
                        video_hashes[video.video_id],
                        now,
                    ),
                )

        channel = PublicChannel(
            identity=identity,
            description=payload.get("description", ""),
            country=payload.get("country"),
            custom_url=payload.get("custom_url"),
            published_at=payload.get("published_at"),
            videos=videos,
        )
        return ChannelSyncResult(
            channel=channel,
            snapshot_id=snapshot_id,
            snapshot_version=snapshot_version,
            new_video_ids=tuple(new_ids),
            changed_video_ids=tuple(changed_ids),
            unchanged_video_ids=tuple(unchanged_ids),
            private_analytics_available=False,
            metadata={
                "channel_changed": channel_changed,
                "snapshot_created": snapshot_needed or latest_snapshot is None,
                "incremental_noop": not (snapshot_needed or latest_snapshot is None),
                "public_only": True,
            },
        )

    @staticmethod
    def _classify_videos(conn: Any, video_hashes: dict[str, str]) -> tuple[list[str], list[str], list[str]]:
        new_ids: list[str] = []
        changed_ids: list[str] = []
        unchanged_ids: list[str] = []
        for video_id, data_hash in video_hashes.items():
            old_video = conn.execute(
                "SELECT data_hash FROM channel_videos WHERE video_id = ?",
                (video_id,),
            ).fetchone()
            if old_video is None:
                new_ids.append(video_id)
            elif old_video[0] == data_hash:
                unchanged_ids.append(video_id)
            else:
                changed_ids.append(video_id)
        return new_ids, changed_ids, unchanged_ids

    @staticmethod
    def _video(item: dict[str, Any]) -> PublicVideo:
        video_id = str(item.get("video_id", "")).strip()
        title = str(item.get("title", "")).strip()
        if not video_id or not title:
            raise ValueError("public video requires video_id and title")
        return PublicVideo(
            video_id=video_id,
            title=title,
            description=str(item.get("description", "")),
            published_at=item.get("published_at"),
            duration_seconds=item.get("duration_seconds"),
            view_count=item.get("view_count"),
            like_count=item.get("like_count"),
            comment_count=item.get("comment_count"),
            thumbnail_url=item.get("thumbnail_url"),
            is_short=bool(item.get("is_short", False)),
        )

    @staticmethod
    def _video_dict(video: PublicVideo) -> dict[str, Any]:
        return {
            "video_id": video.video_id,
            "title": video.title,
            "description": video.description,
            "published_at": video.published_at,
            "duration_seconds": video.duration_seconds,
            "view_count": video.view_count,
            "like_count": video.like_count,
            "comment_count": video.comment_count,
            "thumbnail_url": video.thumbnail_url,
            "is_short": video.is_short,
        }
