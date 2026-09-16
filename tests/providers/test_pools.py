from __future__ import annotations

import pytest

from app.providers.key_pool import CredentialPool
from app.providers.models import CredentialSlot, ProviderName


def _pool() -> CredentialPool:
    return CredentialPool(
        ProviderName.FAL,
        [CredentialSlot(ProviderName.FAL, f"FAL_KEY_{i}", f"secret-{i}") for i in range(1, 4)],
    )


def test_round_robin_and_redaction_never_expose_secret_in_identifier() -> None:
    pool = _pool()
    leases = [pool.acquire() for _ in range(3)]
    assert [lease.slot_id for lease in leases] == ["FAL_KEY_1", "FAL_KEY_2", "FAL_KEY_3"]
    assert leases[0].redacted() == "fal.ai:FAL_KEY_1"
    assert "secret-1" not in leases[0].redacted()


def test_quarantined_slot_is_skipped() -> None:
    pool = _pool()
    first = pool.acquire()
    pool.quarantine(first.slot_id, "rate_limit", seconds=60)
    assert pool.acquire().slot_id == "FAL_KEY_2"


def test_empty_or_all_quarantined_pool_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="No configured credentials"):
        CredentialPool(ProviderName.TAVILY, [])
    pool = _pool()
    for slot in pool.configured_slots:
        pool.quarantine(slot, "rate_limit", seconds=60)
    with pytest.raises(RuntimeError, match="temporarily quarantined"):
        pool.acquire()
