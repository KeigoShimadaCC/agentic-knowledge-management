# KnowledgeOS — Progress Tracker

> Last updated: 2026-05-15 (Phase 9A merged to main; PHASE-ENHANCE-03 UX-T1 shipped; PHASE-FIX-01/02 complete)

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
- [x] **Subtask 2** — Search snippet sanitization: `ts_headline` now uses sentinel chars (`\x01`/`\x02`); `_parse_snippet()` returns `SearchSnippet{text, highlights}`; `SearchResultCard.tsx` renders with `<mark>` React nodes (no `dangerouslySetInnerHTML`). XSS regression tests added.
- [x] **Subtask 3** — Search eval fixture expansion: 4 Japanese/mixed-language cases added to `tests/fixtures/search_eval_cases.json`; parametric test `test_jp_mixed_search_does_not_crash` added.
- [x] **Subtask 4** — Search debug visibility: `SearchModal.tsx` now has a "Show scores" toggle (localStorage-persisted); `SearchResultCard.tsx` renders `score`, `keyword_score`, `vector_score` when debug is on; `useSearch` and `hybridSearch` forward `debug` flag.
- [x] **Subtask 5** — Index/reindex observability: `GET /api/v1/objects/{id}/index-status` endpoint added (returns total_chunks, embedded_count, status, last_embedded_at). Documented in `docs/API.md` and `docs/INGESTION.md`. `scripts/reindex.py` CLI added.
- [x] **Subtask 6** — Documentation and final validation: `docs/API.md` updated (snippet shape, debug param, index-status endpoint); `docs/SECURITY.md` updated (XSS mitigation section, answer_from_kb wire-up note); `docs/INGESTION.md` updated (reindex CLI).

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

