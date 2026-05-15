-- KnowledgeOS Database Schema
-- Postgres 16
-- Generated from migrations 0001–0009
-- All UUIDs use gen_random_uuid() (requires pgcrypto extension)

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ─── Users ────────────────────────────────────────────────────────────────────

CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT NOT NULL UNIQUE,
    display_name  TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at    TIMESTAMPTZ
);

-- ─── Sessions ─────────────────────────────────────────────────────────────────

CREATE TABLE sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  TEXT NOT NULL UNIQUE,
    user_agent  TEXT,
    ip_address  TEXT,
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_sessions_user_id    ON sessions(user_id);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);

-- ─── Objects ──────────────────────────────────────────────────────────────────
-- Universal base record for all knowledge items.
-- kind is a String(32) validated in application code — no DB CHECK constraint.
-- Valid kinds: page, asset, source, chat, project, claim, task,
--              resume_bullet_set, interview_story, note, bookmark, collection.

CREATE TABLE objects (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind         TEXT NOT NULL,
    title        TEXT NOT NULL DEFAULT '',
    description  TEXT,
    tags         TEXT[] NOT NULL DEFAULT '{}',
    metadata     JSONB NOT NULL DEFAULT '{}',
    is_pinned    BOOLEAN NOT NULL DEFAULT false,
    is_archived  BOOLEAN NOT NULL DEFAULT false,
    ai_generated BOOLEAN NOT NULL DEFAULT false,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at   TIMESTAMPTZ
);

