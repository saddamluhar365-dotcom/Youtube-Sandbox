# YouTube Sandbox Phase-1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Render-deployable sandbox that turns one recipe topic into a validated 90-second, 1080x1920 MP4 made from 9 connected 10-second AI video clips with ambient ASMR and background music, without any YouTube upload capability.

**Architecture:** A Python HTTP service owns a persistent job state machine and isolated per-job workspaces. Gemini produces structured scene plans; a fal.ai provider router submits authorized video jobs and downloads clips; an audio layer produces/assembles non-dialogue ambience/music; FFmpeg performs deterministic assembly and media validation. Secrets remain in Render environment variables.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic, httpx, pytest, FFmpeg, Render, fal.ai API, optional Gemini API.

**Spec:** `docs/superpowers/specs/2026-09-16-youtube-sandbox-design.md`

## Global Constraints

- 90 seconds total, exactly 9 x 10-second clips.
- Ghibli-inspired 2D village ASMR recipe format.
- No dialogue and no narration.
- Ambient village/cooking ASMR plus soft background music.
- Final target 1080x1920 MP4.
- API keys only from environment variables; never commit secrets.
- Authorized fal.ai quotas only; no quota circumvention.
- YouTube upload/publishing/OAuth is excluded from Phase-1.
- Every task must leave a testable working state.

---

### Task 1: Bootstrap service and configuration

**Files:**
- Create: `pyproject.toml`
- Create: `app/__init__.py`
- Create: `app/config.py`
- Create: `app/main.py`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `tests/test_config.py`

**Interfaces:**
- `Settings.from_env() -> Settings`
- `create_app() -> FastAPI`
- `GET /health -> JSON readiness response`

- [ ] **Step 1: Write the failing configuration and health tests**
- [ ] **Step 2: Run `pytest -q tests/test_config.py` and verify failure**
- [ ] **Step 3: Implement settings validation, secret-name loading, and `/health`**
- [ ] **Step 4: Run `pytest -q tests/test_config.py` and verify pass**
- [ ] **Step 5: Add FFmpeg executable detection to readiness without exposing environment values**
- [ ] **Step 6: Run `python -m compileall app` and commit**

### Task 2: Job model and state machine

**Files:**
- Create: `app/jobs/models.py`
- Create: `app/jobs/store.py`
- Create: `app/jobs/state.py`
- Create: `tests/jobs/test_state.py`

**Interfaces:**
- `JobState`: `queued`, `planning`, `generating_clips`, `generating_audio`, `assembling`, `validating`, `completed`, `failed`, `cancelled`
- `JobStore.create(topic: str) -> Job`
- `JobStore.get(job_id: str) -> Job | None`
- `JobStore.transition(job_id: str, state: JobState) -> Job`

- [ ] **Step 1: Write state transition tests including invalid transitions**
- [ ] **Step 2: Run targeted tests and verify failure**
- [ ] **Step 3: Implement the state machine and durable SQLite-backed store**
- [ ] **Step 4: Run `pytest -q tests/jobs/test_state.py`**
- [ ] **Step 5: Commit**

### Task 3: Structured scene planner

**Files:**
- Create: `app/planner/models.py`
- Create: `app/planner/gemini.py`
- Create: `app/planner/service.py`
- Create: `tests/planner/test_service.py`

**Interfaces:**
- `ScenePlan` contains `index`, `duration_seconds`, `visual_prompt`, `audio_prompt`, `transition_note`.
- `Planner.plan(topic: str) -> list[ScenePlan]`

- [ ] **Step 1: Write tests that reject fewer/more than 9 scenes and durations other than 10 seconds**
- [ ] **Step 2: Run targeted tests and verify failure**
- [ ] **Step 3: Implement provider abstraction and Gemini adapter using structured JSON output**
- [ ] **Step 4: Add prompt constraints for 3-5 meaningful visual beats, continuity, no dialogue/narration, and village ASMR**
- [ ] **Step 5: Validate returned plans with Pydantic**
- [ ] **Step 6: Run tests with mocked Gemini responses and commit**

### Task 4: fal.ai multi-key provider router

**Files:**
- Create: `app/providers/fal/models.py`
- Create: `app/providers/fal/client.py`
- Create: `app/providers/fal/router.py`
- Create: `tests/providers/test_fal_router.py`

**Interfaces:**
- `FalKeyPool.next_available() -> FalCredential`
- `FalVideoClient.submit(prompt: str, aspect_ratio: str) -> str`
- `FalVideoClient.wait(job_id: str) -> ProviderVideoResult`
- `FalVideoClient.download(result, destination) -> Path`

- [ ] **Step 1: Write tests for round-robin selection, temporary key quarantine, transient retry, and permanent auth failure**
- [ ] **Step 2: Run targeted tests and verify failure**
- [ ] **Step 3: Implement environment-driven `FAL_KEY_1` through `FAL_KEY_7` loading**
- [ ] **Step 4: Implement bounded retry/backoff and provider status polling**
- [ ] **Step 5: Implement safe response parsing and binary download verification**
- [ ] **Step 6: Ensure logs never contain key values**
- [ ] **Step 7: Run targeted tests and commit**

### Task 5: Clip generation worker

**Files:**
- Create: `app/pipeline/clip_generator.py`
- Create: `tests/pipeline/test_clip_generator.py`

