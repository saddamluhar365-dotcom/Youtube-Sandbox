from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from .db import Database


@dataclass(frozen=True)
class Pattern:
    pattern_type: str
    description: str
    evidence_type: str
    evidence: dict[str, Any]
    confidence: float
    sample_size: int


@dataclass(frozen=True)
class GapAnalysis:
    channel_id: str
    status: str
    sample_size: int
    top_topics: tuple[tuple[str, int], ...]
    patterns: tuple[Pattern, ...]
    gaps: tuple[str, ...] = ()


class GapEngine:
    """Deterministic Level-2 analysis over persisted public channel data.

    It reports observations only. It never converts missing private analytics
    into invented CTR, retention, audience or algorithm claims.
    """

    def __init__(self, db: Database):
        self.db = db
        self.db.initialize()

    def analyze(self, channel_id: str) -> GapAnalysis:
        with self.db.connection() as conn:
            videos = conn.execute(
                """SELECT video_id, title, duration_seconds, view_count
                   FROM channel_videos WHERE channel_id = ?
                   ORDER BY published_at DESC""",
                (channel_id,),
            ).fetchall()
            topics = conn.execute(
                """SELECT vt.video_id, vt.topic, vt.confidence
                   FROM video_topics vt
                   JOIN channel_videos cv ON cv.video_id = vt.video_id
                   WHERE cv.channel_id = ?""",
                (channel_id,),
            ).fetchall()

        sample_size = len(videos)
        if sample_size == 0:
            return GapAnalysis(channel_id, "INSUFFICIENT_DATA", 0, (), ())

        topic_counts = Counter(str(row[1]).strip() for row in topics if str(row[1]).strip())
        top_topics = tuple(topic_counts.most_common(10))
        patterns: list[Pattern] = []

        if top_topics:
            topic, count = top_topics[0]
            patterns.append(
                Pattern(
                    "topic_concentration",
                    f"{count} of {sample_size} analyzed videos have the topic label '{topic}'.",
                    "observed_data",
                    {"topic": topic, "count": count},
                    round(count / sample_size, 4),
                    sample_size,
                )
            )

        durations = [float(row[2]) for row in videos if row[2] is not None]
        if durations:
            short_count = sum(1 for value in durations if value <= 180)
            patterns.append(
                Pattern(
                    "duration_profile",
                    f"{short_count} of {len(durations)} videos have duration at or below 180 seconds.",
                    "observed_data",
                    {"short_or_short_form_count": short_count, "duration_sample": len(durations)},
                    round(short_count / len(durations), 4),
                    len(durations),
                )
            )

        view_values = [int(row[3]) for row in videos if row[3] is not None]
        if view_values:
            ordered = sorted(view_values)
            median = ordered[len(ordered) // 2]
            max_views = max(ordered)
            patterns.append(
                Pattern(
                    "public_view_distribution",
                    f"Public view counts range from {min(ordered)} to {max_views}; median is {median}.",
                    "observed_data",
                    {"min": min(ordered), "max": max_views, "median": median},
                    1.0,
                    len(ordered),
                )
            )

        return GapAnalysis(channel_id, "observed", sample_size, top_topics, tuple(patterns))
