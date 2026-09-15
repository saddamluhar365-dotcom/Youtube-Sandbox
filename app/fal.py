from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

import httpx

from .config import Settings


@dataclass
class ProviderVideoResult:
    url: str
    raw: dict


class FalKeyPool:
    def __init__(self, keys: tuple[str, ...]):
        self.keys = keys
        self._cursor = 0
        self._blocked: dict[str, float] = {}
        self._lock = Lock()

    def next_available(self) -> str:
        if not self.keys:
            raise RuntimeError("no fal.ai keys configured")
        now = time.time()
        with self._lock:
            for _ in range(len(self.keys)):
                key = self.keys[self._cursor % len(self.keys)]
                self._cursor += 1
                if self._blocked.get(key, 0) <= now:
                    return key
        raise RuntimeError("all configured fal.ai keys are temporarily unavailable")

    def quarantine(self, key: str, seconds: float = 60) -> None:
        with self._lock:
            self._blocked[key] = time.time() + seconds


class FalVideoClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.pool = FalKeyPool(settings.fal_keys)

    def _headers(self, key: str) -> dict[str, str]:
        return {"Authorization": f"Key {key}", "Content-Type": "application/json"}

    def submit(self, prompt: str, aspect_ratio: str = "9:16") -> str:
        key = self.pool.next_available()
        url = f"https://queue.fal.run/{self.settings.fal_model}"
        payload = {"prompt": prompt, "aspect_ratio": aspect_ratio, "duration": 10}
        try:
            response = httpx.post(url, headers=self._headers(key), json=payload, timeout=60)
            if response.status_code in (401, 403):
                self.pool.quarantine(key, 300)
                raise RuntimeError("fal.ai authentication failed")
            if response.status_code in (429, 500, 502, 503, 504):
                self.pool.quarantine(key, 60)
                raise RuntimeError(f"fal.ai transient failure: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            request_id = data.get("request_id") or data.get("id")
            if not request_id:
                raise RuntimeError("fal.ai response did not contain request id")
            return request_id
        except httpx.HTTPError as exc:
            self.pool.quarantine(key, 30)
            raise RuntimeError("fal.ai network request failed") from exc

    def wait(self, request_id: str) -> ProviderVideoResult:
        key = self.pool.next_available()
        base = f"https://queue.fal.run/{self.settings.fal_model}/requests/{request_id}"
        deadline = time.time() + self.settings.fal_timeout_seconds
        while time.time() < deadline:
            response = httpx.get(f"{base}/status", headers={"Authorization": f"Key {key}"}, timeout=30)
            if response.status_code in (401, 403):
                self.pool.quarantine(key, 300)
                raise RuntimeError("fal.ai authentication failed while polling")
            response.raise_for_status()
            status = response.json().get("status", "").upper()
            if status == "COMPLETED":
                result = httpx.get(f"{base}", headers={"Authorization": f"Key {key}"}, timeout=30)
                result.raise_for_status()
                data = result.json()
                url = self._find_video_url(data)
                return ProviderVideoResult(url=url, raw=data)
            if status in {"FAILED", "CANCELLED"}:
                raise RuntimeError(f"fal.ai generation {status.lower()}")
            time.sleep(self.settings.fal_poll_seconds)
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
