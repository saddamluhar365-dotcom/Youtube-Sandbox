from __future__ import annotations

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse

from .config import Settings
from .models import CreateJobRequest, JobResponse
from .pipeline import Pipeline

settings = Settings.from_env()
pipeline = Pipeline(settings)


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
        return JobResponse(job_id=job["id"], state=job["state"], progress=job["progress"], error=job["error"], validation=job["validation"])

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
        pipeline.store.transition(job_id, __import__("app.models", fromlist=["JobState"]).JobState.CANCELLED)
        return {"job_id": job_id, "state": "cancelled"}

    return app


app = create_app()
