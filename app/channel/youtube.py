from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable


class YouTubePublicCollector:
    """Collect public channel/video metadata without downloading media."""

    def __init__(self, ytdl_factory: Callable[..., Any] | None = None):
        if ytdl_factory is None:
            from yt_dlp import YoutubeDL
            ytdl_factory = YoutubeDL
        self._factory = ytdl_factory

    def collect(self, channel_id: str) -> dict[str, Any]:
        channel_id = str(channel_id).strip()
        if not channel_id:
            raise ValueError("channel id is required")
        if not channel_id.startswith("UC"):
            raise ValueError("channel id must start with UC")

        options = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": True,
            "ignoreerrors": True,
            "no_warnings": True,
        }
        url = f"https://www.youtube.com/channel/{channel_id}/videos"
        with self._factory(options) as ydl:
            info = ydl.extract_info(url, download=False)

        if not isinstance(info, dict):
            raise RuntimeError("YouTube returned no public channel metadata")
        entries = info.get("entries") or []
        videos = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            video = self._video(entry)
            if video is not None:
                videos.append(video)
        return {
            "title": str(info.get("title") or info.get("channel") or "").strip(),
            "description": str(info.get("description") or ""),
            "videos": videos,
        }

    @staticmethod
    def _video(entry: dict[str, Any]) -> dict[str, Any] | None:
        video_id = str(entry.get("id") or "").strip()
        title = str(entry.get("title") or "").strip()
        if not video_id or not title:
            return None
        duration = entry.get("duration")
        duration_value = float(duration) if isinstance(duration, (int, float)) else None
        published_at = YouTubePublicCollector._date(entry.get("upload_date"))
        return {
            "video_id": video_id,
            "title": title,
            "description": str(entry.get("description") or ""),
            "published_at": published_at,
            "duration_seconds": duration_value,
            "view_count": YouTubePublicCollector._integer(entry.get("view_count")),
            "like_count": YouTubePublicCollector._integer(entry.get("like_count")),
            "comment_count": YouTubePublicCollector._integer(entry.get("comment_count")),
            "thumbnail_url": entry.get("thumbnail"),
            "is_short": duration_value is not None and duration_value <= 60,
        }

    @staticmethod
    def _integer(value: Any) -> int | None:
        return int(value) if isinstance(value, (int, float)) and value >= 0 else None

    @staticmethod
    def _date(value: Any) -> str | None:
        text = str(value or "").strip()
        if len(text) != 8 or not text.isdigit():
            return None
        try:
            return datetime.strptime(text, "%Y%m%d").replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            return None
