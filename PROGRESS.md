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

**Goal:** Make all knowledge searchable — by exact keyword, by semantic meaning, and by a hybrid of both — with a clean search UI.

- [ ] **Subtask 1** — Chunking pipeline: split page/source text into overlapping chunks; store in `chunks` table with `chunk_idx`, `token_count`, `source_locator` (page/paragraph reference)
- [ ] **Subtask 2** — Embedding pipeline: OpenAI `text-embedding-3-small` for each chunk; store vector ID in Qdrant with payload (`object_id`, `chunk_id`, `kind`)
- [ ] **Subtask 3** — Postgres full-text search: `tsvector` column on `objects` (title) and `pages` (content_text); GIN index; `GET /search/keyword?q=` endpoint
- [ ] **Subtask 4** — Qdrant vector search: `POST /search/vector` endpoint; query embedding → Qdrant nearest neighbors → return ranked objects
- [ ] **Subtask 5** — Hybrid search endpoint: `POST /search/hybrid` — parallel keyword + vector → merge + rerank by combined score
- [ ] **Subtask 6** — Search UI: global search bar (Cmd+K), unified results panel (tabs: All / Pages / Sources / Assets), result cards with excerpt highlighting
- [ ] **Subtask 7** — Re-index worker job: `reindex_object(object_id)` — chunk → embed → upsert to Qdrant; triggered on page/source create and update
- [ ] **Subtask 8** — Tests + docs: search API tests, embedding mock fixtures, update `docs/ARCHITECTURE.md` + `docs/INGESTION.md`

---

## Phase 4 — Graph ⬜ Planned

**Goal:** Give the knowledge base a graph backbone — typed bidirectional links between any objects, traversable graph neighborhoods, and visual backlink panels.

- [ ] **Subtask 1** — Typed link UI: "Link to…" button in page editor opens object picker; creates typed edge (`links_to`, `derived_from`, `mentions`, `supports`, `contradicts`, etc.)
- [ ] **Subtask 2** — Backlinks panel: right sidebar shows all objects that link to the current page; clicking navigates to the linking object
- [ ] **Subtask 3** — Kùzu graph DB setup: embedded Kùzu instance in the worker process; stored under `~/KnowledgeOS/data/kuzu/`
- [ ] **Subtask 4** — Graph sync worker: on every edge create/delete in Postgres, mirror to Kùzu; full re-sync script `scripts/reindex_graph.py`
- [ ] **Subtask 5** — Graph neighborhood retrieval: `GET /objects/{id}/related?depth=2&edge_types=links_to,mentions` — traverses Kùzu up to N hops, returns ranked related objects
- [ ] **Subtask 6** — Graph search endpoint: `POST /search/graph` — find objects reachable from a seed set via specified edge types
- [ ] **Subtask 7** — Graph panel UI: collapsible "Related" section in right sidebar showing linked objects grouped by edge type
- [ ] **Subtask 8** — Tests + docs: edge traversal tests, Kùzu sync tests, update `docs/DATA_MODEL.md` + `docs/ARCHITECTURE.md`

---

## Phase 5 — AI Assistant ⬜ Planned

**Goal:** Embed AI directly into the editing and research workflow — summarize, extract, suggest links, and answer questions grounded in the local knowledge base with source citations.

**Prerequisite:** OpenAI API key set in `infra/.env`.

- [ ] **Subtask 1** — OpenAI client setup: typed wrapper around `openai` Python SDK; configurable model; cost tracking to `agent_runs` table; retries with exponential backoff
- [ ] **Subtask 2** — AI sidebar component: collapsible right panel; chat-style UI; scoped to current page, selected text, or whole workspace; shows "AI" badge on AI-generated content
- [ ] **Subtask 3** — Summarize page: `POST /ai/summarize` → LLM summary stored back on the page object; one-click in toolbar
- [ ] **Subtask 4** — Summarize source: same for PDF/web/YouTube sources; displays summary in source detail panel
- [ ] **Subtask 5** — Extract claims: `POST /ai/extract-claims` → creates `Claim` objects linked to source/page via `derived_from` edge
- [ ] **Subtask 6** — Extract tasks + entities: extract action items (→ Task objects), people, orgs, concepts from a page or source
- [ ] **Subtask 7** — Suggest links: `POST /ai/suggest-links` → LLM reviews current page content, searches KB, proposes edges to related objects with explanation
- [ ] **Subtask 8** — KB Q&A with citations: `POST /ai/answer` — hybrid retrieval → context pack → LLM answer → response includes `[source_id, chunk_id]` citations; displayed as clickable chips in AI sidebar
- [ ] **Subtask 9** — Triage inbox: `POST /ai/triage-inbox` → LLM classifies and routes unprocessed items in `library/inbox/`
- [ ] **Subtask 10** — All AI writes create `agent_runs` audit rows; UI shows AI-generated badge on agent-created objects
- [ ] **Subtask 11** — Tests + docs: mock OpenAI responses in tests; update `docs/AGENT_GUIDE.md`

