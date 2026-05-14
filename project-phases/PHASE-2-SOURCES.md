# KnowledgeOS — Phase 2 Plan

## Context

Phase 1 is complete and pushed to main (9 commits, 25 passing integration tests).
This document is the actionable plan for Phase 2: Sources and Rich Media Ingestion.

**Orchestration model**: Claude Code plans and orchestrates; Codex agents write all code.
**Commit cadence**: After every subtask. Small reviewable commits.
**Repo**: `https://github.com/KeigoShimadaCC/agentic-knowledge-management` (branch: main)
**Working directory**: `/Users/keigoshimada/Documents/agentic-knowledge-management`

---

## Phase 1 Audit — Verified Complete

| Area | Status | Notes |
|------|--------|-------|
| Docker Compose (5 services) | ✅ Complete | postgres, redis, qdrant, api, web with healthchecks |
| SQLAlchemy models (9 tables) | ✅ Complete | User, Session, KosObject, Page, Asset, Edge, Chunk, IngestionJob, AgentRun |
| Alembic migration 0001 | ✅ Complete | All 9 tables, indexes, constraints |
| FastAPI auth endpoints | ✅ Complete | register, login, logout, /me with httponly session cookies |
| Objects/Pages/Assets CRUD | ✅ Complete | Full CRUD + soft delete + restore |
| Content-addressed storage | ✅ Complete | `assets/{sha256[:2]}/{sha256}/original{ext}` with atomic writes |
| Next.js App Router shell | ✅ Complete | 3-panel layout, auth flow, protected routes |
| Tiptap editor with auto-save | ✅ Complete | StarterKit, Placeholder, Typography, Link, Image; 800ms debounce |
| Asset upload UI | ✅ Complete | Drag-and-drop, XHR progress, SHA256 dedup, grid view |
| Integration tests | ✅ Complete | 25 tests passing (auth, objects, pages, assets, health) |
| Git history | ✅ Complete | 9 commits pushed to main |
| Worker (services/worker/) | ⚠️ Stub | Empty package — needs Phase 2 implementation |
| MCP (services/mcp/) | ⚠️ Stub | Empty package — Phase 6 target |
| docs/*.md | ⚠️ Stubs | All 7 docs exist but are single-title stubs; need content |

**Phase 1 blockers for Phase 2**: None. All 25 tests pass. Foundation is solid.

**Technical debt to note**:
- `VALID_KINDS` in `object.py` needs `"source"` added before Phase 2 API endpoints can work
- Worker `pyproject.toml` has no dependencies — needs a full dependency declaration
- Docs need real content (will be addressed in Subtask 0 and Subtask 9)

---

## Phase 2 — Sources and Rich Media

### Goal

Evolve KnowledgeOS from a basic page/file app into a real personal knowledge base that can ingest, store, preview, extract text from, and link structured **Source** objects: PDFs, images, videos, YouTube URLs, web articles, and CSV files.

Sources are first-class knowledge objects. They live alongside pages. Ingestion runs as background jobs via RQ.

### Definition of Done

- [ ] `POST /api/v1/sources` creates a source from an asset upload or pasted URL
- [ ] RQ worker picks up the ingestion job and extracts metadata/text
- [ ] PDF: page count + full text extracted and stored
- [ ] Image: dimensions captured, thumbnail generated
- [ ] CSV: 20-row preview stored as JSON
- [ ] YouTube: title/channel from oEmbed + transcript stored as text
- [ ] Web URL: title + article text extracted via httpx + BeautifulSoup
- [ ] Sources list/detail UI in the browser at `localhost:3000/sources`
- [ ] Page editor can insert a citation chip linking to a source (creates page→source Edge)
- [ ] All new API endpoints tested (target: ~25 new tests, ~50 total)
- [ ] Docs updated (DATA_MODEL, API, INGESTION, ARCHITECTURE)
- [ ] All commits pushed to `main`
- [ ] `PYTHONPATH=services/api uv run pytest tests/api -v` — all tests pass
- [ ] `pnpm -F web build` — zero TypeScript errors

---

## Subtask Checklist

- [ ] Subtask 0 — Phase 1 stabilization + add `"source"` to VALID_KINDS + write docs stubs with real content
- [ ] Subtask 1 — Source data model + Alembic migration 0002
- [ ] Subtask 2 — Source CRUD API endpoints
- [ ] Subtask 3 — Source creation flows (upload→source, URL→source, optional create_source param)
- [ ] Subtask 4 — Worker foundation: RQ runner + job lifecycle
- [ ] Subtask 5 — File extractors: PDF, image, CSV
- [ ] Subtask 6 — URL extractors: YouTube oEmbed + transcript, web article
- [ ] Subtask 7 — Source UI: list, detail, create modal, previews
- [ ] Subtask 8 — Citation edges in page editor (page→source, Tiptap CitationExtension)
- [ ] Subtask 9 — Tests + documentation update

---

## Architecture Decisions

### Source object strategy
Use `kind="source"` in the existing `KosObject` table + a dedicated `sources` table (FK → objects.id), exactly matching how `pages` and `assets` work. Rationale: reuses soft-delete, tagging, pinning, archiving, and Edge infrastructure immediately. The objects list/filter API (`?kind=source`) already works without code changes.

### source_type
PostgreSQL enum `source_type_enum` via `sa.Enum("pdf","image","video","audio","youtube","web","csv","file", name="source_type_enum")`. DB enforces constraint; Pydantic mirrors as `Literal`. Adding new types requires only `ALTER TYPE source_type_enum ADD VALUE`.

### Worker process
Synchronous RQ worker (`rq worker kos-ingest`). Runs as a separate process sharing the same `DATABASE_URL` and `LIBRARY_ROOT` env vars. Uses **sync** SQLAlchemy (`psycopg2`) — not asyncpg — because RQ jobs are synchronous. The worker package imports API models directly (workspace member of kos-api).

### Ingestion flow
```
POST /sources
  → INSERT objects (kind="source") + INSERT sources (status="pending")
  → INSERT ingestion_jobs (status="pending")
  → asyncio.to_thread(queue.enqueue, "kos_worker.tasks.ingest_source", source_id, job_id)
  → return SourceOut (ingestion_status="pending")

Worker picks up job:
  → UPDATE ingestion_jobs status="running", started_at=now(), attempts+=1
  → extractor(source) runs → writes extracted_text, page_count, thumbnail_path, preview_data
  → UPDATE sources ingestion_status="ready"|"error"
  → UPDATE ingestion_jobs status="success"|"failed", finished_at=now()
```

### Storage structure
```
~/KnowledgeOS/library/
  assets/{sha256[:2]}/{sha256}/original{ext}        ← Phase 1 (unchanged)
  sources/{source_id}/
    thumbnail.jpg                                    ← PDF p1 cover, image thumb, YT thumb
    extracted_text.txt                               ← PDF/web/YT transcript text
    preview.json                                     ← CSV rows, YT oEmbed metadata
```

### YouTube metadata
- Title/author/thumbnail: `httpx.get("https://www.youtube.com/oembed?url={url}&format=json")` — no API key needed
- Transcript: `youtube-transcript-api` Python library (pure HTTP, no subprocess, no download)
- Fallback: if transcript unavailable, mark `ingestion_status="ready"` with oEmbed data only

---

## Data Model Plan

### New table: `sources`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK FK→objects.id CASCADE | |
| source_type | source_type_enum NOT NULL | pdf/image/video/audio/youtube/web/csv/file |
| url | Text nullable | for youtube/web; NULL for file-backed |
| asset_id | UUID FK→objects.id SET NULL nullable | link to original Asset if file-backed |
| ingestion_status | String(16) default "pending" | pending/running/ready/error |
| extracted_text | Text nullable | full text: PDF, web body, YT transcript |
| page_count | Integer nullable | PDF pages |
| thumbnail_path | Text nullable | relative path under library/ |
| preview_data | JSONB nullable | CSV preview rows, YT oEmbed JSON |
| error_message | Text nullable | last extractor error |
| created_at | DateTime TZ | |
| updated_at | DateTime TZ | |

### Modify existing
- `services/api/app/models/object.py`: Add `"source"` to `VALID_KINDS`
- `services/api/app/models/__init__.py`: Import `Source`

### New Edge kinds (no schema change — uses existing `edges` table)
- `"derives_from"`: source → asset (source was created from this asset)
- `"cites"`: page → source (page cites/references this source)

### Migration
`alembic/versions/0002_add_sources.py` — creates `source_type_enum` type + `sources` table

---

## API Plan

### New endpoints: `/api/v1/sources`

| Method | Path | Description |
|--------|------|-------------|
| POST | /sources | Create source from asset_id or URL |
| GET | /sources | List sources (paginated; filter: source_type, ingestion_status, q) |
| GET | /sources/{id} | Get source detail |
| PATCH | /sources/{id} | Update title/tags/description |
| DELETE | /sources/{id} | Soft delete |
| POST | /sources/{id}/restore | Restore soft-deleted source |
| GET | /sources/{id}/text | Stream extracted_text as plain text |
| GET | /sources/{id}/thumbnail | Serve thumbnail JPEG |

**POST /sources body** (discriminated by source_type):
```json
// File-backed:  {"source_type": "pdf",     "asset_id": "<uuid>"}
// URL-backed:   {"source_type": "youtube", "url": "https://youtu.be/..."}
//               {"source_type": "web",     "url": "https://..."}
```

### New endpoints: `/api/v1/edges`

| Method | Path | Description |
|--------|------|-------------|
| POST | /edges | Create edge (source_id, target_id, kind) |
| GET | /edges | List edges (filter: source_id, target_id, kind) |
| DELETE | /edges/{id} | Soft delete edge |

### Modified endpoints
- `POST /assets/upload`: Add optional `?create_source=true` query param — if set, auto-creates a Source after upload and enqueues ingestion job

### New schemas
- `services/api/app/schemas/source.py`: `SourceCreate`, `SourceOut`, `SourceUpdate`
- `services/api/app/schemas/edge.py`: `EdgeCreate`, `EdgeOut`

---

## UI Plan

### New routes
- `apps/web/src/app/(app)/sources/page.tsx` — sources list
- `apps/web/src/app/(app)/sources/[id]/page.tsx` — source detail

### New components
- `src/components/sources/SourceCard.tsx` — type icon, title, status badge (color-coded)
- `src/components/sources/SourceList.tsx` — grid/list toggle
- `src/components/sources/SourceDetail.tsx` — metadata, thumbnail, text preview, linked pages
- `src/components/sources/CreateSourceModal.tsx` — two tabs: "Paste URL" / "Upload File"
- `src/components/editor/SourcePicker.tsx` — modal to search/select a source for citation
- `src/components/editor/extensions/CitationExtension.ts` — Tiptap inline node storing source_id

### Modified components
- `src/components/layout/Sidebar.tsx` — add Sources nav item with `BookOpen` icon
- `src/components/editor/EditorToolbar.tsx` — add "Cite Source" button
- `src/components/editor/PageEditor.tsx` — register CitationExtension; on save, diff nodes → POST /edges
- `src/types/index.ts` — add `SourceOut`, `SourceType`, `IngestionStatus`, `EdgeOut`
- `src/lib/api.ts` — add sources and edges API methods

### UX details
- Status badge colors: pending=gray, running=amber pulse, ready=green, error=red
- Citation chip: inline `[Source Title]` with hover tooltip showing source_type + status
- SWR polling: `refreshInterval: ["pending","running"].includes(status) ? 3000 : 0`
- CSV preview: HTML `<table>` showing first 20 rows from `preview_data`
- Thumbnail: `<img src="/api/v1/sources/{id}/thumbnail">` with fallback icon

---

## Worker / Ingestion Plan

### Package structure
```
services/worker/
  pyproject.toml           ← deps: rq, psycopg2-binary, sqlalchemy, redis, pypdf,
  kos_worker/              │         pillow, youtube-transcript-api, httpx,
    __init__.py            │         beautifulsoup4, filetype
    worker.py              ← rq Worker entry point
    tasks.py               ← ingest_source(source_id, job_id) dispatcher
    db.py                  ← sync sqlalchemy session (psycopg2 driver)
    extractors/
      __init__.py
      pdf.py               ← pypdf text + page count; Pillow thumbnail
      image.py             ← Pillow dimensions + thumbnail
      csv_ex.py            ← stdlib csv, 20-row preview JSON
      youtube.py           ← httpx oEmbed + youtube-transcript-api
      web.py               ← httpx + BeautifulSoup4 title + body text
      file_.py             ← filetype detection, delegates to correct extractor
```

### Extractor contract
Each extractor returns a dict of fields to write back to the `sources` row:
```python
def extract(source: Source, db: Session) -> dict:
    # returns: {ingestion_status, extracted_text, page_count, thumbnail_path, preview_data, error_message}
```

### Worker run command (dev)
```bash
PYTHONPATH=services/api DATABASE_URL="postgresql://kos:kospass@localhost:5432/knowledgeos" \
  LIBRARY_ROOT="$HOME/KnowledgeOS/library" \
  uv run --package kos-worker rq worker kos-ingest
```

### Risk: pypdf thumbnail
pypdf extracts text but cannot render PDFs to images. Use `pypdf` for text only. For thumbnail, try `pdf2image` (requires `poppler`) with a conditional import — if not available, skip thumbnail (PDF sources show a default PDF icon). Do not block on thumbnail availability.

---

## Tests

### New test files
| File | Coverage |
|------|----------|
| `tests/api/test_sources.py` | create from asset, create from URL, list, get, filter by type, soft delete, restore, thumbnail, text endpoints (~15 tests) |
| `tests/api/test_edges.py` | create citation edge, list, soft delete, duplicate idempotent (~5 tests) |
| `tests/worker/test_extractors.py` | PDF text, image dims, CSV preview (unit tests with fixture files, mocked DB session) |
| `tests/worker/conftest.py` | sync DB session fixture for worker tests |
| `tests/worker/fixtures/` | sample.pdf (small), sample.csv, sample.jpg |

### Target: ~50 total tests passing (25 existing + ~25 new)

### Test isolation for worker tests
Worker uses sync SQLAlchemy. Use a separate `tests/worker/conftest.py` with `psycopg2` sync session fixture against `knowledgeos_test` DB.

### Mocking in API tests
RQ job enqueue should be mocked in source CRUD tests (no running Redis required). Use `unittest.mock.patch("rq.Queue.enqueue")` in the source test fixtures.

---

## Documentation Updates

| Doc | Updates needed |
|-----|----------------|
| `docs/DATA_MODEL.md` | Add sources table schema; update KosObject VALID_KINDS; document edge kinds |
| `docs/API.md` | Add /sources and /edges endpoint reference |
| `docs/INGESTION.md` | Full ingestion pipeline: job creation → RQ → extractor → status update |
| `docs/ARCHITECTURE.md` | Add worker service; update system diagram; storage structure |
| `docs/AGENT_GUIDE.md` | How agents should create and query sources via API |
| `project-phases/PHASE-2-SOURCES.md` | Full copy of this plan (saved to repo) |

---

## Subtask Details

### Subtask 0 — Phase 1 stabilization + VALID_KINDS + docs skeleton

**Goal**: Add `"source"` to VALID_KINDS, write real content into stub docs, save plan to project-phases/.

**Files to modify**:
- `services/api/app/models/object.py` — add `"source"` to VALID_KINDS tuple
- `docs/ARCHITECTURE.md`, `docs/DATA_MODEL.md`, `docs/INGESTION.md`, `docs/API.md`, `docs/AGENT_GUIDE.md` — write substantive content summarizing Phase 1 + Phase 2 intent
- `project-phases/PHASE-2-SOURCES.md` — copy this plan document

**Validation**: `PYTHONPATH=services/api uv run pytest tests/api -q` → 25 passed (VALID_KINDS change must not break existing tests)

**Commit**: `chore: add source to VALID_KINDS, write real doc content, save phase 2 plan`

**Codex-delegatable**: Partially (Codex writes docs; VALID_KINDS change is 1 line)

---

### Subtask 1 — Source data model + Alembic migration 0002

**Goal**: Add `sources` table and `source_type_enum` to the database.

**Files to create**:
- `services/api/app/models/source.py` — SQLAlchemy 2.0 Mapped/mapped_column Source model
- `services/api/alembic/versions/0002_add_sources.py` — migration

**Files to modify**:
- `services/api/app/models/__init__.py` — import Source

**Key details**:
- `source_type_enum`: `sa.Enum("pdf","image","video","audio","youtube","web","csv","file", name="source_type_enum", create_type=True)`
- `asset_id`: `ForeignKey("objects.id", ondelete="SET NULL")` nullable
- `ingestion_status`: `String(16)` with `server_default="pending"` (not enum — stays flexible)
- `preview_data`: `JSONB` nullable
- All timestamps: `DateTime(timezone=True)`
- Index on `(user_id, ingestion_status)` via KosObject join

**Validation**: `cd services/api && uv run alembic upgrade head` completes; `psql -c "\d sources"` shows all columns

**Commit**: `feat(db): add sources table and source_type_enum (migration 0002)`

**Codex-delegatable**: Yes

---

### Subtask 2 — Source CRUD API endpoints

**Goal**: Full CRUD for `/api/v1/sources` including list, get, patch, delete, restore.

**Files to create**:
- `services/api/app/schemas/source.py` — `SourceCreate`, `SourceOut`, `SourceUpdate`
- `services/api/app/services/source_service.py` — `create_source`, `get_source_or_404`, `list_sources`, `update_source`, `soft_delete_source`, `restore_source`
- `services/api/app/api/v1/sources.py` — router with all endpoints

**Files to modify**:
- `services/api/app/api/v1/router.py` — include sources_router at `/api/v1`

**Key details**:
- `SourceCreate` uses a Pydantic validator: requires `asset_id` for file types (pdf/image/video/audio/csv/file) and `url` for URL types (youtube/web); raises 422 if mismatched
- RQ enqueue: `await asyncio.to_thread(queue.enqueue, "kos_worker.tasks.ingest_source", str(source_id), str(job_id))` to avoid blocking the async event loop
- `list_sources` reuses `object_service.list_objects` pattern; joins `sources` table for `source_type`/`ingestion_status` filters
- `SourceOut` includes: all `KosObject` fields + all `Source` fields
- `/sources/{id}/text`: `StreamingResponse` serving `extracted_text` as `text/plain`
- `/sources/{id}/thumbnail`: `FileResponse` serving `thumbnail_path`; 404 if no thumbnail

**Validation**: New test file `tests/api/test_sources.py` with 5 basic CRUD tests passing

**Commit**: `feat(api): add /sources CRUD endpoints with ingestion job enqueue`

**Codex-delegatable**: Yes

---

### Subtask 3 — Source creation flows

**Goal**: Wire asset upload → source creation, and validate URL→source creation path.

**Files to modify**:
- `services/api/app/api/v1/assets.py` — add `create_source: bool = Query(False)` param; if true, call `source_service.create_from_asset()` after upload
- `services/api/app/services/source_service.py` — add `create_from_asset(db, user_id, asset, asset_obj) -> (KosObject, Source)`
- `services/api/app/core/storage.py` — add `ensure_source_dir(source_id: str) -> Path` creating `library/sources/{source_id}/`

**Key details**:
- `create_source=false` is the default — existing 25 tests must continue passing unchanged
- `create_from_asset` infers `source_type` from `asset.content_type` (e.g., `"application/pdf"` → `"pdf"`, `"image/jpeg"` → `"image"`)
- Creates a `"derives_from"` edge: source → asset
- Returns a combined response: `{object, asset, source, job}` when `create_source=true`

**Validation**: `PYTHONPATH=services/api uv run pytest tests/api -q` → still 25+ passed; new tests for create_source flow

**Commit**: `feat(api): asset upload with optional source creation and derives_from edge`

**Codex-delegatable**: Yes

---

### Subtask 4 — Worker foundation: RQ runner + job lifecycle

**Goal**: A runnable `rq worker kos-ingest` process with full job lifecycle tracking.

**Files to create**:
- `services/worker/kos_worker/worker.py` — entry point (imports queue, starts rq.Worker)
- `services/worker/kos_worker/tasks.py` — `ingest_source(source_id: str, job_id: str)` dispatcher
- `services/worker/kos_worker/db.py` — sync SQLAlchemy session: `DATABASE_URL` with `postgresql+psycopg2://` driver prefix substituted for `postgresql+asyncpg://`
- `services/worker/kos_worker/extractors/__init__.py`

**Files to modify**:
- `services/worker/pyproject.toml` — add deps: `rq>=1.16`, `psycopg2-binary>=2.9`, `sqlalchemy[asyncio]>=2.0`, `redis[hiredis]>=5.0`, `aiofiles>=23.2`
- `services/worker/kos_worker/__init__.py` — add version

**Key details**:
- `tasks.ingest_source`: opens sync DB session, sets job status="running", dispatches to extractor based on source.source_type, commits result; on exception sets status="failed" with traceback in error_message
- Worker imports `Source`, `KosObject`, `IngestionJob` models from `app.models` (PYTHONPATH must include `services/api`)
- `kos_worker/db.py` replaces `asyncpg` with `psycopg2` in driver string: `url.replace("asyncpg", "psycopg2").replace("+asyncpg", "+psycopg2")`

**Validation**: `PYTHONPATH=services/api uv run --package kos-worker python -m kos_worker.worker` starts without error; submit a stub job and verify lifecycle fields update in DB

**Commit**: `feat(worker): RQ worker foundation with job lifecycle management`

**Codex-delegatable**: Yes

---

### Subtask 5 — File extractors: PDF, image, CSV

**Goal**: Extract text/metadata from file-backed sources.

**Files to create**:
- `services/worker/kos_worker/extractors/pdf.py`
- `services/worker/kos_worker/extractors/image.py`
- `services/worker/kos_worker/extractors/csv_ex.py`
- `services/worker/kos_worker/extractors/file_.py` — filetype detection + delegation
- `tests/worker/conftest.py` — sync DB session fixture
- `tests/worker/fixtures/sample.pdf`, `sample.csv`, `sample.jpg`
- `tests/worker/test_extractors.py`

**Files to modify**:
- `services/worker/pyproject.toml` — add: `pypdf>=4.0`, `pillow>=10.0`, `filetype>=1.2`

**Key details**:
- PDF: `pypdf.PdfReader(path)` → join all page text; `len(reader.pages)` for page_count; thumbnail via `Pillow.Image.open(BytesIO(reader.pages[0].images[0].data))` if page has embedded image — otherwise skip thumbnail
- Image: `Pillow.Image.open(path)` → `img.size` → `(width, height)`; thumbnail via `img.thumbnail((512,512))` → save to `library/sources/{source_id}/thumbnail.jpg`; also write back `assets.width/height` if NULL
- CSV: `csv.DictReader(open(path, encoding="utf-8-sig"))` → read up to 20 rows → `preview_data = {"headers": [...], "rows": [...]}`
- All extractors write derivatives to `library/sources/{source_id}/`
- Test: use real tiny fixture files, mock only the DB session

**Validation**: `PYTHONPATH=services/api uv run pytest tests/worker/ -q` → all extractor unit tests pass

**Commit**: `feat(worker): PDF, image, and CSV extractors`

**Codex-delegatable**: Yes

---

### Subtask 6 — URL extractors: YouTube + web

**Goal**: Fetch metadata and transcript/text for URL-backed sources.

**Files to create**:
- `services/worker/kos_worker/extractors/youtube.py`
- `services/worker/kos_worker/extractors/web.py`

**Files to modify**:
- `services/worker/pyproject.toml` — add: `httpx>=0.27`, `beautifulsoup4>=4.12`, `youtube-transcript-api>=0.6`

**Key details**:
- YouTube: `httpx.get(f"https://www.youtube.com/oembed?url={url}&format=json", timeout=10)` → title, author_name, thumbnail_url stored in `preview_data`; download thumbnail via `httpx.get(thumbnail_url)` → save JPEG; then `YouTubeTranscriptApi.get_transcript(video_id, languages=["en","ja"])` → join segments → `extracted_text`. Catch `TranscriptsDisabled` / `NoTranscriptFound` → set `extracted_text=None`, still mark `ingestion_status="ready"`
- Web: `httpx.get(url, follow_redirects=True, timeout=15, headers={"User-Agent": "KnowledgeOS/1.0"})` → parse with `BeautifulSoup(html, "html.parser")` → extract `title` tag, `<meta name="description">`, all `<p>` text joined. `extracted_text` = title + description + body paragraphs. Capture `og:image` for thumbnail if available. On non-200: mark `ingestion_status="error"`
- Extractor tests: use `respx` or `pytest-httpx` to mock HTTP responses

**Validation**: `PYTHONPATH=services/api uv run pytest tests/worker/ -q` → all tests pass including URL extractor tests

**Commit**: `feat(worker): YouTube oEmbed + transcript and web article extractors`

**Codex-delegatable**: Yes

---

### Subtask 7 — Source UI

**Goal**: Sources section in the browser with list, detail, create flows, and previews.

**Files to create**:
- `apps/web/src/app/(app)/sources/page.tsx`
- `apps/web/src/app/(app)/sources/[id]/page.tsx`
- `apps/web/src/components/sources/SourceCard.tsx`
- `apps/web/src/components/sources/SourceList.tsx`
- `apps/web/src/components/sources/SourceDetail.tsx`
- `apps/web/src/components/sources/CreateSourceModal.tsx`
- `apps/web/src/lib/hooks/useSources.ts`
- `apps/web/src/lib/hooks/useSource.ts`

**Files to modify**:
- `apps/web/src/components/layout/Sidebar.tsx` — add Sources nav item (`BookOpen` from lucide-react)
- `apps/web/src/types/index.ts` — add `SourceOut`, `SourceType`, `IngestionStatus`, `EdgeOut`
- `apps/web/src/lib/api.ts` — add `listSources`, `createSource`, `getSource`, `updateSource`, `deleteSource`, `createEdge`

**Key UX details**:
- Status badge: `pending`=gray dot, `running`=amber animate-pulse dot, `ready`=green dot, `error`=red dot
- `CreateSourceModal` has two tabs: "Paste URL" (text input → POST /sources with url) and "Upload File" (drag-drop → POST /assets/upload?create_source=true)
- Source detail shows: thumbnail (if available), metadata table, extracted_text in scrollable `<pre>`, CSV preview `<table>`, linked pages list from edges
- SWR polling while status is pending/running: `useSWR(key, fetcher, { refreshInterval: isProcessing ? 3000 : 0 })`
- TypeScript: strict, no `any`; all API response shapes typed in `types/index.ts`

**Validation**: `pnpm -F web typecheck` → 0 errors; manual browser smoke test create PDF source → see status update to ready

**Commit**: `feat(web): Sources list, detail, and create UI with status polling`

**Codex-delegatable**: Yes

---

### Subtask 8 — Citation edges in page editor

**Goal**: Tiptap editor "Cite Source" button that inserts a citation chip and creates a page→source Edge.

**Files to create (API)**:
- `services/api/app/api/v1/edges.py` — POST /edges, GET /edges, DELETE /edges/{id}
- `services/api/app/schemas/edge.py` — `EdgeCreate`, `EdgeOut`
- `services/api/app/services/edge_service.py` — `create_edge` (idempotent via unique constraint), `list_edges`, `delete_edge`

**Files to create (Frontend)**:
- `apps/web/src/components/editor/SourcePicker.tsx` — modal; search sources by title; select → inserts citation node
- `apps/web/src/components/editor/extensions/CitationExtension.ts` — Tiptap inline node storing `data-source-id` and `data-source-title`

**Files to modify (Frontend)**:
- `apps/web/src/components/editor/EditorToolbar.tsx` — "Cite" button (`Link` icon)
- `apps/web/src/components/editor/PageEditor.tsx` — register CitationExtension; on content save, detect citation nodes → call `createEdge({source_id: page_id, target_id: source_id, kind: "cites"})`

**Files to modify (API)**:
- `services/api/app/api/v1/router.py` — include edges_router

**Key details**:
- Citation chip renders as: `<span data-source-id="...">📎 Source Title</span>`
- `createEdge` API: duplicate edges (same source+target+kind) handled by unique constraint; API returns 200 (not 409) on conflict
- `edge_service.create_edge` uses `INSERT ... ON CONFLICT DO NOTHING RETURNING *`; if no row returned, fetches existing

**Validation**: `pnpm -F web typecheck` → 0 errors; manual test insert citation in page → edge appears in DB

**Commit**: `feat(web,api): citation edges in page editor with Tiptap CitationExtension`

**Codex-delegatable**: Yes

---

### Subtask 9 — Tests + documentation

**Goal**: Full integration test coverage for Phase 2 + real doc content.

**Files to create**:
- `tests/api/test_sources.py` — ~15 tests
- `tests/api/test_edges.py` — ~5 tests
- `tests/worker/test_extractors.py` — ~8 unit tests
- `tests/worker/fixtures/sample.pdf`, `sample.csv`, `sample.jpg`
- `tests/worker/conftest.py`
- `project-phases/PHASE-2-SOURCES.md` — plan doc saved to repo

**Files to modify**:
- `docs/DATA_MODEL.md` — sources table, edge kinds
- `docs/API.md` — /sources and /edges endpoints
- `docs/INGESTION.md` — full pipeline diagram + extractor details
- `docs/ARCHITECTURE.md` — updated system diagram with worker service
- `docs/AGENT_GUIDE.md` — how agents create/query sources

**Validation**: `PYTHONPATH=services/api uv run pytest tests/ -q` → ~50 passed; `pnpm -F web build` → 0 TS errors

**Commit**: `test: Phase 2 integration tests (~50 total)`
**Commit**: `docs: update DATA_MODEL, API, INGESTION, ARCHITECTURE for Phase 2`

**Codex-delegatable**: Yes

---

## Subtask Dependencies

```
0 (stabilize)
└─ 1 (data model)
   └─ 2 (source CRUD)
      ├─ 3 (create flows) ─────────── 7 (Source UI)
      │                               └─ 8 (citation editor)
      └─ 4 (worker foundation)
         ├─ 5 (file extractors)
         └─ 6 (URL extractors)
```

Subtasks 2+4 can run in parallel after subtask 1.
Subtasks 5+6 can run in parallel after subtask 4.
Subtask 7 can start after subtask 2 (uses API).
Subtask 8 requires subtask 7.
Subtask 9 runs last (or in parallel with subtask 8 for doc-only files).

---

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| pypdf cannot render PDF thumbnails | Skip thumbnail for PDF if no embedded images; show default PDF icon in UI |
| YouTube transcript unavailable | Catch `TranscriptsDisabled`; mark ready without extracted_text |
| YouTube oEmbed rate limiting | Add 1s retry backoff; cache oEmbed response in preview_data |
| Worker sync DB session conflicts with test DB | Use separate `tests/worker/conftest.py` with psycopg2 sync engine |
| RQ enqueue blocking async FastAPI | Wrap `queue.enqueue()` in `asyncio.to_thread()` |
| Large PDF text exceeds DB column | `extracted_text` is `TEXT` (unlimited in Postgres); also write to filesystem as backup |
| URL fetch blocked/timeout | Hard 15s timeout in httpx; on failure set `ingestion_status="error"` with error_message |
| Test DB state between API and worker tests | Worker tests use function-scoped sync fixtures; same `knowledgeos_test` DB |

---

## Codex Delegation Plan

| Subtask | Delegate to Codex? | Notes |
|---------|-------------------|-------|
| 0 | Partially | Claude edits VALID_KINDS (1 line); Codex writes docs |
| 1 | Yes | Clear schema spec; straightforward SQLAlchemy model |
| 2 | Yes | Pattern matches existing pages.py/assets.py; hand Codex those as reference |
| 3 | Yes | Small extension to existing assets.py |
| 4 | Yes | Provide exact file structure above |
| 5 | Yes | Provide extractor contract; Codex implements each extractor |
| 6 | Yes | Provide exact library usage above |
| 7 | Yes | Provide types and API contract; Codex implements components |
| 8 | Yes | Provide CitationExtension spec; Codex implements |
| 9 | Yes | Provide test names and assertions; Codex implements |

Each Codex task should reference:
- Existing similar file as pattern (e.g., "model Source like app/models/asset.py")
- Exact acceptance criteria (validation command)
- Files to NOT touch

---

## Phase 2 Out of Scope

- AI summarization or embedding
- Vector search (Qdrant)
- Graph DB (Kùzu) sync
- MCP server
- PDF annotation/highlighting
- Browser extension
- Real-time WebSocket updates
- Collaboration/multi-user
- Mobile UI
- Cloud deployment
- Full-text search across sources (Phase 3)
- Automatic entity/claim extraction (Phase 5)

---

## Phase 3+ Roadmap (High-Level)

| Phase | Focus | Key Components |
|-------|-------|----------------|
| 3 | Search | Chunking pipeline → Postgres FTS + Qdrant vectors → hybrid search API + UI |
| 4 | Graph | Typed edge UI, Kùzu sync worker, graph neighborhood retrieval endpoint |
| 5 | AI Assistant | OpenAI integration, AI sidebar, summarize/extract/suggest, KB Q&A with citations |
| 6 | MCP Server | read/search/write/ingest tools, agent identity + audit via agent_runs, tool allowlist |
| 7 | Chat Import | ChatGPT/Claude JSON import → LLM structuring → KB objects + claim extraction |
| 8 | Workspaces | Saved multi-pane layouts, workspace-scoped AI context, link sets |
| 9 | Career Memory | Project schema, evidence-linked resume bullets, STAR story generator |

**Note**: OpenAI API key is needed for Phase 5. User to provide key before Phase 5 begins.
