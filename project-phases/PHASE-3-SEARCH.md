# KnowledgeOS — Phase 3 Plan

## Context

Phase 1 (Foundation) and Phase 2 (Sources & Rich Media) are complete and pushed to main.
- 45 integration tests passing
- 17/80 subtasks complete
- Qdrant is running in Docker Compose on port 6333
- Worker extractors are operational (PDF, image, CSV, YouTube, web)
- `chunks` table exists but lacks embedding-tracking fields needed for search

This document is the actionable plan for Phase 3: Search.

**Orchestration model**: Claude Code plans and orchestrates; Codex agents write all code.
**Commit cadence**: After every subtask. Small reviewable commits.
**Repo**: `https://github.com/KeigoShimadaCC/agentic-knowledge-management` (branch: main)
**Working directory**: `/Users/keigoshimada/Documents/agentic-knowledge-management`

---

## Phase 2 Audit — Verified Complete

| Area | Status | Notes |
|------|--------|-------|
| 45 integration tests | ✅ | All passing |
| Sources CRUD API | ✅ | 8 endpoints, schemas, service |
| Worker extractors | ✅ | PDF, image, CSV, YouTube, web, file_ |
| RQ job lifecycle | ✅ | pending→running→success/failed, attempts/timestamps |
| Sources UI | ✅ | List, detail, create modal, status polling |
| Citation edges | ✅ | CitationExtension, SourcePicker, POST /edges |
| Edges CRUD API | ✅ | POST/GET/DELETE /edges |
| Docs updated | ✅ | ARCHITECTURE, DATA_MODEL, API, INGESTION |
| PROGRESS.md | ✅ | Phase 2 marked complete |
| project-phases/PHASE-2-SOURCES.md | ✅ | Saved |
| TypeScript clean | ✅ | pnpm typecheck → 0 errors |

**Gaps resolved in Subtask 0:**
- `chunks` table: added `content_hash`, `embedding_status`, `qdrant_point_id`, `source_locator`, `updated_at` (migration 0003)
- `app/config.py`: added `openai_api_key`, `embedding_model`, `embedding_dimension`, `qdrant_collection`

---

## Phase 3 — Search

### Goal

Turn KnowledgeOS from a storage/ingestion system into a **retrieval system**. All pages and sources become searchable by exact keyword, semantic meaning, and a hybrid of both. Search is the foundation that Phases 4–9 build on.

---

## Definition of Done

- [ ] Existing 45 tests still pass
- [ ] `chunks` table has embedding tracking fields (migration 0003) ✅ Done
- [ ] Pages are chunked and stored in `chunks`
- [ ] Sources are chunked and stored in `chunks`
- [ ] Reindex job can index one object by ID
- [ ] Reindex-all script can rebuild all chunks and Qdrant points from scratch
- [ ] Qdrant collection `knowledgeos_chunks` is created and populated
- [ ] Embedding provider abstracted (OpenAI first; mock in tests)
- [ ] Missing `OPENAI_API_KEY` does NOT break app boot or keyword search
- [ ] `GET /api/v1/search/keyword?q=` works across pages and sources
- [ ] `POST /api/v1/search/vector` works when embeddings enabled
- [ ] `POST /api/v1/search/hybrid` returns merged ranked results with snippets
- [ ] Search UI reachable from browser with Cmd+K shortcut
- [ ] All new API endpoints tested (target: ~65 total tests)
- [ ] Docs updated: ARCHITECTURE, DATA_MODEL, API, INGESTION, AGENT_GUIDE
- [ ] PROGRESS.md updated
- [ ] All commits pushed to main
- [ ] `pnpm -F web build` → 0 TypeScript errors

---

## Subtask Checklist

