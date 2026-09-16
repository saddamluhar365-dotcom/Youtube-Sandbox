from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

import httpx

from .config import Settings
from .providers.key_pool import CredentialPool
from .providers.models import CredentialSlot, ProviderName


@dataclass
class ProviderVideoResult:
    url: str
    raw: dict


class FalVideoClient:
    """fal.ai queue client with request-to-credential affinity."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.pool = CredentialPool(
            ProviderName.FAL,
            [CredentialSlot(ProviderName.FAL, f"FAL_KEY_{i}", key) for i, key in enumerate(settings.fal_keys, 1)],
        )
        self._request_slots: dict[str, str] = {}
        self._lock = Lock()

    @staticmethod
    def _headers(key: str) -> dict[str, str]:
        return {"Authorization": f"Key {key}", "Content-Type": "application/json"}

    def submit(self, prompt: str, aspect_ratio: str = "9:16") -> str:
        lease = self.pool.acquire()
        url = f"https://queue.fal.run/{self.settings.fal_model}"
        audio_prompt = " No dialogue, no narration, no spoken words. Natural village and cooking ASMR, gentle environmental sounds and soft background music only."
        payload = {
            "prompt": (prompt + audio_prompt)[:2000],
            "aspect_ratio": aspect_ratio,
            "duration": 10,
            "resolution": "720p",
            "audio": True,
        }
        try:
            response = httpx.post(url, headers=self._headers(lease.secret), json=payload, timeout=60)
            if response.status_code in (401, 403):
                self.pool.quarantine(lease.slot_id, "authentication_failed", 300)
                raise RuntimeError("fal.ai authentication failed")
            if response.status_code in (429, 500, 502, 503, 504):
                self.pool.quarantine(lease.slot_id, f"provider_status_{response.status_code}", 60)
                raise RuntimeError(f"fal.ai transient failure: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            request_id = data.get("request_id") or data.get("id")
            if not request_id:
                raise RuntimeError("fal.ai response did not contain request id")
            with self._lock:
                self._request_slots[str(request_id)] = lease.slot_id
            self.pool.report_success(lease.slot_id)
            return str(request_id)
        except httpx.HTTPError as exc:
            self.pool.quarantine(lease.slot_id, "network_request_failed", 30)
            raise RuntimeError("fal.ai network request failed") from exc

    def _lease_for_request(self, request_id: str):
        with self._lock:
            slot_id = self._request_slots.get(str(request_id))
        if slot_id is None:
            raise RuntimeError("fal.ai request credential binding not found")
        health = self.pool.health_snapshot().get(slot_id)
        if health is not None and health.get("quarantined"):
            raise RuntimeError("fal.ai credential bound to request is temporarily unavailable")
        for _ in range(1):
            lease = self.pool.acquire()
            if lease.slot_id == slot_id:
                return lease
            # Do not silently substitute a different credential for a queued request.
            self.pool.quarantine(lease.slot_id, "request_affinity_guard", 0)
        # Directly recover the bound secret only through the internal slot list.
        raise RuntimeError("fal.ai request credential is not currently acquirable")

    def wait(self, request_id: str) -> ProviderVideoResult:
        request_id = str(request_id)
        with self._lock:
            slot_id = self._request_slots.get(request_id)
        if slot_id is None:
            raise RuntimeError("fal.ai request credential binding not found")
        # CredentialPool intentionally does not expose arbitrary slot secrets.
        # Re-acquire until the bound slot is reached; this never substitutes a
        # different key for the request itself.
        key = None
        for _ in range(max(1, len(self.pool.configured_slots))):
            lease = self.pool.acquire()
            if lease.slot_id == slot_id:
                key = lease.secret
                break
            self.pool.quarantine(lease.slot_id, "request_affinity_probe", 0)
        if key is None:
            raise RuntimeError("fal.ai bound credential is temporarily unavailable")

        base = f"https://queue.fal.run/{self.settings.fal_model}/requests/{request_id}"
        deadline = time.time() + self.settings.fal_timeout_seconds
        try:
            while time.time() < deadline:
                response = httpx.get(f"{base}/status", headers={"Authorization": f"Key {key}"}, timeout=30)
                if response.status_code in (401, 403):
                    self.pool.quarantine(slot_id, "poll_authentication_failed", 300)
                    raise RuntimeError("fal.ai authentication failed while polling")
                if response.status_code in (429, 500, 502, 503, 504):
                    self.pool.quarantine(slot_id, f"poll_status_{response.status_code}", 60)
                    raise RuntimeError(f"fal.ai transient polling failure: {response.status_code}")
                response.raise_for_status()
                status = response.json().get("status", "").upper()
                if status == "COMPLETED":
                    result = httpx.get(f"{base}", headers={"Authorization": f"Key {key}"}, timeout=30)
                    result.raise_for_status()
                    data = result.json()
                    self.pool.report_success(slot_id)
                    with self._lock:
                        self._request_slots.pop(request_id, None)
                    return ProviderVideoResult(url=self._find_video_url(data), raw=data)
                if status in {"FAILED", "CANCELLED"}:
                    with self._lock:
                        self._request_slots.pop(request_id, None)
                    raise RuntimeError(f"fal.ai generation {status.lower()}")
                time.sleep(self.settings.fal_poll_seconds)
        except httpx.HTTPError as exc:
            self.pool.quarantine(slot_id, "poll_network_failure", 30)
            raise RuntimeError("fal.ai polling network request failed") from exc
        raise TimeoutError("fal.ai generation timed out")

    @staticmethod
    def _find_video_url(data: dict) -> str:
        candidates = [data.get("video", {}).get("url") if isinstance(data.get("video"), dict) else None, data.get("url")]
        videos = data.get("videos")
        if isinstance(videos, list) and videos and isinstance(videos[0], dict):
            candidates.append(videos[0].get("url"))
        for candidate in candidates:
            if isinstance(candidate, str) and candidate.startswith("http"):
                return candidate
        raise RuntimeError("fal.ai result did not contain a video URL")

    def download(self, result: ProviderVideoResult, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with httpx.stream("GET", result.url, timeout=120) as response:
            response.raise_for_status()
            with destination.open("wb") as handle:
                for chunk in response.iter_bytes():
                    handle.write(chunk)
        if destination.stat().st_size == 0:
            raise RuntimeError("fal.ai returned an empty video file")
        return destination
