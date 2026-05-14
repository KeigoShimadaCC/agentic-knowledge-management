# KnowledgeOS — Progress Tracker

> Last updated: 2026-05-14

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

## Hardening Track — Search Quality + Multilingual Retrieval 🚧 In Progress

**Goal:** Strengthen retrieval quality for multilingual content (Japanese focus), harden security of search snippets, and increase observability and debug visibility.

See [`project-phases/HARDENING-SEARCH-QUALITY-MULTILINGUAL.md`](project-phases/HARDENING-SEARCH-QUALITY-MULTILINGUAL.md) for the full subtask spec.

- [x] **Subtask 0** — Audit and finalize plan: add plan to `project-phases/`, update `PROGRESS.md`
- [ ] **Subtask 1** — Multilingual keyword fallback: support Japanese/mixed-language via `ILIKE` fallback + `pg_trgm`
- [ ] **Subtask 2** — Search snippet sanitization: prevent XSS in highlighted snippets
- [ ] **Subtask 3** — Search eval fixture expansion: add Japanese and mixed-language cases to `search_eval_cases.json`
- [ ] **Subtask 4** — Search debug visibility: display ranking scores in UI (optional/dev-mode)
- [ ] **Subtask 5** — Index/reindex observability: add index status endpoint and document reindex commands
- [ ] **Subtask 6** — Documentation and final validation: update API/Architecture/Security docs

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

## Phase 5 — AI Assistant + Inbox/Triage ⬜ Planned

**Goal:** Embed AI directly into the editing and research workflow. Prerequisite: `object_revisions` table in place before AI can write back to pages (see `docs/REVISION_HISTORY.md`).

**Prerequisite:** OpenAI API key set in `infra/.env`.

- [ ] **Subtask 1** — OpenAI client setup: typed wrapper, configurable model, cost tracking to `agent_runs`, retries with exponential backoff
- [ ] **Subtask 2** — AI sidebar component: collapsible right panel, chat-style UI, scoped to current page/selected text/workspace; "AI" badge on agent-generated content
- [ ] **Subtask 3** — Summarize page: `POST /ai/summarize` → LLM summary stored back on page; one-click in toolbar
- [ ] **Subtask 4** — Summarize source: same for PDF/web/YouTube; displays in source detail panel
- [ ] **Subtask 5** — Extract claims: `POST /ai/extract-claims` → creates `Claim` objects linked via `derived_from` edge
- [ ] **Subtask 6** — Extract tasks + entities: action items → Task objects; people/orgs/concepts mentioned
- [ ] **Subtask 7** — Suggest links: `POST /ai/suggest-links` → search KB, propose edges with explanation
- [ ] **Subtask 8** — KB Q&A with citations: `POST /ai/answer` — hybrid retrieval → context pack → LLM answer with `[source_id, chunk_id]` citations
- [ ] **Subtask 9** — Inbox/Triage: `POST /ai/triage-inbox` → LLM classifies and routes unprocessed items in `library/inbox/`; inbox view in sidebar
- [ ] **Subtask 10** — `object_revisions` table: implement as prerequisite to AI page writes; link to `agent_runs`; rollback API
- [ ] **Subtask 11** — All AI writes create `agent_runs` rows; UI shows AI-generated badge
- [ ] **Subtask 12** — Tests + docs: mock OpenAI in tests; update `docs/AGENT_GUIDE.md`, `docs/REVISION_HISTORY.md`

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

**Structured Import (requires Phase 5 AI):**
- [ ] **Subtask 1** — LLM summarizer: decisions, open questions, action items, claims, concepts, projects
- [ ] **Subtask 2** — Object extraction: Claim, Task, concept → edges from chat
- [ ] **Subtask 3** — Tests + docs: fixture exports; update `docs/INGESTION.md`

---

## Phase 6B — Structured Chat Import ⬜ In Progress

**Goal:** Turn imported chats into structured, linked, reusable knowledge through explicit AI-backed summary generation and apply flow.

See [`project-phases/PHASE-6B-STRUCTURED-CHAT-IMPORT.md`](project-phases/PHASE-6B-STRUCTURED-CHAT-IMPORT.md) for the full subtask spec.

