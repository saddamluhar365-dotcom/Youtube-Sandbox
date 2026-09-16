from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher

from .db import Database


_STOPWORDS = {
    "a", "an", "and", "the", "of", "with", "in", "on", "for", "to",
    "village", "style", "desi", "homemade", "homemade", "traditional",
    "sabzi", "tarkari", "dish", "recipe", "food",
}
_ALIASES = {
    "aloo": "potato",
    "alu": "potato",
    "tamatar": "tomato",
    "pyaz": "onion",
    "pyaaz": "onion",
    "adrak": "ginger",
    "lehsun": "garlic",
    "mirch": "chili",
    "hari": "green",
    "kaccha": "raw",
    "kacha": "raw",
    "aam": "mango",
    "bajra": "pearl millet",
}


@dataclass(frozen=True)
class RecipeCandidate:
    name: str
    ingredients: list[str] = field(default_factory=list)
    main_ingredient: str | None = None
    cooking_method: str | None = None
    region: str | None = None
    food_category: str | None = None
    story_angle: str | None = None
    visual_concept: str | None = None
    asmr_elements: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    source_video_id: str | None = None


@dataclass(frozen=True)
class UniquenessResult:
    allowed: bool
    reason: str
    matched_recipe_id: str | None = None
    similarity: float = 0.0


