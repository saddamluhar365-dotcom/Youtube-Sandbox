from __future__ import annotations

from app.competitors.discovery import CompetitorDiscovery, DiscoveryCandidate


def test_discovery_selects_comparable_peers_without_global_ranking() -> None:
    candidates = (
        DiscoveryCandidate("UC1", "@foodone", "Food One", "food village", "hi", "shorts", "mid", "tavily"),
        DiscoveryCandidate("UC2", "@foodtwo", "Food Two", "food village", "hi", "shorts", "mid", "tavily"),
        DiscoveryCandidate("UC3", "@gaming", "Gaming", "gaming", "hi", "shorts", "large", "tavily"),
    )

    peers = CompetitorDiscovery().discover(
        niche="food village",
        language="hi",
        format_type="shorts",
        scale_band="mid",
        candidates=candidates,
        limit=5,
    )

    assert [peer.channel_id for peer in peers] == ["UC1", "UC2"]
    assert all(peer.discovery_source == "tavily" for peer in peers)
    assert all(peer.scale_band == "mid" for peer in peers)


def test_discovery_returns_no_peers_when_comparable_evidence_is_missing() -> None:
    candidate = DiscoveryCandidate("UC1", "@foodone", "Food One", None, None, None, None, "tavily")

    peers = CompetitorDiscovery().discover(
        niche="food village",
        language="hi",
        format_type="shorts",
        scale_band="mid",
        candidates=(candidate,),
    )

    assert peers == ()
