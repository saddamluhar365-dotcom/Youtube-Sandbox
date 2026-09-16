from __future__ import annotations

import pytest

from app.creative.blueprint import ProductionBlueprintBuilder, ProductionBlueprintValidator
from app.creative.models import StoryBlueprint, WorldBible
from app.intelligence.recipe_master import RecipeCandidate


def _recipe() -> RecipeCandidate:
    return RecipeCandidate(
        name="Raw Mango Chutney",
        ingredients=["raw mango", "chili", "salt"],
        main_ingredient="raw mango",
        cooking_method="grinding",
        region="Gujarat",
        food_category="chutney",
        story_angle="forgotten village summer recipe",
        visual_concept="stone grinding in a village courtyard",
        asmr_elements=["grinding", "birds", "wind"],
    )


def _world() -> WorldBible:
    return WorldBible(
        status="LOCKED",
        location="Gujarat village courtyard",
        season="summer",
        weather="warm clear morning",
        kitchen="mud-and-stone village kitchen",
        character={"appearance": "consistent adult female character"},
        props=("stone grinder", "clay bowl", "mangoes"),
        visual_language=("Ghibli-inspired 2D", "cozy", "cinematic"),
    )


def _story() -> StoryBlueprint:
    return StoryBlueprint(
        status="LOCKED",
        beats=("hook", "origin", "discovery", "transformation", "reveal"),
        hook="A forgotten summer taste is hiding in one raw mango.",
        origin="The recipe survived in a quiet village kitchen.",
        discovery="The old grinding method reveals the texture.",
        transformation="Fresh mango and spices become a vivid chutney.",
        reveal="The final chutney carries the forgotten village flavor.",
    )


def test_builder_creates_exactly_nine_ten_second_scenes_with_three_to_five_beats() -> None:
    builder = ProductionBlueprintBuilder()
    scenes = builder.build_scenes(
        recipe=_recipe(),
        world=_world(),
        story=_story(),
        scene_specs=[
            {"purpose": f"scene {index}", "beats": ["beat 1", "beat 2", "beat 3"]}
            for index in range(1, 10)
        ],
    )

    assert len(scenes) == 9
    assert all(scene.duration_seconds == 10 for scene in scenes)
    assert all(3 <= len(scene.beats) <= 5 for scene in scenes)
    assert scenes[0].scene_number == 1
    assert scenes[-1].scene_number == 9


def test_validator_rejects_wrong_scene_count_duration_and_beat_count() -> None:
    builder = ProductionBlueprintBuilder()
    scenes = builder.build_scenes(
        recipe=_recipe(),
        world=_world(),
        story=_story(),
        scene_specs=[
            {"purpose": f"scene {index}", "beats": ["beat 1", "beat 2", "beat 3"]}
            for index in range(1, 10)
        ],
    )
    scenes[0] = scenes[0].__class__(
        **{**scenes[0].__dict__, "duration_seconds": 9, "beats": ("only", "two")}
    )

    report = ProductionBlueprintValidator().validate(
        recipe=_recipe(), world=_world(), story=_story(), scenes=tuple(scenes)
    )

    assert report.valid is False
    assert "scene_count" not in report.errors
    assert any("duration" in error for error in report.errors)
    assert any("beats" in error for error in report.errors)


def test_validator_rejects_missing_continuity_and_required_prompt_fields() -> None:
    builder = ProductionBlueprintBuilder()
    scenes = builder.build_scenes(
        recipe=_recipe(),
        world=_world(),
        story=_story(),
        scene_specs=[
            {
                "purpose": f"scene {index}",
                "beats": ["beat 1", "beat 2", "beat 3"],
                "prompt": "complete visual prompt",
            }
            for index in range(1, 10)
        ],
    )
    broken = scenes[4].__class__(
        **{
            **scenes[4].__dict__,
            "continuity_in": "",
            "continuity_out": "",
            "prompt": "",
        }
    )
    scenes[4] = broken

    report = ProductionBlueprintValidator().validate(
        recipe=_recipe(), world=_world(), story=_story(), scenes=tuple(scenes)
    )

    assert report.valid is False
    assert any("continuity" in error for error in report.errors)
    assert any("prompt" in error for error in report.errors)


def test_validator_accepts_complete_nine_scene_blueprint() -> None:
    builder = ProductionBlueprintBuilder()
    blueprint = builder.build(
        recipe=_recipe(),
        world=_world(),
        story=_story(),
        scene_specs=[
            {
                "purpose": f"scene {index}",
                "beats": ["beat 1", "beat 2", "beat 3"],
                "prompt": "complete visual prompt",
                "camera": "cinematic medium shot",
                "lighting": "soft morning light",
                "movement": "smooth connected motion",
                "asmr": "natural village ASMR",
            }
            for index in range(1, 10)
        ],
    )

    assert blueprint.status == "VALIDATED"
    assert len(blueprint.scenes) == 9
    assert ProductionBlueprintValidator().validate(
        recipe=blueprint.recipe,
        world=blueprint.world,
        story=blueprint.story,
        scenes=blueprint.scenes,
    ).valid is True


def test_builder_rejects_non_nine_scene_input() -> None:
    with pytest.raises(ValueError, match="exactly 9"):
        ProductionBlueprintBuilder().build_scenes(
            recipe=_recipe(),
            world=_world(),
            story=_story(),
            scene_specs=[
                {"purpose": "scene", "beats": ["a", "b", "c"]}
                for _ in range(8)
            ],
        )
