# KnowledgeOS Architecture

KnowledgeOS is a local-first personal AI knowledge base designed to run on a Mac with Docker Compose. Phase 1 establishes the durable core: a browser UI, an authenticated API, relational metadata in Postgres, Redis-backed background jobs, and content-addressed files on the local filesystem.

## System Diagram

```text
Browser
  |
  | HTTP, httponly kos_session cookie
  v
Next.js web (:3000)
  |
  | /api/v1/* requests
  v
FastAPI api (:8000)
  |\
  | \-- Postgres (:5432)  users, sessions, objects, pages, assets, edges,
  |                        chunks, ingestion_jobs, agent_runs
  |
  |---- Redis (:6379)     RQ queue and job coordination
  |
  \---- Filesystem        ~/KnowledgeOS/library/assets/{prefix}/{sha}/original{ext}

RQ worker
  |\
  | \-- Postgres          read jobs, update objects/assets/source state
  |
  \---- Filesystem        read originals, write extracted derivatives

Qdrant (:6333)           reserved for vector search in a later phase
```

## Services

| Service | Port | Purpose |
| --- | ---: | --- |
| `web` | `3000` | Next.js 14 App Router frontend. Provides the editor and object browsing UI. |
| `api` | `8000` | FastAPI application. Owns authentication, object CRUD, page content, asset upload/download, and future ingestion endpoints. |
| `postgres` | `5432` | Primary durable database. Stores users, sessions, universal object records, specialization tables, edges, chunks, jobs, and agent audit records. |
| `redis` | `6379` | Queue backend for RQ. Used by the API to enqueue jobs and by the worker to claim work. |
| `qdrant` | `6333` | Vector database reserved for semantic search in Phase 3+. It is part of the local stack but not central to Phase 1 behavior. |

## Runtime Responsibilities

The frontend is intentionally thin. It renders KnowledgeOS workflows in the browser and talks to the API over HTTP. It does not write directly to Postgres, Redis, or the local library directory.

The API is the system boundary for all application state changes. It validates requests, resolves the current user from the session cookie, writes metadata to Postgres, stores uploaded binary content in the library, and returns JSON responses to the frontend or trusted local clients.

The worker (`services/worker/kos_worker/`) runs as a separate process via `rq worker kos-ingest`. It is responsible for slow ingestion tasks: extracting text from PDFs, generating thumbnails, reading CSV previews, fetching YouTube transcripts, scraping web articles, and updating source status after asynchronous work completes.

Postgres is the source of truth for identity, object metadata, page documents, asset records, graph edges, ingestion status, and agent run records. The filesystem is the source of truth for large original files and later extracted derivatives. Redis is transient coordination state and should not be treated as durable storage.

## Phase 1 Data Flow

For normal object and page actions:

1. The user performs an action in the browser, such as creating a page or updating page content.
2. The web app sends an authenticated request to `api` using the `kos_session` cookie.
3. FastAPI validates the session and user.
4. FastAPI writes the object row and specialization row in Postgres.
5. FastAPI returns JSON to the frontend.

For asset upload:

1. The browser sends a multipart upload to `POST /api/v1/assets/upload`.
2. The API streams or reads the file, computes its SHA-256 digest, and determines a content-addressed path.
3. The original file is stored under the local KnowledgeOS library.
4. The API creates an `objects` row with `kind="asset"` and an `assets` row with filename, content type, size, hash, path, status, and optional media metadata.
5. The API returns the asset object metadata.

## Filesystem Storage

Uploaded asset originals use content-addressed storage:

```text
~/KnowledgeOS/library/assets/{sha256[:2]}/{sha256}/original{ext}
```

For example, an uploaded PDF with digest `ab12...` is stored under:

```text
~/KnowledgeOS/library/assets/ab/ab12.../original.pdf
```

The SHA-256 path makes duplicate detection straightforward, keeps large files out of the database, and avoids relying on user-provided filenames for identity. The database stores the canonical `sha256` and `storage_path`; display names remain metadata.

## Authentication Flow

KnowledgeOS uses local session authentication:

1. A user registers or logs in through `POST /api/v1/auth/register` or `POST /api/v1/auth/login`.
2. The API creates a random session token.
3. The raw token is sent to the browser as an httponly `kos_session` cookie.
4. Only a SHA-256 hash of the token is stored in the `sessions` table.
5. On each authenticated request, the API hashes the presented cookie token, looks up the session, checks validity, and loads the associated user.

