# KnowledgeOS

> **A local-first personal AI knowledge operating system.**  
> Dump everything, structure it, search it semantically, traverse it as a graph, and let AI agents operate it — all entirely on your Mac, with no cloud dependency and no data leaving your machine.

---

## Philosophy

Most knowledge tools are either too simple (note apps that can't reason) or too complex (enterprise wikis that require a team to maintain). KnowledgeOS is built on a different premise:

**Your knowledge should be a living system, not a filing cabinet.**

The design decisions all follow from this:

- **Local-first, always.** Every byte lives under `~/KnowledgeOS/`. No sync service, no cloud account required. You own your data unconditionally.
- **Agent-ready from the start.** Claude, ChatGPT, Codex, and local LLMs can search, read, write, and link knowledge through a built-in MCP server — not as a bolt-on feature, but as a first-class access mode.
- **Structured but flexible.** Everything is a typed object (`KosObject`) with a common base. Pages, sources, assets, claims, projects, and chats are all objects you can search, link, and reason over in the same interface.
- **Soft everything.** No hard deletes. No permanent overwrites. Every agent write is logged with a before/after diff. You can always undo, audit, or restore.
- **Durable indexes, not canonical truth.** Qdrant (vector) and Kùzu (graph) are re-buildable from Postgres + filesystem. Postgres is the operational source of truth. Indexes are caches.

The full product vision is in [`project-phases/IDEA-DRAFT.md`](project-phases/IDEA-DRAFT.md).

---

## Current Status

Phases 1-4, Phase 6A Chat Import Lite, and Phase 6B Structured Chat Import are complete. Phase 5 AI Assistant/Inbox and Phase 7 MCP remain planned.

See [`PROGRESS.md`](PROGRESS.md) for the canonical progress tracker.

| Phase | Status |
|---|---|
| Phase 1 — Foundation | ✅ Complete (25 tests) |
| Phase 2 — Sources & Rich Media | ✅ Complete (45 tests) |
| Phase 3 — Search | ✅ Complete |
| Phase 4 — Graph Lite | ✅ Complete |
| Phase 5 — AI Assistant + Inbox/Triage | ⬜ Planned |
| Phase 6A — Chat Import Lite | ✅ Complete |
| Phase 6B — Structured Chat Import | ✅ Complete |
| Phase 7 — MCP Server | ⬜ Planned |

**Phase 2 added:**
- Typed `source` objects (PDF, image, video, YouTube, web article, CSV)
- RQ background worker with per-type extractors (text, metadata, thumbnail, transcript)
- Sources list + detail UI with status polling
- Citation edges in the Tiptap page editor (`CitationExtension`)
- `POST/GET/PATCH/DELETE /api/v1/sources` and `POST/GET/DELETE /api/v1/edges`

See [`project-phases/PHASE-2-SOURCES.md`](project-phases/PHASE-2-SOURCES.md) for the full subtask spec.

---

## Architecture

```
Browser (Next.js 14 + React + Tiptap)
  └─► FastAPI  /api/v1
        ├─► Postgres 16          ← operational source of truth
        │     objects, pages, edges, chunks, agent_runs, ingestion_jobs
        ├─► Redis                ← RQ job queue + cache
        ├─► ~/KnowledgeOS/library/  ← binary assets (SHA-256 content-addressed)
        ├─► Qdrant               ← vector index (re-buildable)
        └─► Kùzu                 ← graph index (re-buildable)

Python Workers (RQ)
  └─► ingestion → text extraction → chunking → embedding → graph sync → AI extraction

MCP Server (:8765)
  └─► read / search / write / ingest tools
        ↑
  Claude / ChatGPT / Codex / Cursor / local agents
```

**Canonical source of truth:** Postgres (structured data) + local filesystem (binary assets).  
**Qdrant and Kùzu are indexes.** Treat them as caches; they can be rebuilt from Postgres at any time.  
**All host ports bind to `127.0.0.1` only.** LAN access is opt-in.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 + React 18 + Tailwind CSS |
| Editor | Tiptap / ProseMirror (stores content as JSON) |
| Backend API | FastAPI + SQLAlchemy 2.0 async |
| Background workers | Python + Redis + RQ |
| MCP server | Python MCP server (Phase 6) |
| Operational DB | Postgres 16 |
| Vector DB | Qdrant (local Docker) |
| Graph DB | Kùzu (embedded in worker process) |
| Queue / cache | Redis 7 |
| Asset storage | Local filesystem, content-addressed by SHA-256 |
| AI | OpenAI API (Phase 5+); Ollama local LLMs (later) |
| Deployment | Docker Compose on Mac |

---

## Quick Start

### Prerequisites

- macOS, Docker Desktop, Node.js 20+, pnpm 10+, Python 3.12+, uv

### Setup

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd agentic-knowledge-management

# 2. Create local directories + copy .env
bash scripts/setup.sh

# 3. Edit infra/.env — set SESSION_SECRET to a 32+ char random string
#    (everything else works with defaults)

# 4. Start all services
docker compose -f infra/docker-compose.yml up -d

# 5. Open the app
open http://localhost:3000
```

Register an account on first visit. All data stays local.

---

## Development

### Frontend (apps/web)

```bash
pnpm dev          # Next.js dev server on :3000 with hot reload
pnpm typecheck    # tsc --noEmit (strict mode)
pnpm lint         # ESLint via next lint
pnpm build        # production build
```

### Backend API (services/api)

```bash
cd services/api
uv run uvicorn app.main:app --reload --port 8000   # dev server
uv run ruff check .                                 # lint
uv run ruff format .                                # format
uv run python -c "from app.models import *; print('OK')"  # sanity check
```

### Integration Tests

Tests run against a live `knowledgeos_test` Postgres database (auto-created and torn down per test). Requires Postgres running (via Docker or local).

```bash
cd tests
uv run pytest api/ -v                          # all 45 integration tests
uv run pytest api/test_pages.py -v             # single file
uv run pytest api/test_pages.py::test_create_page  # single test
```

### Alembic Migrations

```bash
cd services/api
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```

### Infrastructure

```bash
docker compose -f infra/docker-compose.yml up -d      # start (background)
docker compose -f infra/docker-compose.yml up         # start (foreground logs)
docker compose -f infra/docker-compose.yml down       # stop
docker compose -f infra/docker-compose.yml down -v    # stop + wipe volumes (destructive)

# Dev override: hot-reload with source mounts
docker compose -f infra/docker-compose.yml -f infra/docker-compose.override.yml up
```

---

## File Layout

```
.
├── apps/web/              Next.js frontend
│   └── src/
│       ├── app/           App Router: (auth)/ and (app)/ route groups
│       ├── components/    UI components (editor, assets, auth, layout)
│       ├── lib/           API client, SWR hooks
│       └── types/         Shared TypeScript types
│
├── services/api/          FastAPI backend
│   └── app/
│       ├── api/v1/        Route handlers (auth, objects, pages, assets, health)
│       ├── core/          Deps, security, library, storage utilities
│       ├── db/            Session, base model
│       ├── models/        SQLAlchemy ORM models
│       ├── schemas/        Pydantic request/response schemas
│       └── services/      Business logic layer
│
├── services/worker/       RQ background worker (Phase 2+)
├── services/mcp/          MCP server (Phase 6+)
│
├── packages/
│   ├── shared-types/      Shared TypeScript types (Phase 2+)
│   ├── schemas/           JSON schemas (Phase 2+)
│   └── prompts/           Shared AI prompt templates (Phase 5+)
│
├── infra/                 Docker Compose, Dockerfiles, .env.example
├── scripts/               setup.sh, backup.sh, reindex.py (Phase 3+)
├── tests/api/             Integration tests (pytest + httpx)
├── docs/                  Architecture, data model, API, MCP, ingestion, security
└── project-phases/        Phase-by-phase implementation plans
```

---

## Data Model

### The `KosObject` pattern

Every entity in the system — pages, assets, notes, bookmarks, collections — is a row in the `objects` table with a `kind` discriminator. Specialized tables (`pages`, `assets`, etc.) extend it by foreign key.

```
objects (id, user_id, kind, title, tags[], metadata{}, is_pinned, is_archived, deleted_at)
  ├── pages     (content_json, content_text, word_count, version)
  ├── assets    (sha256, storage_path, content_type, size_bytes, status)
  └── edges     (source_id, target_id, kind: link/child/citation/related/...)
```

Future object types (`sources`, `claims`, `projects`, `chats`, `concepts`, `tasks`, `workspaces`) extend the same base. See [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md) for the full schema.

### Asset storage

Binary files are stored content-addressed under `LIBRARY_ROOT`:

```
~/KnowledgeOS/library/assets/<sha256[:2]>/<sha256>/original.<ext>
```

Write-once semantics: if the path already exists, the upload is a no-op (deduplication by hash).

### Soft deletes

All user-owned records use `deleted_at` (nullable timestamp). Hard deletes are never performed. Trash is filtered out by `deleted_at IS NULL` in all standard queries.

---

## Product Modules (Full Vision)

The complete product is built across 9 phases. Phase 1 is done; phases 2–9 are planned.

| Module | Description | Phase |
|---|---|---|
| **Wiki pages** | Rich Tiptap editor, subpages, backlinks, typed links | 1 ✅ |
| **Asset library** | Upload, preview, and manage files (images, PDFs, videos, CSV) | 1 ✅ |
| **Rich media sources** | PDF viewer, YouTube metadata, web article ingestion, image OCR | 2 ✅ |
| **Keyword + semantic search** | Postgres FTS + Qdrant vector + hybrid reranking | 3 |
| **Graph Lite** | Typed edge UI, backlinks panel, related objects from Postgres edges | 4 |
| **AI assistant + Inbox/Triage** | Summarize, extract, suggest links, RAG Q&A, triage inbox | 5 |
| **Chat import** | Import ChatGPT/Claude exports → searchable chats + structured objects | 6 |
| **MCP server** | Staged rollout: read/search → create → update/archive | 7 |
| **Multi-pane workspaces** | Side-by-side research desks, saved layouts, drag-across-pane | 8 |
| **Career/project memory** | Project schema, evidence-linked resume bullets, interview stories | 9 |

---

## Roadmap

| Phase | Goal | Status |
|---|---|---|
| 1 — Foundation | Docker, Postgres, auth, page CRUD, Tiptap editor, asset upload, 25 tests | **Done** |
| 2 — Sources & Rich Media | PDF/YouTube/web/CSV ingestion, RQ worker, citation edges, 45 tests | **Done** |
| 3 — Search | Chunking, Postgres FTS, Qdrant vectors, hybrid search, Cmd+K UI | Done |
| 4 — Graph Lite | Typed edge API, backlinks, related objects from Postgres; Kùzu later | Done |
| 5 — AI Assistant + Inbox/Triage | AI sidebar, summarize/extract/suggest, KB Q&A, triage inbox | Planned |
| 6A — Chat Import Lite | Raw upload/paste of ChatGPT/Claude/Markdown/text exports; searchable chats | Done |
| 6B — Structured Chat Import | AI summaries, extracted claims/tasks, turn-grounded graph links | Done |
| 7 — MCP Server | Staged: read/search tools → create tools → update/archive tools | Planned |
| 8 — Workspaces | Multi-pane layout engine, saved workspaces, AI scoped to workspace | Planned |
| 9 — Career Memory | Project schema UI, resume bullet generator, interview story generator | Planned |

Each phase has a detailed spec in [`project-phases/`](project-phases/).

---

## MCP & Agent Access

Phase 7 will expose KnowledgeOS through a local MCP server.

**Read/search tools:** `search_objects`, `hybrid_search`, `get_object`, `get_page`, `get_related_objects`, `answer_from_kb`  
**Write tools:** `create_page`, `update_page`, `create_claim`, `create_edge`, `archive_object`  
**Ingestion tools:** `ingest_url`, `ingest_file`, `import_chat`, `triage_inbox`

**Safety invariants (always enforced):**
- Every agent write logs an `agent_runs` row (identity, model, input, output, changed objects)
- All writes are soft-delete only — no hard deletes through MCP
- No arbitrary shell execution through any MCP tool
- No file access outside `~/KnowledgeOS/`
- API keys and session secrets are never returned in tool outputs

See [`docs/MCP_TOOLS.md`](docs/MCP_TOOLS.md) for the full tool spec and [`docs/SECURITY.md`](docs/SECURITY.md) for the auth and audit design.

---

## Environment Variables

Copy `infra/.env.example` to `infra/.env` before starting Docker.

| Variable | Default | Required |
|---|---|---|
| `SESSION_SECRET` | *(must set)* | **Yes** — min 32 chars |
| `POSTGRES_DB` | `knowledgeos` | No |
| `POSTGRES_USER` | `kos` | No |
| `POSTGRES_PASSWORD` | `kospass` | No |
| `LIBRARY_ROOT` | `~/KnowledgeOS/library` | No |
| `OPENAI_API_KEY` | *(not set)* | Phase 5+ |

---

## For AI Agents

If you are a coding agent (Claude, Codex, Cursor) working in this repo:

- Read **[`CLAUDE.md`](CLAUDE.md)** first — it is the operating contract for agents.
- Read **[`docs/AGENT_GUIDE.md`](docs/AGENT_GUIDE.md)** for data model rules and agent write constraints.
- Postgres is the source of truth. Do not mutate DB directly — go through the API or typed service functions.
- Every write must create an `agent_runs` audit row.
- Qdrant and Kùzu are indexes. They are re-buildable; never treat them as canonical.
- Soft-delete only. `deleted_at` is the pattern. Never call `DELETE` on user data.

---

## Documentation

| File | Contents |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System diagram, service boundaries, sequence flows |
| [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md) | Full Postgres schema, object types, edge types |
| [`docs/API.md`](docs/API.md) | REST API reference |
| [`docs/MCP_TOOLS.md`](docs/MCP_TOOLS.md) | MCP tool spec, resources, prompts |
| [`docs/INGESTION.md`](docs/INGESTION.md) | Ingestion pipeline stages, job types, media handling |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Auth, sessions, audit log, MCP safety model |
| [`docs/AGENT_GUIDE.md`](docs/AGENT_GUIDE.md) | Rules for AI agents writing to this system |
| [`project-phases/IDEA-DRAFT.md`](project-phases/IDEA-DRAFT.md) | Original full product spec |
| [`project-phases/PHASE-1-FOUNDATION.md`](project-phases/PHASE-1-FOUNDATION.md) | Phase 1 subtask spec |
