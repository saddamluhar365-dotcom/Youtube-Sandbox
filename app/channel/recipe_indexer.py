from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.intelligence.recipe_master import RecipeCandidate, RecipeMaster


@dataclass(frozen=True)
class RecipeIndexResult:
    indexed: bool
    reason: str
    recipe_id: str | None = None


class RecipeIndexer:
    """Bridge explicit channel recipe metadata into the persistent Recipe Master.

    The indexer is deliberately conservative: it never invents ingredients or
    recipe identity from a title alone. Enrichment can happen upstream, but the
    persistence layer only accepts explicit structured recipe evidence.
    """

    def __init__(self, master: RecipeMaster):
        self.master = master

    def index_video(self, video_id: str, payload: Mapping[str, Any]) -> RecipeIndexResult:
        recipe = payload.get("recipe")
        if not isinstance(recipe, Mapping):
            return RecipeIndexResult(False, "no_explicit_recipe_metadata")

        try:
            name = str(recipe.get("name", "")).strip()
            ingredients = self._strings(recipe.get("ingredients"))
            if not name or not ingredients:
                return RecipeIndexResult(False, "invalid_recipe_metadata")

            candidate = RecipeCandidate(
                name=name,
                ingredients=ingredients,
                main_ingredient=self._optional(recipe.get("main_ingredient")),
                cooking_method=self._optional(recipe.get("cooking_method")),
                region=self._optional(recipe.get("region")),
                food_category=self._optional(recipe.get("food_category")),
                story_angle=self._optional(recipe.get("story_angle")),
                visual_concept=self._optional(recipe.get("visual_concept")),
                asmr_elements=self._strings(recipe.get("asmr_elements")),
                aliases=self._strings(recipe.get("aliases")),
                source_video_id=video_id,
            )
            existing = self.master.check_uniqueness(candidate)
            if not existing.allowed and existing.matched_recipe_id:
                return RecipeIndexResult(False, existing.reason, existing.matched_recipe_id)
            return RecipeIndexResult(True, "indexed", self.master.register(candidate))
        except (TypeError, ValueError):
            return RecipeIndexResult(False, "invalid_recipe_metadata")

    @staticmethod
    def _optional(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _strings(value: Any) -> list[str]:
        if not isinstance(value, (list, tuple)):
            return []
        return [str(item).strip() for item in value if str(item).strip()]
