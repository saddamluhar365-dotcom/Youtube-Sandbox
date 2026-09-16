from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .db import Database


@dataclass(frozen=True)
class CompetitorChannel:
    channel_id: str | None
    channel_handle: str | None
    channel_url: str | None
    title: str
    niche: str | None = None
    language: str | None = None
    scale_band: str | None = None
    discovery_source: str = "unknown"


class CompetitorStore:
    """Persistent peer-channel registry; discovery evidence stays attributable."""

    def __init__(self, db: Database):
        self.db = db
        self.db.initialize()

    def save(self, competitor: CompetitorChannel) -> str:
        if not competitor.title.strip():
            raise ValueError("competitor title is required")
        now = datetime.now(timezone.utc).isoformat()
        payload = {
            "channel_id": competitor.channel_id,
            "channel_handle": competitor.channel_handle,
            "channel_url": competitor.channel_url,
            "title": competitor.title.strip(),
            "niche": competitor.niche,
            "language": competitor.language,
            "scale_band": competitor.scale_band,
            "discovery_source": competitor.discovery_source,
        }
        data_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest()

        with self.db.connection() as conn:
            row = None
            if competitor.channel_id:
                row = conn.execute(
                    "SELECT competitor_id FROM competitors WHERE channel_id = ? LIMIT 1",
                    (competitor.channel_id,),
                ).fetchone()
            if row is None and competitor.channel_handle:
                row = conn.execute(
                    "SELECT competitor_id FROM competitors WHERE channel_handle = ? LIMIT 1",
                    (competitor.channel_handle,),
                ).fetchone()

            competitor_id = str(row[0]) if row else "competitor_" + uuid.uuid4().hex
            if row:
                conn.execute(
                    """UPDATE competitors SET channel_id=?, channel_handle=?, channel_url=?, title=?,
                       niche=?, language=?, scale_band=?, discovery_source=?, data_hash=?, last_seen_at=?
                       WHERE competitor_id=?""",
                    (*payload.values(), data_hash, now, competitor_id),
                )
            else:
                conn.execute(
                    """INSERT INTO competitors
                       (competitor_id, channel_id, channel_handle, channel_url, title, niche, language,
                        scale_band, discovery_source, data_hash, first_seen_at, last_seen_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (competitor_id, *payload.values(), data_hash, now, now),
                )
        return competitor_id

    def list_all(self) -> list[dict[str, Any]]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM competitors ORDER BY last_seen_at DESC, competitor_id"
            ).fetchall()
        return [dict(row) for row in rows]
