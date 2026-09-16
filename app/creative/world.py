from __future__ import annotations

from app.creative.models import WorldBible


class WorldBuilder:
    """Build a deterministic, locked world bible from explicit creative inputs."""

    def build(
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
        values = (location, season, weather, kitchen)
        if any(not value or not value.strip() for value in values):
            raise ValueError("location, season, weather and kitchen are required")
        if not character:
            raise ValueError("character bible is required")
        if any(not str(key).strip() or not str(value).strip() for key, value in character.items()):
            raise ValueError("character bible fields must be non-empty")
        return WorldBible(
            status="LOCKED",
            location=location.strip(),
            season=season.strip(),
            weather=weather.strip(),
            kitchen=kitchen.strip(),
            character=dict(character),
            props=tuple(item.strip() for item in props if item.strip()),
            visual_language=tuple(item.strip() for item in visual_language if item.strip()),
        )


__all__ = ["WorldBuilder"]
