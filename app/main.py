from __future__ import annotations

from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .agent.master import BlueprintRequest, MasterAgent
from .config import Settings
from .intelligence.db import Database
from .intelligence.recipe_master import RecipeCandidate
from .models import CreateJobRequest, JobResponse, JobState
from .pipeline import Pipeline

settings = Settings.from_env()
pipeline = Pipeline(settings)
intelligence_db = Database(settings.data_dir / "intelligence.sqlite3")
master_agent = MasterAgent(db=intelligence_db)


class ChannelSyncRequest(BaseModel):
    handle: str = Field(min_length=1)


class BlueprintApiRequest(BaseModel):
    recipe: dict[str, Any]
    world: dict[str, Any]
    story: dict[str, Any]
    scenes: list[dict[str, Any]]
    audio_direction: list[str] = Field(default_factory=list)


def _recipe_from_api(value: dict[str, Any]) -> RecipeCandidate:
    return RecipeCandidate(
        name=str(value.get("name", "")),
        ingredients=[str(item) for item in value.get("ingredients", [])],
        main_ingredient=value.get("main_ingredient"),
        cooking_method=value.get("cooking_method"),
        region=value.get("region"),
        food_category=value.get("food_category"),
        story_angle=value.get("story_angle"),
        visual_concept=value.get("visual_concept"),
        asmr_elements=[str(item) for item in value.get("asmr_elements", [])],
        aliases=[str(item) for item in value.get("aliases", [])],
        source_video_id=value.get("source_video_id"),
    )


def create_app() -> FastAPI:
    app = FastAPI(title="YouTube Sandbox", version="0.1.0")

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "ffmpeg": settings.ffmpeg_available(),
            "fal_keys_configured": len(settings.fal_keys),
            "gemini_configured": bool(settings.gemini_api_key),
            "youtube_upload_enabled": False,
        }

    @app.post("/api/v1/jobs", response_model=JobResponse, status_code=202)
    def create_job(request: CreateJobRequest, background: BackgroundTasks) -> JobResponse:
        if not settings.fal_keys:
            raise HTTPException(status_code=503, detail="No fal.ai API keys configured in Render environment")
        if not settings.ffmpeg_available():
            raise HTTPException(status_code=503, detail="FFmpeg/ffprobe is not available")
        job = pipeline.store.create(request.topic)
        background.add_task(pipeline.run, job["id"], request.style, request.recipe_constraints)
        return JobResponse(job_id=job["id"], state=job["state"], progress=0)

    @app.get("/api/v1/jobs/{job_id}", response_model=JobResponse)
    def get_job(job_id: str) -> JobResponse:
        job = pipeline.store.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="job not found")
        return JobResponse(
            job_id=job["id"],
            state=job["state"],
            progress=job["progress"],
            error=job["error"],
            validation=job["validation"],
        )

    @app.get("/api/v1/jobs/{job_id}/output")
    def output(job_id: str):
        job = pipeline.store.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="job not found")
        if job["state"] != "completed":
            raise HTTPException(status_code=409, detail="output is available only after validation succeeds")
        path = settings.data_dir / job_id / "final.mp4"
        if not path.is_file():
            raise HTTPException(status_code=404, detail="final artifact not found")
        return FileResponse(path, media_type="video/mp4", filename=f"youtube-sandbox-{job_id}.mp4")

    @app.post("/api/v1/jobs/{job_id}/cancel")
    def cancel(job_id: str) -> dict:
        job = pipeline.store.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="job not found")
        if job["state"] not in {"queued", "planning"}:
            raise HTTPException(status_code=409, detail="job can no longer be cancelled safely")
        pipeline.store.transition(job_id, JobState.CANCELLED)
        return {"job_id": job_id, "state": "cancelled"}

    @app.post("/api/v1/channels/sync", status_code=200)
    def sync_channel(request: ChannelSyncRequest) -> dict:
        try:
            analysis = master_agent.analyze_channel(request.handle)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "channel_id": analysis.channel_id,
            "status": analysis.status,
            "video_count": analysis.video_count,
            "topics": analysis.topics,
            "pillars": analysis.pillars,
            "hooks": analysis.hooks,
            "formats": analysis.formats,
            "recipes": analysis.recipes,
            "observations": analysis.observations,
            "hypotheses": analysis.hypotheses,
            "private_analytics_available": analysis.private_analytics_available,
        }

    @app.get("/api/v1/channels/{handle:path}", status_code=200)
    def get_channel(handle: str) -> dict:
        analysis = master_agent.get_channel_analysis(handle)
        if analysis is None:
            raise HTTPException(status_code=404, detail="channel not found")
        return {
            "channel_id": analysis.channel_id,
            "status": analysis.status,
            "video_count": analysis.video_count,
            "topics": analysis.topics,
            "pillars": analysis.pillars,
            "hooks": analysis.hooks,
            "formats": analysis.formats,
            "recipes": analysis.recipes,
            "observations": analysis.observations,
            "hypotheses": analysis.hypotheses,
            "private_analytics_available": analysis.private_analytics_available,
        }

    @app.post("/api/v1/creative/blueprints", status_code=200)
    def create_blueprint(request: BlueprintApiRequest) -> dict:
        try:
            blueprint = master_agent.create_blueprint(
                BlueprintRequest(
                    recipe=_recipe_from_api(request.recipe),
                    world=request.world,
                    story=request.story,
                    scenes=request.scenes,
                    audio_direction=request.audio_direction,
                )
            )
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "status": blueprint.status,
            "duration_seconds": blueprint.duration_seconds,
            "scene_count": blueprint.scene_count,
            "recipe": blueprint.recipe,
            "world": blueprint.world,
            "story": blueprint.story,
            "scenes": blueprint.scenes,
            "audio_direction": blueprint.audio_direction,
            "validation_errors": blueprint.validation_errors,
        }

    return app


app = create_app()
