from __future__ import annotations

import re
from collections.abc import Callable

import httpx

from .models import ChannelIdentity

_HANDLE_RE = re.compile(r"^@[A-Za-z0-9._-]{3,30}$")
_CHANNEL_ID_RE = re.compile(r"(?:youtube\.com/)?channel/(UC[A-Za-z0-9_-]{20,})")
_ITEMPROP_RE = re.compile(r'<meta[^>]+itemprop=[\"\']channelId[\"\'][^>]+content=[\"\'](UC[A-Za-z0-9_-]+)[\"\']', re.I)
_CONTENT_FIRST_RE = re.compile(r'<meta[^>]+content=[\"\'](UC[A-Za-z0-9_-]+)[\"\'][^>]+itemprop=[\"\']channelId[\"\']', re.I)
_TITLE_RE = re.compile(r'<title[^>]*>(.*?)</title>', re.I | re.S)


def normalize_handle(value: str) -> str:
    raw = value.strip()
    if not raw:
        raise ValueError("channel handle is required")

    if raw.startswith("http://") or raw.startswith("https://"):
        raw = raw.split("?", 1)[0].split("#", 1)[0].rstrip("/")
        match = re.search(r"youtube\.com/(@[A-Za-z0-9._-]{3,30})$", raw, re.I)
        if match:
            raw = match.group(1)
        else:
            channel_match = _CHANNEL_ID_RE.search(raw)
            if channel_match:
                return channel_match.group(1)
    elif raw.lower().startswith("youtube.com/"):
        raw = raw.split("?", 1)[0].rstrip("/")
        match = re.search(r"youtube\.com/(@[A-Za-z0-9._-]{3,30})$", raw, re.I)
        if match:
            raw = match.group(1)

    if _HANDLE_RE.fullmatch(raw):
        return raw
    if raw.startswith("UC") and len(raw) >= 20:
        return raw
    raise ValueError("invalid YouTube channel handle or channel URL")


class ChannelHandleResolver:
    """Resolve a public @handle to a channel ID without inventing identity data."""

    def __init__(self, fetch_html: Callable[[str], str] | None = None):
        self._fetch_html = fetch_html or self._http_fetch

    def resolve(self, handle: str) -> ChannelIdentity:
        normalized = normalize_handle(handle)
        if normalized.startswith("UC"):
            return ChannelIdentity(
                channel_id=normalized,
                channel_handle="",
                channel_url=f"https://www.youtube.com/channel/{normalized}",
            )

        url = f"https://www.youtube.com/{normalized}"
        html = self._fetch_html(url)
        channel_id = self._extract_channel_id(html)
        if not channel_id:
            raise LookupError(
                f"YouTube did not expose a channel ID for {normalized}; no identity was fabricated"
            )
        title = self._extract_title(html)
        return ChannelIdentity(
            channel_id=channel_id,
            channel_handle=normalized,
            channel_url=url,
            title=title,
        )

    @staticmethod
    def _http_fetch(url: str) -> str:
        response = httpx.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 YouTube-Sandbox/1.0"},
            follow_redirects=True,
            timeout=30,
        )
        response.raise_for_status()
        return response.text

    @staticmethod
    def _extract_channel_id(html: str) -> str | None:
        for pattern in (_ITEMPROP_RE, _CONTENT_FIRST_RE):
            match = pattern.search(html)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def _extract_title(html: str) -> str | None:
        match = _TITLE_RE.search(html)
        if not match:
            return None
        title = re.sub(r"\s+", " ", match.group(1)).strip()
        return title or None
