# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project North Star

KnowledgeOS is a **local-first personal AI knowledge base** that runs entirely on the user's Mac via Docker Compose. The user dumps, structures, searches, and reasons over personal and professional knowledge — pages, rich media, sources, projects, AI chat histories — through a browser-only UI. The system is **agent-ready**: Claude, Codex, ChatGPT, and local agents can safely search, read, create, update, and link knowledge through the built-in MCP server and internal API. Every feature must work offline, stay private, and keep all data under `~/KnowledgeOS/`.

---

## Agent Operating Model

**Claude is the orchestrator. Codex agents are implementation coders.**

| Role | Responsibility |
|---|---|
| Claude | Plan, decompose, assign tasks to Codex, review outputs, enforce architecture, update docs |
| Codex | Implement bounded tasks, write tests, return a concise handoff note |

**Before writing any code for a non-trivial task:**
1. Write a brief implementation plan (goal, affected files, acceptance criteria, risks).
2. Confirm the plan fits the architecture before proceeding.
3. Assign Codex tasks with a clear scope boundary and a verification method.

When reviewing Codex output: check for architecture drift, missing tests, and undocumented schema/API changes before accepting.

---

## Non-Negotiable Rules

These apply to Claude, Codex, and any other agent at all times.

- **Never hard-delete user data.** Use `deleted_at` soft-delete on all user-owned records.
- **All agent writes must produce an audit trail.** Log agent identity, timestamp, and action to `agent_runs` table.
- **Never expose API keys or secrets through MCP tools or API responses.** Redact before returning.
- **All files must stay under `~/KnowledgeOS/` (or `LIBRARY_ROOT`).** Never write outside this tree.
- **Prefer internal API / MCP tools over direct DB or filesystem mutation.** Only the API and workers touch Postgres and the library directly.
- **No arbitrary shell execution through MCP.** MCP tools are read/search/write/ingest only.
- **No paid SaaS dependencies without explicit approval.** Local-first and free infrastructure except AI API costs (OpenAI, Anthropic).
- **Update the relevant doc in `docs/` whenever schema, API, MCP tools, or ingestion behavior changes.**

---

## Architecture Snapshot

```
Browser (Next.js + Tiptap)
  └─► FastAPI  (/api/v1)
        ├─► Postgres 16      ← operational truth (objects, pages, users, edges, audit)
        ├─► Redis             ← queue (RQ) + cache
        ├─► ~/KnowledgeOS/library/  ← binary assets (content-addressed by SHA-256)
        ├─► Qdrant           ← vector index (not canonical; rebuilt from Postgres)
        └─► Kùzu             ← graph index (not canonical; rebuilt from Postgres edges)

Python Workers (RQ)  ← ingestion, RAG, embedding, graph sync
MCP Server           ← agent read/search/write/ingest interface
```

**Canonical source of truth:** Postgres for structured data; local filesystem for large binaries.
**Qdrant and Kùzu are indexes**, not canonical stores. Treat them as re-buildable caches.

All services run via `docker compose -f infra/docker-compose.yml`. See `docs/ARCHITECTURE.md` for the full diagram and `docs/DATA_MODEL.md` for the schema.

---

## Data Ownership & Storage Rules

- `KosObject` is the universal base: every page, asset, note, bookmark, and collection is a row in `objects` with a `kind` discriminator. Specialized tables (`pages`, `assets`, etc.) extend it.
- Assets stored at `LIBRARY_ROOT/assets/<sha256[:2]>/<sha256>/original<ext>` — write-once, content-addressed.
- Soft-delete pattern: set `deleted_at`; filter on `deleted_at IS NULL` in all queries.
- User data is never sent to external services without explicit opt-in. AI embeddings and summaries are derived data; the source always stays local.

---

## MCP & Agent Safety Rules

- MCP tools expose: `search`, `read_object`, `create_page`, `update_page`, `link_objects`, `ingest_url`, `ingest_file`. Nothing else.
- Every MCP write must validate the calling agent identity (from session or token) and write an `agent_runs` audit row.
- MCP read tools may return object content, metadata, and search results. They must never return `api_keys`, `session_secret`, or password hashes.
- Ingestion tools accept URLs and file paths under `LIBRARY_ROOT` only. Reject paths outside the library root.
- Rate-limit MCP write tools per agent identity to prevent runaway loops.

See `docs/MCP_TOOLS.md` for the full tool spec and `docs/SECURITY.md` for auth and audit design.

---

## Development Workflow

### Setup & run
```bash
bash scripts/setup.sh                             # first-time: creates ~/KnowledgeOS dirs + infra/.env
docker compose -f infra/docker-compose.yml up -d  # start all services
```

### Frontend (apps/web)
```bash
pnpm dev          # Next.js dev on :3000
pnpm typecheck    # tsc --noEmit
pnpm lint         # ESLint
```

### Backend (services/api)
```bash
cd services/api
uv run uvicorn app.main:app --reload   # hot-reload dev server
uv run ruff check . && uv run ruff format .
```

### Verify in browser — for any frontend change, open `http://localhost:3000` and validate the golden path before marking work done.

### For ingestion, search, or RAG changes — test with realistic fixtures (multi-page PDF, long article, audio file) not just unit mocks.

---

## Quality Gates

Run all applicable gates before committing. Do not skip a gate because a task "feels small."

| Layer | Command |
|---|---|
| Frontend types | `pnpm typecheck` |
| Frontend lint | `pnpm lint` |
| API lint | `uv run ruff check services/api` |
| API integration tests | `cd tests && uv run pytest api/` *(requires running Postgres)* |
| Single test file | `cd tests && uv run pytest api/test_pages.py` |

Integration tests spin up against `knowledgeos_test` database (auto-created, torn down per test). They use real FastAPI + real Postgres — no mocks.

---

## Git / Commit Discipline

- **Commit after each coherent unit:** schema migration, API endpoint, UI component, worker pipeline, MCP tool, test suite, docs update. Not before.
- **Do not mix unrelated changes in one commit.**
- **Run the relevant quality gates before every commit.**
- **Push after committing** unless explicitly told otherwise.
- Use conventional commit prefixes: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `infra`.
- Keep commit messages explicit: what changed and why, not just what file changed.

Example: `feat(api): soft-delete endpoint for objects with audit log entry`

---

## Keeping This File Healthy

- **Target under 200 lines.** Move detailed specs to `docs/*.md` and point here.
- If a new rule is durable (would help any future agent), add it with a surgical edit — don't bloat this file.
- Use `.claude/rules/` for path-scoped rules (e.g., frontend-only or worker-only conventions).
- If you discover this file has become stale or contradictory, fix it before continuing work.

---

## Where to Find Details

| Topic | File |
|---|---|
| Full architecture & sequence diagrams | `docs/ARCHITECTURE.md` |
| Postgres schema & model decisions | `docs/DATA_MODEL.md` |
| REST API reference | `docs/API.md` |
| MCP tool spec | `docs/MCP_TOOLS.md` |
| Ingestion pipeline design | `docs/INGESTION.md` |
| Auth, sessions, audit log | `docs/SECURITY.md` |
| Agent prompts & RAG guide | `docs/AGENT_GUIDE.md` |
| Phase-by-phase build plan | `project-phases/` |

---

## When Unsure

- **Wrong assumption is cheap to fix → make a reasonable call, document it in the commit message, move on.**
- **Wrong assumption would be expensive (schema migration, breaking API change, data loss risk) → stop and ask.**
- When you make a judgment call, leave a brief comment or commit note so the next agent can understand the reasoning.
