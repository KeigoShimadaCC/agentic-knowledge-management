# KnowledgeOS — Progress Tracker

> Last updated: 2026-05-15 (audit run; phase claims cross-checked against repo)

---

## North Star

Build a **local-first personal AI Knowledge OS** where the user can dump, structure, search, and reason over personal and professional knowledge — pages, rich media, sources, projects, and AI chat histories. The system is **agent-ready**: Claude, Codex, ChatGPT, and local agents can search, read, create, update, and link knowledge safely through a built-in MCP server and internal API. Everything runs locally on Mac via Docker. No cloud dependency. No data leaves the machine.

---

## Phase 1 — Foundation ✅ Complete

**Goal:** Establish the full development infrastructure, data model, auth system, page editor, and file upload so that a user can create pages, write content, and store files locally.

**Commits:** 9 commits · 25 integration tests passing

- [x] **Subtask 0** — Monorepo scaffold: pnpm workspace, uv workspace, root configs, directory tree, doc stubs
- [x] **Subtask 1** — Docker Compose: postgres, redis, qdrant, api, web — all with healthchecks; all ports bound to 127.0.0.1
- [x] **Subtask 2** — Postgres schema + SQLAlchemy 2.0 models: users, sessions, objects, pages, assets, edges, chunks, ingestion_jobs, agent_runs + Alembic migration 0001
- [x] **Subtask 3** — FastAPI shell + session-cookie auth: register, login, logout, /me; bcrypt passwords; httponly cookie; session token stored as sha256 hash
- [x] **Subtask 4** — Objects/Pages/Assets CRUD: full CRUD with soft-delete, restore, trash endpoint, content-addressed asset storage (`assets/{sha256[:2]}/{sha256}/original.{ext}`)
- [x] **Subtask 5** — Next.js 14 app shell: App Router, (auth) and (app) route groups, 3-panel layout (sidebar + main + detail), protected routes, auth flow
- [x] **Subtask 6** — Tiptap page editor: StarterKit, Placeholder, Typography, Link, Image; 800ms debounce auto-save; word count footer; toolbar
- [x] **Subtask 7** — Asset upload UI: drag-and-drop zone, XHR progress bars, SHA-256 deduplication, 4-column gallery grid, full-screen preview modal
- [x] **Subtask 8** — Integration test suite: 25 passing tests across auth, objects, pages, assets, health (pytest-asyncio + httpx ASGITransport)

---

## Phase 2 — Sources & Rich Media ✅ Complete

**Goal:** Evolve the app into a real knowledge base by ingesting typed Source objects — PDFs, images, videos, YouTube URLs, web articles, CSVs — and extracting metadata and text via a background RQ worker.

**Commits:** 9 commits · 45 integration tests passing

- [x] **Subtask 0** — Phase 1 stabilization: add `"source"` to `VALID_KINDS`, write real content into `docs/` stubs, save phase 2 plan to `project-phases/PHASE-2-SOURCES.md`
- [x] **Subtask 1** — Source data model + Alembic migration 0002: `sources` table, `source_type_enum` (pdf/image/video/audio/youtube/web/csv/file), `ingestion_status`, `extracted_text`, `thumbnail_path`, `preview_data`
- [x] **Subtask 2** — Source CRUD API: `POST/GET/PATCH/DELETE /api/v1/sources`, restore, `/text`, `/thumbnail` endpoints; source_service; Pydantic schemas with discriminated validation; RQ enqueue wired up; router registered
- [x] **Subtask 3** — Source creation flows: `?create_source=true` param on `POST /assets/upload`; auto-infer source_type from MIME; creates `derives_from` edge (source → asset)
- [x] **Subtask 4** — Worker foundation: `kos_worker/worker.py` (RQ entry point), `tasks.ingest_source()` dispatcher, sync SQLAlchemy session (psycopg2), full job lifecycle (pending → running → success/failed)
- [x] **Subtask 5** — File extractors: PDF (pypdf text + page count + thumbnail), image (Pillow dimensions + thumbnail), CSV (20-row JSON preview); write derivatives to `library/sources/{id}/`
- [x] **Subtask 6** — URL extractors: YouTube (oEmbed title/author + transcript via `youtube-transcript-api`), web article (httpx + BeautifulSoup4 title + body text)
- [x] **Subtask 7** — Sources UI: `/sources` list page (SourceCard with status badge + polling), `/sources/[id]` detail (thumbnail, metadata, extracted text, CSV preview table), CreateSourceModal (URL tab + upload tab), Sources nav item in sidebar
- [x] **Subtask 8** — Citation edges in page editor: `CitationExtension` Tiptap node (stores `data-source-id`), SourcePicker modal, "Cite" toolbar button, on-save sync creates `page→source` edges via `POST /edges`; edges CRUD API
- [x] **Subtask 9** — Tests + docs: `test_sources.py` (15 tests), `test_edges.py` (5 tests); update `docs/DATA_MODEL.md`, `docs/API.md`, `docs/INGESTION.md`, `docs/ARCHITECTURE.md`