- [x] Subtask 0 — Phase 2 stabilization + chunks migration 0003
- [x] Subtask 1 — Embedding provider abstraction + Qdrant collection setup
- [x] Subtask 2 — Chunking pipeline (page + source content → chunks table)
- [x] Subtask 3 — Reindex worker jobs (reindex_object, reindex_all)
- [ ] Subtask 4 — Keyword search API (`GET /search/keyword`)
- [ ] Subtask 5 — Vector search API (`POST /search/vector`)
- [ ] Subtask 6 — Hybrid search API (`POST /search/hybrid`)
- [ ] Subtask 7 — Search UI (Cmd+K, results page, mode selector)
- [ ] Subtask 8 — Tests + documentation

---

## Subtask Details

### Subtask 0 — Phase 2 stabilization + chunks migration 0003 ✅

**Goal**: Add embedding-tracking fields to `chunks`, add `openai_api_key` to config, save this plan to repo.

**Files modified**:
- `services/api/app/models/chunk.py` — added `user_id`, `source_locator`, `content_hash`, `embedding_status`, `embedding_model`, `embedded_at`, `qdrant_point_id`, `updated_at`
- `services/api/app/config.py` — added `openai_api_key`, `embedding_model`, `embedding_dimension`, `qdrant_collection`
- `services/api/alembic/versions/0003_chunks_search_fields.py` — additive migration (user_id + all search fields)
- `docs/DATA_MODEL.md` — corrected chunks table documentation
- `project-phases/PHASE-3-SEARCH.md` — this plan
- `README.md` — Phase 2 complete, Phase 3 next, 45 tests
- `PROGRESS.md` — revised roadmap
- `docs/ARCHITECTURE.md` — offline/degradation behavior
- `docs/SECURITY.md` — offline/degradation + revision history ref
- `docs/AGENT_GUIDE.md` — Phase 2 is live, Phase 3 search guidance
- `docs/REVISION_HISTORY.md` — new: design doc for future agent write auditing
- `docs/SEARCH_EVAL.md` — new: search eval fixture guide
- `tests/fixtures/search_eval_cases.json` — new: eval query cases

**Commit**: `feat(db): prepare chunks table for idempotent search indexing`

---

### Subtask 1 — Embedding provider abstraction + Qdrant collection setup

**Goal**: Wrap embedding generation behind a provider interface; create the Qdrant collection.

**Files to create**:
- `services/api/app/search/__init__.py`
- `services/api/app/search/embedding.py` — provider abstraction + OpenAI provider
- `services/api/app/search/qdrant_client.py` — Qdrant client wrapper + collection init

**`embedding.py` design**:
```python
class EmbeddingProvider(ABC):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...

class OpenAIEmbeddingProvider(EmbeddingProvider):
    # uses openai.AsyncOpenAI; batches up to 100 texts
    # model from settings.embedding_model
    # raises EmbeddingDisabledError if no API key

class MockEmbeddingProvider(EmbeddingProvider):
    # returns deterministic zeros for tests
    # activated when settings.openai_api_key == "test-mock"

def get_embedding_provider() -> EmbeddingProvider:
    if not settings.openai_api_key:
        return DisabledProvider()  # raises on embed(), is_enabled()=False
    if settings.openai_api_key == "test-mock":
        return MockEmbeddingProvider()
    return OpenAIEmbeddingProvider()
```

**`qdrant_client.py` design**:
```python
# Wraps qdrant_client.AsyncQdrantClient
# Collection: "knowledgeos_chunks"
# Vector size: settings.embedding_dimension (1536 for text-embedding-3-small)
# Distance: COSINE
# create_collection_if_not_exists() — idempotent, call at app startup
# upsert_chunks(points: list[PointStruct]) — batch upsert
# search(query_vector, limit, filter) -> list[ScoredPoint]
# delete_by_object_id(object_id: str) — delete all points for an object
```

**Files to modify**:
- `services/api/app/main.py` — on startup: call `create_collection_if_not_exists()`; if Qdrant down, log warning and continue
- `services/api/pyproject.toml` — add `"openai>=1.0"`, `"qdrant-client>=1.9"`

