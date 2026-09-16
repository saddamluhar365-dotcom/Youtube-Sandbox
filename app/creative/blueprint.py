from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Mapping, Sequence

from app.intelligence.recipe_master import RecipeCandidate

from .models import StoryBlueprint, WorldBible


@dataclass(frozen=True)
class SceneBlueprint:
    scene_number: int
    duration_seconds: int
    content_mode: str
    purpose: str
    beats: tuple[str, ...]
    camera: str
    lighting: str
    movement: str
    asmr: str
    continuity_in: str
    continuity_out: str
    references: tuple[str, ...] = ()
    negative_constraints: tuple[str, ...] = ()
    prompt: str = ""


@dataclass(frozen=True)
class ProductionBlueprint:
    status: str
    created_at: str
    duration_seconds: int
    scene_count: int
    recipe: RecipeCandidate
    world: WorldBible
    story: StoryBlueprint
    scenes: tuple[SceneBlueprint, ...]
    audio_direction: tuple[str, ...] = ()
    validation_errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class BlueprintValidationReport:
    valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


class ProductionBlueprintValidator:
    """Hard gate for the locked 90-second / 9-scene production contract."""

    SCENE_COUNT = 9
    SCENE_DURATION = 10
    TOTAL_DURATION = 90
    MIN_BEATS = 3
    MAX_BEATS = 5
    REQUIRED_TEXT_FIELDS = (
        "purpose",
        "camera",
        "lighting",
        "movement",
        "asmr",
        "prompt",
        "continuity_in",
        "continuity_out",
    )
    CONTENT_MODES = {"ambient", "story"}

    def validate(
        self,
        *,
        recipe: RecipeCandidate,
        world: WorldBible,
        story: StoryBlueprint,
        scenes: Sequence[SceneBlueprint],
    ) -> BlueprintValidationReport:
        errors: list[str] = []
        scene_tuple = tuple(scenes)

        if not recipe.name.strip():
            errors.append("recipe name is required")
        if not world.location.strip() or not world.kitchen.strip():
            errors.append("world location and kitchen are required")
        if not story.hook.strip() or not story.reveal.strip():
            errors.append("story hook and reveal are required")

        if len(scene_tuple) != self.SCENE_COUNT:
            errors.append(f"scene_count must be exactly {self.SCENE_COUNT}")

        for expected_number, scene in enumerate(scene_tuple, start=1):
            prefix = f"scene {expected_number}"
            if scene.scene_number != expected_number:
                errors.append(f"{prefix}: scene_number must be {expected_number}")
            if scene.duration_seconds != self.SCENE_DURATION:
                errors.append(f"{prefix}: duration must be exactly {self.SCENE_DURATION} seconds")
            if not self.MIN_BEATS <= len(scene.beats) <= self.MAX_BEATS:
                errors.append(
                    f"{prefix}: beats must contain {self.MIN_BEATS}-{self.MAX_BEATS} meaningful beats"
                )
            if scene.content_mode not in self.CONTENT_MODES:
                errors.append(f"{prefix}: content_mode must be ambient or story")
            for beat_index, beat in enumerate(scene.beats, start=1):
                if not isinstance(beat, str) or not beat.strip():
                    errors.append(f"{prefix}: beat {beat_index} is empty")
            for field_name in self.REQUIRED_TEXT_FIELDS:
                value = getattr(scene, field_name)
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"{prefix}: {field_name} is required")

        if scene_tuple:
            ambient_count = sum(scene.content_mode == "ambient" for scene in scene_tuple)
            story_count = sum(scene.content_mode == "story" for scene in scene_tuple)
            if ambient_count < 4 or story_count < 4:
                errors.append("content mix must contain at least 4 ambient and 4 story scenes")

            for previous, current in zip(scene_tuple, scene_tuple[1:]):
                if previous.continuity_out.strip() != current.continuity_in.strip():
                    errors.append(
                        f"continuity mismatch between scene {previous.scene_number} and scene {current.scene_number}"
                    )

        return BlueprintValidationReport(valid=not errors, errors=tuple(errors))