---

## Phase 3 — Search ✅ Complete

**Goal:** Make all knowledge searchable — by exact keyword, by semantic meaning, and by a hybrid of both — with a clean search UI. Keyword search must work offline with no API keys.

See [`project-phases/PHASE-3-SEARCH.md`](project-phases/PHASE-3-SEARCH.md) for the full subtask spec.

- [x] **Subtask 0** — Phase 2 audit + Phase 3 stabilization: `chunks` migration 0003 (user_id, source_locator, content_hash, embedding_status, embedding_model, embedded_at, qdrant_point_id, updated_at); search eval fixtures; offline/degradation docs; revision history design; README + PROGRESS.md roadmap refresh
- [x] **Subtask 1** — Chunking pipeline: `services/api/app/search/chunker.py` splits text into overlapping chunks; `chunk_service.py` chunks pages, sources, and asset metadata into `chunks` rows with `chunk_idx`, `token_count`, `source_locator`, and `content_hash`
- [x] **Subtask 2** — Embedding provider abstraction + Qdrant collection setup: `EmbeddingProvider`, disabled/mock/OpenAI providers, Qdrant client wrapper, `knowledgeos_chunks` collection init on API startup, graceful Qdrant-unavailable startup behavior
- [x] **Subtask 3** — Reindex worker jobs: `reindex_object(object_id)`, `reindex_all_objects()`, worker-side embedding/Qdrant upsert, deterministic RQ job IDs, page/source save hooks, and source-ingestion completion hook
- [x] **Subtask 4** — Keyword search API: `GET /search/keyword?q=&kind=&limit=&offset=`; Postgres FTS with `plainto_tsquery` + snippet; works with no API key
- [x] **Subtask 5** — Vector search API: `POST /search/vector`; graceful 503 when embeddings disabled; Qdrant nearest neighbors → hydrate from Postgres
- [x] **Subtask 6** — Hybrid search API: `POST /search/hybrid`; parallel keyword + vector → combined score; keyword-only fallback when embeddings unavailable; `debug` mode for score breakdown
- [x] **Subtask 7** — Search UI: Cmd+K modal; unified results (tabs: All / Pages / Sources); result cards with title, kind badge, snippet, date; keyboard navigation
- [x] **Subtask 8** — Search eval fixtures → test assertions: load `tests/fixtures/search_eval_cases.json`; at least one fixture-driven test asserts keyword results contain expected kinds
- [x] **Subtask 9** — Tests + docs: `test_search.py` (~15 tests); chunking tests; update `docs/ARCHITECTURE.md`, `docs/INGESTION.md`, `docs/API.md`; target ~65 total tests

---

## Hardening Track — Search Quality + Multilingual Retrieval 🚧 Partial

**Goal:** Strengthen retrieval quality for multilingual content (Japanese focus), harden security of search snippets, and increase observability and debug visibility.

See [`project-phases/HARDENING-SEARCH-QUALITY-MULTILINGUAL.md`](project-phases/HARDENING-SEARCH-QUALITY-MULTILINGUAL.md) for the full subtask spec.