**Validation**: `uv run ruff check services/api/app/search/` + import smoke test

**Commit**: `feat(search): embedding provider abstraction and qdrant collection setup`
**Codex-delegatable**: Yes

---

### Subtask 2 — Chunking pipeline

**Goal**: Implement deterministic chunker; extract text from pages and sources; write chunks to Postgres.

**Files to create**:
- `services/api/app/search/chunker.py` — text splitter
- `services/api/app/services/chunk_service.py` — `chunk_object(db, obj_id)`, `delete_chunks_for_object(db, obj_id)`

**`chunker.py` design**:
```python
CHUNK_SIZE = 1000  # approximate characters (~250 tokens)
CHUNK_OVERLAP = 150  # characters

def chunk_text(text: str, object_id: str, source_locator: dict | None = None) -> list[ChunkData]:
    # Split by paragraphs first, then by character limit
    # Each chunk: {content, chunk_idx, token_count, content_hash, source_locator}
    # content_hash = sha256(content.encode())[:32]
    # Skip chunks < 20 characters
    # Returns list of ChunkData dataclasses
```

**`chunk_service.py` design**:
```python
async def chunk_object(db: AsyncSession, object_id: uuid.UUID) -> list[Chunk]:
    # Load KosObject → determine kind
    # If page: load Page, use content_text
    # If source: load Source, use extracted_text; if CSV prepend headers/rows preview
    # If asset: use obj.title + " " + obj.description
    # Call chunker.chunk_text()
    # Compare content_hash with existing chunks to skip unchanged
    # Delete stale chunks (chunk_idx positions not in new set)
    # Insert/update chunks with embedding_status="pending"
    # Return new/updated chunks

async def delete_chunks_for_object(db: AsyncSession, object_id: uuid.UUID) -> int:
    # Hard delete (chunks are derived data, not user data)
```

**Text sources by kind**:
| Kind | Text source |
|------|-------------|
| `page` | `pages.content_text` |
| `source` | `sources.extracted_text`; CSV: prefix with `preview_data.headers + rows[:5]` |
| `asset` | `objects.title + " " + objects.description` |

**Commit**: `feat(search): chunking pipeline for pages and sources`
**Codex-delegatable**: Yes

---

### Subtask 3 — Reindex worker jobs ✅

**Goal**: Worker tasks that embed pending chunks, upsert to Qdrant, and clean up stale points.

**Files to create**:
- `services/worker/kos_worker/indexer.py` — sync wrapper for embedding + Qdrant upsert

**Files to modify**:
- `services/worker/kos_worker/tasks.py` — add `reindex_object(object_id: str)` and `reindex_all_objects()`
- `services/worker/pyproject.toml` — add `"openai>=1.0"`, `"qdrant-client>=1.9"`

**`reindex_object(object_id)` flow**:
```
1. open sync DB session
2. load KosObject — skip if deleted
3. chunk content (sync via asyncio.run around async chunk_service)
4. for each chunk with embedding_status="pending":
   a. embed via OpenAI sync client
   b. upsert to Qdrant: payload = {chunk_id, object_id, kind, title, chunk_idx, tags, source_type, created_at, updated_at, content_hash}
   c. update chunk: embedding_status="embedded", qdrant_point_id=str(chunk.id)
5. delete Qdrant points for object_id not in current chunk IDs
6. commit
```

**`reindex_all_objects()` flow**:
```
1. query all non-deleted objects with kind in ("page", "source")
2. for each: enqueue reindex_object(object_id) with job_id=f"reindex:{object_id}"
3. return object count
```

**Trigger points**:
| Event | Action |
|-------|--------|
| Page PUT/PATCH saved | enqueue `reindex_object(page_id)` |
| `ingest_source` completes (status="ready") | enqueue `reindex_object(source_id)` |
| Source PATCH (title/tags) | enqueue `reindex_object(source_id)` |

