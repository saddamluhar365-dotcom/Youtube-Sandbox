from __future__ import annotations

from dataclasses import dataclass, field

from app.intelligence.recipe_master import RecipeCandidate


@dataclass(frozen=True)
class RecipeDecision:
    recipe: RecipeCandidate
    status: str
    score: float
    score_breakdown: dict[str, float] = field(default_factory=dict)
    rationale: tuple[str, ...] = ()
    locked_at: str | None = None


@dataclass(frozen=True)
class WorldBible:
    status: str
    location: str
    season: str
    weather: str
    kitchen: str
    character: dict[str, str] = field(default_factory=dict)
    props: tuple[str, ...] = ()
    visual_language: tuple[str, ...] = ()


@dataclass(frozen=True)
class StoryBlueprint:
    status: str
    beats: tuple[str, ...]
    hook: str
    origin: str
    discovery: str
    transformation: str
    reveal: str


def _ensure_score(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 4)


__all__ = ["RecipeDecision", "WorldBible", "StoryBlueprint", "_ensure_score"]
