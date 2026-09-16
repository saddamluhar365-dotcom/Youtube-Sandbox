from __future__ import annotations

from datetime import datetime, timezone

from app.intelligence.recipe_master import RecipeCandidate, RecipeMaster

from .models import RecipeDecision, StoryBlueprint, WorldBible, _ensure_score
from .story import StoryBuilder
from .world import WorldBuilder


class CreativeDirector:
    """Level 3 decision layer.

    Creative choices are explicit and explainable. Recipe uniqueness is checked
    against the persistent RecipeMaster before a decision can be locked.
    Missing optional signals receive a neutral value rather than invented data.
    """

    _WEIGHTS = {
        "visual_appeal": 0.15,
        "transformation": 0.15,
        "asmr": 0.15,
        "story": 0.15,
        "uniqueness": 0.20,
        "demand": 0.10,
        "feasibility": 0.10,
    }

    def __init__(self, recipe_master: RecipeMaster | None):
        self.recipe_master = recipe_master
        self.world_builder = WorldBuilder()
        self.story_builder = StoryBuilder()

    def select_recipe(
        self,
        candidates: list[RecipeCandidate] | tuple[RecipeCandidate, ...],
        *,
        demand_signals: dict[str, float] | None = None,
        feasibility_signals: dict[str, float] | None = None,
        uniqueness_signals: dict[str, float] | None = None,
        visual_signals: dict[str, float] | None = None,
        transformation_signals: dict[str, float] | None = None,
        asmr_signals: dict[str, float] | None = None,
        story_signals: dict[str, float] | None = None,
        gap_report: object | None = None,
    ) -> RecipeDecision:
        if not candidates:
            raise ValueError("at least one recipe candidate is required")

        demand_signals = demand_signals or {}
        feasibility_signals = feasibility_signals or {}
        uniqueness_signals = uniqueness_signals or {}
        visual_signals = visual_signals or {}
        transformation_signals = transformation_signals or {}
        asmr_signals = asmr_signals or {}
        story_signals = story_signals or {}

        scored: list[tuple[float, RecipeCandidate, dict[str, float], tuple[str, ...]]] = []
        rejected: list[str] = []
        for candidate in candidates:
            if self.recipe_master is not None:
                uniqueness = self.recipe_master.check_uniqueness(candidate)
                if not uniqueness.allowed:
                    rejected.append(f"{candidate.name}: {uniqueness.reason}")
                    continue
                uniqueness_value = uniqueness_signals.get(candidate.name, 1.0)
            else:
                uniqueness_value = uniqueness_signals.get(candidate.name, 0.5)

            key = candidate.name
            breakdown = {
                "visual_appeal": self._signal(visual_signals, key),
                "transformation": self._signal(transformation_signals, key, self._has_transformation(candidate)),
                "asmr": self._signal(asmr_signals, key, self._has_asmr(candidate)),
                "story": self._signal(story_signals, key, self._has_story(candidate)),
                "uniqueness": _ensure_score(uniqueness_value),
                "demand": self._signal(demand_signals, key),
                "feasibility": self._signal(feasibility_signals, key),
            }
            score = _ensure_score(sum(breakdown[name] * weight for name, weight in self._WEIGHTS.items()))
            rationale = self._rationale(breakdown, gap_report)
            scored.append((score, candidate, breakdown, rationale))

        if not scored:
            detail = "; ".join(rejected) if rejected else "no usable candidates"
            raise ValueError(f"no unique recipe candidate is selectable: {detail}")

        score, recipe, breakdown, rationale = max(scored, key=lambda item: item[0])
        # The intermediate SELECTED state is intentionally not returned: callers
        # receive a decision only after the required selection gate succeeds.
        return RecipeDecision(
            recipe=recipe,
            status="LOCKED",
            score=score,
            score_breakdown=breakdown,
            rationale=rationale,
            locked_at=self._now(),
        )

    def build_world(
        self,
        *,
        location: str,
        season: str,
        weather: str,
        kitchen: str,
        character: dict[str, str],
        props: tuple[str, ...] = (),
        visual_language: tuple[str, ...] = (),
    ) -> WorldBible:
        return self.world_builder.build(
            location=location,
            season=season,
            weather=weather,
            kitchen=kitchen,
            character=character,
            props=props,
            visual_language=visual_language,
        )

    def build_story(
        self,
        *,
        hook: str,
        origin: str,
        discovery: str,
        transformation: str,
        reveal: str,
    ) -> StoryBlueprint:
        return self.story_builder.build(
            hook=hook,
            origin=origin,
            discovery=discovery,
            transformation=transformation,
            reveal=reveal,
        )

    @staticmethod
    def _signal(values: dict[str, float], key: str, default: float = 0.5) -> float:
        return _ensure_score(values.get(key, default))

    @staticmethod
    def _has_transformation(candidate: RecipeCandidate) -> float:
        return 0.8 if candidate.cooking_method else 0.5

    @staticmethod
    def _has_asmr(candidate: RecipeCandidate) -> float:
        return 0.8 if candidate.asmr_elements else 0.5

    @staticmethod
    def _has_story(candidate: RecipeCandidate) -> float:
        return 0.8 if candidate.story_angle else 0.5

    @staticmethod
    def _rationale(breakdown: dict[str, float], gap_report: object | None) -> tuple[str, ...]:
        items = [
            f"visual_appeal={breakdown['visual_appeal']:.4f}",
            f"transformation={breakdown['transformation']:.4f}",
            f"asmr={breakdown['asmr']:.4f}",
            f"story={breakdown['story']:.4f}",
            f"uniqueness={breakdown['uniqueness']:.4f}",
            f"demand={breakdown['demand']:.4f}",
            f"feasibility={breakdown['feasibility']:.4f}",
        ]
        if gap_report is not None and getattr(gap_report, "status", None) == "observed":
            items.append("peer-gap evidence was available as an input")
        return tuple(items)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()


__all__ = ["CreativeDirector"]
