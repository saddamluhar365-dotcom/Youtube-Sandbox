from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    fal_keys: tuple[str, ...]
    fal_model: str
    fal_poll_seconds: float
    fal_timeout_seconds: float
    gemini_api_key: str | None
    gemini_model: str
    enable_real_provider_tests: bool
    max_output_mb: int

    @classmethod
    def from_env(cls) -> "Settings":
        keys = tuple(
            value for value in (os.getenv(f"FAL_KEY_{i}", "").strip() for i in range(1, 8))
            if value
        )
        return cls(
            data_dir=Path(os.getenv("DATA_DIR", "./jobs")),
            fal_keys=keys,
            fal_model=os.getenv("FAL_VIDEO_MODEL", "fal-ai/vidu/q3/text-to-video"),
            fal_poll_seconds=float(os.getenv("FAL_POLL_SECONDS", "3")),
            fal_timeout_seconds=float(os.getenv("FAL_TIMEOUT_SECONDS", "900")),
            gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            enable_real_provider_tests=os.getenv("ENABLE_REAL_PROVIDER_TESTS", "false").lower() == "true",
            max_output_mb=int(os.getenv("MAX_OUTPUT_MB", "500")),
        )

    def ffmpeg_available(self) -> bool:
        return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
