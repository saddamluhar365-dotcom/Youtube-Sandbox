from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field, field_validator


class JobState(str, Enum):
    QUEUED = "queued"
    PLANNING = "planning"
    GENERATING_CLIPS = "generating_clips"
    GENERATING_AUDIO = "generating_audio"
    ASSEMBLING = "assembling"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScenePlan(BaseModel):
    index: int = Field(ge=1, le=9)
    duration_seconds: int = Field(default=10)
    visual_prompt: str = Field(min_length=20, max_length=5000)
    audio_prompt: str = Field(min_length=10, max_length=2000)
    transition_note: str = Field(min_length=5, max_length=1000)

    @field_validator("duration_seconds")
    @classmethod
    def ten_seconds(cls, value: int) -> int:
        if value != 10:
            raise ValueError("every scene must be exactly 10 seconds")
        return value


class CreateJobRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=500)
    recipe_constraints: str = Field(default="", max_length=2000)
    style: str = Field(default="Ghibli-inspired 2D Indian village ASMR", max_length=500)


class JobResponse(BaseModel):
    job_id: str
    state: JobState
    progress: int
    error: str | None = None
    validation: dict | None = None
