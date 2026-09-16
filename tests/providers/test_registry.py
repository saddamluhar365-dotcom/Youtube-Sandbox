from __future__ import annotations

from app.providers.registry import ProviderRegistry


def test_registry_has_four_provider_pools_with_seven_slot_contract(monkeypatch) -> None:
    for prefix in ("TAVILY_KEY", "GEMINI_KEY", "HF_TOKEN", "FAL_KEY"):
        for index in range(1, 8):
            monkeypatch.setenv(f"{prefix}_{index}", f"secret-{prefix}-{index}")

    registry = ProviderRegistry()
    readiness = registry.readiness()

    assert set(readiness) == {"tavily", "gemini", "huggingface", "fal.ai"}
    for provider in readiness.values():
        assert len(provider["configured_slots"]) == 7
        for slot in provider["health"].values():
            assert "last_error" in slot
            assert all(not str(value).startswith("secret-") for value in slot.values() if value is not None)