Use deterministic RQ job ID `f"reindex:{object_id}"` to prevent queue flooding from autosave.

**Commit**: `feat(worker): reindex_object and reindex_all_objects jobs`
**Codex-delegatable**: Yes

**Implemented notes**:
- `services/worker/kos_worker/tasks.py` exposes `reindex_object(object_id)` and `reindex_all_objects()`.
- `services/worker/kos_worker/indexer.py` embeds chunks and writes Qdrant points with chunk/object payload metadata.
- Page `PUT`/`PATCH`, source `PATCH`, and completed source ingestion enqueue `reindex_object` with deterministic `job_id=f"reindex:{object_id}"`.
- Source ingestion now enqueues to the worker's `kos-ingest` queue with the correct `ingest_source(job_id)` argument shape.

---

### Subtask 4 — Keyword search API

**Goal**: Postgres full-text search across pages and sources.

**Files to create**:
- `services/api/app/api/v1/search.py` — search router
- `services/api/app/schemas/search.py` — `SearchResult`, `KeywordSearchParams`
- `services/api/app/services/search_service.py` — `keyword_search(...)`

**Files to modify**:
- `services/api/app/api/v1/router.py` — include search_router at `/search`

**Endpoint**: `GET /api/v1/search/keyword`
Query params: `q` (required), `kind` (optional), `source_type` (optional), `limit` (default 20), `offset` (default 0)

**Implementation**: Postgres `plainto_tsquery` + `ts_rank_cd` + `ts_headline` across pages and sources. UNION both result sets, sort by rank DESC. If `kind` filter provided, skip the other table.

**SearchResult shape**:
```python
class SearchResult(BaseModel):
    id: uuid.UUID
    kind: str
    title: str
    snippet: str | None
    tags: list[str]
    score: float
    updated_at: datetime
    source_type: str | None
    ingestion_status: str | None
```

**Commit**: `feat(api): keyword search endpoint with Postgres FTS`
**Codex-delegatable**: Yes

---

### Subtask 5 — Vector search API

**Goal**: Semantic search over embedded chunks via Qdrant.

**Endpoint**: `POST /api/v1/search/vector`
Body: `{q, kind?, source_type?, limit?, score_threshold?}`

**Flow**:
```
1. get_embedding_provider() → if disabled, return HTTP 503 {"detail": "embeddings_disabled"}
2. embed([q]) → query_vector
3. qdrant_client.search(query_vector, limit, filter_by kind if provided)
4. collect chunk payloads → unique object_ids
5. batch-load objects from Postgres
6. return list[SearchResult] with snippet from chunk.content
```

**Qdrant filter** (if kind provided):
```python
Filter(must=[FieldCondition(key="object_kind", match=MatchValue(value=kind))])
```

**Tests**: `OPENAI_API_KEY=test-mock` activates MockEmbeddingProvider; mock or real Qdrant.

**Commit**: `feat(api): vector search endpoint via qdrant`
**Codex-delegatable**: Yes

---

### Subtask 6 — Hybrid search API

**Goal**: Merge keyword and vector results into a single ranked response.

**Endpoint**: `POST /api/v1/search/hybrid`
Body: `{q, kind?, source_type?, limit?, debug?}`

**Scoring**:
```python
combined = 0.45 * keyword_score + 0.45 * vector_score + 0.10 * recency_boost
# recency_boost: 1.0 if <7d, 0.5 if <30d, 0.0 otherwise
# Merge by object_id; missing score in one source → 0.0 for that component
```

If embeddings disabled: return keyword results only, add `{"embeddings_disabled": true}` to response metadata.
If `debug=true`: include per-result `{keyword_score, vector_score, recency_boost}`.

**Commit**: `feat(api): hybrid search endpoint with keyword+vector merging`
**Codex-delegatable**: Yes

---

### Subtask 7 — Search UI

**Goal**: Global search experience in the browser.

