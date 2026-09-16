from __future__ import annotations

from app.creative.models import StoryBlueprint


class StoryBuilder:
    """Create a locked five-beat recipe-story structure."""

    def build(
        self,
        *,
        hook: str,
        origin: str,
        discovery: str,
        transformation: str,
        reveal: str,
    ) -> StoryBlueprint:
        values = (hook, origin, discovery, transformation, reveal)
        if any(not value or not value.strip() for value in values):
            raise ValueError("all five story beats are required")
        return StoryBlueprint(
            status="LOCKED",
            beats=tuple(value.strip() for value in values),
            hook=hook.strip(),
            origin=origin.strip(),
            discovery=discovery.strip(),
            transformation=transformation.strip(),
            reveal=reveal.strip(),
        )


__all__ = ["StoryBuilder"]