class RecipeMaster:
    """Persistent recipe registry and conservative no-repeat gate.

    The gate is intentionally deterministic and explainable. It combines exact
    canonical-name matching, ingredient overlap, cooking-method overlap,
    story/visual overlap, and token similarity. It does not require an LLM.
    """

    def __init__(self, db: Database, semantic_threshold: float = 0.72):
        if not 0.5 <= semantic_threshold <= 0.99:
            raise ValueError("semantic_threshold must be between 0.5 and 0.99")
        self.db = db
        self.semantic_threshold = semantic_threshold

    def register(self, candidate: RecipeCandidate) -> str:
        self._validate(candidate)
        normalized = self.normalize_name(candidate.name)
        ingredients = sorted({self.canonical_token(x) for x in candidate.ingredients if x.strip()})
        fingerprint = self.fingerprint(candidate)
        recipe_id = "recipe_" + uuid.uuid4().hex
        now = self._now()

        with self.db.connection() as conn:
            existing = conn.execute(
                "SELECT recipe_id FROM recipes WHERE normalized_name = ? LIMIT 1",
                (normalized,),
            ).fetchone()
            if existing:
                return str(existing[0])
            conn.execute(
                """INSERT INTO recipes (
                    recipe_id, normalized_name, main_ingredient, cooking_method,
                    region, food_category, story_angle, visual_concept,
                    asmr_elements, aliases_json, ingredients_json,
                    similarity_fingerprint, source_video_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    recipe_id,
                    normalized,
                    self.canonical_token(candidate.main_ingredient or "") or None,
                    self.canonical_token(candidate.cooking_method or "") or None,
                    self.canonical_text(candidate.region),
                    self.canonical_text(candidate.food_category),
                    self.canonical_text(candidate.story_angle),
                    self.canonical_text(candidate.visual_concept),
                    json.dumps(sorted(set(candidate.asmr_elements)), ensure_ascii=False),
                    json.dumps(sorted(set(candidate.aliases + [candidate.name])), ensure_ascii=False),
                    json.dumps(ingredients, ensure_ascii=False),
                    fingerprint,
                    candidate.source_video_id,
                    now,
                    now,
                ),
            )
        return recipe_id

    def check_uniqueness(self, candidate: RecipeCandidate) -> UniquenessResult:
        self._validate(candidate)
        normalized = self.normalize_name(candidate.name)
        candidate_ingredients = {self.canonical_token(x) for x in candidate.ingredients if x.strip()}
        candidate_text = self._candidate_text(candidate)

        with self.db.connection() as conn:
            rows = conn.execute(
                """SELECT recipe_id, normalized_name, main_ingredient, cooking_method,
                          region, story_angle, visual_concept, aliases_json,
                          ingredients_json, similarity_fingerprint
                   FROM recipes"""
            ).fetchall()

        for row in rows:
            if normalized == row[1]:
                return UniquenessResult(False, "exact_duplicate", str(row[0]), 1.0)
            aliases = {self.normalize_name(x) for x in json.loads(row[7] or "[]")}
            if normalized in aliases:
                return UniquenessResult(False, "alias_duplicate", str(row[0]), 1.0)

            stored_ingredients = set(json.loads(row[8] or "[]"))
            ingredient_overlap = self._jaccard(candidate_ingredients, stored_ingredients)
            name_similarity = SequenceMatcher(None, normalized, row[1]).ratio()
            semantic_similarity = SequenceMatcher(None, candidate_text, self._row_text(row)).ratio()
            same_method = bool(
                candidate.cooking_method
                and self.canonical_token(candidate.cooking_method) == (row[3] or "")
            )
            same_main = bool(
                candidate.main_ingredient
                and self.canonical_token(candidate.main_ingredient) == (row[2] or "")
            )
            same_story = bool(candidate.story_angle and self.canonical_text(candidate.story_angle) == (row[5] or ""))
            same_visual = bool(candidate.visual_concept and self.canonical_text(candidate.visual_concept) == (row[6] or ""))

            score = self._score(
                ingredient_overlap,
                name_similarity,
                semantic_similarity,
                same_method,
                same_main,
                same_story,
                same_visual,
            )
            if score >= self.semantic_threshold or (
                same_main and same_method and ingredient_overlap >= 0.5
            ):
                return UniquenessResult(False, "semantic_duplicate", str(row[0]), round(score, 4))

        return UniquenessResult(True, "unique", None, 0.0)

    def mark_used(self, recipe_id: str) -> None:
        now = self._now()
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT use_count FROM recipes WHERE recipe_id = ?", (recipe_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown recipe_id: {recipe_id}")
            conn.execute(
                """UPDATE recipes
                   SET use_count = use_count + 1,
                       first_used_at = COALESCE(first_used_at, ?),
                       last_used_at = ?,
                       updated_at = ?
                   WHERE recipe_id = ?""",
                (now, now, now, recipe_id),
            )

    def get(self, recipe_id: str) -> dict | None:
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM recipes WHERE recipe_id = ?", (recipe_id,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def normalize_name(value: str) -> str:
        value = unicodedata.normalize("NFKC", value).casefold()
        value = re.sub(r"[^\w\s-]", " ", value, flags=re.UNICODE)
        tokens = [RecipeMaster.canonical_token(x) for x in value.replace("-", " ").split()]
        tokens = [x for x in tokens if x and x not in _STOPWORDS]
        return " ".join(sorted(tokens))

    @staticmethod
    def canonical_token(value: str) -> str:
        value = unicodedata.normalize("NFKC", value).casefold().strip()
        value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE)
        return _ALIASES.get(value, value)

    @staticmethod
    def canonical_text(value: str | None) -> str | None:
        if value is None:
            return None
        text = " ".join(value.casefold().split())
        return text or None

    def fingerprint(self, candidate: RecipeCandidate) -> str:
        payload = {
            "name": self.normalize_name(candidate.name),
            "ingredients": sorted(self.canonical_token(x) for x in candidate.ingredients),
            "main": self.canonical_token(candidate.main_ingredient or ""),
            "method": self.canonical_token(candidate.cooking_method or ""),
            "region": self.canonical_text(candidate.region),
            "story": self.canonical_text(candidate.story_angle),
            "visual": self.canonical_text(candidate.visual_concept),
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _jaccard(left: set[str], right: set[str]) -> float:
        if not left and not right:
            return 1.0
        if not left or not right:
            return 0.0
        return len(left & right) / len(left | right)

    @staticmethod
    def _score(
        ingredient_overlap: float,
        name_similarity: float,
        semantic_similarity: float,
        same_method: bool,
        same_main: bool,
        same_story: bool,
        same_visual: bool,
    ) -> float:
        score = (
            ingredient_overlap * 0.30
            + name_similarity * 0.20
            + semantic_similarity * 0.20
            + (0.10 if same_method else 0.0)
            + (0.10 if same_main else 0.0)
            + (0.05 if same_story else 0.0)
            + (0.05 if same_visual else 0.0)
        )
        return min(1.0, score)

    def _candidate_text(self, candidate: RecipeCandidate) -> str:
        parts = [
            self.normalize_name(candidate.name),
            " ".join(sorted(self.canonical_token(x) for x in candidate.ingredients)),
            self.canonical_token(candidate.main_ingredient or ""),
            self.canonical_token(candidate.cooking_method or ""),
            self.canonical_text(candidate.region) or "",
            self.canonical_text(candidate.story_angle) or "",
            self.canonical_text(candidate.visual_concept) or "",
        ]
        return " | ".join(parts)

    def _row_text(self, row) -> str:
        return " | ".join(
            [
                row[1] or "",
                " ".join(json.loads(row[8] or "[]")),
                row[2] or "",
                row[3] or "",
                row[4] or "",
                row[5] or "",
                row[6] or "",
            ]
        )

    @staticmethod
    def _validate(candidate: RecipeCandidate) -> None:
        if not candidate.name or not candidate.name.strip():
            raise ValueError("recipe name is required")
        if not candidate.ingredients:
            raise ValueError("at least one ingredient is required")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
