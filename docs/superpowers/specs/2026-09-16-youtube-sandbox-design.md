# YouTube Sandbox — Master Agent Architecture Design

## 1. Goal
Build a local-first, high-quality YouTube content intelligence and production sandbox. The system is not a simple automation script. It maintains persistent knowledge about YouTube, persistent intelligence about the owned channel, a no-repeat recipe/content catalog, competitor intelligence, and a production director that creates a locked blueprint before video generation.

The first implementation target is a PC-local sandbox. Provider credentials are supplied through environment variables only. SQLite is initialized automatically on first run. YouTube publishing/OAuth is out of scope for the initial build.

## 2. Provider Configuration
The provider layer supports independent pools of up to seven credentials per provider:

- fal.ai: `FAL_KEY_1` through `FAL_KEY_7` — video/media generation.
- Google Gemini: `GEMINI_KEY_1` through `GEMINI_KEY_7` — structured reasoning, extraction, planning and analysis.
- Tavily: `TAVILY_KEY_1` through `TAVILY_KEY_7` — web research/search.
- Hugging Face: `HF_TOKEN_1` through `HF_TOKEN_7` — character/reference image generation.

Provider pools use round-robin selection, bounded retry behavior, temporary quarantine for failed/rate-limited credentials, and safe logging. Credential values are never stored in SQLite, returned by APIs, or committed to Git.

## 3. System Layers

### Level 1 — YouTube Algorithm Knowledge Base
Purpose: build an evidence-backed, versioned knowledge base describing how YouTube discovery/recommendation and viewer response work.

Sources are classified separately as:
- `official_fact` — directly supported by authoritative YouTube documentation.
- `observed_data` — measurements from owned/authorized channel analytics.
- `external_evidence` — researched external material.
- `hypothesis` — an agent inference that requires validation.

The knowledge base covers recommendation surfaces, Shorts behavior, Search, viewer satisfaction, appeal, engagement, retention, traffic sources, topic interest, competition, seasonality and related documented concepts. It must not claim access to a secret or exact YouTube algorithm formula.

Every knowledge record has source, claim, evidence, collection/verification timestamps, confidence, status and version metadata.

### Level 2 — Channel Intelligence & Competitor Gap Engine
Purpose: deeply understand the owned channel once, persist the resulting snapshot, and thereafter perform incremental synchronization instead of repeatedly re-analyzing the complete channel.

First deep scan builds:
- channel profile and description;
- niche, sub-niches and content pillars;
- complete public video/Short inventory;
- titles, descriptions and hashtags;
- topics, recipes/dishes and ingredients;
- hooks, story structures and visual patterns;
- available authorized analytics and performance metrics;
- winners, average performers, underperformers and outliers.

The recipe master catalog is mandatory. Each dish/recipe receives normalized naming, alternate names, ingredients, main ingredient, cooking method, region, story angle, visual concept, ASMR elements and a similarity fingerprint. New ideas must pass an anti-repeat gate against exact, semantic, ingredient, method, story and visual overlap.

Channel snapshots are versioned. Incremental sync detects new or changed content/metrics and updates only affected records and analyses.

Competitor discovery is based on topic, audience, format, language, content promise and comparable scale, not merely keyword similarity. Competitor channels and videos receive persistent records. Gap analysis compares the owned channel with its peer group and distinguishes evidence from hypotheses.

### Level 3 — Creative Production Director
Purpose: convert Level 1 knowledge and Level 2 intelligence into one locked production blueprint before generation.

The director finalizes:
- topic;
- recipe/dish;
- story concept and emotional arc;
- village/cozy ASMR world;
- character bible;
- character reference image plan;
- reference image prompts;
- 9-scene storyboard;
- camera angles and movement;
- composition and lens/look;
- lighting and environment;
- character actions and continuity;
- ambient ASMR and soft music direction;
- negative constraints;
- final image/video/audio prompts.

The target format is 90 seconds made from exactly nine independent 10-second clips. Every clip contains 3–5 meaningful visual beats and is connected to neighboring clips. The target visual direction is Ghibli-inspired 2D village atmosphere, with no dialogue or narration and approximately 50% village/ambient life and 50% recipe/story/transformation/reveal content.

Major creative decisions progress through `draft -> selected -> locked`. A locked recipe, character, world, story, camera language, audio direction or scene plan cannot be silently changed during production.

The final artifact is a versioned `PRODUCTION_BLUEPRINT` consumed by the production layer.

### Level 4 — Production Executor
Purpose: execute only the approved Level 3 blueprint.

