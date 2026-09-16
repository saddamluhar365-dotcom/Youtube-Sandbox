from pathlib import Path

from app.channel.recipe_indexer import RecipeIndexer
from app.intelligence.db import Database
from app.intelligence.recipe_master import RecipeMaster


def _seed_video(db: Database, video_id: str) -> None:
    db.initialize()
    with db.connection() as conn:
        conn.execute(
            """INSERT INTO channel_profiles
               (channel_id, channel_handle, channel_url, title, description, data_hash)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("UCtestchannel000000000000", "@test", "https://youtube.com/@test",
             "Test Channel", "", "hash"),
        )
        conn.execute(
            """INSERT INTO channel_videos
               (video_id, channel_id, title, description, published_at, duration_seconds,
                view_count, like_count, comment_count, thumbnail_url, data_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (video_id, "UCtestchannel000000000000", "Test Video", "",
             "2026-01-01T00:00:00+00:00", 90, 0, 0, 0, None, "hash-video"),
        )


def test_indexer_registers_explicit_recipe_metadata(tmp_path: Path) -> None:
    db = Database(tmp_path / "recipes.db")
    _seed_video(db, "video-1")
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
