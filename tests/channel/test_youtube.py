from __future__ import annotations

from app.channel.youtube import YouTubePublicCollector


class FakeYoutubeDL:
    def __init__(self, options):
        self.options = options

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def extract_info(self, url, download=False):
        assert download is False
        assert url.endswith("/videos")
        return {
            "title": "Test Food Channel",
            "description": "Public channel",
            "channel": "Test Food Channel",
            "entries": [
                {
                    "id": "abc123",
                    "title": "Village Chutney",
                    "description": "A public description",
                    "upload_date": "20260916",
                    "duration": 10,
                    "view_count": 1234,
                    "like_count": 55,
                    "comment_count": 7,
                    "thumbnail": "https://img.example/abc.jpg",
                }
            ],
        }


def test_collector_normalizes_public_video_metadata() -> None:
    collector = YouTubePublicCollector(ytdl_factory=FakeYoutubeDL)
    payload = collector.collect("UC12345678901234567890")
    assert payload["title"] == "Test Food Channel"
    assert payload["videos"][0]["video_id"] == "abc123"
    assert payload["videos"][0]["is_short"] is True
    assert payload["videos"][0]["view_count"] == 1234


def test_collector_rejects_missing_channel_id() -> None:
    collector = YouTubePublicCollector(ytdl_factory=FakeYoutubeDL)
    try:
        collector.collect("")
    except ValueError as exc:
        assert "channel id" in str(exc).lower()
    else:
        raise AssertionError("missing channel id was accepted")
