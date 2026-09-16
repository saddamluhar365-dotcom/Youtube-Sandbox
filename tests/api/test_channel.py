from __future__ import annotations

from fastapi.testclient import TestClient

from app.channel.models import ChannelIdentity, ChannelSyncResult, PublicChannel


class FakeSyncProvider:
    def sync(self, handle: str) -> ChannelSyncResult:
        identity = ChannelIdentity(
            channel_id="UC12345678901234567890",
            channel_handle=handle,
            channel_url=f"https://www.youtube.com/{handle}",
            title="API Demo",
        )
        return ChannelSyncResult(
            channel=PublicChannel(identity=identity, videos=()),
            snapshot_id="snapshot-api",
            snapshot_version=1,
            new_video_ids=(),
            changed_video_ids=(),
            unchanged_video_ids=(),
            private_analytics_available=False,
            metadata={"public_only": True},
        )


def test_channel_sync_endpoint_accepts_handle_and_returns_safe_metadata(monkeypatch):
    from app import main
    from app.agent.master import MasterAgent

    monkeypatch.setattr(main, "master_agent", MasterAgent(sync_provider=FakeSyncProvider()))
    client = TestClient(main.create_app())

    response = client.post("/api/v1/channels/sync", json={"handle": "@demo"})

    assert response.status_code == 200
    body = response.json()
    assert body["channel_id"] == "UC12345678901234567890"
    assert body["private_analytics_available"] is False
    assert "api_key" not in response.text.lower()


def test_channel_get_returns_404_for_unknown_channel(monkeypatch):
    from app import main
    from app.agent.master import MasterAgent

    monkeypatch.setattr(main, "master_agent", MasterAgent())
    client = TestClient(main.create_app())

    response = client.get("/api/v1/channels/@missing")

    assert response.status_code == 404
