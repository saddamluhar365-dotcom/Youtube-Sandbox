# YouTube Sandbox Master Agent v2 — Production Architecture

## Goal
Build a PC-local, evidence-driven YouTube Shorts intelligence and production agent that analyzes one owned YouTube channel plus five reference channels using public data only, deeply inspects public videos, persists intelligence in SQLite, creates a locked production blueprint, generates one locked character reference pack, generates exactly nine connected 10-second clips sequentially, edits them automatically, enhances the final video for YouTube Shorts 1080x1920 delivery, exports the recipe-named MP4 outside the project sandbox, and cleans temporary sandbox assets only after successful verification.

## Public-Data-Only Boundary
No YouTube OAuth, Studio-private analytics, account cookies, passwords, private audience data, private CTR, private impressions, private retention, or publishing capability is required. Handle is the primary channel input. Public channel/video metadata and publicly accessible video content are the analysis source. When a signal cannot be established from public evidence, the system records `INSUFFICIENT_DATA` rather than inventing it.

## Provider Architecture
Providers are capability-locked at the workflow/project level; credential slots are independently rotatable.

- Tavily: web research/search only; `TAVILY_KEY_1` ... `TAVILY_KEY_7`.
- Gemini: LLM reasoning, extraction, planning and structured analysis only; `GEMINI_KEY_1` ... `GEMINI_KEY_7`.
- Hugging Face: character/reference image generation; `HF_TOKEN_1` ... `HF_TOKEN_7`.
- Video provider: either fal.ai or Hugging Face, selected before production and locked for the entire Short; its credential/token slot may rotate within that provider.

Provider fallback never silently crosses provider boundaries. Key rotation handles rate limits, transient failures and temporary credential quarantine without bypassing provider quotas. Request-to-key association is persisted so polling uses the submitting credential when provider semantics require it.

Secrets are never stored in SQLite, logs, API responses or Git. SQLite stores only provider identity, key slot identifier, health state, usage/error metadata and timestamps.

## Level 1 — YouTube Algorithm Knowledge Base
Maintain a versioned evidence base of authoritative YouTube public documentation and clearly separated external evidence. Classify records as `OFFICIAL_FACT`, `OBSERVATION`, `HYPOTHESIS`, `CREATIVE_DECISION`, or `UNVERIFIED`. Store source, claim, evidence, collected/verified timestamps, confidence, status, version and references. Never claim an exact secret algorithm formula or guarantee virality.

## Level 2 — Channel Intelligence and Reference Gap Engine
Input is one owned channel handle plus five reference channel handles/URLs.

### Channel resolution
Resolve every handle to a stable channel ID and persist handle/channel mapping. The owned channel is `OWN`; the five supplied channels are `REFERENCE_1` through `REFERENCE_5`.

### First deep scan
For all six channels, ingest public channel metadata and the complete public video/Short inventory available to the ingestion source. Analyze actual video content, not metadata alone. Videos are downloaded/cached as needed for analysis and inspected through playback/timeline/frame sampling. Analysis includes hook timing, scene/shot boundaries, visual changes, pacing, camera/framing/movement, characters, setting, props, recipes, ingredients, cooking actions, transformations, story structure, transitions, audio/ASMR events, titles, descriptions, hashtags, thumbnails, publish timing and public performance signals.

### Incremental memory
Persist channel and video snapshots, hashes, first/last seen times, last sync times and analysis versions. On later runs: unchanged content is reused; new content is analyzed; changed content triggers targeted re-analysis. Historical snapshots remain available.

### Recipe Master / no-repeat gate
Every detected recipe/dish from the owned channel is permanently normalized and stored during the first deep scan. Store alternate names, ingredients, main ingredient, method, region/origin, category, story angle, visual concept, ASMR elements, source video, use count and similarity fingerprint. New concepts are checked against exact names, semantic similarity, ingredient overlap, cooking method, story angle, visual concept and previous usage. Similar dishes are treated as potential repeats even when names differ.

### Reference-channel intelligence
Persist all five reference channels and their videos as a comparable peer set. Analyze top/recent/low performers, recurring formats, hooks, titles, visual patterns, pacing, topics, recipes, story structures and saturation. Compare against the owned channel and produce evidence-backed gaps, hypotheses, recommended experiments and confidence levels.

## Level 3 — Creative Production Director
Convert Level 1 + Level 2 intelligence into a complete locked `PRODUCTION_BLUEPRINT` before any generation.

