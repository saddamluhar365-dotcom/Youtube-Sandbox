from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from statistics import median

from app.channel.analyzer import ChannelAnalysis


@dataclass(frozen=True)
class GapObservation:
    dimension: str
    description: str
    evidence_type: str = "observed_data"
    evidence: dict[str, object] = field(default_factory=dict)
    confidence: float = 0.0
    sample_size: int = 0


@dataclass(frozen=True)
class GapHypothesis:
    hypothesis_type: str
    statement: str
    evidence: tuple[str, ...] = ()
    confidence: float = 0.0
    validation_status: str = "pending"


@dataclass(frozen=True)
class GapReport:
    status: str
    owned_channel_id: str
    peer_count: int
    observations: tuple[GapObservation, ...] = ()
    hypotheses: tuple[GapHypothesis, ...] = ()


class GapAnalyzer:
    """Compare an owned channel with a comparable peer group using public data only."""

    def compare(
        self,
        owned: ChannelAnalysis,
        peers: tuple[ChannelAnalysis, ...],
    ) -> GapReport:
        usable_peers = tuple(peer for peer in peers if peer.video_count > 0)
        if owned.video_count == 0 or not usable_peers:
            return GapReport(
                status="INSUFFICIENT_DATA",
                owned_channel_id=owned.channel_id,
                peer_count=len(usable_peers),
            )

        observations: list[GapObservation] = []
        hypotheses: list[GapHypothesis] = []
        peer_count = len(usable_peers)

        owned_topics = {name for name, _ in owned.topics}
        peer_topic_counts: Counter[str] = Counter()
        for peer in usable_peers:
            peer_topic_counts.update(name for name, _ in peer.topics)
        missing_topics = tuple(name for name, count in peer_topic_counts.most_common() if name not in owned_topics and count >= 1)[:5]
        if missing_topics:
            observations.append(
                GapObservation(
                    dimension="topic_coverage",
                    description="Peer channels expose recurring public topic labels that are not observed in the owned channel sample.",
                    evidence={"peer_topics_not_observed": missing_topics},
                    confidence=round(min(1.0, len(missing_topics) / 5), 4),
                    sample_size=owned.video_count + sum(peer.video_count for peer in usable_peers),
                )
            )
            hypotheses.append(
                GapHypothesis(
                    hypothesis_type="topic_test",
                    statement="Some peer-observed topics may be candidates for controlled content experiments on the owned channel.",
                    evidence=missing_topics,
                    confidence=0.5,
                )
            )

        owned_hooks = set(owned.hooks)
        peer_hooks = Counter(hook for peer in usable_peers for hook in peer.hooks)
        missing_hooks = tuple(hook for hook, _ in peer_hooks.most_common() if hook not in owned_hooks)[:5]
        if missing_hooks:
            observations.append(
                GapObservation(
                    dimension="hook_pattern_coverage",
                    description="Peer channels contain public title hook patterns that are not observed in the owned channel sample.",
                    evidence={"peer_hooks_not_observed": missing_hooks},
                    confidence=round(min(1.0, len(missing_hooks) / 5), 4),
                    sample_size=owned.video_count + sum(peer.video_count for peer in usable_peers),
                )
            )
            hypotheses.append(
                GapHypothesis(
                    hypothesis_type="hook_test",
                    statement="Unobserved peer hook patterns may be worth testing while preserving the owned channel's content identity.",
                    evidence=missing_hooks,
                    confidence=0.5,
                )
            )

        owned_format = self._dominant_format(owned.formats)
        peer_formats = tuple(self._dominant_format(peer.formats) for peer in usable_peers)
        peer_format_counts = Counter(value for value in peer_formats if value is not None)
        if owned_format and peer_format_counts:
            peer_mode, peer_mode_count = peer_format_counts.most_common(1)[0]
            if peer_mode != owned_format:
                observations.append(
                    GapObservation(
                        dimension="duration_profile",
                        description="The dominant public duration bucket differs between the owned channel and the comparable peer group.",
                        evidence={
                            "owned_dominant_bucket": owned_format,
                            "peer_dominant_bucket": peer_mode,
                            "peer_channels_with_bucket": peer_mode_count,
                        },
                        confidence=round(peer_mode_count / peer_count, 4),
                        sample_size=owned.video_count + sum(peer.video_count for peer in usable_peers),
                    )
                )
                hypotheses.append(
                    GapHypothesis(
                        hypothesis_type="duration_test",
                        statement="A controlled test of the peer group's observed duration profile may reveal whether format length changes audience response.",
                        evidence=(owned_format, peer_mode),
                        confidence=round(peer_mode_count / peer_count, 4),
                    )
                )

        owned_view_median = self._public_view_median(owned)
        peer_view_medians = tuple(self._public_view_median(peer) for peer in usable_peers)
        usable_peer_views = tuple(value for value in peer_view_medians if value is not None)
        if owned_view_median is not None and usable_peer_views:
            peer_median = median(usable_peer_views)
            observations.append(
                GapObservation(
                    dimension="public_view_distribution",
                    description="Public view-count medians are available for the owned channel and comparable peer sample; this is descriptive and not a quality ranking.",
                    evidence={
                        "owned_median_views": owned_view_median,
                        "peer_median_views": peer_median,
                        "peer_channels_with_view_data": len(usable_peer_views),
                    },
                    confidence=round(len(usable_peer_views) / peer_count, 4),
                    sample_size=owned.video_count + sum(peer.video_count for peer in usable_peers),
                )
            )

        return GapReport(
            status="observed",
            owned_channel_id=owned.channel_id,
            peer_count=peer_count,
            observations=tuple(observations),
            hypotheses=tuple(hypotheses),
        )

    @staticmethod
    def _dominant_format(formats: tuple[tuple[str, int], ...]) -> str | None:
        return formats[0][0] if formats else None

    @staticmethod
    def _public_view_median(analysis: ChannelAnalysis) -> int | None:
        values = getattr(analysis, "public_view_counts", ())
        if not values:
            return None
        return int(median(values))
