from __future__ import annotations

from datetime import datetime, timezone

from app.channel.analyzer import ChannelAnalyzer
from app.channel.models import ChannelIdentity, PublicChannel, PublicVideo
from app.competitors.gap import GapAnalyzer


def _channel(channel_id: str, titles: tuple[str, ...], durations: tuple[float, ...]) -> PublicChannel:
    videos = tuple(
        PublicVideo(
            video_id=f"{channel_id}_{index}",
            title=title,
            published_at=datetime(2026, 9, 1 + index, tzinfo=timezone.utc).isoformat(),
            duration_seconds=duration,
            view_count=1000 * (index + 1),
            is_short=duration <= 60,
        )
        for index, (title, duration) in enumerate(zip(titles, durations))
    )
    return PublicChannel(
        identity=ChannelIdentity(
            channel_id=channel_id,
            channel_handle=f"@{channel_id.lower()}",
            channel_url=f"https://youtube.com/channel/{channel_id}",
            title=channel_id,
        ),
        videos=videos,
    )


def test_gap_analyzer_separates_observations_from_hypotheses() -> None:
    analyzer = ChannelAnalyzer()
    owned = analyzer.analyze(
        _channel("UCOWNED123456789012345", ("Village Food Secret", "Mango Chutney Recipe"), (45, 50))
    )
    peer_a = analyzer.analyze(
        _channel("UCPEER12345678901234567", ("Village Curry", "Village Chutney"), (90, 100))
    )
    peer_b = analyzer.analyze(
        _channel("UCPEER22345678901234567", ("Village Dal", "Village Curry"), (80, 95))
    )

    report = GapAnalyzer().compare(owned, (peer_a, peer_b))

    assert report.status == "observed"
    assert report.peer_count == 2
    assert report.observations
    assert all(item.evidence_type == "observed_data" for item in report.observations)
    assert all(item.sample_size > 0 for item in report.observations)
    assert all("ctr" not in item.description.lower() for item in report.observations)
    assert all("retention" not in item.description.lower() for item in report.observations)
    assert all(item.validation_status == "pending" for item in report.hypotheses)


def test_gap_analyzer_reports_insufficient_data_without_inventing_a_gap() -> None:
    analyzer = ChannelAnalyzer()
    owned = analyzer.analyze(_channel("UCOWNED123456789012345", (), ()))

    report = GapAnalyzer().compare(owned, ())

    assert report.status == "INSUFFICIENT_DATA"
    assert report.peer_count == 0
    assert report.observations == ()
    assert report.hypotheses == ()
