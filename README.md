# YouTube Sandbox — Master Agent

Production-oriented, local-first YouTube Shorts intelligence and generation agent for **90-second vertical Shorts built from exactly 9 × 10-second clips**.

## Agent architecture

1. **Level 1 — YouTube Knowledge Base**: evidence-aware storage for official facts, observed channel data, external evidence and hypotheses. Evidence classes are never silently mixed.
2. **Level 2 — Channel Intelligence**: handle → channel ID resolution, public channel/video ingestion, incremental snapshots, recipe master, semantic no-repeat gate, comparable competitor discovery and public-data gap analysis.
3. **Level 3 — Creative Director**: recipe decision, world bible, story blueprint and validated 9-scene production blueprint.
4. **Generation pipeline**: 9 × 10-second video generation, audio, FFmpeg assembly and final media validation.
5. **Provider security**: isolated seven-slot pools for fal.ai, Gemini, Tavily and Hugging Face with round-robin acquisition, temporary quarantine and redacted health state.

## Locked production rules

- Exactly 9 clips × 10 seconds = 90 seconds.
- Every clip is a connected 3–5 beat mini-sequence; static single-action clips are rejected by the blueprint validator.
- Ambient/cozy village visuals and story/food transformation are both represented in the blueprint.
- No dialogue, narration or text overlays in the generated production prompts.
- Recipe Master blocks exact and semantic duplicates, including alias/ingredient/method/story overlap.
- YouTube OAuth/upload/publishing remains disabled until explicitly added.

## Data and security

- SQLite is the local intelligence database; secrets are never stored there.
- Provider credentials are read from environment variables only: `FAL_KEY_1..7`, `GEMINI_KEY_1..7`, `TAVILY_KEY_1..7`, `HF_TOKEN_1..7`.
- `.env.example` contains names only; never commit real keys.
- CI runs tests, Python compilation and the repository secret scanner.
- Provider errors exposed to health state are redacted against the originating credential.
- Public YouTube sync is public-data only. Private YouTube Analytics requires authenticated YouTube/Analytics access and is not fabricated by this system.

## Local PC setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install .
Copy-Item .env.example .env
pytest -q
python -m compileall app
python scripts/security_scan.py
uvicorn app.main:app --host 0.0.0.0 --port 10000
```

Set the real provider keys in the local environment before using external generation/research providers. Do not put them in source files, JSON requests, SQLite, GitHub or logs.

## API

- `GET /health` — service, provider readiness and intelligence schema state.
- `POST /api/v1/channels/sync` — resolve a channel handle and perform public incremental ingestion + analysis.
- `GET /api/v1/channels/{handle}` — return the latest persisted public analysis.
- `POST /api/v1/creative/blueprints` — validate and build a 9-scene production blueprint.
- `POST /api/v1/jobs` — run the generation pipeline after a topic is supplied.
- `GET /api/v1/jobs/{job_id}` — job status.
- `GET /api/v1/jobs/{job_id}/output` — validated MP4.
- `POST /api/v1/jobs/{job_id}/cancel` — safe cancellation before generation starts.

## Verification gate

The branch is not considered release-ready until GitHub Actions is **GREEN** for the exact branch head. Real provider smoke tests should only be enabled intentionally after local configuration; CI does not consume production credentials.