CREATE INDEX idx_objects_user_id         ON objects(user_id);
CREATE INDEX idx_objects_kind            ON objects(kind);
CREATE INDEX idx_objects_created_at      ON objects(created_at DESC);
CREATE INDEX idx_objects_deleted_at_null ON objects(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX idx_objects_tags            ON objects USING GIN(tags);

-- ─── Pages ────────────────────────────────────────────────────────────────────

CREATE TABLE pages (
    id           UUID PRIMARY KEY REFERENCES objects(id) ON DELETE CASCADE,
    content_json JSONB NOT NULL DEFAULT '{}',
    content_text TEXT NOT NULL DEFAULT '',
    word_count   INT NOT NULL DEFAULT 0,
    version      INT NOT NULL DEFAULT 1,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─── Assets ───────────────────────────────────────────────────────────────────

CREATE TABLE assets (
    id            UUID PRIMARY KEY REFERENCES objects(id) ON DELETE CASCADE,
    filename      TEXT NOT NULL,
    content_type  TEXT NOT NULL,
    size_bytes    BIGINT NOT NULL,
    sha256        TEXT NOT NULL,
    storage_path  TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'uploading'
                  CHECK (status IN ('uploading', 'ready', 'error')),
    width         INT,
    height        INT,
    duration_secs FLOAT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_assets_sha256 ON assets(sha256);
CREATE INDEX idx_assets_status ON assets(status);

-- ─── Sources — Phase 2 ────────────────────────────────────────────────────────
-- Migration 0002: source_type_enum + sources table.

CREATE TYPE source_type_enum AS ENUM (
    'pdf', 'image', 'video', 'audio', 'youtube', 'web', 'csv', 'file'
);

CREATE TABLE sources (
    id               UUID PRIMARY KEY REFERENCES objects(id) ON DELETE CASCADE,
    source_type      source_type_enum NOT NULL,
    url              TEXT,
    asset_id         UUID REFERENCES objects(id) ON DELETE SET NULL,
    ingestion_status VARCHAR(16) NOT NULL DEFAULT 'pending',
    extracted_text   TEXT,
    page_count       INT,
    thumbnail_path   TEXT,
    preview_data     JSONB,
    error_message    TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_sources_ingestion_status ON sources(ingestion_status);

-- ─── Edges ────────────────────────────────────────────────────────────────────
-- Edge kind is validated in application code so legacy and future graph kinds
-- can coexist without a destructive enum/check migration.

CREATE TABLE edges (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_id  UUID NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
    target_id  UUID NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
    kind       TEXT NOT NULL DEFAULT 'link',
    weight     FLOAT NOT NULL DEFAULT 1.0,
    metadata   JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    UNIQUE (source_id, target_id, kind)
);

CREATE INDEX idx_edges_source_id ON edges(source_id);
CREATE INDEX idx_edges_target_id ON edges(target_id);
CREATE INDEX idx_edges_user_id   ON edges(user_id);

-- ─── Chunks ───────────────────────────────────────────────────────────────────
-- Migration 0001: base columns.
-- Migration 0003: user_id, search-readiness fields for idempotent indexing.

CREATE TABLE chunks (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    object_id        UUID NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
    user_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    chunk_idx        INT NOT NULL,
    content          TEXT NOT NULL,
    token_count      INT,
    metadata         JSONB NOT NULL DEFAULT '{}',
    source_locator   JSONB,
    content_hash     TEXT,
    embedding_status VARCHAR(16) NOT NULL DEFAULT 'pending',
    embedding_model  TEXT,
    embedded_at      TIMESTAMPTZ,
    qdrant_point_id  TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (object_id, chunk_idx)
);

CREATE INDEX idx_chunks_object_id       ON chunks(object_id);
CREATE INDEX ix_chunks_user_id          ON chunks(user_id);
CREATE INDEX ix_chunks_embedding_status ON chunks(embedding_status);
CREATE INDEX ix_chunks_content_hash     ON chunks(content_hash);

-- ─── Ingestion Jobs ───────────────────────────────────────────────────────────

CREATE TABLE ingestion_jobs (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    object_id    UUID REFERENCES objects(id) ON DELETE SET NULL,
    status       TEXT NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending', 'running', 'done', 'failed')),
    job_type     TEXT NOT NULL,
    payload      JSONB NOT NULL DEFAULT '{}',
    result       JSONB,
    error        TEXT,
    attempts     INT NOT NULL DEFAULT 0,
    max_attempts INT NOT NULL DEFAULT 3,
    enqueued_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at   TIMESTAMPTZ,
    finished_at  TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_ingestion_jobs_status  ON ingestion_jobs(status);
CREATE INDEX idx_ingestion_jobs_user_id ON ingestion_jobs(user_id);

-- ─── Agent Runs ───────────────────────────────────────────────────────────────

CREATE TABLE agent_runs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status        TEXT NOT NULL DEFAULT 'running'
                  CHECK (status IN ('running', 'done', 'failed', 'cancelled')),
    agent_type    TEXT NOT NULL,
    input         JSONB NOT NULL DEFAULT '{}',
    output        JSONB,
    error         TEXT,
    model         TEXT,
    input_tokens  INT,
    output_tokens INT,
    cost_usd      NUMERIC(10, 6),
    started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at   TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_agent_runs_user_id ON agent_runs(user_id);
CREATE INDEX idx_agent_runs_status  ON agent_runs(status);

-- ─── Object Revisions — Phase 5 ──────────────────────────────────────────────
-- Migration 0004: audit trail for user and agent writes.
-- Also adds objects.ai_generated (see ALTER TABLE above, folded into CREATE TABLE).

CREATE TABLE object_revisions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    object_id       UUID NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rev_num         INT NOT NULL,
    changed_by      VARCHAR(64) NOT NULL DEFAULT 'user',
    agent_run_id    UUID REFERENCES agent_runs(id) ON DELETE SET NULL,
    before_snapshot JSONB NOT NULL DEFAULT '{}',
    after_snapshot  JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (object_id, rev_num)
);

CREATE INDEX ix_object_revisions_object_id  ON object_revisions(object_id);
CREATE INDEX ix_object_revisions_user_id    ON object_revisions(user_id);
CREATE INDEX ix_object_revisions_agent_run  ON object_revisions(agent_run_id);

-- ─── Chats — Phase 6A + 6B ────────────────────────────────────────────────────
-- Migration 0005: base chats table.
-- Migration 0006: structured_summary_* columns.

CREATE TABLE chats (
    id                               UUID PRIMARY KEY REFERENCES objects(id) ON DELETE CASCADE,
    provider                         VARCHAR(32) NOT NULL,
    external_chat_id                 TEXT,
    source_filename                  TEXT,
    raw_storage_path                 TEXT NOT NULL,
    raw_format                       VARCHAR(16) NOT NULL,
    turn_count                       INT NOT NULL DEFAULT 0,
    started_at                       TIMESTAMPTZ,
    ended_at                         TIMESTAMPTZ,
    imported_at                      TIMESTAMPTZ NOT NULL DEFAULT now(),
    parsed_turns                     JSONB NOT NULL DEFAULT '[]',
    content_text                     TEXT NOT NULL DEFAULT '',
    metadata                         JSONB NOT NULL DEFAULT '{}',
    structured_summary               JSONB,
    structured_summary_status        VARCHAR(16) NOT NULL DEFAULT 'none',
    structured_summary_agent_run_id  UUID REFERENCES agent_runs(id) ON DELETE SET NULL,
    structured_summary_updated_at    TIMESTAMPTZ,
    structured_summary_hash          VARCHAR(64),
    created_at                       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_chats_provider                   ON chats(provider);
CREATE INDEX ix_chats_imported_at                ON chats(imported_at);
CREATE INDEX ix_chats_structured_summary_status  ON chats(structured_summary_status);

-- ─── Projects — Phase 9A ──────────────────────────────────────────────────────
-- Migration 0007: career project memory.

CREATE TABLE projects (
    id                          UUID PRIMARY KEY REFERENCES objects(id) ON DELETE CASCADE,
    period_start                DATE,
    period_end                  DATE,
    role                        TEXT,
    organization                TEXT,
    problem                     TEXT,
    actions                     TEXT,
    results                     TEXT,
    metrics                     JSONB NOT NULL DEFAULT '{}',
    skills                      TEXT[] NOT NULL DEFAULT '{}',
    status                      VARCHAR(16) NOT NULL DEFAULT 'active',
    confidence                  VARCHAR(16) NOT NULL DEFAULT 'manual',
    extracted_from              UUID REFERENCES objects(id) ON DELETE SET NULL,
    extracted_by_agent_run_id   UUID REFERENCES agent_runs(id) ON DELETE SET NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_projects_period_start ON projects(period_start);
CREATE INDEX ix_projects_period_end   ON projects(period_end);
CREATE INDEX ix_projects_status       ON projects(status);
CREATE INDEX ix_projects_skills       ON projects USING GIN(skills);

-- ─── Workspaces — Phase 8B ────────────────────────────────────────────────────
-- Migration 0008: named multi-pane UI layouts.
-- Workspaces are personal application state, not knowledge objects — no objects row.

CREATE TABLE workspaces (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    layout_json JSONB NOT NULL DEFAULT '{}',
    is_pinned   BOOLEAN NOT NULL DEFAULT false,
    last_used_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ
);

CREATE INDEX ix_workspaces_user_id    ON workspaces(user_id);
CREATE INDEX ix_workspaces_user_active ON workspaces(user_id) WHERE deleted_at IS NULL;
CREATE INDEX ix_workspaces_last_used  ON workspaces(last_used_at DESC NULLS LAST);

-- ─── Career Artifacts — Phase 9 ───────────────────────────────────────────────
-- Migration 0009: resume bullet sets and interview story records.
-- Both extend objects (kind = 'resume_bullet_set' / 'interview_story').

CREATE TABLE resume_bullet_sets (
    id             UUID PRIMARY KEY REFERENCES objects(id) ON DELETE CASCADE,
    project_id     UUID NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
    target_role    TEXT,
    emphasis       TEXT,
    count          SMALLINT NOT NULL,
    bullets        JSONB NOT NULL DEFAULT '[]',
    agent_run_id   UUID REFERENCES agent_runs(id) ON DELETE SET NULL,
    prompt_version VARCHAR(16),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_resume_bullet_sets_project_id ON resume_bullet_sets(project_id);

CREATE TABLE interview_story_records (
    id             UUID PRIMARY KEY REFERENCES objects(id) ON DELETE CASCADE,
    project_id     UUID NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
    question_type  VARCHAR(16) NOT NULL DEFAULT 'behavioral',
    target_role    TEXT,
    max_words      INT NOT NULL DEFAULT 400,
    word_count     INT NOT NULL DEFAULT 0,
    story          JSONB NOT NULL DEFAULT '{}',
    agent_run_id   UUID REFERENCES agent_runs(id) ON DELETE SET NULL,
    prompt_version VARCHAR(16),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_interview_story_records_project_id ON interview_story_records(project_id);
