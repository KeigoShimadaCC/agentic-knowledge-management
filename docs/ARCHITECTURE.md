# KnowledgeOS Architecture

KnowledgeOS is a local-first personal AI knowledge base designed to run on a Mac with Docker Compose. The current shipped stack includes the browser UI, authenticated FastAPI API, Postgres source of truth, Redis-backed background jobs, content-addressed local files, search, graph traversal, AI assistant routes, chat import, read-only MCP, and Workspace Lite.

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
FastAPI api (host :8001 -> container :8000)
  |\
  | \-- Postgres (host :5433 -> container :5432)
  |                        users, sessions, objects, pages, assets, edges,
  |                        chunks, ingestion_jobs, agent_runs
  |
  |---- Redis (:6379)     RQ queue and job coordination
  |
  \---- Filesystem        ~/KnowledgeOS/library/assets/{prefix}/{sha}/original{ext}

MCP client
  |
  | stdio -> kos-mcp -> X-KOS-Internal-Token
  v
FastAPI api

RQ worker
  |\
  | \-- Postgres          read jobs, update objects/assets/source state
  |
  \---- Filesystem        read originals, write extracted derivatives

Qdrant (host/container :6333)  vector search index
```

## Services

| Service | Host port | Container port | Purpose |
| --- | ---: | ---: | --- |
| `web` | `3000` | `3000` | Next.js 14 App Router frontend. Provides the editor and object browsing UI. |
| `api` | `8001` | `8000` | FastAPI application. Owns authentication, object CRUD, page content, asset upload/download, ingestion endpoints, AI routes, and internal MCP auth. |
| `postgres` | `5433` | `5432` | Primary durable database. Stores users, sessions, universal object records, specialization tables, edges, chunks, jobs, revisions, and agent audit records. |
| `redis` | `6379` | `6379` | Queue backend for RQ. Used by the API to enqueue jobs and by the worker to claim work. |
| `qdrant` | `6333` / `6334` | `6333` / `6334` | Rebuildable vector database for semantic search. |

All published ports bind to `127.0.0.1`. Use container hostnames such as `api:8000` or `postgres:5432` only from inside the Docker network; host-side tools should use `127.0.0.1:8001` for the API and `127.0.0.1:5433` for Postgres.

## Runtime Responsibilities

The frontend is intentionally thin. It renders KnowledgeOS workflows in the browser and talks to the API over HTTP. It does not write directly to Postgres, Redis, or the local library directory.

The API is the system boundary for all application state changes. It validates requests, resolves the current user from the session cookie, writes metadata to Postgres, stores uploaded binary content in the library, and returns JSON responses to the frontend or trusted local clients.

The worker (`services/worker/kos_worker/`) runs as a separate process via `rq worker kos-ingest`. It is responsible for slow ingestion tasks: extracting text from PDFs, generating thumbnails, reading CSV previews, fetching YouTube transcripts, scraping web articles, and updating source status after asynchronous work completes.

Postgres is the source of truth for identity, object metadata, page documents, asset records, graph edges, chat imports, revisions, ingestion status, and agent run records. The filesystem is the source of truth for large original files and later extracted derivatives. Redis is transient coordination state and should not be treated as durable storage.

## Backup and Restore Boundary

The supported local backup entry point is `bash scripts/backup.sh`. It writes timestamped backups under `~/KnowledgeOS/backups/`:

- `postgres.dump` from `pg_dump -Fc` against the Compose Postgres service.
- `library.tar.gz`, a compressed copy of `~/KnowledgeOS/library/` excluding `tmp/`.
- `qdrant-snapshot.json` when the local Qdrant collection can create a snapshot, or a skipped marker when Qdrant is unavailable.

Postgres and the library directory are canonical. Redis, Qdrant, and future graph indexes are derived or transient state and can be rebuilt from canonical data.

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

## Phase 6A: Chat Import Lite

Chat Import Lite treats transcripts as first-class knowledge objects:

1. Browser uploads or pastes a transcript to `/api/v1/chats/import`.
2. The API parses ChatGPT JSON, Claude-like Markdown, Markdown labels, or plain text without calling an LLM.
3. The API creates `objects.kind="chat"` plus a `chats` row containing normalized turns and `content_text`.
4. Raw files and `metadata.json` are stored under `library/chats`.
5. Import and restore enqueue `reindex_object(chat_id)`.
6. Keyword search reads `chats.content_text`; vector search uses normal chunk/Qdrant indexing after reindex.

Deletes are soft deletes on `objects.deleted_at`; raw chat files are retained.

## Phase 6B: Structured Chat Import

Structured Chat Import turns a stored transcript into reusable knowledge through an explicit
preview/apply flow:

1. The chat detail UI calls `POST /api/v1/chats/{id}/structured-summary`.
2. The API builds a grounded prompt from normalized turns and calls the configured AI provider.
3. Strict JSON is validated before storage. Invalid JSON is repaired once, then returned as a
   clear failure.
4. Preview storage updates the chat summary fields and writes an `object_revisions` row tied to
   the `agent_runs` audit row.
5. Applying the summary creates/reuses generic `claim` and `task` objects, preserving `turn_refs`
   in metadata.
6. Extracted claims use `claim -> chat` / `derives_from`; tasks use `task -> chat` /
   `created_from`.
7. The chat and extracted objects enqueue normal reindex jobs.

Concepts and project-like entities remain in `structured_summary` unless those object systems
exist. No MCP tools or autonomous background processing are part of Phase 6B.

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

### Snippet shape

Search snippets are returned as a structured object — not raw HTML:

```json
{ "text": "plain string", "highlights": [[0, 7], [23, 35]] }
```

`ts_headline` uses sentinel characters (`\x01`/`\x02`) to mark matched terms. The `_parse_snippet()` helper in `search_service.py` converts these into character index ranges. The frontend renders highlights as React `<mark>` nodes with no `dangerouslySetInnerHTML`.

### Multilingual fallback

When Postgres FTS (`plainto_tsquery`) returns no hits, keyword search falls back to `ILIKE '%query%'` over `title` and `content_text`. This covers Japanese, Chinese, and other scripts not tokenised by the `english` text-search config.

### Index observability

`GET /api/v1/objects/{id}/index-status` returns chunk count, embedded count, aggregated status (`not_indexed` / `pending` / `partial` / `done`), and `last_embedded_at`. Use `scripts/reindex.py` to enqueue reindex jobs manually.

## Phase 8A: Workspace Lite (frontend-only)

Workspace Lite adds a split-pane side panel to the app shell. It is implemented entirely as React client state — no backend schema changes, no new API endpoints.

### Architecture

```
AppShell (flex h-screen)
  ├── Sidebar (w-60)
  ├── <main> (min-w-0 flex-1)          ← min-w-0 prevents flex overflow when pane opens
  │     └── [route children]
  │           └── PageView (for /pages/[id])
  │                 ├── editor (flex-1)
  │                 └── GraphPanel (w-72)  ← unchanged, lives inside PageView
  ├── WorkspaceSidePane (w-96, md+ only)  ← NEW: conditionally rendered
  └── SearchModal (fixed overlay)
```

### State management

`WorkspaceLiteProvider` (React context, `"use client"`) wraps `(app)/layout.tsx`. It exposes:

```ts
sidePaneObject: SidePaneObject | null
openSidePane(obj: SidePaneObject): void
closeSidePane(): void
```

No URL params, no persistence. Side pane state resets on page navigation, which is intentional.

### Routing helper

`lib/objectRouting.ts` exports `objectRoute(kind, id)` and `objectKindLabel(kind)`. All components that previously had inline route-building logic now use these functions.

### Entry points

| Component | How user opens side pane |
|-----------|--------------------------|
| `SearchModal` → `SearchResultCard` | Columns icon button beside each result |
| `BacklinksPanel` | Columns icon button beside each backlink item |
| `RelatedPanel` | Columns icon button beside each related item |

Side pane hides below the `md` breakpoint (< 768px). ESC key closes it.

### Notes for agents

Workspace state is local UI state only. Do not add persistence for workspace layouts in this branch — that belongs to Phase 8 proper. The `WorkspaceLiteProvider` is intentionally isolated in `components/workspace/`; its internals can be replaced without touching consumers.
