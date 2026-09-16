from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ChannelIdentity:
    channel_id: str
    channel_handle: str
    channel_url: str
    title: str | None = None


@dataclass(frozen=True)
class PublicVideo:
    video_id: str
    title: str
    description: str = ""
    published_at: str | None = None
    duration_seconds: float | None = None
    view_count: int | None = None
    like_count: int | None = None
    comment_count: int | None = None
    thumbnail_url: str | None = None
    is_short: bool = False


@dataclass(frozen=True)
class PublicChannel:
    identity: ChannelIdentity
    description: str = ""
    country: str | None = None
    custom_url: str | None = None
    published_at: str | None = None
    videos: tuple[PublicVideo, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ChannelSyncResult:
    channel: PublicChannel
    snapshot_id: str
    snapshot_version: int
    new_video_ids: tuple[str, ...] = field(default_factory=tuple)
    changed_video_ids: tuple[str, ...] = field(default_factory=tuple)
    unchanged_video_ids: tuple[str, ...] = field(default_factory=tuple)
    private_analytics_available: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
