from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from .models import PublicChannel


@dataclass(frozen=True)
class ChannelObservation:
    pattern_type: str
    description: str
    evidence_type: str = "observed_data"
    evidence: dict[str, object] = field(default_factory=dict)
    confidence: float = 0.0
    sample_size: int = 0


@dataclass(frozen=True)
class ChannelHypothesis:
    hypothesis_type: str
    statement: str
    evidence: tuple[str, ...] = ()
    confidence: float = 0.0
    validation_status: str = "pending"


@dataclass(frozen=True)
class ChannelAnalysis:
    channel_id: str
    status: str
    video_count: int
    topics: tuple[tuple[str, int], ...] = ()
    pillars: tuple[tuple[str, int], ...] = ()
    hooks: tuple[str, ...] = ()
    formats: tuple[tuple[str, int], ...] = ()
    recipes: tuple[str, ...] = ()
    observations: tuple[ChannelObservation, ...] = ()
    hypotheses: tuple[ChannelHypothesis, ...] = ()
    private_analytics_available: bool = False


class ChannelAnalyzer:
    """Deterministic analysis of public channel metadata.

    This analyzer deliberately avoids claiming private Analytics metrics or
    inferring CTR, retention, audience behavior, or recommendation outcomes.
    """

    _HASHTAG_RE = re.compile(r"(?<!\w)#([\w-]+)")
    _HOOK_PATTERNS = (
        re.compile(r"\bwhy\b", re.IGNORECASE),
        re.compile(r"\bsecret\b", re.IGNORECASE),
        re.compile(r"\bmystery\b", re.IGNORECASE),
        re.compile(r"\bhow\b", re.IGNORECASE),
        re.compile(r"\bforgotten\b", re.IGNORECASE),
        re.compile(r"\blost\b", re.IGNORECASE),
    )

    def analyze(self, channel: PublicChannel) -> ChannelAnalysis:
        videos = tuple(channel.videos)
        if not videos:
            return ChannelAnalysis(
                channel_id=channel.identity.channel_id,
                status="INSUFFICIENT_DATA",
                video_count=0,
            )

        topic_counts: Counter[str] = Counter()
        hook_types: list[str] = []
        duration_counts: Counter[str] = Counter()
        recipes: list[str] = []

        for video in videos:
            tags = self._HASHTAG_RE.findall(f"{video.title} {video.description}")
            if tags:
                topic_counts.update(tag.lower().replace("-", " ") for tag in tags)
            else:
                words = [word.lower() for word in re.findall(r"[A-Za-z]{4,}", video.title)]
                topic_counts.update(words[:3])

            for pattern in self._HOOK_PATTERNS:
                match = pattern.search(video.title)
                if match:
                    hook_types.append(match.group(0).lower())
                    break

            if video.duration_seconds is not None:
                duration = float(video.duration_seconds)
                if duration <= 60:
                    duration_counts["0-60s"] += 1
                elif duration <= 180:
                    duration_counts["61-180s"] += 1
                else:
                    duration_counts["180s+"] += 1

            # Recipe extraction is intentionally conservative: only titles that
            # explicitly contain food-oriented markers are surfaced as candidates.
            lowered = video.title.lower()
            if any(marker in lowered for marker in ("recipe", "curry", "chutney", "sabzi", "dal", "pickle")):
                recipes.append(video.title.strip())

        topics = tuple(topic_counts.most_common(10))
        hooks = tuple(sorted(set(hook_types)))
        formats = tuple(duration_counts.most_common())
        pillars = self._build_pillars(topics)

        observations: list[ChannelObservation] = []
        if topics:
            topic, count = topics[0]
            observations.append(
                ChannelObservation(
                    pattern_type="topic_concentration",
                    description=f"The most frequently observed public topic label is '{topic}' in {count} of {len(videos)} videos.",
                    evidence={"topic": topic, "count": count, "video_count": len(videos)},
                    confidence=round(min(1.0, count / len(videos)), 4),
                    sample_size=len(videos),
                )
            )
        if formats:
            label, count = formats[0]
            observations.append(
                ChannelObservation(
                    pattern_type="format_duration_profile",
                    description=f"{count} of {len(videos)} analyzed videos fall in the public duration bucket '{label}'.",
                    evidence={"bucket": label, "count": count, "video_count": len(videos)},
                    confidence=round(count / len(videos), 4),
                    sample_size=len(videos),
                )
            )

        return ChannelAnalysis(
            channel_id=channel.identity.channel_id,
            status="observed",
            video_count=len(videos),
            topics=topics,
            pillars=pillars,
            hooks=hooks,
            formats=formats,
            recipes=tuple(dict.fromkeys(recipes)),
            observations=tuple(observations),
            hypotheses=(),
            private_analytics_available=False,
        )

    @staticmethod
    def _build_pillars(topics: tuple[tuple[str, int], ...]) -> tuple[tuple[str, int], ...]:
        pillar_counts: Counter[str] = Counter()
        food_words = {"food", "recipe", "curry", "chutney", "sabzi", "dal", "pickle", "village"}
        for topic, count in topics:
            pillar_counts["food_village"] += count if topic in food_words else 0
            if topic not in food_words:
                pillar_counts["other"] += count
        return tuple((name, count) for name, count in pillar_counts.most_common() if count > 0)