**Interfaces:**
- `ClipGenerator.generate(job_id: str, scenes: list[ScenePlan]) -> list[Path]`

- [ ] **Step 1: Write mocked-provider tests requiring exactly 9 output paths**
- [ ] **Step 2: Verify failure**
- [ ] **Step 3: Implement sequential generation first for predictable quota/resource behavior**
- [ ] **Step 4: Validate each downloaded clip before proceeding to the next stage**
- [ ] **Step 5: Update job progress after each clip**
- [ ] **Step 6: Run tests and commit**

### Task 6: ASMR and background music layer

**Files:**
- Create: `app/audio/models.py`
- Create: `app/audio/service.py`
- Create: `app/audio/mixer.py`
- Create: `tests/audio/test_mixer.py`

**Interfaces:**
- `AudioService.create_ambient_track(scene: ScenePlan, output: Path) -> Path`
- `AudioService.create_music_track(plan: list[ScenePlan], output: Path) -> Path`
- `AudioMixer.mix(voice_free_ambient: Path, music: Path, output: Path) -> Path`

- [ ] **Step 1: Write tests for no-dialogue policy, duration matching, and safe volume levels**
- [ ] **Step 2: Verify failure**
- [ ] **Step 3: Implement an audio-provider abstraction so a native-audio video provider or dedicated audio generator can be plugged in without changing the pipeline**
- [ ] **Step 4: Implement fallback using deterministic locally available ambience/music assets when configured**
- [ ] **Step 5: Add loudness/peak validation and reject malformed audio**
- [ ] **Step 6: Run tests and commit**

### Task 7: FFmpeg assembly and media validation

**Files:**
- Create: `app/media/ffmpeg.py`
- Create: `app/media/validator.py`
- Create: `tests/media/test_validator.py`
- Create: `tests/media/test_ffmpeg.py`

**Interfaces:**
- `FFmpeg.concat_video(clips: list[Path], output: Path) -> Path`
- `FFmpeg.mix_audio(video: Path, audio: Path, output: Path) -> Path`
- `MediaValidator.validate_video(path: Path) -> VideoValidation`

- [ ] **Step 1: Write tests for exact dimensions, duration tolerance, codec readability, and non-zero file size**
- [ ] **Step 2: Verify failure**
- [ ] **Step 3: Implement safe FFmpeg command construction without shell-string interpolation**
- [ ] **Step 4: Implement 1080x1920 normalization and final duration enforcement**
- [ ] **Step 5: Implement `ffprobe` validation**
- [ ] **Step 6: Run tests with generated tiny fixture media and commit**

### Task 8: End-to-end pipeline and API endpoints

**Files:**
- Create: `app/pipeline/orchestrator.py`
- Modify: `app/main.py`
- Create: `tests/api/test_jobs.py`
- Create: `tests/pipeline/test_e2e_mocked.py`

**Interfaces:**
- `POST /api/v1/jobs` returns `job_id` and `state`.
- `GET /api/v1/jobs/{job_id}` returns state/progress/validation metadata.
- `GET /api/v1/jobs/{job_id}/output` streams the MP4 only after successful validation.
- `POST /api/v1/jobs/{job_id}/cancel` cancels eligible jobs.

- [ ] **Step 1: Write API tests for create/status/output/cancel**
- [ ] **Step 2: Verify failure**
- [ ] **Step 3: Implement orchestration and isolated job directories**
- [ ] **Step 4: Ensure failure cleanup and structured error responses**
- [ ] **Step 5: Run the complete mocked pipeline test**
- [ ] **Step 6: Run full `pytest -q` and commit**

### Task 9: Render deployment

**Files:**
- Create: `render.yaml`
- Modify: `.env.example`
- Modify: `README.md`
- Create: `tests/test_render_config.py`

**Interfaces:**
- Render starts the service with the production ASGI command.
- Environment variables are declared as secret inputs rather than committed values.

- [ ] **Step 1: Write config validation test for required runtime command and secret variable names**
- [ ] **Step 2: Verify failure**
- [ ] **Step 3: Implement `render.yaml` with persistent configuration appropriate for Phase-1**
- [ ] **Step 4: Document FFmpeg runtime requirement and Render environment-variable setup**
- [ ] **Step 5: Run tests and commit**

### Task 10: Real-provider smoke test and acceptance test

**Files:**
- Create: `scripts/smoke_test.py`
- Create: `tests/integration/test_real_provider.py`
- Modify: `README.md`

- [ ] **Step 1: Implement an opt-in smoke test that generates exactly one 10-second clip**
- [ ] **Step 2: Run it only when `ENABLE_REAL_PROVIDER_TESTS=true` and provider secrets exist**
- [ ] **Step 3: Validate the downloaded clip**
- [ ] **Step 4: Add a full 9-clip acceptance command that is manually triggered after the single-clip smoke test passes**
- [ ] **Step 5: Verify the final 90-second MP4 and output endpoint**
- [ ] **Step 6: Confirm repository contains no YouTube OAuth/upload code or secret values**
- [ ] **Step 7: Run the full test suite and record the acceptance result**

## Completion Criteria

Phase-1 is complete only when a Render deployment can accept a topic, create nine connected 10-second AI clips using authorized fal.ai capacity, assemble ambient ASMR/music with no narration, produce a validated 1080x1920 approximately-90-second MP4, and expose that MP4 for download. No YouTube upload or publishing functionality may exist in this phase.
