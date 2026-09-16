from __future__ import annotations

import time

import pytest

from app.providers.pool import ProviderKeyPool


def test_round_robin_uses_each_key_without_exposing_secret() -> None:
    pool = ProviderKeyPool("fal.ai", ("secret-a", "secret-b", "secret-c"))
    assert [pool.next().key for _ in range(3)] == ["secret-a", "secret-b", "secret-c"]
    assert "secret-a" not in pool.next().display_name
    assert pool.next().display_name.startswith("fal.ai-key-")


def test_quarantined_key_is_skipped_and_recovers() -> None:
    pool = ProviderKeyPool("gemini", ("a", "b"), quarantine_seconds=0.05)
    first = pool.next()
    pool.quarantine(first.slot, 0.05)
    assert pool.next().slot != first.slot
    time.sleep(0.06)
    assert pool.next().slot == first.slot


def test_empty_or_all_blocked_pool_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="no .* keys configured"):
        ProviderKeyPool("tavily", ())
    pool = ProviderKeyPool("hf", ("only",))
    pool.quarantine(0, 60)
    with pytest.raises(RuntimeError, match="temporarily unavailable"):
        pool.next()