**Structured Import (superseded by Phase 6B):**
- ✅ Implemented in [Phase 6B — Structured Chat Import](#phase-6b--structured-chat-import--complete).
  See subtasks 1–8 under Phase 6B; that section is the canonical record.

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

## Phase Enhance 03 — UX/UI Polish 🚧 In Progress

**Goal:** Lift KnowledgeOS to a polished daily-driver: design system tokens, UI primitives, toast system, keyboard shortcuts overlay, responsive layouts, light theme, and accessibility baseline. All changes purely additive; no existing files renamed or removed.

Working branch: `phase-enhance-03-ux-polish` (worktree: `/private/tmp/akm-enhance-03`)

See [`project-phases/PHASE-ENHANCE-03-UX-POLISH.md`](project-phases/PHASE-ENHANCE-03-UX-POLISH.md) for the full spec.

- [x] **UX-T1** — Design tokens (`tokens.css`), Tailwind extension, Inter + JetBrains Mono fonts, 20 UI primitives (`components/ui/`), 3 layout primitives, `cn()` helper, 7 `data-testid` additions on contractual components, feature flag stubs in `.env.example`. `typecheck ✓  lint ✓  build ✓` — commit `d969ef8`
- [ ] **UX-T2** — Toast system, route error boundaries, mobile drawer, sidebar collapse (Cmd+\), inline save-status feedback
- [ ] **UX-T3** — cmdk search palette + Tiptap bubble/slash menus (both flag-gated; default off)
- [ ] **UX-T4** — Unified list page shell with filters, sort, keyboard nav (j/k), bulk actions
- [ ] **UX-T5** — Light theme support, auth screen redesign, ThemeProvider
- [ ] **UX-T6** — Accessibility baseline (axe audit), shortcut overlay (?), a11y + UX docs

---

## Phase 7B — MCP Write Tools ⬜ Planned

**Goal:** Add create/update/archive write tools to MCP. Phase 5 `object_revisions` now ships, so this phase is unblocked and planned in [`project-phases/PHASE-7B-MCP-WRITE.md`](project-phases/PHASE-7B-MCP-WRITE.md).

- [ ] **v2 — Create Tools:** `create_page`, `create_edge`, `ingest_url`, `ingest_file`; validates agent identity + writes `agent_runs` and `object_revisions`
- [ ] **v3 — Update/Archive Tools:** `update_page`, `archive_object`; before/after snapshots logged; rollback supported
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

## Phase 9A — Career Memory Backend Foundation ✅ Complete

**Goal:** Backend-only foundation for career/project memory: `project` object kind, `projects` table (Alembic `0007`), REST CRUD under `/api/v1/projects`, and `POST /api/v1/ai/extract-project` with mocked-OpenAI integration tests. Spec: [`project-phases/PHASE-9A-CAREER-MEMORY-BACKEND.md`](project-phases/PHASE-9A-CAREER-MEMORY-BACKEND.md).

- [x] **Schema + kind** — `VALID_OBJECT_KINDS` includes `project`; `projects` table mirrors chat/page extension pattern; `Project` ORM model
- [x] **Pydantic + service** — `schemas/project.py` (CRUD + extract request/response), `project_service.py` (CRUD, soft delete, extract with `agent_runs` audit)
- [x] **REST** — `api/v1/projects.py` + router registration; restore via existing `POST /api/v1/objects/{id}/restore`
- [x] **AI** — Thin `extract-project` route in `api/v1/ai.py`; JSON-mode extraction; 503 when `OPENAI_API_KEY` unset; 502 + persisted failed `agent_run` on malformed JSON
- [x] **Tests** — `tests/api/test_projects.py` (12 cases), five new cases appended to `tests/api/test_ai.py`
- [ ] **Follow-up (9B+)** — MCP project tools (after 7B audited writes), resume/interview generators, frontend; optional retrofit of project mutations to `audited_write_service` once Phase 7B merges

**Verification:** `cd tests && PYTHONPATH=../services/api uv run --project ../services/api --extra dev pytest api/ -q` → 135 passed; `pytest unit/` → 16 passed; `cd services/api && uv run ruff check . && uv run ruff format --check .` clean.

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
| 9 | Career & Project Memory | 🚧 In progress (9A backend shipped) | 1 / 8 (9A scope) |
| Enhance-03 | UX/UI Polish | 🚧 In Progress | 1 / 6 PRs (UX-T1 shipped) |

**Total:** 79 / 103 subtasks complete (77 phase subtasks + 2 hardening subtasks of 7)

**Key cross-cutting concepts to track:**
- Inbox/Triage (Phase 5): AI-classified staging area for unprocessed items
- Search evaluation (Phase 3+): `tests/fixtures/search_eval_cases.json` as regression anchors
- Revision history: implemented for Phase 5/6B and required for MCP write tools — see `docs/REVISION_HISTORY.md`
- Offline/degradation contract: keyword search always works; AI features degrade gracefully — see `docs/ARCHITECTURE.md`

**Current repo state notes (2026-05-15 audit):**

*Phase Enhance 02 testing infrastructure started on branch `phase-enhance-02-t1-vitest`:*
- T1 checkpoint 1 complete: added Vitest 4 + jsdom + React Testing Library + MSW scaffold for `apps/web`, root `test:web`, web `test`, `test:run`, and `test:coverage` scripts, and HTML coverage output under `apps/web/coverage/`.
- Added 17 frontend unit/hook tests across `apiFetch` and API helper routing, `objectRoute`, `useAuth`, `useSearch`, and `useAutoSave`.
- Verification: `pnpm -F @kos/web test:run` passed with 5 files / 17 tests in ~1.5s; `pnpm -F @kos/web test:coverage` passed with 84.53% line coverage over the configured T1 targets; `pnpm -F @kos/web typecheck` and `pnpm -F @kos/web lint` passed.

*Phase Fix 02 cleanup completed on branch `phase-fix-02-forgotten-undocumented`:*
- Completed F8-F10: `infra/.env.example` has one `MCP_INTERNAL_TOKEN`, host-side MCP defaults point to `http://127.0.0.1:8001`, local published ports are documented, and host-side Postgres examples/tests use `127.0.0.1:5433`.
- Completed F11: `scripts/backup.sh` ships a local Postgres dump, library tarball, and best-effort Qdrant snapshot flow; verified against running Compose services with output under `~/KnowledgeOS/backups/20260515-021801/`.
- Completed F12: `tests/dummy_pkg` now has a README, with references in `tests/pyproject.toml` and `AGENTS.md`.
- Completed F13: `project-phases/PHASE-7B-MCP-WRITE.md` exists, Phase 7B is marked unblocked, and `docs/MCP_TOOLS.md` links to the write-tools plan.
- Completed F14: docs were swept for shipped Phase 5/6B/7A/8A state; validation also fixed a structured-summary prompt formatting bug and search/test harness issues uncovered by the full suite.

*Verification on Phase Fix 02 branch:*
- Static checks: `grep -c "^MCP_INTERNAL_TOKEN=" infra/.env.example` => `1`; no host-side `localhost:5432` / `127.0.0.1:5432` matches in `README.md`, `docs`, `project-phases`, `tests`, or `scripts`; no stale host-side `MCP_API_BASE_URL=http://127.0.0.1:8000` defaults in `docs`, `infra`, or `README.md`; `bash -n scripts/backup.sh` passed.
- Frontend: `pnpm lint`, `pnpm typecheck`, and `pnpm build` passed.
- Backend/API: `uv run --project services/api --extra dev ruff check services/api` passed; `PYTHONPATH=../services/api uv run --project ../services/api --extra dev pytest api/ unit/ -v` passed with 128 tests and one Qdrant client/server version warning.
- MCP: `uv run --project services/mcp --extra dev pytest services/mcp/tests/ -v` passed with 19 tests.
- Branch state: pushed to `origin/phase-fix-02-forgotten-undocumented`.

*Verified complete and matching the phase plans:*
- Phase 1 Foundation, Phase 2 Sources, Phase 3 Search (incl. multilingual ILIKE fallback), Phase 4 Graph Lite, Phase 5 AI Assistant + Inbox, Phase 6A Chat Import, Phase 6B Structured Chat Import, Phase 7A MCP Read/Search, and Phase 8A Workspace Lite are all implemented and exercised by tests.
- Test counts (2026-05-15): **135** API integration tests across `tests/api/`, 16 unit tests in `tests/unit/`, 19 MCP package tests in `services/mcp/tests/`.
- Alembic migrations 0001–**0007** present (`0007` adds `projects`).

*Phase deviations / known gaps surfaced during this audit:*
- **Phase 5 inbox endpoint path**: ✅ resolved — `PHASE-5-AI-ASSISTANT.md` updated to `GET /api/v1/ai/inbox` (was `/api/v1/objects/inbox`). Frontend and code were already correct.
- **Phase 7A `answer_from_kb` stub is obsolete**: ✅ resolved — wired to `POST /api/v1/ai/answer` with 503 fallback; MCP_TOOLS.md updated; 20 MCP tests passing.
- **Phase 2 docker-compose gap**: ✅ resolved — added `kos-worker` service to `infra/docker-compose.yml` using new `infra/Dockerfile.worker`. `docker compose up -d` now starts the RQ worker automatically.
- **Phase 2 worker tests missing**: ✅ resolved — `tests/worker/` created with 18 unit tests covering PDF, image, CSV, web, and YouTube extractors. Run with `PYTHONPATH=services/api:services/worker uv run pytest tests/worker/ -v`.
- **Hardening track**: ✅ All 6 subtasks resolved (F5). Subtask 2 (XSS), Subtask 3 (JP fixtures), Subtask 4 (debug toggle), Subtask 5 (index-status), Subtask 6 (docs) all complete on branch `phase-fix-01`.

*Frontend routing oddities:* ✅ Resolved in PHASE-FIX-03 (branch `phase-fix-01`).
- All routes unified under `/app/...` prefix (F16, F17).
- Trash view built at `/app/trash` with restore action (F15).
- `objectRouting.ts`, `Sidebar.tsx`, `SourceCard.tsx` updated to match.

*Infrastructure oddities:*
- ✅ Phase Fix 02 resolved MCP env drift: `infra/.env.example` now has one `MCP_INTERNAL_TOKEN`, and host-side `kos-mcp` defaults to the dockerized API at `http://127.0.0.1:8001`.
- ✅ Phase Fix 02 resolved host-side Postgres port drift: docs and tests now use `127.0.0.1:5433`; `postgres:5432` remains the Docker-network address.
- `test_output*.txt` files: `.gitignore` already excludes them; not tracked.
