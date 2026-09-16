from __future__ import annotations

from app.channel.analyzer import ChannelAnalysis, ChannelAnalyzer
from app.channel.models import ChannelIdentity, PublicChannel, PublicVideo


def _channel(videos: tuple[PublicVideo, ...]) -> PublicChannel:
    return PublicChannel(
        identity=ChannelIdentity(
            channel_id="UC12345678901234567890",
            channel_handle="@demo",
            channel_url="https://youtube.com/@demo",
            title="Demo Channel",
        ),
        description="Village food stories",
        videos=videos,
    )


def test_analyzer_extracts_observed_patterns_without_private_metrics() -> None:
    channel = _channel(
        (
            PublicVideo("v1", "Village Aloo Story", "#potato #village", duration_seconds=60, view_count=1000),
            PublicVideo("v2", "Village Tomato Story", "#tomato #village", duration_seconds=90, view_count=500),
        )
    )

    result = ChannelAnalyzer().analyze(channel)

    assert isinstance(result, ChannelAnalysis)
    assert result.status == "observed"
    assert result.video_count == 2
    assert result.private_analytics_available is False
    assert result.observations
    assert all(item.evidence_type == "observed_data" for item in result.observations)
    assert all("CTR" not in item.description and "retention" not in item.description.lower() for item in result.observations)
    assert result.hypotheses == ()


def test_analyzer_returns_insufficient_data_for_empty_channel() -> None:
    result = ChannelAnalyzer().analyze(_channel(()))

    assert result.status == "INSUFFICIENT_DATA"
    assert result.video_count == 0
    assert result.observations == ()
    assert result.hypotheses == ()
