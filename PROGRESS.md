# KnowledgeOS — Progress Tracker

> Last updated: 2026-05-14 (Phase 2 complete)

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

## Phase 3 — Search ⬜ Planned

**Goal:** Make all knowledge searchable — by exact keyword, by semantic meaning, and by a hybrid of both — with a clean search UI. Keyword search must work offline with no API keys.

See [`project-phases/PHASE-3-SEARCH.md`](project-phases/PHASE-3-SEARCH.md) for the full subtask spec.

- [x] **Subtask 0** — Phase 2 audit + Phase 3 stabilization: `chunks` migration 0003 (user_id, source_locator, content_hash, embedding_status, embedding_model, embedded_at, qdrant_point_id, updated_at); search eval fixtures; offline/degradation docs; revision history design; README + PROGRESS.md roadmap refresh
- [ ] **Subtask 1** — Chunking pipeline: split page/source text into overlapping chunks; store in `chunks` table with `chunk_idx`, `token_count`, `source_locator`, `content_hash`; idempotent upsert on `(object_id, chunk_idx)`
- [ ] **Subtask 2** — Embedding provider abstraction + Qdrant collection setup: `EmbeddingProvider` protocol; `OpenAIEmbeddingProvider` + `NoOpEmbeddingProvider`; collection init idempotent; graceful app boot when Qdrant unavailable
- [ ] **Subtask 3** — Reindex worker jobs: `reindex_object(object_id)` (chunk → embed → upsert Qdrant); `reindex_all_objects()`; triggered on page/source save; deterministic RQ job ID to prevent queue flooding
- [ ] **Subtask 4** — Keyword search API: `GET /search/keyword?q=&kind=&limit=&offset=`; Postgres FTS with `plainto_tsquery` + snippet; works with no API key
- [ ] **Subtask 5** — Vector search API: `POST /search/vector`; graceful 503 when embeddings disabled; Qdrant nearest neighbors → hydrate from Postgres
- [ ] **Subtask 6** — Hybrid search API: `POST /search/hybrid`; parallel keyword + vector → combined score; keyword-only fallback when embeddings unavailable; `debug` mode for score breakdown
- [ ] **Subtask 7** — Search UI: Cmd+K modal; unified results (tabs: All / Pages / Sources); result cards with title, kind badge, snippet, date; keyboard navigation
- [ ] **Subtask 8** — Search eval fixtures → test assertions: load `tests/fixtures/search_eval_cases.json`; at least one fixture-driven test asserts keyword results contain expected kinds
- [ ] **Subtask 9** — Tests + docs: `test_search.py` (~15 tests); chunking tests; update `docs/ARCHITECTURE.md`, `docs/INGESTION.md`, `docs/API.md`; target ~65 total tests

---

## Phase 4 — Graph Lite ⬜ Planned

**Goal:** Give the knowledge base a graph backbone using the existing Postgres `edges` table. Surface typed links and backlinks in the UI without requiring Kùzu yet.

- [ ] **Subtask 1** — Typed link UI: "Link to…" button in page editor opens object picker; creates typed edge (`links_to`, `mentions`, `supports`, `contradicts`, `derived_from`)
- [ ] **Subtask 2** — Backlinks panel: right sidebar shows all objects that link to the current page; clicking navigates to the linking object
- [ ] **Subtask 3** — Related objects API: `GET /objects/{id}/related?depth=1&kinds=links_to,mentions` — Postgres edge traversal, one hop
- [ ] **Subtask 4** — Related panel UI: collapsible "Related" section in right sidebar; grouped by edge type
- [ ] **Subtask 5** — Tests + docs: edge traversal tests; update `docs/DATA_MODEL.md` + `docs/ARCHITECTURE.md`

**Kùzu (optional extension):** If graph traversal needs more than 1–2 hops, add Kùzu as an embedded graph layer. Mirror Postgres edges to Kùzu on each edge create/delete. Not required for Phase 4 baseline.

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

## Phase 6 — Chat Import ⬜ Planned

**Goal:** Turn exported ChatGPT and Claude conversations into durable, searchable, linked knowledge objects.

**Chat Import Lite (minimal, useful early):**
- [ ] **Subtask 1** — Chat upload UI: drag-and-drop JSON/Markdown, paste transcript; Chats section in sidebar
- [ ] **Subtask 2** — Parser: ChatGPT `conversations.json` + Claude export → normalized `ChatTurn[]`
- [ ] **Subtask 3** — Raw storage under `library/chats/{provider}/{chat_id}/raw.json`
- [ ] **Subtask 4** — Basic search: chunk and index chat content into `chunks` + Qdrant
- [ ] **Subtask 5** — Chat list/detail UI: show turns, search within chats

**Structured Import (requires Phase 5 AI):**
- [ ] **Subtask 6** — LLM summarizer: decisions, open questions, action items, claims, concepts, projects
- [ ] **Subtask 7** — Object extraction: Claim, Task, concept → edges from chat
- [ ] **Subtask 8** — Tests + docs: fixture exports; update `docs/INGESTION.md`

---

## Phase 7 — MCP Server ⬜ Planned

**Goal:** Expose KnowledgeOS as a local MCP server. Staged rollout: read/search first, then create, then update/archive (requires revision history from Phase 5).

- [ ] **v1 — Read/Search Tools:** `search_objects`, `hybrid_search`, `get_object`, `get_page`, `get_source`, `get_related_objects`, `answer_from_kb`
- [ ] **v2 — Create Tools:** `create_page`, `create_edge`, `ingest_url`, `ingest_file`; each call validates agent identity + writes `agent_runs`
- [ ] **v3 — Update/Archive Tools (requires Phase 5 object_revisions):** `update_page`, `archive_object`; before/after diff logged; rollback supported
- [ ] **MCP resources:** `knowledgeos://objects/{id}`, `knowledgeos://pages/{id}`, `knowledgeos://sources/{id}`, `knowledgeos://search?q=…`
- [ ] **Safety:** no shell execution; no paths outside `LIBRARY_ROOT`; API keys redacted; per-tool enable/disable
- [ ] **Tests + docs:** `docs/MCP_TOOLS.md` full reference; `docs/SECURITY.md` updated

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
| 3 | Search | ⬜ In Progress | 1 / 10 subtasks (subtask 0 done) |
| 4 | Graph Lite | ⬜ Planned | 0 / 5 subtasks |
| 5 | AI Assistant + Inbox/Triage | ⬜ Planned | 0 / 12 subtasks |
| 6 | Chat Import | ⬜ Planned | 0 / 8 subtasks |
| 7 | MCP Server (staged) | ⬜ Planned | 0 / 6 subtasks |
| 8 | Multi-Pane Workspaces | ⬜ Planned | 0 / 8 subtasks |
| 9 | Career & Project Memory | ⬜ Planned | 0 / 8 subtasks |

**Total:** 18 / 74 subtasks complete

**Key cross-cutting concepts to track:**
- Inbox/Triage (Phase 5): AI-classified staging area for unprocessed items
- Search evaluation (Phase 3+): `tests/fixtures/search_eval_cases.json` as regression anchors
- Revision history (Phase 5 prerequisite): required before MCP write tools go live — see `docs/REVISION_HISTORY.md`
- Offline/degradation contract: keyword search always works; AI features degrade gracefully — see `docs/ARCHITECTURE.md`
