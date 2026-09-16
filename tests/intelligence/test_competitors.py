from pathlib import Path

from app.intelligence.competitors import CompetitorChannel, CompetitorStore
from app.intelligence.db import Database


def test_competitor_store_upserts_by_channel_id(tmp_path: Path) -> None:
    store = CompetitorStore(Database(tmp_path / "competitors.db"))
    first = store.save(
        CompetitorChannel(
            channel_id="UCpeer123456789012345678",
            channel_handle="@peer",
            channel_url="https://www.youtube.com/@peer",
            title="Peer Food",
            niche="food shorts",
            language="Hindi",
            scale_band="comparable",
            discovery_source="tavily",
        )
    )
    second = store.save(
        CompetitorChannel(
            channel_id="UCpeer123456789012345678",
            channel_handle="@peer",
            channel_url="https://www.youtube.com/@peer",
            title="Peer Food Updated",
            niche="food shorts",
            language="Hindi",
            scale_band="comparable",
            discovery_source="tavily",
        )
    )

    assert first == second
    rows = store.list_all()
    assert len(rows) == 1
    assert rows[0]["title"] == "Peer Food Updated"


def test_competitor_store_allows_discovery_without_channel_id(tmp_path: Path) -> None:
    store = CompetitorStore(Database(tmp_path / "competitors.db"))
    competitor_id = store.save(
        CompetitorChannel(
            channel_id=None,
            channel_handle="@discovered",
            channel_url="https://www.youtube.com/@discovered",
            title="Discovered Food",
            niche="food shorts",
            language="Hindi",
            scale_band="comparable",
            discovery_source="tavily",
        )
    )

    assert competitor_id
    assert store.list_all()[0]["channel_id"] is None