class ProductionBlueprintBuilder:
    """Builds deterministic scene contracts from an approved Level-3 creative decision."""

    _DEFAULT_AMBIENT = {1, 3, 5, 7, 9}

    def build_scenes(
        self,
        *,
        recipe: RecipeCandidate,
        world: WorldBible,
        story: StoryBlueprint,
        scene_specs: Sequence[Mapping[str, object]],
    ) -> list[SceneBlueprint]:
        if len(scene_specs) != ProductionBlueprintValidator.SCENE_COUNT:
            raise ValueError("scene_specs must contain exactly 9 scenes")

        scenes: list[SceneBlueprint] = []
        previous_anchor = "world-established"
        for number, raw in enumerate(scene_specs, start=1):
            beats = self._beats(raw.get("beats"))
            content_mode = str(raw.get("content_mode") or ("ambient" if number in self._DEFAULT_AMBIENT else "story"))
            purpose = str(raw.get("purpose") or f"connected sequence {number}")
            camera = str(raw.get("camera") or "cinematic medium shot")
            lighting = str(raw.get("lighting") or "soft natural village light")
            movement = str(raw.get("movement") or "smooth connected motion")
            asmr = str(raw.get("asmr") or "natural village ASMR")
            continuity_in = str(raw.get("continuity_in") or previous_anchor)
            continuity_out = str(raw.get("continuity_out") or f"scene-{number}-anchor")
            references = self._string_tuple(raw.get("references"))
            negative_constraints = self._string_tuple(raw.get("negative_constraints"))
            prompt = str(raw.get("prompt") or self._compose_prompt(
                number=number,
                recipe=recipe,
                world=world,
                story=story,
                purpose=purpose,
                beats=beats,
                camera=camera,
                lighting=lighting,
                movement=movement,
                asmr=asmr,
            ))
            scenes.append(
                SceneBlueprint(
                    scene_number=number,
                    duration_seconds=10,
                    content_mode=content_mode,
                    purpose=purpose,
                    beats=beats,
                    camera=camera,
                    lighting=lighting,
                    movement=movement,
                    asmr=asmr,
                    continuity_in=continuity_in,
                    continuity_out=continuity_out,
                    references=references,
                    negative_constraints=negative_constraints,
                    prompt=prompt,
                )
            )
            previous_anchor = continuity_out
        return scenes

    def build(
        self,
        *,
        recipe: RecipeCandidate,
        world: WorldBible,
        story: StoryBlueprint,
        scene_specs: Sequence[Mapping[str, object]],
        audio_direction: Sequence[str] = (),
    ) -> ProductionBlueprint:
        scenes = tuple(
            self.build_scenes(
                recipe=recipe,
                world=world,
                story=story,
                scene_specs=scene_specs,
            )
        )
        report = ProductionBlueprintValidator().validate(
            recipe=recipe,
            world=world,
            story=story,
            scenes=scenes,
        )
        if not report.valid:
            raise ValueError("production blueprint validation failed: " + "; ".join(report.errors))
        return ProductionBlueprint(
            status="VALIDATED",
            created_at=datetime.now(timezone.utc).isoformat(),
            duration_seconds=90,
            scene_count=9,
            recipe=recipe,
            world=world,
            story=story,
            scenes=scenes,
            audio_direction=tuple(audio_direction),
            validation_errors=(),
        )

    @staticmethod
    def _beats(value: object) -> tuple[str, ...]:
        if value is None:
            return ("establish", "transition", "resolve")
        if isinstance(value, str):
            return (value,)
        if isinstance(value, Sequence):
            return tuple(str(item) for item in value)
        raise TypeError("beats must be a sequence of strings")

    @staticmethod
    def _string_tuple(value: object) -> tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, str):
            return (value,)
        if isinstance(value, Sequence):
            return tuple(str(item) for item in value)
        raise TypeError("value must be a sequence of strings")

    @staticmethod
    def _compose_prompt(
        *,
        number: int,
        recipe: RecipeCandidate,
        world: WorldBible,
        story: StoryBlueprint,
        purpose: str,
        beats: tuple[str, ...],
        camera: str,
        lighting: str,
        movement: str,
        asmr: str,
    ) -> str:
        return (
            f"10-second connected scene {number}; purpose: {purpose}; "
            f"recipe: {recipe.name}; location: {world.location}; kitchen: {world.kitchen}; "
            f"visual language: {', '.join(world.visual_language)}; story hook: {story.hook}; "
            f"beats: {' | '.join(beats)}; camera: {camera}; lighting: {lighting}; "
            f"movement: {movement}; ASMR: {asmr}; maintain exact character, world, prop, "
            "lighting and motion continuity; no dialogue, no narration, no text overlays."
        )


__all__ = [
    "BlueprintValidationReport",
    "ProductionBlueprint",
    "ProductionBlueprintBuilder",
    "ProductionBlueprintValidator",
    "SceneBlueprint",
]