- [x] **Subtask 0** — Audit and finalize plan: added to `project-phases/`, PROGRESS updated
- [x] **Subtask 1** — Multilingual keyword fallback: `ILIKE` fallback over title + text in `search_service.py` (commits `8bfc61d`, `f42287f`). No `pg_trgm` migration yet, so the fallback runs without a trigram GIN index.
- [ ] **Subtask 2** — Search snippet sanitization: backend still ships raw `<mark>` snippets via Postgres `ts_headline`; `SearchResultCard.tsx` still calls `dangerouslySetInnerHTML` with no sanitizer. **XSS risk if a user pastes script tags into a page or extracted source text.**
- [ ] **Subtask 3** — Search eval fixture expansion: `tests/fixtures/search_eval_cases.json` still has no Japanese or mixed-language cases.
- [ ] **Subtask 4** — Search debug visibility: backend `HybridRequest.debug: bool = False` plumbed through `schemas/search.py`, but `SearchModal.tsx` does not expose a debug toggle or render scores.
- [ ] **Subtask 5** — Index/reindex observability: no `GET /api/v1/objects/{id}/index-status` endpoint; no doc on `reindex_object` / `reindex_all_objects` worker jobs.
- [ ] **Subtask 6** — Documentation and final validation: not yet rolled into `docs/API.md` / `docs/SECURITY.md` / `docs/ARCHITECTURE.md`.

---

## Phase 4 — Graph Lite ✅ Complete

**Goal:** Give the knowledge base a graph backbone using the existing Postgres `edges` table. Surface typed links and backlinks in the UI without requiring Kùzu yet.

- [x] **Subtask 0** — Phase 3 audit + backend-first Graph Lite plan saved to [`project-phases/PHASE-4-GRAPH-LITE.md`](project-phases/PHASE-4-GRAPH-LITE.md)
- [x] **Subtask 1** — Edge taxonomy + validation: canonical graph edge kinds, legacy kind preservation, service/schema validation
- [x] **Subtask 2** — Harden edge API: idempotent create, soft-delete restoration, ownership checks, deleted object exclusion, metadata/weight support
- [x] **Subtask 3** — Object graph APIs: `GET /objects/{id}/edges`, `/backlinks`, `/related` over Postgres edges, depth 1–2
- [x] **Subtask 4** — Tests + docs: graph API coverage; update `docs/DATA_MODEL.md`, `docs/API.md`, `docs/ARCHITECTURE.md`, `docs/AGENT_GUIDE.md`
- [x] **Subtask 5** — Phase 4B UI: `ObjectPicker` (search-based object selector), `LinkToModal` (typed edge kind chooser), `BacklinksPanel` (inbound links), `RelatedPanel` (depth-1 traversal), `GraphPanel` (tabbed right sidebar in page editor); "Link to…" toolbar button; `EdgeWithObjectsOut` + `RelatedObjectOut` types; `getObjectBacklinks` + `getObjectRelated` API functions

**Phase 4A complete:**
- Edge taxonomy and validation (`links_to`, `cites`, `derives_from`, `mentions`, `supports`, `contradicts`, `related_to`, `summarizes`, `belongs_to_project`, `evidence_for`, `created_from`) with legacy kinds preserved.
- Hardened `/api/v1/edges` behavior: validated kinds, ownership checks for both objects, deleted-object exclusion, idempotent create, soft-deleted edge restore, `weight`, and `metadata`.
- Object graph API foundation: object-centered edge listing, backlinks, and related-object traversal over Postgres only.

**Phase 4B complete:**
- `ObjectPicker` modal searches all KB objects via keyword search API.
- `LinkToModal` lets user choose edge kind (`links_to`, `mentions`, `supports`, `contradicts`, `related_to`) before creating the edge.
- `BacklinksPanel` + `RelatedPanel` render as a collapsible right sidebar in page editor.
- `GraphPanel` provides tabbed Backlinks / Related UI.

**Kùzu (optional):** Deferred. Postgres traversal is sufficient for depth 1–2. Add Kùzu if deeper traversal is needed.

---

## Phase 8A — Workspace Lite ✅ Complete

**Goal:** Let the user open a second object beside their current view without navigating away. Frontend-only split pane (no DB schema changes). Ran in parallel with Phase 5 and Phase 6 on branch `phase8a-workspace-lite`.

See [`project-phases/PHASE-8A-WORKSPACE-LITE.md`](project-phases/PHASE-8A-WORKSPACE-LITE.md) for the full subtask spec.

