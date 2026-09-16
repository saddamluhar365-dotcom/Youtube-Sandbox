from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


def _env_slots(prefix: str) -> tuple[str, ...]:
    return tuple(
        value
        for value in (os.getenv(f"{prefix}_{i}", "").strip() for i in range(1, 8))
        if value
    )


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    fal_keys: tuple[str, ...]
    fal_model: str
    fal_poll_seconds: float
    fal_timeout_seconds: float
    gemini_keys: tuple[str, ...]
    gemini_api_key: str | None
    gemini_model: str
    tavily_keys: tuple[str, ...]
    hf_tokens: tuple[str, ...]
    video_provider: str
    video_model: str
    enable_real_provider_tests: bool
    max_output_mb: int

    @classmethod
    def from_env(cls) -> "Settings":
        fal_keys = _env_slots("FAL_KEY")
        gemini_keys = _env_slots("GEMINI_KEY")
        legacy_gemini = os.getenv("GEMINI_API_KEY", "").strip()
        if legacy_gemini and not gemini_keys:
            gemini_keys = (legacy_gemini,)
        return cls(
            data_dir=Path(os.getenv("DATA_DIR", "./jobs")),
            fal_keys=fal_keys,
            fal_model=os.getenv("FAL_VIDEO_MODEL", "fal-ai/vidu/q3/text-to-video"),
            fal_poll_seconds=float(os.getenv("FAL_POLL_SECONDS", "3")),
            fal_timeout_seconds=float(os.getenv("FAL_TIMEOUT_SECONDS", "900")),
            gemini_keys=gemini_keys,
            gemini_api_key=gemini_keys[0] if gemini_keys else None,
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            tavily_keys=_env_slots("TAVILY_KEY"),
            hf_tokens=_env_slots("HF_TOKEN"),
            video_provider=os.getenv("VIDEO_PROVIDER", "fal.ai").strip().lower(),
            video_model=os.getenv("VIDEO_MODEL", os.getenv("FAL_VIDEO_MODEL", "fal-ai/vidu/q3/text-to-video")),
            enable_real_provider_tests=os.getenv("ENABLE_REAL_PROVIDER_TESTS", "false").lower() == "true",
            max_output_mb=int(os.getenv("MAX_OUTPUT_MB", "500")),
        )

    def ffmpeg_available(self) -> bool:
        return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
