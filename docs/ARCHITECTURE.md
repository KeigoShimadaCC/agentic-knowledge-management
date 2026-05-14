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

The worker is present in Phase 1 as a stub and becomes active in Phase 2. It is responsible for slow ingestion tasks such as extracting text from PDFs, generating previews, reading metadata, and updating source status after asynchronous work completes.

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

## Phase 2 Preview: Sources and Worker Ingestion

Phase 2 promotes external material into first-class `source` objects. A source extends `KosObject` with `kind="source"` and a parallel `sources` table, matching the existing pattern for `pages` and `assets`.

Expected source examples include PDFs, images, videos, YouTube URLs, web articles, and CSV files. Creating a source will enqueue an RQ job. The worker will extract text and metadata, write derivatives to the library, update source status, and create relationships such as:

| Edge | Meaning |
| --- | --- |
| `source -> asset` with `kind="derives_from"` | A source was created from an uploaded asset. |
| `page -> source` with `kind="cites"` | A page cites or references an ingested source. |

## Phase 3+ Direction

Later phases build on the same local-first boundary:

| Area | Planned Role |
| --- | --- |
| Vector search | Use Qdrant for embeddings over chunks, source text, page content, and asset-derived text. |
| Graph | Add Kuzu or another graph layer for richer relationship traversal beyond direct SQL edge queries. |
| AI workflows | Add local or remote model integrations for summarization, question answering, extraction, tagging, and writing assistance. |
| MCP | Expose KnowledgeOS as a controlled local tool surface for AI agents through Model Context Protocol, with API-mediated writes and auditable actions. |
