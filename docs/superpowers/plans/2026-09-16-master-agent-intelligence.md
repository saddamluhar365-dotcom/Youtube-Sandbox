# Master Agent Intelligence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the persistent Level 1–3 intelligence foundation that learns YouTube, deeply snapshots an owned channel from its handle, maintains a permanent no-repeat recipe master, discovers comparable competitors, and produces validated locked production blueprints.

**Architecture:** SQLite is the local memory layer. Public channel discovery is handle-first and incremental; private analytics remain an optional future authenticated source. Intelligence records separate facts, observations, hypotheses and creative decisions. Level 3 consumes persisted intelligence and outputs a versioned `PRODUCTION_BLUEPRINT` that Level 4 can execute without inventing new creative decisions.

**Tech Stack:** Python 3.12+, SQLite, Pydantic, FastAPI, httpx, pytest.

**Spec:** `docs/superpowers/specs/2026-09-16-youtube-sandbox-design.md`

## Global Constraints

- Channel handle is the primary owned-channel input.
- Public channel data may be collected without private Analytics OAuth; private metrics must never be fabricated.
- SQLite must persist channel snapshots, incremental sync metadata, recipes and intelligence.
- API secrets remain environment-only and are never stored in SQLite.
- Recipe no-repeat checks must include exact, semantic, ingredient, cooking-method, story-angle and visual-concept overlap.
- Facts, observations, hypotheses, diagnoses and creative decisions remain separate.
- 90-second output uses exactly 9 scenes of 10 seconds each.
- Every scene contains 3–5 meaningful visual beats.
- No dialogue or narration for the locked Reelios format.
- Approximately 50% ambient village/ASMR and 50% story/recipe/transformation/reveal.
- No YouTube publishing or upload capability is introduced by this plan.

---

### Task 1: Intelligence SQLite foundation

**Files:**
- Create: `app/intelligence/db.py`
- Create: `app/intelligence/schema.py`
- Create: `app/intelligence/models.py`
- Create: `tests/intelligence/test_db.py`

**Interfaces:**
- `Database(path: Path)`
- `Database.initialize() -> None`
- `Database.connection()` context manager
- `Database.schema_version() -> int`

- [ ] Write failing tests for first-run initialization, idempotent initialization and schema version.
- [ ] Run targeted tests and verify failure.
- [ ] Implement SQLite connection settings, WAL mode, foreign keys and schema creation.
- [ ] Add migration/version metadata.
- [ ] Run targeted tests and commit.

### Task 2: Level 1 YouTube knowledge and evidence model

**Files:**
- Create: `app/intelligence/knowledge.py`
- Create: `tests/intelligence/test_knowledge.py`

**Interfaces:**
- `KnowledgeStore.add_fact(...) -> int`
- `KnowledgeStore.add_observation(...) -> int`
- `KnowledgeStore.add_hypothesis(...) -> int`
- `KnowledgeStore.list_by_topic(topic: str) -> list[KnowledgeRecord]`

- [ ] Write tests proving evidence types cannot be silently mixed.
- [ ] Implement versioned evidence records with source, claim, evidence, confidence, status and timestamps.
- [ ] Implement retrieval by topic/status.
- [ ] Ensure unsupported/unknown claims are marked unverified rather than promoted to facts.
- [ ] Run tests and commit.

### Task 3: Channel handle resolver and public ingestion contracts

**Files:**
- Create: `app/channel/models.py`
- Create: `app/channel/resolver.py`
- Create: `app/channel/ingest.py`
- Create: `tests/channel/test_resolver.py`
- Create: `tests/channel/test_ingest.py`

**Interfaces:**
- `ChannelHandleResolver.resolve(handle: str) -> ChannelIdentity`
- `ChannelIngestor.sync(identity: ChannelIdentity) -> ChannelSyncResult`

- [ ] Write tests for handle normalization, URL forms, channel-ID preservation and invalid handles.
- [ ] Implement a provider-neutral resolver interface.
- [ ] Implement public ingestion models for channel/video metadata.
- [ ] Store source IDs and hashes for incremental sync.
- [ ] Explicitly mark private Analytics fields unavailable when OAuth is absent.
- [ ] Run tests and commit.

### Task 4: Channel snapshot and incremental memory

**Files:**
- Create: `app/channel/store.py`
- Create: `app/channel/sync.py`
- Create: `tests/channel/test_sync.py`

**Interfaces:**
- `ChannelStore.save_snapshot(...) -> str`
- `ChannelStore.get_latest_snapshot(channel_id: str) -> ...`
- `ChannelSyncService.sync(handle: str) -> ChannelSyncResult`

- [ ] Write tests for first deep scan, unchanged records, new videos and changed videos.
- [ ] Implement versioned channel snapshots and per-video hashes.
- [ ] Reuse unchanged records and only re-analyze changed/new records.
- [ ] Persist last scan timestamps and analysis version.
- [ ] Run tests and commit.

### Task 5: Recipe Master and semantic no-repeat gate

**Files:**
- Create: `app/recipes/models.py`
- Create: `app/recipes/normalize.py`
- Create: `app/recipes/store.py`
- Create: `app/recipes/similarity.py`
- Create: `tests/recipes/test_normalize.py`
- Create: `tests/recipes/test_similarity.py`