**Audit note:** The repo has Phase 6A complete, but Phase 5 is only partially present. Phase 6B includes the minimal AI client, revision service, and generic Claim/Task object support needed for structured chat import; it does not implement the full Phase 5 AI Assistant/Inbox scope.

- [x] **Subtask 0** — Audit + Phase 6B plan artifact
- [ ] **Subtask 1** — Minimal AI/revision/claim-task prerequisites
- [ ] **Subtask 2** — Structured summary data model
- [ ] **Subtask 3** — Structured summary schema and prompt
- [ ] **Subtask 4** — Structured summary preview API
- [ ] **Subtask 5** — Apply structured summary and extracted objects
- [ ] **Subtask 6** — Search/index integration
- [ ] **Subtask 7** — Chat detail UI
- [ ] **Subtask 8** — Tests and docs

---

## Phase 7A — MCP Read/Search + Safety Foundation ⬜ In Progress

**Goal:** Safe local-only stdio MCP server with read/search tools. No write tools. No shell. No arbitrary filesystem access. `answer_from_kb` deferred until Phase 5 AI endpoint is built.

See [`project-phases/PHASE-7A-MCP.md`](project-phases/PHASE-7A-MCP.md) for the full subtask spec.

- [x] **Subtask 0** — Audit + plan files: create phase doc, update PROGRESS.md
- [ ] **Subtask 1** — MCP config + safety foundation: `McpSettings`, `redact_dict`, `pyproject.toml`, `.env.example`
- [ ] **Subtask 2** — FastAPI internal token auth: `config.py` + `deps.py` + `test_mcp_auth.py`
- [ ] **Subtask 3** — MCP API client: `client.py` (httpx, 6 methods)
- [ ] **Subtask 4** — MCP server scaffold: `server.py` + `tools.py` skeleton + tool registry
- [ ] **Subtask 5** — Search tools: `search_objects`, `hybrid_search` (with 503 fallback)
- [ ] **Subtask 6** — Object/page/source tools: `get_object`, `get_page`, `get_source`
- [ ] **Subtask 7** — Graph tool + `answer_from_kb` stub: `get_related_objects`, disabled stub
- [ ] **Subtask 8** — Tests: `test_config.py`, `test_tools.py`, `test_mcp_auth.py`
- [ ] **Subtask 9** — Docs: `MCP_TOOLS.md`, `SECURITY.md`, `AGENT_GUIDE.md`, `README.md`

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
| 5 | AI Assistant + Inbox/Triage | ⬜ Planned | 0 / 12 subtasks |
| 6A | Chat Import Lite | ✅ Complete | 8 / 8 subtasks |
| 6B | Structured Chat Import | ⬜ In Progress | 1 / 9 subtasks |
| 7A | MCP Read/Search | ⬜ In Progress | 1 / 10 subtasks |
| 7B | MCP Write Tools | ⬜ Planned | 0 / 4 subtasks |
| 8 | Multi-Pane Workspaces | ⬜ Planned | 0 / 8 subtasks |
| 9 | Career & Project Memory | ⬜ Planned | 0 / 8 subtasks |

**Total:** 50 / 99 subtasks complete

**Key cross-cutting concepts to track:**
- Inbox/Triage (Phase 5): AI-classified staging area for unprocessed items
- Search evaluation (Phase 3+): `tests/fixtures/search_eval_cases.json` as regression anchors
- Revision history (Phase 5 prerequisite): required before MCP write tools go live — see `docs/REVISION_HISTORY.md`
- Offline/degradation contract: keyword search always works; AI features degrade gracefully — see `docs/ARCHITECTURE.md`

**Current repo state notes (2026-05-14):**
- Phase 3 search is complete, including keyword, vector, and hybrid API behavior, search UI, integration tests, and API/architecture documentation.
- Phase 6A Chat Import Lite is complete: chat object model/API/parser/storage/search/UI and test coverage are in place. Chat migration is `0005_add_chats.py` because an existing local `0004_object_revisions.py` migration is present in the workspace.
- Phase 6B Structured Chat Import is active. The repo audit found Phase 5 incomplete, so Phase 6B includes only the minimal AI/revision/Claim/Task prerequisites needed for chat structure extraction.