Flow: topic candidates → scoring → recipe candidates → no-repeat gate → final recipe → concept → world bible → character bible → reference plan → story → nine scene plans → camera → lighting → motion → ASMR/music → continuity → model/provider capability analysis → model-specific prompt optimization → validation → lock.

Target content: exactly 90 seconds as nine independent 10-second clips. Every clip has 3–5 meaningful visual beats and connected continuity, with new visual information approximately every 1–2 seconds. Approximately 50% of the final visual runtime is village/cozy/ambient life and approximately 50% is story/food/transformation/reveal. Newer Reelios workflow uses Ghibli-inspired 2D village atmosphere and no dialogue or narration. Character personal names are never emitted in public SEO metadata.

### Model-aware prompting
Before generation, inspect the capabilities of available models. Choose the best compatible model for the project and lock it. Prompts are optimized for the locked model's actual limits and strengths without changing creative intent. A model/provider change is allowed only before production starts, or through an explicit recovery decision when the locked provider/model cannot technically execute a required capability. No mid-project random model switching.

### Reference image lock
Character reference images are always generated through Hugging Face. One reference pack is generated, verified and locked for the entire Short. The pack may contain front, back, left, right, full-body, face and expression/detail views as required by the selected workflow. The same locked pack is reused across all nine scenes.

## Level 4 — Production Executor
Execute only the approved blueprint.

Reference assets are generated one at a time. Each asset is generated, completed, downloaded immediately, verified, hashed, saved to the project sandbox and registered in SQLite before the next asset starts.

Video clips are generated strictly sequentially. For each scene: submit → wait → immediately download → verify → hash → save `scene_XX.mp4` → register metadata → proceed to the next scene. If a clip fails, retry the same scene with the same locked provider/model while rotating only credential slots inside that provider. Do not generate all nine first and download later.

The per-project sandbox contains blueprint, references, videos, audio/intermediate assets, previews, final render staging, metadata and logs. Large media is stored on disk; SQLite stores identifiers, paths and metadata.

## Level 5 — AI Editor, Assembly and Delivery
After all nine clips pass production QA, an AI editing engine assembles the Short. It may auto-trim dead/awkward frames, choose appropriate transitions, optimize pacing, synchronize ASMR/music, and add subtle effects only when they improve storytelling, continuity or viewer experience. It must not arbitrarily change the locked story, recipe, character or scene order.

After editing and timeline lock, create the final YouTube Shorts master at 1080x1920. Enhancement is quality-aware: high-quality scaling/upscaling, artifact/noise reduction where useful, detail preservation, frame-rate consistency, color/contrast consistency, audio normalization, peak/loudness checks and YouTube-friendly encoding. Merely changing dimensions is not considered enhancement.

Final QA checks duration, 1080x1920 dimensions, codec readability, audio presence/health, black/frozen/broken frames, continuity, encoding integrity, file size and output accessibility.

## Final Delivery and Cleanup
After final master creation and successful verification, export the final MP4 outside the sandbox into the project output directory using a sanitized recipe name, e.g. `output/<Recipe-Name>.mp4`.

Only after the external output is verified does the system remove temporary sandbox media: generated clips, reference copies, intermediate renders, temporary audio, download cache and temporary processing artifacts. Permanent intelligence remains in SQLite: channel snapshots, video analysis, recipe master, competitor/reference intelligence, blueprints, generation metadata, QA results and learning history.

If any final validation or export step fails, cleanup does not run; the sandbox remains resumable.

## Persistence
SQLite is initialized automatically. Core entities include providers/key health, jobs, channel profiles/snapshots/videos, video observations, recipes/dishes/ingredients, hooks/titles/formats, competitor/reference channels/videos, performance patterns, hypotheses/diagnoses, creative projects, recipe decisions, character/world/story/scene blueprints, reference assets, prompt packs, production locks, generation requests/results, edit decisions, QA results and output artifacts.

## Testing and Verification
Use TDD for new components. Tests cover provider key routing/quarantine, provider/model lock behavior, handle/channel mapping, incremental sync, video-analysis evidence records, recipe normalization and semantic no-repeat checks, Level 3 blueprint completeness/locks, model-specific prompt optimization, sequential generate-download orchestration, editing decisions, 1080x1920 delivery validation, safe cleanup, API state transitions and secret redaction. Real provider tests are opt-in.

CI must pass before work is claimed complete. If verification fails, repair and rerun until green; never claim green without actual evidence.

## Initial Scope Exclusions
YouTube upload/publishing/scheduling, private analytics/OAuth, quota circumvention, fabricated algorithm claims and automatic provider switching during an active production are excluded.
