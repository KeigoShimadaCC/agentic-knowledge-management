-- KnowledgeOS Database Schema
-- Postgres 16
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

CREATE INDEX idx_sessions_user_id   ON sessions(user_id);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);

-- ─── Objects ──────────────────────────────────────────────────────────────────
-- Union type for all knowledge objects (page, asset, note, bookmark, collection)

CREATE TABLE objects (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind        TEXT NOT NULL CHECK (kind IN ('page','asset','note','bookmark','collection')),
    title       TEXT NOT NULL DEFAULT '',
    description TEXT,
    tags        TEXT[] NOT NULL DEFAULT '{}',
    metadata    JSONB NOT NULL DEFAULT '{}',
    is_pinned   BOOLEAN NOT NULL DEFAULT false,
    is_archived BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ
);

CREATE INDEX idx_objects_user_id        ON objects(user_id);
CREATE INDEX idx_objects_kind           ON objects(kind);
CREATE INDEX idx_objects_created_at     ON objects(created_at DESC);
CREATE INDEX idx_objects_deleted_at_null ON objects(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX idx_objects_tags           ON objects USING GIN(tags);

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
    status        TEXT NOT NULL DEFAULT 'uploading' CHECK (status IN ('uploading','ready','error')),
    width         INT,
    height        INT,
    duration_secs FLOAT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_assets_sha256 ON assets(sha256);
CREATE INDEX idx_assets_status ON assets(status);

-- ─── Edges ────────────────────────────────────────────────────────────────────

CREATE TABLE edges (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_id UUID NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
    -- Edge kind is validated in application code so legacy and future graph kinds
    -- can coexist without a destructive enum/check migration.
    kind      TEXT NOT NULL DEFAULT 'link',
    weight    FLOAT NOT NULL DEFAULT 1.0,
    metadata  JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    UNIQUE (source_id, target_id, kind)
);

CREATE INDEX idx_edges_source_id ON edges(source_id);
CREATE INDEX idx_edges_target_id ON edges(target_id);
CREATE INDEX idx_edges_user_id   ON edges(user_id);

-- ─── Chunks ───────────────────────────────────────────────────────────────────

CREATE TABLE chunks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    object_id   UUID NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
    chunk_idx   INT NOT NULL,
    content     TEXT NOT NULL,
    token_count INT,
    metadata    JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (object_id, chunk_idx)
);

CREATE INDEX idx_chunks_object_id ON chunks(object_id);

-- ─── Ingestion Jobs ───────────────────────────────────────────────────────────

CREATE TABLE ingestion_jobs (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    object_id    UUID REFERENCES objects(id) ON DELETE SET NULL,
    status       TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','running','done','failed')),
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
    status        TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running','done','failed','cancelled')),
    agent_type    TEXT NOT NULL,
    input         JSONB NOT NULL DEFAULT '{}',
    output        JSONB,
    error         TEXT,
    model         TEXT,
    input_tokens  INT,
    output_tokens INT,
    cost_usd      NUMERIC(10,6),
    started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at   TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_agent_runs_user_id ON agent_runs(user_id);
CREATE INDEX idx_agent_runs_status  ON agent_runs(status);
