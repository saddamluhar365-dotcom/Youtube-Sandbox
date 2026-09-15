from __future__ import annotations

import pytest

from app.providers.key_pool import CredentialPool
from app.providers.models import CredentialSlot, ProviderName


def make_pool() -> CredentialPool:
    return CredentialPool(
        ProviderName.FAL,
        [
            CredentialSlot(ProviderName.FAL, "FAL_KEY_1", "secret-one"),
            CredentialSlot(ProviderName.FAL, "FAL_KEY_2", "secret-two"),
            CredentialSlot(ProviderName.FAL, "FAL_KEY_3", "secret-three"),
        ],
    )


def test_round_robin_rotates_configured_slots() -> None:
    pool = make_pool()
    assert pool.acquire().slot_id == "FAL_KEY_1"
    assert pool.acquire().slot_id == "FAL_KEY_2"
    assert pool.acquire().slot_id == "FAL_KEY_3"
    assert pool.acquire().slot_id == "FAL_KEY_1"


def test_quarantined_slot_is_skipped() -> None:
    pool = make_pool()
    pool.quarantine("FAL_KEY_1", "rate limited", seconds=60)
    assert pool.acquire().slot_id == "FAL_KEY_2"


def test_all_quarantined_is_explicit_failure() -> None:
    pool = make_pool()
    for slot in pool.configured_slots:
        pool.quarantine(slot, "temporary failure", seconds=60)
    with pytest.raises(RuntimeError, match="All credentials temporarily quarantined"):
        pool.acquire()


def test_redacted_lease_never_contains_secret() -> None:
    lease = make_pool().acquire()
    assert lease.secret == "secret-one"
    assert "secret-one" not in lease.redacted()
    assert lease.redacted() == "fal.ai:FAL_KEY_1"