**Interfaces:**
- `RecipeNormalizer.normalize(...) -> NormalizedRecipe`
- `RecipeStore.upsert_from_video(...) -> str`
- `RecipeSimilarity.check(candidate, existing) -> SimilarityResult`
- `RecipeStore.find_conflicts(candidate) -> list[RecipeConflict]`

- [ ] Write failing tests for aliases, exact duplicates and overlapping recipe concepts.
- [ ] Implement normalized names, aliases, ingredients, method, region, story/visual concepts and fingerprints.
- [ ] Implement deterministic similarity features without pretending embeddings are available.
- [ ] Implement thresholded conflict classification: exact, high, medium, low, clear.
- [ ] Run tests and commit.

### Task 6: Level 2 analysis and competitor gap engine

**Files:**
- Create: `app/channel/analyzer.py`
- Create: `app/competitors/models.py`
- Create: `app/competitors/discovery.py`
- Create: `app/competitors/gap.py`
- Create: `tests/channel/test_analyzer.py`
- Create: `tests/competitors/test_gap.py`

**Interfaces:**
- `ChannelAnalyzer.analyze(snapshot) -> ChannelAnalysis`
- `CompetitorDiscovery.discover(...) -> list[CompetitorChannel]`
- `GapAnalyzer.compare(owned, peers) -> GapReport`

- [ ] Write tests for evidence/diagnosis separation and insufficient-data behavior.
- [ ] Extract topics, pillars, hooks, formats, recipes and public performance patterns.
- [ ] Define comparable peer-group scoring without ranking creators as universally better/worse.
- [ ] Produce evidence-backed gap observations and hypotheses.
- [ ] Run tests and commit.

### Task 7: Level 3 creative decision engine

**Files:**
- Create: `app/creative/models.py`
- Create: `app/creative/decision.py`
- Create: `app/creative/world.py`
- Create: `app/creative/story.py`
- Create: `tests/creative/test_decision.py`

**Interfaces:**
- `CreativeDirector.select_recipe(...) -> RecipeDecision`
- `CreativeDirector.build_world(...) -> WorldBible`
- `CreativeDirector.build_story(...) -> StoryBlueprint`

- [ ] Write tests for scoring inputs, uniqueness gates and locked decisions.
- [ ] Score candidate recipes using visual, transformation, ASMR, story, uniqueness, demand and feasibility signals.
- [ ] Build world/character/story decisions from Level 1–2 evidence.
- [ ] Enforce draft → selected → locked transitions.
- [ ] Run tests and commit.

### Task 8: 9-scene production blueprint and validator

**Files:**
- Create: `app/creative/blueprint.py`
- Create: `app/creative/validator.py`
- Create: `tests/creative/test_blueprint.py`
- Create: `tests/creative/test_validator.py`

**Interfaces:**
- `ProductionBlueprintBuilder.build(...) -> ProductionBlueprint`
- `ProductionBlueprintValidator.validate(blueprint) -> ValidationReport`

- [ ] Write tests rejecting wrong scene count, wrong duration, missing beats and broken continuity.
- [ ] Build exactly 9 × 10-second scenes with 3–5 visual beats each.
- [ ] Add camera, composition, lighting, motion, ASMR, transitions, continuity and negative constraints.
- [ ] Lock blueprint only after validation succeeds.
- [ ] Run tests and commit.

### Task 9: Master Agent orchestration and API

**Files:**
- Create: `app/agent/master.py`
- Modify: `app/main.py`
- Create: `tests/agent/test_master.py`
- Create: `tests/api/test_channel.py`

**Interfaces:**
- `MasterAgent.analyze_channel(handle: str) -> ChannelAnalysis`
- `MasterAgent.create_blueprint(request) -> ProductionBlueprint`
- `POST /api/v1/channels/sync`
- `GET /api/v1/channels/{handle}`
- `POST /api/v1/creative/blueprints`

- [ ] Write orchestration tests with mocked providers.
- [ ] Implement handle-first channel analysis flow.
- [ ] Implement persistent memory reuse and recipe gate before blueprint creation.
- [ ] Expose only safe metadata; never expose secrets.
- [ ] Run full mocked suite and commit.

### Task 10: Provider pools and security hardening

**Files:**
- Create: `app/providers/pool.py`
- Create: `app/providers/tavily.py`
- Create: `app/providers/gemini.py`
- Create: `app/providers/huggingface.py`
- Modify: `app/config.py`
- Create: `tests/providers/test_pool.py`
- Create: `tests/security/test_secrets.py`

- [ ] Write tests for seven-slot round robin, quarantine and safe logging.
- [ ] Implement provider-neutral key pools for FAL/Gemini/Tavily/HF.
- [ ] Associate asynchronous provider requests with the credential used for submission.
- [ ] Ensure no key value reaches SQLite, API output or logs.
- [ ] Run security tests and commit.

### Task 11: Local PC bootstrap and verification

**Files:**
- Modify: `README.md`
- Modify: `.env.example`
- Create: `scripts/bootstrap_local.py`
- Create: `tests/test_bootstrap.py`

- [ ] Add one-command local initialization for directories, SQLite and readiness checks.
- [ ] Document channel-handle-first workflow and optional private Analytics integration.
- [ ] Run compileall and full pytest.
- [ ] Inspect Git diff for credentials and prohibited YouTube publishing code.
- [ ] Verify GitHub Actions status; do not claim green without an actual successful run.
