from __future__ import annotations

from pathlib import Path

from .audio import AudioService
from .config import Settings
from .fal import FalVideoClient
from .jobs import JobStore
from .media import FFmpeg, MediaValidator
from .models import JobState, ScenePlan
from .planner import Planner


class Pipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.store = JobStore(settings.data_dir)
        self.planner = Planner(settings)
        self.fal = FalVideoClient(settings)
        self.ffmpeg = FFmpeg()
        self.validator = MediaValidator(max_mb=settings.max_output_mb)
        self.audio = AudioService()

    def run(self, job_id: str, style: str, constraints: str) -> None:
        job = self.store.get(job_id)
        if not job:
            return
        root = self.settings.data_dir / job_id
        raw, clips = root / "raw", root / "clips"
        raw.mkdir(parents=True, exist_ok=True); clips.mkdir(parents=True, exist_ok=True)
        try:
            self.store.transition(job_id, JobState.PLANNING)
            scenes = self.planner.plan(job["topic"], style, constraints)
            if len(scenes) != 9: raise RuntimeError("planner must return exactly 9 scenes")
            self.store.progress(job_id, 10)

            self.store.transition(job_id, JobState.GENERATING_CLIPS)
            normalized: list[Path] = []
            for n, scene in enumerate(scenes, 1):
                request_id = self.fal.submit(scene.visual_prompt, "9:16")
                result = self.fal.wait(request_id)
                source = raw / f"scene_{n:02d}.mp4"
                self.fal.download(result, source)
                target = clips / f"scene_{n:02d}.mp4"
                self.ffmpeg.normalize_clip(source, target)
                normalized.append(target)
                self.store.progress(job_id, 10 + n * 7)

            self.store.transition(job_id, JobState.GENERATING_AUDIO)
            audio_path = root / "audio.wav"
            self.audio.create_track(audio_path, 90.0)
            self.store.progress(job_id, 82)

            self.store.transition(job_id, JobState.ASSEMBLING)
            silent = root / "video.mp4"
            final = root / "final.mp4"
            self.ffmpeg.concat_video(normalized, silent)
            self.ffmpeg.mix_audio(silent, audio_path, final)
            self.store.progress(job_id, 94)

            self.store.transition(job_id, JobState.VALIDATING)
            validation = self.validator.validate_video(final)
            self.store.validation(job_id, validation.__dict__)
            if not validation.valid:
                raise RuntimeError(validation.error or "media validation failed")
            self.store.progress(job_id, 100)
            self.store.transition(job_id, JobState.COMPLETED)
        except Exception as exc:
            self.store.fail(job_id, str(exc))