**Files to create**:
- `apps/web/src/components/search/SearchModal.tsx` — Cmd+K modal
- `apps/web/src/components/search/SearchResultCard.tsx` — result card
- `apps/web/src/lib/hooks/useSearch.ts` — debounced, mode-aware SWR hook

**Files to modify**:
- Root layout (find the correct file by reading the app) — Cmd+K listener
- `apps/web/src/lib/api.ts` — add `keywordSearch`, `vectorSearch`, `hybridSearch`
- `apps/web/src/types/index.ts` — add `SearchResult`, `SearchMode`

**SearchModal UX**:
- Cmd+K / Ctrl+K opens modal
- Text input, 300ms debounce, min 2 chars
- Mode tabs: `Keyword | Semantic | Hybrid` (default: Hybrid)
- Scrollable results, ↑↓ keyboard nav, Enter to open, Esc to close
- Loading/empty/error states

**SearchResultCard**: kind badge (page=blue, source=green, asset=gray), snippet, tags, date, click → navigate.

**Commit**: `feat(web): global search UI with Cmd+K, mode selector, and result cards`
**Codex-delegatable**: Yes

---

### Subtask 8 — Tests + documentation

**Goal**: Integration test coverage + updated docs.

**Files to create**:
- `tests/api/test_search.py` — ~15 tests covering keyword/vector/hybrid/auth/filters/snippets
- `tests/api/test_chunk_service.py` — ~5 unit tests for chunker

**Key test cases**:
1. keyword search finds page by content
2. keyword search finds source by extracted_text
3. keyword search empty when no match
4. keyword search requires auth (401)
5. keyword search ?kind filter works
6. vector search returns 503 when no API key
7. vector search with mock provider returns results
8. hybrid fallback to keyword when embeddings disabled
9. hybrid with mocked vector + keyword merges results
10. chunk_service chunks a page into DB rows
11. chunk_service chunks a source with extracted_text
12. reindex removes stale chunks on content change
13. deleted objects excluded from search results
14. limit/offset pagination works
15. snippet field populated in keyword results

**Target**: ~65 total tests (45 existing + 20 new)

**Docs to update**:
- `docs/ARCHITECTURE.md` — search pipeline section
- `docs/DATA_MODEL.md` — migration 0003 chunk fields
- `docs/API.md` — /search endpoints
- `docs/INGESTION.md` — reindexing flow
- `docs/AGENT_GUIDE.md` — search tool guidance
- `PROGRESS.md` — Phase 3 complete

**Commits**:
- `test: Phase 3 search integration tests (~65 total)`
- `docs: document search indexing, chunking, and Qdrant architecture`

**Codex-delegatable**: Yes

---

## Data Model Plan

### Migration 0003 — `chunks` table additive extension (APPLIED)

```sql
-- user_id for ownership-scoped queries and security filtering
ALTER TABLE chunks ADD COLUMN user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE;
UPDATE chunks SET user_id = objects.user_id FROM objects WHERE chunks.object_id = objects.id;
CREATE INDEX ix_chunks_user_id ON chunks (user_id);

-- search-readiness and idempotent embedding pipeline
ALTER TABLE chunks ADD COLUMN source_locator JSONB;
ALTER TABLE chunks ADD COLUMN content_hash TEXT;
ALTER TABLE chunks ADD COLUMN embedding_status VARCHAR(16) NOT NULL DEFAULT 'pending';
ALTER TABLE chunks ADD COLUMN embedding_model TEXT;
ALTER TABLE chunks ADD COLUMN embedded_at TIMESTAMPTZ;
ALTER TABLE chunks ADD COLUMN qdrant_point_id TEXT;
ALTER TABLE chunks ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
CREATE INDEX ix_chunks_embedding_status ON chunks (embedding_status);
CREATE INDEX ix_chunks_object_id ON chunks (object_id);
CREATE INDEX ix_chunks_content_hash ON chunks (content_hash);
```

### Config additions (APPLIED)

