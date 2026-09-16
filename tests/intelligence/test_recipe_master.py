from __future__ import annotations

from app.intelligence.db import Database
from app.intelligence.recipe_master import RecipeMaster, RecipeCandidate


def test_recipe_master_rejects_semantic_duplicate() -> None:
    db = Database(":memory:")
    db.initialize()
    store = RecipeMaster(db)

    store.register(
        RecipeCandidate(
            name="Potato Curry",
            ingredients=["potato", "tomato", "onion"],
            main_ingredient="potato",
            cooking_method="curry",
            region="Gujarat",
            story_angle="village lunch",
            visual_concept="earthen pot potato curry",
        )
    )

    result = store.check_uniqueness(
        RecipeCandidate(
            name="Village Aloo Sabzi",
            ingredients=["aloo", "tamatar", "pyaz"],
            main_ingredient="aloo",
            cooking_method="curry",
            region="Gujarat",
            story_angle="village lunch",
            visual_concept="clay pot village potato sabzi",
        )
    )

    assert result.allowed is False
    assert result.reason == "semantic_duplicate"
    assert result.matched_recipe_id is not None


def test_recipe_master_allows_distinct_recipe() -> None:
    db = Database(":memory:")
    db.initialize()
    store = RecipeMaster(db)

    store.register(
        RecipeCandidate(
            name="Potato Curry",
            ingredients=["potato", "tomato"],
            main_ingredient="potato",
            cooking_method="curry",
            region="Gujarat",
        )
    )

    result = store.check_uniqueness(
        RecipeCandidate(
            name="Raw Mango Chutney",
            ingredients=["raw mango", "jaggery", "cumin"],
            main_ingredient="raw mango",
            cooking_method="chutney",
            region="Rajasthan",
        )
    )

    assert result.allowed is True
    assert result.reason == "unique"


def test_recipe_master_records_usage() -> None:
    db = Database(":memory:")
    db.initialize()
    store = RecipeMaster(db)

    recipe_id = store.register(
        RecipeCandidate(name="Bajra Rotla", ingredients=["bajra flour"])
    )
    store.mark_used(recipe_id)

    with db.connection() as conn:
        row = conn.execute(
            "SELECT use_count, first_used_at, last_used_at FROM recipes WHERE recipe_id = ?",
            (recipe_id,),
        ).fetchone()

    assert row[0] == 1
    assert row[1] is not None
    assert row[2] is not None
