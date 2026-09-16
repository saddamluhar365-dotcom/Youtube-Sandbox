from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class ProviderKey:
    provider: str
    slot: int
    key: str

    @property
    def display_name(self) -> str:
        return f"{self.provider}-key-{self.slot + 1}"


class ProviderKeyPool:
    """Thread-safe round-robin credential pool with temporary quarantine.

    Secret values are retained only in memory and are never included in the
    public representation of a key. Quarantine is provider-local and does not
    attempt to circumvent provider rate limits.
    """

    def __init__(self, provider: str, keys: tuple[str, ...], quarantine_seconds: float = 60.0):
        provider = provider.strip().lower()
        if not provider:
            raise ValueError("provider is required")
        if not keys:
            raise RuntimeError(f"no {provider} keys configured")
        if quarantine_seconds < 0:
            raise ValueError("quarantine_seconds must be non-negative")
        cleaned = tuple(key.strip() for key in keys if key and key.strip())
        if not cleaned:
            raise RuntimeError(f"no {provider} keys configured")
        self.provider = provider
        self.keys = cleaned
        self.quarantine_seconds = quarantine_seconds
        self._cursor = 0
        self._blocked: dict[int, float] = {}
        self._lock = Lock()

    def next(self) -> ProviderKey:
        now = time.monotonic()
        with self._lock:
            for _ in range(len(self.keys)):
                slot = self._cursor % len(self.keys)
                self._cursor += 1
                if self._blocked.get(slot, 0.0) <= now:
                    return ProviderKey(self.provider, slot, self.keys[slot])
        raise RuntimeError(f"all {self.provider} keys are temporarily unavailable")

    def quarantine(self, slot: int, seconds: float | None = None) -> None:
        if not 0 <= slot < len(self.keys):
            raise IndexError("invalid provider key slot")
        duration = self.quarantine_seconds if seconds is None else seconds
        if duration < 0:
            raise ValueError("quarantine duration must be non-negative")
        with self._lock:
            self._blocked[slot] = time.monotonic() + duration

    def available_count(self) -> int:
        now = time.monotonic()
        with self._lock:
            return sum(self._blocked.get(slot, 0.0) <= now for slot in range(len(self.keys)))
