# KnowledgeOS Ingestion

Ingestion is the path from external material into usable KnowledgeOS objects. Phase 1 supports manual asset upload. Phase 2 adds first-class sources and asynchronous extraction with RQ workers.

## Phase 1: Manual Asset Upload

Phase 1 ingestion is file storage plus metadata registration:

1. The browser sends `POST /api/v1/assets/upload` as `multipart/form-data`.
2. The API receives the file and computes its SHA-256 digest.
3. The API chooses the content-addressed storage path:

   ```text
   ~/KnowledgeOS/library/assets/{sha256[:2]}/{sha256}/original{ext}
   ```

4. The original file is written to the local library.
5. The API creates an `objects` row with `kind="asset"`.
6. The API creates an `assets` row with filename, content type, size, digest, storage path, status, and optional media dimensions.
7. The API returns asset metadata to the client.

Phase 1 does not extract text, generate thumbnails, chunk content, or create embeddings. Uploaded files are durable originals that later phases can process.

## Phase 2: Source Ingestion Flow

Phase 2 introduces source objects for PDFs, images, videos, YouTube URLs, web articles, and CSV files. A source is a knowledge object that points to an uploaded asset or external URL and tracks extraction state.

Flow:

1. Client calls `POST /api/v1/sources`.
2. API validates `source_type` and either `asset_id` or `url`.
3. API creates an `objects` row with `kind="source"`.
4. API creates a `sources` specialization row.
5. API creates an `ingestion_jobs` row with `status="pending"`.
6. API enqueues an RQ job in Redis.
7. Worker claims the job and marks it `running`.
8. Worker runs the extractor for the source type.
9. Worker writes derivatives to the local library.
10. Worker updates source metadata and status to `ready`, or records an error and sets status to `error`.

The API remains the write boundary for interactive clients. The worker is trusted application code that updates ingestion state and derived metadata.

## Source Types and Extractors

| Source type | Input | Phase 2 extractor |
| --- | --- | --- |
| `pdf` | Uploaded PDF asset | `pypdf` for text and document metadata |
| `image` | Uploaded image asset | `Pillow` for dimensions, format, EXIF where available, and thumbnails |
| `csv` | Uploaded CSV asset | Python standard library `csv` module for headers, row counts, and previews |
| `youtube` | YouTube URL | oEmbed for metadata and `youtube-transcript-api` for captions when available |
| `web` | HTTP or HTTPS URL | `httpx` fetch plus `BeautifulSoup` parsing for title, metadata, and readable text |

Extractors should be deterministic where possible, store their outputs as files, and write compact metadata to Postgres. Large extracted text should not be embedded directly into arbitrary JSON fields when a derivative file is more appropriate.

## Job Lifecycle

Ingestion jobs use a small lifecycle:

| Status | Meaning |
| --- | --- |
| `pending` | DB record exists and work has been queued, but no worker has started it. |
| `running` | A worker has claimed the job and extraction is in progress. |
| `ready` | Extraction completed and source metadata/derivatives are available. |
| `error` | Extraction failed. The job should retain an error message and enough metadata to debug or retry. |

Source status should mirror the relevant job status for the current extraction attempt. A later retry can create a new job while preserving previous failure metadata for audit.

## Derivative Storage

Phase 2 derivatives should live under a source-specific directory:

```text
~/KnowledgeOS/library/sources/{source_id}/thumbnail.jpg
~/KnowledgeOS/library/sources/{source_id}/extracted_text.txt
~/KnowledgeOS/library/sources/{source_id}/preview.json
```

Recommended derivative meanings:

| File | Purpose |
| --- | --- |
| `thumbnail.jpg` | Small visual preview for images, PDFs, videos, or web pages when available |
| `extracted_text.txt` | Plain text extracted from the source |
| `preview.json` | Structured preview such as title, author, page count, headers, sample rows, or transcript segments |

Database rows should store paths, status, source type, and compact metadata. The filesystem should hold large derivative payloads.

