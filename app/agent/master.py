from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, Sequence

from app.channel.analyzer import ChannelAnalysis, ChannelAnalyzer
from app.channel.models import ChannelIdentity, ChannelSyncResult, PublicChannel, PublicVideo
from app.creative.blueprint import ProductionBlueprint, ProductionBlueprintBuilder
from app.creative.models import StoryBlueprint, WorldBible
from app.intelligence.db import Database
from app.intelligence.recipe_master import RecipeCandidate, RecipeMaster


class ChannelSyncProvider(Protocol):
    def sync(self, handle: str) -> ChannelSyncResult: ...


@dataclass(frozen=True)
class BlueprintRequest:
    recipe: RecipeCandidate
    world: dict[str, Any]
    story: dict[str, Any]
    scenes: Sequence[dict[str, object]]
    audio_direction: Sequence[str] = ()


class MasterAgent:
    """Handle-first orchestrator for the persistent Level 1-3 intelligence flow."""

    def __init__(
        self,
        *,
        db: Database | None = None,
        sync_provider: ChannelSyncProvider | None = None,
        analyzer: ChannelAnalyzer | None = None,
        recipe_master: RecipeMaster | Any | None = None,
    ) -> None:
        self.db = db
        if self.db is not None:
            self.db.initialize()
        self.sync_provider = sync_provider
        self.analyzer = analyzer or ChannelAnalyzer()
        self.recipe_master = recipe_master or (RecipeMaster(self.db) if self.db is not None else None)
        self.blueprint_builder = ProductionBlueprintBuilder()
        self._analysis_cache: dict[str, ChannelAnalysis] = {}

    def analyze_channel(self, handle: str) -> ChannelAnalysis:
        normalized = str(handle).strip()
        if not normalized:
            raise ValueError("channel handle is required")
        if self.sync_provider is None:
            raise RuntimeError("channel sync provider is not configured")
        result = self.sync_provider.sync(normalized)
        if not isinstance(result, ChannelSyncResult):
            raise TypeError("channel sync provider must return ChannelSyncResult")
        analysis = self.analyzer.analyze(result.channel)
        self._analysis_cache[result.channel.identity.channel_id] = analysis
        return analysis

    def get_channel_analysis(self, handle: str) -> ChannelAnalysis | None:
        channel_id = self._resolve_persisted_channel_id(handle)
        if channel_id is None:
            return None
        cached = self._analysis_cache.get(channel_id)
        if cached is not None:
            return cached
        channel = self._load_persisted_channel(channel_id)
        if channel is None:
            return None
        analysis = self.analyzer.analyze(channel)
        self._analysis_cache[channel_id] = analysis
        return analysis

    def create_blueprint(self, request: BlueprintRequest) -> ProductionBlueprint:
        if self.recipe_master is not None:
            uniqueness = self.recipe_master.check_uniqueness(request.recipe)
            if not uniqueness.allowed:
                raise ValueError(f"recipe is not unique: {uniqueness.reason}")

        world = WorldBible(
            location=str(request.world.get("location", "")),
            season=str(request.world.get("season", "")),
            weather=str(request.world.get("weather", "")),
            kitchen=str(request.world.get("kitchen", "")),
            character={str(k): str(v) for k, v in dict(request.world.get("character", {})).items()},
            props=tuple(str(v) for v in request.world.get("props", ())),
            visual_language=tuple(str(v) for v in request.world.get("visual_language", ())),
        )
        story = StoryBlueprint(
            hook=str(request.story.get("hook", "")),
            origin=str(request.story.get("origin", "")),
            discovery=str(request.story.get("discovery", "")),
            transformation=str(request.story.get("transformation", "")),
            reveal=str(request.story.get("reveal", "")),
        )
        blueprint = self.blueprint_builder.build(
            recipe=request.recipe,
            world=world,
            story=story,
            scene_specs=request.scenes,
            audio_direction=request.audio_direction,
        )
        return blueprint

    def _resolve_persisted_channel_id(self, handle: str) -> str | None:
        if self.db is None:
            return None
        normalized = handle.strip().lstrip("@")
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT channel_id FROM channel_profiles WHERE channel_handle = ? LIMIT 1",
                (f"@{normalized}",),
            ).fetchone()
            if row is None:
                row = conn.execute(
                    "SELECT channel_id FROM channel_profiles WHERE channel_id = ? LIMIT 1",
                    (handle.strip(),),
                ).fetchone()
        return None if row is None else str(row[0])

    def _load_persisted_channel(self, channel_id: str) -> PublicChannel | None:
        if self.db is None:
            return None
        with self.db.connection() as conn:
            profile = conn.execute(
                """SELECT channel_handle, channel_url, title, description, country,
                          custom_url, published_at
                   FROM channel_profiles WHERE channel_id = ?""",
                (channel_id,),
            ).fetchone()
            if profile is None:
                return None
            rows = conn.execute(
                """SELECT video_id, title, description, published_at, duration_seconds,
                          is_short, view_count, like_count, comment_count, thumbnail_url
                   FROM channel_videos WHERE channel_id = ? ORDER BY published_at DESC, video_id""",
                (channel_id,),
            ).fetchall()

        identity = ChannelIdentity(
            channel_id=channel_id,
            channel_handle=profile[0],
            channel_url=profile[1],
            title=profile[2] or "",
        )
        videos = tuple(
            PublicVideo(
                video_id=str(row[0]),
                title=str(row[1]),
                description=str(row[2] or ""),
                published_at=row[3],
                duration_seconds=row[4],
                is_short=bool(row[5]),
                view_count=row[6],
                like_count=row[7],
                comment_count=row[8],
                thumbnail_url=row[9],
            )
            for row in rows
        )
        return PublicChannel(
            identity=identity,
            description=profile[3] or "",
            country=profile[4],
            custom_url=profile[5],
            published_at=profile[6],
            videos=videos,
        )


__all__ = ["BlueprintRequest", "ChannelSyncProvider", "MasterAgent"]