- [x] **Subtask 0** — Audit + plan files: create phase doc, update PROGRESS.md
- [x] **Subtask 1** — Routing helper (`objectRoute`) + `WorkspaceLiteProvider` React context
- [x] **Subtask 2** — `ObjectPaneViewer`: `PagePaneView`, `SourcePaneView`, asset/fallback views
- [x] **Subtask 3** — Side pane layout: `WorkspaceSidePane` + AppShell integration (`min-w-0`, conditional pane)
- [x] **Subtask 4** — Open in side pane from search results (`SearchResultCard` + `SearchModal`)
- [x] **Subtask 5** — Open in side pane from graph panels (`BacklinksPanel`, `RelatedPanel`)
- [x] **Subtask 6** — Polish (ESC key, responsive behavior, smooth transition) + docs

---

## Phase 5 — AI Assistant + Inbox/Triage ✅ Complete

**Goal:** Embed AI directly into the editing and research workflow. Every AI write creates an `agent_runs` row + `object_revisions` row; features degrade gracefully when `OPENAI_API_KEY` is absent.

See [`project-phases/PHASE-5-AI-ASSISTANT.md`](project-phases/PHASE-5-AI-ASSISTANT.md) for the full subtask spec.

- [x] **Subtask 0** — Migration 0004: `object_revisions` table + `ai_generated` column on objects; `openai_chat_model`/`openai_max_tokens` config; plan saved to `project-phases/`
- [x] **Subtask 1** — AI client module + router scaffold: `app/ai/client.py` (`call_ai()` wrapper auto-creates `AgentRun` rows), `app/ai/prompts.py` (all prompt templates), `app/services/revision_service.py` (`create_revision()`), `app/schemas/ai.py` (all request/response schemas), `app/api/v1/ai.py` (router registered)
- [x] **Subtask 2** — Summarize endpoint: `POST /api/v1/ai/summarize` reads page/source content, generates summary, writes to `metadata_["ai_summary"]`, creates `object_revisions` record; cache + force-refresh supported
- [x] **Subtask 3** — Extract claims + tasks: `POST /api/v1/ai/extract-claims` and `/extract-tasks` create typed child objects + `mentions` edges; JSON parse errors degrade gracefully
- [x] **Subtask 4** — Suggest links: `POST /api/v1/ai/suggest-links` uses keyword search + LLM ranking; read-only (no auto-write)
- [x] **Subtask 5** — KB Q&A: `POST /api/v1/ai/answer` uses hybrid search + LLM; returns citations parsed from `Sources: [uuid]` pattern
- [x] **Subtask 6** — Inbox API + triage: `GET /api/v1/ai/inbox` (last 30 days, no tags/description); `POST /api/v1/ai/triage` (read-only tag/title/summary suggestions)
- [x] **Subtask 7** — AI Sidebar UI: `AiPanel` component in `GraphPanel` (new "AI" tab alongside Backlinks/Related); Summarize, Extract Claims/Tasks, Suggest Links (with Create Link button), Ask KB with citations
- [x] **Subtask 8** — Inbox UI: `/inbox` page + `InboxView` + `TriageModal` (toggle tags, edit title, apply via `PATCH /objects/{id}`); Inbox nav link in Sidebar
- [x] **Subtask 9** — Tests + docs: `tests/api/test_ai.py` (14 tests with mocked OpenAI); `docs/API.md` updated with all AI endpoints

---

## Phase 6A — Chat Import Lite ✅ Complete

> Historical note: the bottom `Structured Import (requires Phase 5 AI)` subtasks listed under this phase have been superseded by the standalone Phase 6B section below. They are retained for traceability only.



**Goal:** Turn pasted/uploaded ChatGPT, Claude, Markdown, and plain-text conversations into durable, searchable chat objects without AI extraction.

See [`project-phases/PHASE-6A-CHAT-IMPORT-LITE.md`](project-phases/PHASE-6A-CHAT-IMPORT-LITE.md) for the full subtask spec.

