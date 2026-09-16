from __future__ import annotations

SCHEMA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS provider_health (
    provider TEXT NOT NULL,
    slot INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'unknown',
    failure_count INTEGER NOT NULL DEFAULT 0,
    quarantined_until TEXT,
    last_error_code TEXT,
    last_checked_at TEXT,
    PRIMARY KEY (provider, slot),
    CHECK (slot BETWEEN 1 AND 7)
);

CREATE TABLE IF NOT EXISTS channel_profiles (
    channel_id TEXT PRIMARY KEY,
    channel_handle TEXT NOT NULL,
    channel_url TEXT,
    title TEXT,
    description TEXT,
    country TEXT,
    custom_url TEXT,
    published_at TEXT,
    source TEXT NOT NULL DEFAULT 'public',
    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_sync_at TEXT,
    data_hash TEXT,
    analysis_version INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_channel_profiles_handle
    ON channel_profiles(channel_handle);

CREATE TABLE IF NOT EXISTS channel_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL REFERENCES channel_profiles(channel_id) ON DELETE CASCADE,
    snapshot_version INTEGER NOT NULL,
    captured_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_hash TEXT NOT NULL,
    analysis_version INTEGER NOT NULL DEFAULT 1,
    video_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'complete',
    UNIQUE(channel_id, snapshot_version)
);

CREATE INDEX IF NOT EXISTS idx_channel_snapshots_channel
    ON channel_snapshots(channel_id, snapshot_version DESC);

CREATE TABLE IF NOT EXISTS channel_videos (
    video_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL REFERENCES channel_profiles(channel_id) ON DELETE CASCADE,
    snapshot_id TEXT REFERENCES channel_snapshots(snapshot_id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    description TEXT,
    published_at TEXT,
    duration_seconds REAL,
    is_short INTEGER NOT NULL DEFAULT 0 CHECK (is_short IN (0, 1)),
    view_count INTEGER,
    like_count INTEGER,
    comment_count INTEGER,
    thumbnail_url TEXT,
    data_hash TEXT NOT NULL,
    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_analyzed_at TEXT,
    analysis_version INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_channel_videos_channel
    ON channel_videos(channel_id, published_at DESC);

CREATE TABLE IF NOT EXISTS video_topics (
    video_id TEXT NOT NULL REFERENCES channel_videos(video_id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.0,
    source TEXT NOT NULL DEFAULT 'analysis',
    PRIMARY KEY(video_id, topic)
);

CREATE TABLE IF NOT EXISTS recipes (
    recipe_id TEXT PRIMARY KEY,
    normalized_name TEXT NOT NULL,
    main_ingredient TEXT,
    cooking_method TEXT,
    region TEXT,
    food_category TEXT,
    story_angle TEXT,
    visual_concept TEXT,
    asmr_elements TEXT,
    aliases_json TEXT NOT NULL DEFAULT '[]',
    ingredients_json TEXT NOT NULL DEFAULT '[]',
    similarity_fingerprint TEXT NOT NULL,
    first_used_at TEXT,
    last_used_at TEXT,
    use_count INTEGER NOT NULL DEFAULT 0,
    source_video_id TEXT REFERENCES channel_videos(video_id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_recipes_normalized_name
    ON recipes(normalized_name);
CREATE INDEX IF NOT EXISTS idx_recipes_main_ingredient
    ON recipes(main_ingredient);
CREATE INDEX IF NOT EXISTS idx_recipes_fingerprint
    ON recipes(similarity_fingerprint);

CREATE TABLE IF NOT EXISTS knowledge_records (
    knowledge_id INTEGER PRIMARY KEY AUTOINCREMENT,
    evidence_type TEXT NOT NULL CHECK (
        evidence_type IN ('official_fact', 'observed_data', 'external_evidence', 'hypothesis')
    ),
    topic TEXT NOT NULL,
    claim TEXT NOT NULL,
    evidence TEXT NOT NULL,
    source_url TEXT,
    source_name TEXT,
    source_published_at TEXT,
    collected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_verified_at TEXT,
    confidence REAL NOT NULL DEFAULT 0.0 CHECK (confidence BETWEEN 0.0 AND 1.0),
    status TEXT NOT NULL DEFAULT 'unverified',
    version INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_knowledge_topic
    ON knowledge_records(topic, evidence_type, status);

CREATE TABLE IF NOT EXISTS competitors (
    competitor_id TEXT PRIMARY KEY,
    channel_id TEXT,
    channel_handle TEXT,
    channel_url TEXT,
    title TEXT,
    niche TEXT,
    language TEXT,
    scale_band TEXT,
    discovery_source TEXT,
    data_hash TEXT,
    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS performance_patterns (
    pattern_id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT NOT NULL REFERENCES channel_profiles(channel_id) ON DELETE CASCADE,
    pattern_type TEXT NOT NULL,
    description TEXT NOT NULL,
    evidence_json TEXT NOT NULL DEFAULT '{}',
    confidence REAL NOT NULL DEFAULT 0.0 CHECK (confidence BETWEEN 0.0 AND 1.0),
    sample_size INTEGER,
    status TEXT NOT NULL DEFAULT 'observed',
    analysis_version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS hypotheses (
    hypothesis_id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT REFERENCES channel_profiles(channel_id) ON DELETE CASCADE,
    hypothesis_type TEXT NOT NULL,
    statement TEXT NOT NULL,
    evidence_json TEXT NOT NULL DEFAULT '[]',
    confidence REAL NOT NULL DEFAULT 0.0 CHECK (confidence BETWEEN 0.0 AND 1.0),
    validation_status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS creative_projects (
    project_id TEXT PRIMARY KEY,
    channel_id TEXT REFERENCES channel_profiles(channel_id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    topic TEXT NOT NULL,
    format TEXT NOT NULL DEFAULT '90s_short',
    duration_seconds INTEGER NOT NULL DEFAULT 90,
    blueprint_version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recipe_decisions (
    decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL REFERENCES creative_projects(project_id) ON DELETE CASCADE,
    recipe_id TEXT NOT NULL REFERENCES recipes(recipe_id) ON DELETE RESTRICT,
    decision_status TEXT NOT NULL DEFAULT 'draft',
    rationale TEXT NOT NULL,
    score REAL,
    decided_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    locked_at TEXT
);

CREATE TABLE IF NOT EXISTS story_blueprints (
    story_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES creative_projects(project_id) ON DELETE CASCADE,
    premise TEXT NOT NULL,
    emotional_arc TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    version INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS scene_blueprints (
    project_id TEXT NOT NULL REFERENCES creative_projects(project_id) ON DELETE CASCADE,
    scene_index INTEGER NOT NULL CHECK (scene_index BETWEEN 1 AND 9),
    duration_seconds INTEGER NOT NULL CHECK (duration_seconds = 10),
    purpose TEXT NOT NULL,
    beats_json TEXT NOT NULL,
    camera_json TEXT NOT NULL,
    lighting TEXT NOT NULL,
    motion TEXT NOT NULL,
    asmr TEXT NOT NULL,
    transition TEXT NOT NULL,
    continuity_json TEXT NOT NULL DEFAULT '{}',
    prompt TEXT NOT NULL,
    negative_constraints TEXT NOT NULL,
    PRIMARY KEY(project_id, scene_index)
);

CREATE TABLE IF NOT EXISTS production_blueprints (
    blueprint_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES creative_projects(project_id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    payload_json TEXT NOT NULL,
    validation_json TEXT NOT NULL DEFAULT '{}',
    locked_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, version)
);
"""