```python
openai_api_key: str = ""
embedding_model: str = "text-embedding-3-small"
embedding_dimension: int = 1536
qdrant_collection: str = "knowledgeos_chunks"
```

### Qdrant collection

```
Collection: knowledgeos_chunks
Vector: COSINE, dimension=settings.embedding_dimension (1536)
Point ID: chunk UUID string
Payload: {chunk_id, object_id, object_kind, title, chunk_idx, source_type, tags, created_at, updated_at, content_hash, source_locator}
```

---

## API Plan

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/search/keyword | Postgres FTS; params: q, kind, source_type, limit, offset |
| POST | /api/v1/search/vector | Qdrant nearest neighbors; body: {q, kind, source_type, limit, score_threshold?} |
| POST | /api/v1/search/hybrid | Merged results; body: {q, kind, source_type, limit, debug?} |

No breaking changes to existing endpoints.

---

## Worker / Indexing Plan

### New tasks
- `reindex_object(object_id: str)` — chunk + embed + upsert Qdrant + clean stale
- `reindex_all_objects()` — enqueue reindex for all non-deleted pages+sources

### New file
- `services/worker/kos_worker/indexer.py` — sync wrapper for embedding + Qdrant

### Trigger points
- Page save → enqueue `reindex_object`
- Source ingestion complete → enqueue `reindex_object`
- Source PATCH → enqueue `reindex_object`
- Use deterministic job ID `f"reindex:{object_id}"` to deduplicate

---

## Qdrant Plan

1. Already running in Docker Compose port 6333, persistent volume `qdrant-data`
2. `create_collection_if_not_exists()` called at app startup (idempotent)
3. `AsyncQdrantClient` in FastAPI routes; `QdrantClient` in sync RQ worker
4. Qdrant down → log warning, disable vector search gracefully
5. Reindex is idempotent: upsert overwrites same chunk_id point

---

## UI Plan

### New components
- `apps/web/src/components/search/SearchModal.tsx`
- `apps/web/src/components/search/SearchResultCard.tsx`

### New hooks
- `apps/web/src/lib/hooks/useSearch.ts`

### Modified files
- Root layout — Cmd+K listener
- `apps/web/src/lib/api.ts` — search API methods
- `apps/web/src/types/index.ts` — SearchResult, SearchMode

### UX
- Default mode: Hybrid
- Debounce: 300ms, min 2 chars
- Results limit: 10 in modal
- Keyboard nav: ↑↓ + Enter to open, Esc to close

---

## Tests

| File | Coverage | Count |
|------|----------|-------|
| `tests/api/test_search.py` | keyword/vector/hybrid, auth, filters, snippets | ~15 |
| `tests/api/test_chunk_service.py` | chunk page/source/empty, delete | ~5 |
| Existing `tests/api/` | unchanged, 45 passing | 45 |

**Target**: ~65 total

**Vector search test strategy**: `OPENAI_API_KEY=test-mock` → MockEmbeddingProvider (deterministic zero vectors). Use real Qdrant (already running locally) to avoid mock drift.

---

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| OpenAI embedding cost in tests | MockEmbeddingProvider for all tests |
| Qdrant unavailable in CI | Graceful skip; existing 45 tests never touch Qdrant |
| Autosave flooding reindex queue | Deterministic RQ job ID deduplicates |
| Large PDF extracted_text | Character-based chunker; never loads full text as one vector |
| content_hash collision | SHA-256 first 32 chars; negligible risk at this scale |
| Postgres FTS performance | On-the-fly tsvector is fine for Phase 3 scale; add stored tsvector column if slow |
| Worker sync/async mismatch | `indexer.py` uses `asyncio.run()` to call async chunk_service from sync RQ task |
| Qdrant cold start | Startup hook is idempotent; warns but doesn't crash if Qdrant unavailable |

---

## Codex Delegation Plan