---

## Phase 6 — MCP Server ⬜ Planned

**Goal:** Expose the knowledge base as a first-class MCP server so that Claude, ChatGPT, Codex, and local agents can search, read, write, and ingest knowledge through standardized tools.

- [ ] **Subtask 1** — MCP server scaffold: `services/mcp/server.py`; listens on `:8765`; wired into `docker-compose.yml`
- [ ] **Subtask 2** — Read/search tools: `search_objects`, `hybrid_search`, `get_object`, `get_page`, `get_source`, `get_project`, `get_related_objects`, `answer_from_kb`
- [ ] **Subtask 3** — Write tools: `create_page`, `update_page`, `create_claim`, `create_edge`, `archive_object`; each call validates agent identity + writes `agent_runs` row
- [ ] **Subtask 4** — Ingestion tools: `ingest_url`, `ingest_file`, `import_chat`, `triage_inbox`, `run_ingestion_job`
- [ ] **Subtask 5** — MCP resources: stable `knowledgeos://objects/{id}`, `knowledgeos://pages/{id}`, `knowledgeos://sources/{id}`, `knowledgeos://search?q=…` URIs
- [ ] **Subtask 6** — MCP prompts: `kb_search_prompt`, `source_summary_prompt`, `claim_extraction_prompt`, `chat_import_summary_prompt`
- [ ] **Subtask 7** — Agent identity + audit: every MCP write requires `agent_id` header; logs to `agent_runs`; before/after diff for page edits
- [ ] **Subtask 8** — Safety enforcement: no shell execution tools; no file access outside `LIBRARY_ROOT`; API keys redacted from all tool outputs; per-tool enable/disable config
- [ ] **Subtask 9** — MCP server docker service + `infra/.env` wiring; local-only bind by default
- [ ] **Subtask 10** — Tests + docs: MCP tool integration tests; `docs/MCP_TOOLS.md` with full tool reference; `docs/SECURITY.md` updated

---

## Phase 7 — Chat Import ⬜ Planned

**Goal:** Turn exported ChatGPT and Claude conversations into durable, searchable, linked knowledge objects — capturing decisions, claims, tasks, and concepts as first-class KB entities.

- [ ] **Subtask 1** — Chat upload UI: drag-and-drop JSON/Markdown upload; paste transcript; Chats section in sidebar
- [ ] **Subtask 2** — ChatGPT export parser: parse `conversations.json` format (ChatGPT export); normalize into internal `ChatTurn[]` structure
- [ ] **Subtask 3** — Claude export parser: parse Claude conversation export format
- [ ] **Subtask 4** — Raw storage: store original export file unchanged under `library/chats/{provider}/{chat_id}/raw.json`
- [ ] **Subtask 5** — LLM summarizer pipeline: turn parsed chat into `structured_summary` JSON (title, date, key decisions, open questions, action items, claims, concepts, projects, sources)
- [ ] **Subtask 6** — Object extraction worker: create linked KB objects from summary — `Claim` objects, `Task` objects, concept mentions → edges
- [ ] **Subtask 7** — Chat object UI: chat detail view with structured summary; expandable raw transcript; linked objects panel
- [ ] **Subtask 8** — Chat indexing: chunk and embed chat content for vector search; add to Qdrant and Kùzu graph
- [ ] **Subtask 9** — Tests + docs: import pipeline tests with fixture exports; `docs/INGESTION.md` updated

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
| 3 | Search | ⬜ Planned | 0 / 8 subtasks |
| 4 | Graph | ⬜ Planned | 0 / 8 subtasks |
| 5 | AI Assistant | ⬜ Planned | 0 / 11 subtasks |
| 6 | MCP Server | ⬜ Planned | 0 / 10 subtasks |
| 7 | Chat Import | ⬜ Planned | 0 / 9 subtasks |
| 8 | Multi-Pane Workspaces | ⬜ Planned | 0 / 8 subtasks |
| 9 | Career & Project Memory | ⬜ Planned | 0 / 8 subtasks |

**Total:** 17 / 80 subtasks complete
