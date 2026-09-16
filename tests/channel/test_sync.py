from pathlib import Path

import pytest

from app.channel.ingest import PublicChannelIngestor
from app.channel.models import ChannelIdentity
from app.channel.store import ChannelStore
from app.channel.sync import ChannelSyncService
from app.intelligence.db import Database


class StubResolver:
    def __init__(self, identity: ChannelIdentity):
        self.identity = identity
        self.calls: list[str] = []

    def resolve(self, handle: str) -> ChannelIdentity:
        self.calls.append(handle)
        return self.identity


def test_sync_resolves_handle_and_collects_by_channel_id(tmp_path: Path) -> None:
    identity = ChannelIdentity("UC12345678901234567890", "@Reelios", "https://www.youtube.com/@Reelios")
    resolver = StubResolver(identity)
    collected: list[str] = []

    def collector(channel_id: str) -> dict:
        collected.append(channel_id)
        return {"title": "Reelios", "videos": [{"video_id": "abc", "title": "Recipe"}]}

    db = Database(tmp_path / "channel.db")
    service = ChannelSyncService(resolver, collector, PublicChannelIngestor(db))
    result = service.sync("@Reelios")

    assert resolver.calls == ["@Reelios"]
    assert collected == [identity.channel_id]
    assert result.new_video_ids == ("abc",)
    assert result.snapshot_version == 1


def test_sync_rejects_non_mapping_collector_output(tmp_path: Path) -> None:
    identity = ChannelIdentity("UC12345678901234567890", "@Reelios", "https://www.youtube.com/@Reelios")
    resolver = StubResolver(identity)
    db = Database(tmp_path / "channel.db")
    service = ChannelSyncService(resolver, lambda _: [], PublicChannelIngestor(db))

    with pytest.raises(TypeError, match="dictionary payload"):
        service.sync("@Reelios")


def test_store_exposes_latest_snapshot_and_sync_metadata(tmp_path: Path) -> None:
    db = Database(tmp_path / "channel.db")
    store = ChannelStore(db)
    identity = ChannelIdentity("UC12345678901234567890", "@Reelios", "https://www.youtube.com/@Reelios")
    result = store.save_and_sync(
        identity,
        {"title": "Reelios", "videos": [{"video_id": "abc", "title": "Recipe"}]},
    )

    snapshot = store.get_latest_snapshot(identity.channel_id)
    metadata = store.get_sync_metadata(identity.channel_id)

    assert snapshot is not None
    assert snapshot["snapshot_id"] == result.snapshot_id
    assert snapshot["snapshot_version"] == 1
    assert snapshot["video_count"] == 1
    assert metadata is not None
    assert metadata["channel_handle"] == "@Reelios"
    assert metadata["last_sync_at"]
    assert len(metadata["data_hash"]) == 64
    assert len(store.get_video_hash("abc")) == 64
    assert store.get_video_hash("missing") is None
