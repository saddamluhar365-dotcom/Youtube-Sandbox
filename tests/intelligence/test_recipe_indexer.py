from pathlib import Path

from app.channel.recipe_indexer import RecipeIndexer
from app.intelligence.db import Database
from app.intelligence.recipe_master import RecipeMaster


def test_indexer_registers_explicit_recipe_metadata(tmp_path: Path) -> None:
    db = Database(tmp_path / "recipes.db")
    master = RecipeMaster(db)
    indexer = RecipeIndexer(master)

    result = indexer.index_video(
        "video-1",
        {
            "title": "Village Aloo Sabzi",
            "recipe": {
                "name": "Potato Curry",
                "ingredients": ["aloo", "tamatar", "pyaz"],
                "main_ingredient": "aloo",
                "cooking_method": "curry",
                "region": "Gujarat",
                "story_angle": "village comfort food",
                "visual_concept": "clay-pot curry",
            },
        },
    )

    assert result.indexed is True
    assert result.recipe_id
    assert master.get(result.recipe_id)["source_video_id"] == "video-1"


def test_indexer_skips_missing_recipe_metadata(tmp_path: Path) -> None:
    db = Database(tmp_path / "recipes.db")
    indexer = RecipeIndexer(RecipeMaster(db))

    result = indexer.index_video("video-2", {"title": "A Short"})

    assert result.indexed is False
    assert result.reason == "no_explicit_recipe_metadata"


def test_indexer_rejects_invalid_recipe_metadata(tmp_path: Path) -> None:
    db = Database(tmp_path / "recipes.db")
    indexer = RecipeIndexer(RecipeMaster(db))

    result = indexer.index_video(
        "video-3",
        {"recipe": {"name": "Unknown", "ingredients": []}},
    )

    assert result.indexed is False
    assert result.reason == "invalid_recipe_metadata"
