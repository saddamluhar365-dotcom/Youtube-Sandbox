from __future__ import annotations

import json
from typing import Any

import httpx

from .config import Settings
from .models import ScenePlan


class Planner:
    def __init__(self, settings: Settings):
        self.settings = settings

    def plan(self, topic: str, style: str = "Ghibli-inspired 2D Indian village ASMR", constraints: str = "") -> list[ScenePlan]:
        if self.settings.gemini_api_key:
            try:
                scenes = self._gemini(topic, style, constraints)
                if len(scenes) == 9:
                    return scenes
            except Exception:
                pass
        return self._fallback(topic, style)

    def _gemini(self, topic: str, style: str, constraints: str) -> list[ScenePlan]:
        prompt = f'''Create exactly 9 connected scenes for a 90-second vertical recipe short about: {topic}.
Style: {style}. Extra constraints: {constraints or "none"}.
Each scene is exactly 10 seconds and has 3-5 meaningful visual beats. No dialogue, no narration, no subtitles.
Audio must describe only natural village/cooking ASMR and soft instrumental background music.
Return ONLY JSON array with objects: index, duration_seconds, visual_prompt, audio_prompt, transition_note.'''
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.settings.gemini_model}:generateContent"
        response = httpx.post(url, params={"key": self.settings.gemini_api_key}, json={"contents":[{"parts":[{"text":prompt}]}]}, timeout=60)
        response.raise_for_status()
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        data: Any = json.loads(text)
        return [ScenePlan.model_validate(item) for item in data]

    def _fallback(self, topic: str, style: str) -> list[ScenePlan]:
        beats = [
            "quiet village morning establishes the kitchen and ingredients",
            "fresh ingredients are washed and arranged with close ASMR details",
            "ingredients are chopped and prepared with rhythmic hand movements",
            "a clay stove fire starts and the cooking vessel warms",
            "ingredients enter the vessel and simmer with visible texture changes",
            "spices and finishing ingredients are added in a beautiful close-up",
            "the dish cooks while the village environment remains calm and alive",
            "the finished dish is plated traditionally and revealed in a slow camera move",
            "final hero shot of the dish with village sunset ambience and a peaceful ending",
        ]
        return [ScenePlan(index=i, duration_seconds=10,
            visual_prompt=f"{style}. Recipe topic: {topic}. Scene {i}: {beat}. 3-5 distinct visual beats, smooth cinematic motion, consistent character and environment, warm hand-painted 2D animation, no text, no dialogue, no narration.",
            audio_prompt="No speech. Natural rural Indian village ambience, cooking ASMR, fire, utensils, wind, birds and ingredient sounds appropriate to the scene; soft unobtrusive instrumental music.",
            transition_note=f"Connect naturally from scene {i-1} and hand off the action clearly to scene {i+1}." if i < 9 else "Resolve into a calm final hero shot.") for i, beat in enumerate(beats, 1)]
