from __future__ import annotations

import os

from .key_pool import CredentialPool
from .models import CredentialSlot, ProviderName, ProviderProfile


class ProviderRegistry:
    def __init__(self) -> None:
        self.profiles = {
            ProviderName.TAVILY: ProviderProfile(ProviderName.TAVILY, "web_research"),
            ProviderName.GEMINI: ProviderProfile(ProviderName.GEMINI, "llm_reasoning"),
            ProviderName.HUGGING_FACE: ProviderProfile(ProviderName.HUGGING_FACE, "reference_images"),
            ProviderName.FAL: ProviderProfile(ProviderName.FAL, "video_generation_media"),
        }
        self.pools: dict[ProviderName, CredentialPool] = {}
        for provider in self.profiles:
            try:
                self.pools[provider] = self._build_pool(provider)
            except RuntimeError:
                # Startup and /health must remain usable before local .env setup.
                continue

    @staticmethod
    def _prefix(provider: ProviderName) -> str:
        return {
            ProviderName.TAVILY: "TAVILY_KEY",
            ProviderName.GEMINI: "GEMINI_KEY",
            ProviderName.HUGGING_FACE: "HF_TOKEN",
            ProviderName.FAL: "FAL_KEY",
        }[provider]

    def _build_pool(self, provider: ProviderName) -> CredentialPool:
        prefix = self._prefix(provider)
        slots = [
            CredentialSlot(provider, f"{prefix}_{index}", os.getenv(f"{prefix}_{index}", "").strip())
            for index in range(1, 8)
        ]
        return CredentialPool(provider, slots)

    def get(self, name: str | ProviderName) -> ProviderProfile:
        return self.profiles[ProviderName(name)]

    def pool(self, name: str | ProviderName) -> CredentialPool:
        provider = ProviderName(name)
        pool = self.pools.get(provider)
        if pool is None:
            raise RuntimeError(f"No configured credentials for provider {provider.value}")
        return pool

    def readiness(self) -> dict[str, dict[str, object]]:
        result: dict[str, dict[str, object]] = {}
        for provider, profile in self.profiles.items():
            pool = self.pools.get(provider)
            result[provider.value] = {
                "capability": profile.capability,
                "configured_slots": pool.configured_slots if pool else (),
                "health": pool.health_snapshot() if pool else {},
                "ready": pool is not None,
            }
        return result
