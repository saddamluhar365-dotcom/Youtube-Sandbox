# YouTube Sandbox — Phase 1

Render-deployable sandbox for generating **Ghibli-inspired 2D village ASMR recipe Shorts**.

## Phase-1 scope

`Topic → Gemini scene plan → 9 × 10s fal.ai clips → dialogue-free audio → FFmpeg → validation → MP4`

- Exactly 9 clips × 10 seconds.
- Vertical 1080×1920 output.
- No dialogue and no narration.
- Ambient/cooking ASMR + soft background music layer.
- fal.ai credentials are read only from Render environment variables.
- Up to 7 configured fal.ai credentials are supported by the key pool.
- YouTube OAuth/upload/publishing is intentionally **not included**.

## API

- `GET /health`
- `POST /api/v1/jobs` with `{ "topic": "..." }`
- `GET /api/v1/jobs/{job_id}`
- `GET /api/v1/jobs/{job_id}/output`
- `POST /api/v1/jobs/{job_id}/cancel`

Example:

```bash
curl -X POST https://YOUR-RENDER-SERVICE.onrender.com/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"topic":"Traditional village tomato chutney"}'
```

Then poll the returned job ID until `state` becomes `completed` and open the output endpoint.

## Render setup

Deploy this repository as a Docker web service. Render reads `render.yaml` and the Docker image installs FFmpeg/ffprobe.

Set the following secrets in Render:

- `FAL_KEY_1` … `FAL_KEY_7`
- `GEMINI_API_KEY` (optional; fallback scene planner works without it)

Do **not** put keys in GitHub, request JSON, logs, or job records.

## Important audio note

Phase-1 has a deterministic dialogue-free audio fallback so the assembly pipeline can be tested without another credential. A real ASMR/audio provider can be plugged into the audio interface later without changing the video/job API.

## Local test

```bash
pip install .
pytest -q
uvicorn app.main:app --host 0.0.0.0 --port 10000
```

A real fal.ai smoke test should be run only after the service health check succeeds and the provider/model configured in `FAL_VIDEO_MODEL` is confirmed to accept the payload shape used by the deployment.
