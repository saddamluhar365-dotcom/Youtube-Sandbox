from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class VideoValidation:
    valid: bool
    width: int = 0
    height: int = 0
    duration: float = 0.0
    has_audio: bool = False
    size_bytes: int = 0
    error: str | None = None


class FFmpeg:
    def __init__(self, ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe"):
        self.ffmpeg, self.ffprobe = ffmpeg, ffprobe

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(args, capture_output=True, text=True, check=False, timeout=900)

    def normalize_clip(self, source: Path, output: Path) -> Path:
        output.parent.mkdir(parents=True, exist_ok=True)
        args = [self.ffmpeg, "-y", "-i", str(source), "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30", "-t", "10", "-map", "0:v:0", "-map", "0:a:0?", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", str(output)]
        result = self._run(args)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg clip normalization failed: {result.stderr[-500:]}")
        return output

    def concat_video(self, clips: list[Path], output: Path) -> Path:
        if len(clips) != 9:
            raise ValueError("exactly 9 clips are required")
        output.parent.mkdir(parents=True, exist_ok=True)
        list_file = output.with_suffix(".txt")
        list_file.write_text("\n".join(f"file '{p.resolve().as_posix().replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'" for p in clips), encoding="utf-8")
        args = [self.ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", "-movflags", "+faststart", str(output)]
        result = self._run(args)
        list_file.unlink(missing_ok=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg concat failed: {result.stderr[-500:]}")
        return output

    def mix_audio(self, video: Path, music: Path, output: Path) -> Path:
        args = [self.ffmpeg, "-y", "-i", str(video), "-i", str(music), "-filter_complex", "[0:a]volume=0.85[va];[1:a]volume=0.15[ma];[va][ma]amix=inputs=2:duration=first:dropout_transition=2[a]", "-map", "0:v:0", "-map", "[a]", "-t", "90", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(output)]
        result = self._run(args)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg audio mix failed: {result.stderr[-500:]}")
        return output


class MediaValidator:
    def __init__(self, ffprobe: str = "ffprobe", max_mb: int = 500):
        self.ffprobe, self.max_mb = ffprobe, max_mb

    def validate_video(self, path: Path) -> VideoValidation:
        try:
            size = path.stat().st_size
            if size <= 0 or size > self.max_mb * 1024 * 1024:
                return VideoValidation(False, size_bytes=size, error="invalid output size")
            result = subprocess.run([self.ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], capture_output=True, text=True, check=False, timeout=60)
            if result.returncode != 0:
                return VideoValidation(False, size_bytes=size, error="ffprobe could not decode output")
            data = json.loads(result.stdout)
            streams = data.get("streams", [])
            video = next((s for s in streams if s.get("codec_type") == "video"), None)
            audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
            if not video:
                return VideoValidation(False, size_bytes=size, error="missing video stream")
            duration = float(data.get("format", {}).get("duration", 0))
            width, height = int(video.get("width", 0)), int(video.get("height", 0))
            valid = width == 1080 and height == 1920 and 88.0 <= duration <= 92.0 and audio is not None
            error = None if valid else "quality gate failed: expected 1080x1920, ~90s and audio"
            return VideoValidation(valid, width, height, duration, audio is not None, size, error)
        except Exception as exc:
            return VideoValidation(False, error=str(exc))