- [x] **Subtask 0** — Audit + Phase 6A plan artifact
- [x] **Subtask 1** — Chat object model, `chats` specialization table, object-kind validation, and library `chats/` setup
- [x] **Subtask 2** — Parser/storage/services for ChatGPT batch JSON, Claude-like Markdown, Markdown labels, and plain-text fallback
- [x] **Subtask 3** — Authenticated `/api/v1/chats` import/list/detail/raw/delete/restore/reindex endpoints
- [x] **Subtask 4** — Chunk/search/reindex integration for `chat.content_text`
- [x] **Subtask 5** — `/app/chats` list/import UI and `/app/chats/[id]` turn/detail/raw UI
- [x] **Subtask 6** — Shared frontend object routing for `kind=chat` in search/graph/all-object navigation
- [x] **Subtask 7** — Parser/API/search tests, fixtures, docs, and progress updates

**Structured Import (requires Phase 5 AI):**
- [ ] **Subtask 1** — LLM summarizer: decisions, open questions, action items, claims, concepts, projects
- [ ] **Subtask 2** — Object extraction: Claim, Task, concept → edges from chat
- [ ] **Subtask 3** — Tests + docs: fixture exports; update `docs/INGESTION.md`

---

## Phase 6B — Structured Chat Import ✅ Complete

**Goal:** Turn imported chats into structured, linked, reusable knowledge through explicit AI-backed summary generation and apply flow.

See [`project-phases/PHASE-6B-STRUCTURED-CHAT-IMPORT.md`](project-phases/PHASE-6B-STRUCTURED-CHAT-IMPORT.md) for the full subtask spec.

**Audit note:** The repo has Phase 6A complete, but Phase 5 is only partially present. Phase 6B includes the minimal AI client, revision service, and generic Claim/Task object support needed for structured chat import; it does not implement the full Phase 5 AI Assistant/Inbox scope.

- [x] **Subtask 0** — Audit + Phase 6B plan artifact
- [x] **Subtask 1** — Minimal AI/revision/claim-task prerequisites
- [x] **Subtask 2** — Structured summary data model
- [x] **Subtask 3** — Structured summary schema and prompt
- [x] **Subtask 4** — Structured summary preview API
- [x] **Subtask 5** — Apply structured summary and extracted objects
- [x] **Subtask 6** — Search/index integration
- [x] **Subtask 7** — Chat detail UI
- [x] **Subtask 8** — Tests and docs

---

## Phase 7A — MCP Read/Search + Safety Foundation ✅ Complete

**Goal:** Safe local-only stdio MCP server with read/search tools. No write tools. No shell. No arbitrary filesystem access. `answer_from_kb` registered as disabled stub.

**Commits:** 4 commits · 24 tests passing (19 MCP package + 5 FastAPI token auth)

See [`project-phases/PHASE-7A-MCP.md`](project-phases/PHASE-7A-MCP.md) for the full subtask spec.

- [x] **Subtask 0** — Audit + plan files: create phase doc, update PROGRESS.md
- [x] **Subtask 1** — MCP config + safety foundation: `McpSettings`, `redact_dict`, `pyproject.toml`, `.env.example`
- [x] **Subtask 2** — FastAPI internal token auth: `config.py` + `deps.py` + 5 `test_mcp_auth.py` tests
- [x] **Subtask 3** — MCP API client: `client.py` (httpx, 6 methods, depth/limit caps)
- [x] **Subtask 4** — MCP server scaffold: `server.py` + `tools.py` + tool registry + `list_tools`/`call_tool` handlers
- [x] **Subtask 5** — Search tools: `search_objects`, `hybrid_search` (with 503 → keyword fallback)
- [x] **Subtask 6** — Object/page/source tools: `get_object`, `get_page` (50k truncation), `get_source` (configurable text truncation)
- [x] **Subtask 7** — Graph tool + `answer_from_kb` stub: `get_related_objects` (depth capped at 2), disabled stub with clear error
- [x] **Subtask 8** — Tests: `test_config.py` (6), `test_tools.py` (13), `test_mcp_auth.py` (5) — all passing
- [x] **Subtask 9** — Docs: `MCP_TOOLS.md` (full rewrite), `SECURITY.md` (MCP token + safety section), `AGENT_GUIDE.md` (MCP usage patterns)

---

## Phase 7B — MCP Write Tools ⬜ Planned

**Goal:** Add create/update/archive write tools to MCP. Requires Phase 5 `object_revisions` table.