## Edge Creation

Source ingestion may create graph relationships:

| Edge | Created when |
| --- | --- |
| `source -> asset`, `kind="derives_from"` | A source is created from an uploaded asset |
| `page -> source`, `kind="cites"` | A user or agent attaches a source citation to a page |

Extraction itself should not invent page citations. Citation edges should be created by explicit user or agent action.

## Phase 3: Chunking, Reindexing, and Embeddings

Phase 3 extends ingestion from extraction to retrieval:

1. Read extracted text from pages and sources.
2. Split text into chunks.
3. Store chunks in the `chunks` table with object references and positions.
4. Generate vector embeddings for each chunk.
5. Store vectors in Qdrant.
6. Use vector search for semantic retrieval, AI question answering, and context assembly.

Chunking is repeatable so an object can be reindexed when content or extraction logic changes.

Reindex triggers:

| Event | Action |
| --- | --- |
| Page `PUT`/`PATCH` save | Enqueue `reindex_object(page_id)` |
| Source `PATCH` metadata update | Enqueue `reindex_object(source_id)` |
| Source ingestion completion | Enqueue `reindex_object(source_id)` |
| Manual rebuild | `reindex_all_objects()` enqueues all non-deleted pages, sources, chats, claims, and tasks |

Reindex jobs use deterministic RQ job IDs (`reindex-{object_id}`; UUID text uses only letters, digits, and dashes per RQ rules) to avoid flooding the queue during repeated saves.

### `scripts/reindex.py` — CLI helper

```bash
# Reindex all objects (enqueues jobs via RQ)
PYTHONPATH=services/api:services/worker uv run python scripts/reindex.py --all

# Reindex specific objects by UUID
PYTHONPATH=services/api:services/worker uv run python scripts/reindex.py \
  3f7d1a2b-... f82c9e01-...
```

Requires `REDIS_URL` and `DATABASE_URL` in the environment (or `infra/.env` sourced). The worker service must be running to process the queued jobs. Check index status via `GET /api/v1/objects/{id}/index-status`.

## Phase 6A: Chat Import Lite

Chat imports are synchronous API operations. `POST /api/v1/chats/import` accepts either multipart upload (`.json`, `.md`, `.markdown`, `.txt`) or JSON paste content. ChatGPT multi-conversation exports create one `chat` object per conversation.

Raw chat bytes are written under `library/chats`, using object UUIDs for identity instead of user filenames. Single chat imports write `chats/{provider}/{chat_id}/raw.{json|md|txt}` plus `metadata.json`. ChatGPT batch uploads also preserve the exact uploaded export at `chats/chatgpt/imports/{batch_uuid}/raw.json`.

The parser normalizes turns into `role`, `author`, `content`, `created_at`, and `metadata`. `chats.content_text` stores the searchable transcript projection. Keyword search reads this Postgres field immediately; vector/hybrid search can include chats after the normal `reindex_object(chat_id)` chunk and embedding job runs. No LLM calls happen during Phase 6A import.

## Phase 6B: Structured Chat Import

Structured import is an explicit, user-triggered AI flow on top of an existing imported chat:

1. The user opens a chat and clicks Generate structured summary.
2. The API sends parsed turns to the configured AI provider and requires strict JSON output.
3. The response is validated, stored on `chats.structured_summary`, marked `previewed`, and logged through `agent_runs` plus `object_revisions`.
4. The user clicks Apply.
5. The API marks the summary `applied`, creates or reuses generic `claim` and `task` objects, stores `turn_refs` and confidence in metadata, and creates graph edges back to the chat.
6. The chat and extracted objects are queued for reindexing.

Keyword search can find applied structured summaries immediately from Postgres fields. Vector
search includes the summary and extracted objects after the normal reindex/embedding pipeline
runs. If embeddings or AI are disabled, keyword search still works and structured generation
returns a clear provider-disabled error.