| Subtask | Delegate? | Notes |
|---------|-----------|-------|
| 0 — Migration + config | ✅ Done | |
| 1 — Embedding + Qdrant | Yes | Provide class design; reference source_service.py as pattern |
| 2 — Chunking pipeline | Yes | Provide chunker design above |
| 3 — Reindex worker | Yes | Provide tasks.py design; reference existing ingest_source as pattern |
| 4 — Keyword search | Yes | Provide SQL above; reference pages.py/sources.py as router pattern |
| 5 — Vector search | Yes | Provide flow above; mock provider in tests |
| 6 — Hybrid search | Yes | Provide scoring formula above |
| 7 — Search UI | Yes | Provide SearchModal design; reference CreateSourceModal.tsx as pattern |
| 8 — Tests + docs | Yes | Provide test list above |

---

## Subtask Dependencies

```
0 (migration + config) ✅
└─ 1 (embedding + qdrant)
   ├─ 2 (chunking pipeline)
   │  └─ 3 (reindex worker)
   │     ├─ 5 (vector search)
   │     └─ 6 (hybrid search) ─── requires 4+5
   │        └─ 7 (search UI) ─── requires 4+5+6
   └─ 4 (keyword search) ─── can start after 0 alone
      └─ 8 (tests + docs) ─── runs last
```

Subtask 4 (keyword) is independent of embeddings — can start immediately after Subtask 0.
Subtasks 5+6 need Subtask 1 (embedding provider) + Subtask 3 (indexed Qdrant data).
Subtask 7 (UI) needs all three search endpoints.

---

## Phase 4+ Roadmap

### Phase 4 — Graph
- Typed edge UI (link any two objects)
- Backlinks panel in page/source detail
- Kùzu embedded graph DB (`~/KnowledgeOS/data/kuzu/`)
- Graph sync worker: Postgres edges → Kùzu on create/delete
- `GET /objects/{id}/related?depth=2&kinds=cites,links_to`
- Related objects panel in UI

### Phase 5 — AI Assistant
**Prerequisite: OpenAI API key**
- OpenAI client wrapper (`services/api/app/ai/`)
- AI sidebar in page editor (collapsible, context-scoped)
- `POST /ai/summarize` — summary stored on object
- `POST /ai/extract-claims` — Claim objects linked via edges
- `POST /ai/suggest-links` — search KB, propose edges with explanation
- `POST /ai/answer` — hybrid search → context pack → LLM answer with citations
- All AI writes logged to `agent_runs`

### Phase 6 — MCP Server
- `services/mcp/server.py` — FastMCP or raw MCP SDK
- Read tools: `search_objects`, `hybrid_search`, `get_object`, `get_page`, `get_source`
- Write tools: `create_page`, `update_page`, `create_edge`, `archive_object`
- Ingestion tools: `ingest_url`, `ingest_file`
- MCP resources: `knowledgeos://objects/{id}`, `knowledgeos://search?q=`
- Agent identity header + `agent_runs` audit; no shell execution; no paths outside LIBRARY_ROOT

### Phase 7 — Chat Import
- Drag-and-drop ChatGPT/Claude JSON export
- Parser → normalized `ChatTurn[]` structure
- Raw storage under `library/chats/{provider}/{chat_id}/raw.json`
- LLM structured summary: decisions, claims, tasks, concepts, projects
- Chat indexed into chunks + Qdrant

### Phase 8 — Multi-Pane Workspaces
- Resizable 2–4 pane layout engine
- `workspaces` table with `layout_json`
- Save/restore named workspaces
- Drag text between panes → quote block with back-reference
- AI context scoped to workspace

### Phase 9 — Career & Project Memory
- `projects` table: period, role, problem, actions, metrics, skills, artifacts
- Project extraction AI: LLM reads pages/chats/sources → populates schema
- Evidence linking: pages/sources/claims → `belongs_to_project` edges
- Resume bullet generator: 3 variants with evidence citations
- STAR story generator + career memory dashboard