- [ ] **v2 — Create Tools:** `create_page`, `create_edge`, `ingest_url`, `ingest_file`; validates agent identity + writes `agent_runs`
- [ ] **v3 — Update/Archive Tools:** `update_page`, `archive_object`; before/after diff logged; rollback supported
- [ ] **MCP resources:** `knowledgeos://objects/{id}`, `knowledgeos://pages/{id}`, `knowledgeos://sources/{id}`
- [ ] **Tests + docs**

---

## Phase 8 — Multi-Pane Workspaces ⬜ Planned

**Goal:** Transform the app into a serious research environment — multiple pages, sources, and AI tools open side by side in a saved, reusable workspace layout.

- [ ] **Subtask 1** — Pane layout engine: split main area into 2–4 resizable panes; each pane can independently show any object (page, source, asset, search)
- [ ] **Subtask 2** — Workspace data model: `workspaces` table with `layout_json` storing open pane configurations; CRUD API
- [ ] **Subtask 3** — Save/restore workspace: "Save Workspace" button; named workspace list in sidebar; restore opens exact pane set
- [ ] **Subtask 4** — Drag selected text between panes: drag text from source pane → creates a quote block in page pane with back-reference
- [ ] **Subtask 5** — Link pane to pane: "Link current page to another open page" command; creates typed edge instantly
- [ ] **Subtask 6** — AI scoped to workspace: AI sidebar context picker — "Ask about this pane", "Ask about selected panes", "Ask about whole workspace"
- [ ] **Subtask 7** — Workspace-scoped search: search results filtered to objects open or linked in the current workspace
- [ ] **Subtask 8** — Tests + docs: workspace CRUD tests; UI smoke test; `docs/ARCHITECTURE.md` updated

---

## Phase 9 — Career & Project Memory ⬜ Planned

**Goal:** Make KnowledgeOS a personal career memory system — structured project records, evidence-linked resume bullets, and STAR interview stories generated from real project data.

- [ ] **Subtask 1** — Project schema + UI: `projects` table (period, role, problem, actions, metrics, skills, artifacts); Project object create/edit form
- [ ] **Subtask 2** — Project extraction assistant: `POST /ai/create-project-memory` — LLM reads a set of pages/chats/sources scoped to a project and populates the project schema
- [ ] **Subtask 3** — Evidence linking: attach pages, sources, claims, and chat summaries to a project as `belongs_to_project` edges; evidence panel in project view
- [ ] **Subtask 4** — Resume bullet generator: `POST /ai/generate-resume-bullets` — input: project_id + target role + emphasis; output: 3 bullet variants with evidence citations and confidence flags
- [ ] **Subtask 5** — Interview story generator: STAR format story generator from project record; exportable as Markdown
- [ ] **Subtask 6** — Career memory dashboard: timeline view of projects; filter by skill/role/period; evidence completeness indicator per project
- [ ] **Subtask 7** — Export: generate Markdown / PDF resume section from selected projects + bullets
- [ ] **Subtask 8** — Tests + docs: project extraction tests; bullet generation tests with mocked OpenAI; `docs/AGENT_GUIDE.md` updated with career module

---

## Summary

| Phase | Name | Status | Progress |
|---|---|---|---|
| 1 | Foundation | ✅ Complete | 8 / 8 subtasks |
| 2 | Sources & Rich Media | ✅ Complete | 9 / 9 subtasks |
| 3 | Search | ✅ Complete | 10 / 10 subtasks |
| 4 | Graph Lite | ✅ Complete | 6 / 6 subtasks |
| 8A | Workspace Lite | ✅ Complete | 7 / 7 subtasks |
| 5 | AI Assistant + Inbox/Triage | ✅ Complete | 9 / 9 subtasks |
| 6A | Chat Import Lite | ✅ Complete | 8 / 8 subtasks |
| 6B | Structured Chat Import | ✅ Complete | 9 / 9 subtasks |
| 7A | MCP Read/Search | ✅ Complete | 10 / 10 subtasks |
| Hardening | Search Quality + Multilingual | 🚧 Partial | 2 / 7 subtasks |
| 7B | MCP Write Tools | ⬜ Planned | 0 / 4 subtasks |
| 8 | Multi-Pane Workspaces | ⬜ Planned | 0 / 8 subtasks |
| 9 | Career & Project Memory | ⬜ Planned | 0 / 8 subtasks |