The browser cannot read the cookie from JavaScript because it is httponly. Logging out deletes or invalidates the session so subsequent requests no longer resolve to a user.

## Phase 2: Sources and Worker Ingestion

Phase 2 promotes external material into first-class `source` objects. A source extends `KosObject` with `kind="source"` and a parallel `sources` table, matching the existing pattern for `pages` and `assets`.

Source types: PDFs, images, videos, YouTube URLs, web articles, and CSV files. Creating a source enqueues an RQ job. The `kos-worker` process (`services/worker/`) extracts text and metadata, writes derivatives to the library, updates source status, and creates relationships:

| Edge | Meaning |
| --- | --- |
| `source -> asset` with `kind="derives_from"` | A source was created from an uploaded asset. |
| `page -> source` with `kind="cites"` | A page cites or references an ingested source. |

## Offline and AI Provider Degradation

**Core app features work fully offline** — page editing, source creation, asset uploads, keyword search, and all CRUD operations require no internet connection and no API keys.

**AI/API-backed features degrade gracefully** when external providers are unavailable:

| Feature | Requires | Offline behavior |
| --- | --- | --- |
| Keyword search | Nothing | Always available |
| Vector embedding | `OPENAI_API_KEY` | Returns 503 with `{"detail": "embeddings_disabled"}` — not a 500 |
| Hybrid search | `OPENAI_API_KEY` | Falls back to keyword-only; adds `"embeddings_disabled": true` to response |
| Source extraction (YouTube transcript, web scrape) | Network | Worker marks job `error`; extracted_text left blank; manual retry supported |
| AI summarization, extraction, Q&A | `OPENAI_API_KEY` | Endpoint returns 503; no partial state written |
| AI suggestions and link proposals | `OPENAI_API_KEY` | Same graceful error |

**No user data is sent to external AI providers unless the user explicitly invokes an AI-backed feature.** Indexing and search are local by default. AI features activate only when `OPENAI_API_KEY` is set and the user triggers the action.

**Local LLM support** (e.g., Ollama) is a future option behind the `EmbeddingProvider` abstraction. No current code assumes OpenAI as the only option.

## Phase 3+ Direction

| Area | Planned Role |
| --- | --- |
| Vector search | Qdrant for chunk embeddings; gracefully disabled when no API key |
| Graph Lite | Typed edge UI, backlinks, related objects from Postgres; Kùzu added later |
| AI workflows | Summarization, Q&A, extraction — all behind provider abstraction, all opt-in |
| Inbox/Triage | AI-classified staging area for unprocessed items |
| Chat Import | ChatGPT/Claude export → searchable chat history + linked knowledge objects |
| MCP | Staged rollout: read/search tools first, then create, then update/archive |

## Phase 4: Graph Lite

Graph Lite uses Postgres `edges` as the canonical graph source. It does not require Kuzu, Qdrant, embeddings, or Phase 3 search endpoints.

Current graph flow:

1. API validates both objects belong to the authenticated user and are not soft-deleted.
2. API validates edge kind against code-level taxonomy.
3. API creates or restores the unique `(source_id, target_id, kind)` edge.
4. Object-centered endpoints read incoming/outgoing edges and hydrate source/target summaries from Postgres.
5. Related-object traversal runs over Postgres edges with depth capped at 2.

Kuzu remains a future derived index. It should be introduced only if Postgres edge traversal is no longer sufficient for the local-first workload.

## Phase 3: Search Pipeline

KnowledgeOS provides three search modes:

| Mode | Endpoint | Backend |
| --- | --- | --- |
| Keyword | `GET /api/v1/search/keyword` | Postgres `to_tsvector` + `plainto_tsquery` |
| Vector | `POST /api/v1/search/vector` | Qdrant cosine similarity |
| Hybrid | `POST /api/v1/search/hybrid` | Merged: 0.45 keyword + 0.45 vector + 0.10 recency |

### Indexing pipeline

1. Content is chunked into ~1000-character overlapping segments (`chunker.py`).
2. Each chunk is stored in the `chunks` table with a `content_hash` for idempotency.
3. Chunks with `embedding_status="pending"` are embedded via OpenAI `text-embedding-3-small` and upserted to Qdrant (`knowledgeos_chunks`).
4. Qdrant collection `knowledgeos_chunks` uses COSINE distance, dimension 1536.
5. Reindex is triggered on page save and after source ingestion completes.

If `OPENAI_API_KEY` is not set, vector search returns 503 and hybrid search falls back to keyword-only.