The executor generates character references through the configured image provider, generates the nine video clips through the configured video provider, obtains/creates audio, assembles media with FFmpeg, validates every quality gate and stores the final artifact. The executor must not invent a new recipe, story, character or visual direction when a locked blueprint exists.

## 4. Persistence Model
SQLite is the system memory and job state store for the local sandbox. It is initialized automatically on first startup.

Core domains include:
- provider configuration metadata and health state (never secret values);
- jobs and job state transitions;
- Level 1 knowledge and evidence;
- channel snapshots and public/authorized analytics;
- recipes, dishes, ingredients and similarity fingerprints;
- competitor channels and videos;
- performance patterns, diagnoses and hypotheses;
- creative projects, recipe decisions, character bibles, references, world bibles;
- story and scene blueprints;
- prompt packs and production blueprints;
- experiment definitions and results.

Generated media is stored in isolated per-job directories. Database records contain paths/identifiers and metadata rather than embedding large media files.

## 5. Channel Data Ingestion
The system supports two distinct data classes:

1. Public channel data: discoverable channel/video metadata and public performance signals.
2. Private/authorized analytics: data available only through an authenticated YouTube analytics integration when that integration is later configured.

Tavily is used for research and public web discovery; it is not treated as a substitute for private YouTube Analytics access.

## 6. Incremental Memory Strategy
Each major dataset carries synchronization metadata such as source identifier, content hash where applicable, first-seen time, last-seen time, last-synchronized time and analysis version.

On subsequent runs:
- unchanged records are reused;
- new records are ingested and analyzed;
- changed records trigger targeted re-analysis;
- historical snapshots remain available for longitudinal comparison.

The system therefore avoids a full channel deep analysis for every new Short.

## 7. Evidence and Decision Integrity
The agent must never mix facts and guesses. Knowledge, observations, hypotheses, diagnoses and creative decisions remain distinct records.

Each hypothesis/diagnosis stores evidence references, confidence, sample size when applicable, created/updated timestamps and validation status.

Recommendations must explain what evidence supports them and must not guarantee virality. The system optimizes for measurable learning and improved decision quality rather than claiming deterministic control over YouTube distribution.

## 8. Level 3 Production Blueprint Schema
A production blueprint contains:

- project metadata and target format;
- final recipe and decision rationale;
- character bible and reference requirements;
- reference image prompts/results;
- world/environment bible;
- story premise and emotional arc;
- audio direction;
- nine scene records, each exactly 10 seconds;
- 3–5 visual beats per scene;
- camera/composition/lighting/motion/continuity instructions;
- image/video/audio prompts and negative constraints;
- blueprint version and lock status.

A blueprint validator must reject incomplete or internally inconsistent plans before Level 4 execution.

## 9. Security
- All provider secrets come from environment variables.
- `.env` remains ignored by Git.
- SQLite contains no plaintext API credentials.
- API responses and logs redact provider secrets and authorization headers.
- Provider failures are handled without attempting to bypass quotas or rate limits.
- No YouTube publishing, upload, scheduling or OAuth write capability is included in the initial production executor.

## 10. Initial Local PC Experience
The repository must be self-contained for local setup:

1. Run the setup script.
2. Create/verify Python environment and dependencies.
3. Check FFmpeg.
4. Create required directories.
5. Initialize SQLite schema automatically.
6. Create/validate local configuration from `.env`.
7. Start the local API/UI.
8. Report dependency/provider readiness through `/health` without exposing secrets.

No manual SQLite creation or schema command should be required for normal first-run setup.

## 11. Testing Strategy
Tests must cover:
- SQLite initialization and migrations;
- provider key-pool routing and quarantine;
- Level 1 evidence classification;
- Level 2 channel snapshot/incremental sync;
- recipe normalization and duplicate/similarity gate;
- competitor scoring and gap analysis;
- Level 3 blueprint validation and lock behavior;
- prompt-pack schema validation;
- media generation orchestration with mocked providers;
- FFmpeg command construction and final media validation;
- API/job state transitions;
- security checks ensuring secrets are not persisted or returned.

Real provider tests are opt-in and must use configured credentials. They must not be required for ordinary CI.

## 12. Explicit Non-Goals for the Initial Build
- YouTube automatic publishing/scheduling.
- Guaranteed viral outcomes.
- Quota/rate-limit circumvention.
- Multi-user billing/authentication.
- Treating unverified web claims as algorithm facts.
- Re-running full channel analysis for every content request.