**Total:** 78 / 103 subtasks complete (76 phase subtasks + 2 hardening subtasks of 7)

**Key cross-cutting concepts to track:**
- Inbox/Triage (Phase 5): AI-classified staging area for unprocessed items
- Search evaluation (Phase 3+): `tests/fixtures/search_eval_cases.json` as regression anchors
- Revision history (Phase 5 prerequisite): required before MCP write tools go live — see `docs/REVISION_HISTORY.md`
- Offline/degradation contract: keyword search always works; AI features degrade gracefully — see `docs/ARCHITECTURE.md`

**Current repo state notes (2026-05-15 audit):**

*Verified complete and matching the phase plans:*
- Phase 1 Foundation, Phase 2 Sources, Phase 3 Search (incl. multilingual ILIKE fallback), Phase 4 Graph Lite, Phase 5 AI Assistant + Inbox, Phase 6A Chat Import, Phase 6B Structured Chat Import, Phase 7A MCP Read/Search, and Phase 8A Workspace Lite are all implemented and exercised by tests.
- Test counts (2026-05-15): 112 API integration tests across `tests/api/`, 16 unit tests in `tests/unit/`, 19 MCP package tests in `services/mcp/tests/`.
- Alembic migrations 0001–0006 all present and consistent.

*Phase deviations / known gaps surfaced during this audit:*
- **Phase 5 inbox endpoint path**: spec says `GET /api/v1/objects/inbox`; implementation lives at `GET /api/v1/ai/inbox`. Frontend matches the actual path. Spec doc is the one that's stale, not the code.
- **Phase 7A `answer_from_kb` stub is obsolete**: `services/mcp/kos_mcp/tools.py` still raises `"Phase 5 AI assistant endpoint has not been implemented yet."` even though Phase 5 is now complete. Wiring this to `POST /api/v1/ai/answer` is a clean Phase 7A follow-up (not Phase 7B since it is read-only).
- **Phase 2 docker-compose gap**: `infra/docker-compose.yml` defines `postgres`, `redis`, `qdrant`, `api`, `web` but no `worker` service. RQ jobs (PDF extraction, embedding, reindex) only run if the user manually starts `rq worker kos-ingest` on the host. `docker compose up -d` alone leaves all source ingestion stuck in `pending`.
- **Phase 2 worker tests missing**: `tests/worker/` was specified in `PHASE-2-SOURCES.md` (extractor tests with `sample.pdf`, `sample.jpg`, `sample.csv`) but does not exist. Extractor logic in `services/worker/kos_worker/extractors/` has no automated coverage.
- **Hardening track**: only Subtasks 0 + 1 are complete (see section above). Snippet sanitization, JP fixtures, debug UI, and index-status endpoint are still open.

*Frontend routing oddities (not phase blockers but worth fixing):*
- `Sidebar.tsx` links to `/app/trash` but no route exists at `(app)/app/trash/`.
- `Sidebar.tsx` links to `/app/assets`, but the actual route file is `(app)/assets/page.tsx`, which serves at `/assets`. The active-state highlight and link both resolve to a 404 until you fix one side.
- Inconsistent grouping: pages list is at `/app/pages` but page detail is at `/pages/[id]`; chats are entirely under `/app/chats/…`; sources are entirely under `/sources/…`. This is organic drift, not a phase-plan requirement.

*Infrastructure oddities:*
- `infra/.env.example` defines `MCP_INTERNAL_TOKEN=` twice and `MCP_API_BASE_URL=http://127.0.0.1:8000`, but the dockerized API is published on `127.0.0.1:8001` (compose maps `8001 → api:8000`). A host-side `kos-mcp` run against the dockerized API will need `MCP_API_BASE_URL=http://127.0.0.1:8001`.
- Postgres in `docker-compose.yml` is published on `127.0.0.1:5433` (not 5432). Tests and scripts that assume 5432 should target 5433 or use the Docker network DNS.
- `README.md` previously referenced `scripts/backup.sh` and `scripts/reindex.py`; only `scripts/setup.sh` and `scripts/run_tests.sh` exist. README has been corrected.
- `test_output.txt` and `test_output_2.txt` are checked-in pytest log dumps (≈260KB / 21KB) at the repo root. They should be `.gitignore`d or deleted.
