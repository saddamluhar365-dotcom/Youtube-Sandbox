from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock

from .models import CredentialLease, CredentialSlot, ProviderName


@dataclass
class _Health:
    quarantined_until: float = 0.0
    failures: int = 0
    successes: int = 0
    last_error: str | None = None


class CredentialPool:
    """Seven-slot provider-local credential rotation with temporary quarantine."""

    def __init__(self, provider: ProviderName, slots: list[CredentialSlot]) -> None:
        self.provider = provider
        self._slots = [slot for slot in slots if slot.configured]
        self._health = {slot.slot_id: _Health() for slot in self._slots}
        self._secrets = {slot.slot_id: slot.secret for slot in self._slots}
        self._cursor = 0
        self._lock = Lock()

    @property
    def configured_slots(self) -> tuple[str, ...]:
        return tuple(slot.slot_id for slot in self._slots)

    def acquire(self) -> CredentialLease:
        with self._lock:
            if not self._slots:
                raise RuntimeError(f"No configured credentials for provider {self.provider.value}")
            now = time.monotonic()
            for offset in range(len(self._slots)):
                index = (self._cursor + offset) % len(self._slots)
                slot = self._slots[index]
                if self._health[slot.slot_id].quarantined_until <= now:
                    self._cursor = (index + 1) % len(self._slots)
                    return CredentialLease(self.provider, slot.slot_id, self._secrets[slot.slot_id])
            raise RuntimeError(f"All credentials temporarily quarantined for provider {self.provider.value}")

    def report_success(self, slot_id: str) -> None:
        with self._lock:
            health = self._health.get(slot_id)
            if health is not None:
                health.successes += 1
                health.last_error = None

    def quarantine(self, slot_id: str, reason: str, seconds: int = 60) -> None:
        with self._lock:
            health = self._health.get(slot_id)
            if health is None:
                return
            health.failures += 1
            secret = self._secrets.get(slot_id)
            safe_reason = reason
            if secret:
                safe_reason = safe_reason.replace(secret, "[REDACTED]")
            health.last_error = safe_reason[:500]
            health.quarantined_until = max(health.quarantined_until, time.monotonic() + max(1, seconds))

    def health_snapshot(self) -> dict[str, dict[str, int | float | str | None]]:
        with self._lock:
            now = time.monotonic()
            return {
                slot_id: {
                    "failures": health.failures,
                    "successes": health.successes,
                    "quarantined": health.quarantined_until > now,
                    "last_error": health.last_error,
                }
                for slot_id, health in self._health.items()
            }
