# KnowledgeOS API Reference

Base URL:

```text
http://127.0.0.1:8001
```

`127.0.0.1:8001` is the Docker Compose host port. If you run FastAPI natively with `uvicorn --port 8000`, use `http://127.0.0.1:8000` instead. Inside the Docker network, services use `http://api:8000`.

Versioned API prefix:

```text
/api/v1
```

All JSON examples show the stable shape clients should rely on. Extra fields may be returned as the implementation grows.

## Authentication

KnowledgeOS uses a local httponly session cookie named `kos_session`. The cookie is created by `POST /api/v1/auth/register` or `POST /api/v1/auth/login` and is sent automatically by the browser on later requests.

Clients outside the browser must preserve and resend the cookie. The raw session token is never stored in the database; the server stores a SHA-256 hash and resolves each request by session lookup.

## Errors

Error responses use:

```json
{
  "detail": "Human-readable error message",
  "code": "machine_readable_code"
}
```

Common status codes:

| Status | Meaning |
| ---: | --- |
| `400` | Invalid request body or unsupported operation |
| `401` | Missing, expired, or invalid session |
| `403` | Authenticated user is not allowed to access the resource |
| `404` | Resource not found, including soft-deleted resources outside trash routes |
| `409` | Conflict, such as duplicate registration email |
| `422` | Validation error |
| `500` | Unexpected server error |

## Pagination

List endpoints use:

```text
?page=1&limit=20
```

Paginated responses use:

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "limit": 20,
  "pages": 0
}
```

## Health

### `GET /api/v1/health`

Checks whether the API process is running.

Request body: none.

Response:

```json
{
  "status": "ok"
}
```

Status codes: `200`.

## Auth Endpoints

### `POST /api/v1/auth/register`

Creates a user and starts a session.

Request:

```json
{
  "email": "you@example.com",
  "password": "correct horse battery staple",
  "display_name": "You"
}
```

Response:

```json
{
  "user": {
    "id": "uuid",
    "email": "you@example.com",
    "display_name": "You",
    "created_at": "2026-05-14T00:00:00Z"
  }
}
```

Status codes: `201`, `400`, `409`, `422`.

Side effect: sets httponly `kos_session` cookie.

### `POST /api/v1/auth/login`

Authenticates an existing user and starts a session.

Request:

```json
{
  "email": "you@example.com",
  "password": "correct horse battery staple"
}
```

Response:

```json
{
  "user": {
    "id": "uuid",
    "email": "you@example.com",
    "display_name": "You"
  }
}
```

Status codes: `200`, `400`, `401`, `422`.

Side effect: sets httponly `kos_session` cookie.

### `POST /api/v1/auth/logout`

Invalidates the current session.

Request body: none.

Response:

```json
{
  "ok": true
}
```

Status codes: `200`, `401`.

Side effect: clears or invalidates `kos_session`.

### `GET /api/v1/auth/me`

Returns the authenticated user.

Request body: none.

Response:

```json
{
  "user": {
    "id": "uuid",
    "email": "you@example.com",
    "display_name": "You"
  }
}
```

Status codes: `200`, `401`.

## Object Endpoints

Object responses share this base shape:

```json
{
  "id": "uuid",
  "kind": "page",
  "title": "Research Notes",
  "description": null,
  "tags": ["research"],
  "metadata": {},
  "is_pinned": false,
  "is_archived": false,
  "created_at": "2026-05-14T00:00:00Z",
  "updated_at": "2026-05-14T00:00:00Z",
  "deleted_at": null
}
```

### `GET /api/v1/objects`

Lists non-deleted objects for the current user.

Query parameters:

| Name | Type | Notes |
| --- | --- | --- |
| `page` | integer | Default `1` |
| `limit` | integer | Default `20` |
| `q` | string | Optional keyword search |
| `kind` | string | Optional object kind filter |

Request body: none.

Response:

```json
{
  "items": [
    {
      "id": "uuid",
      "kind": "page",
      "title": "Research Notes",
      "description": null,
      "tags": [],
      "metadata": {},
      "is_pinned": false,
      "is_archived": false,
      "created_at": "2026-05-14T00:00:00Z",
      "updated_at": "2026-05-14T00:00:00Z",
      "deleted_at": null
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 20,
  "pages": 1
}
```

Status codes: `200`, `401`, `422`.

### `POST /api/v1/objects`

Creates a base object. Use specialized endpoints for pages and assets when content or files are involved.

Request:

```json
{
  "kind": "note",
  "title": "Inbox note",
  "description": "Optional summary",
  "tags": ["inbox"],
  "metadata": {},
  "is_pinned": false,
  "is_archived": false
}
```

Response: object shape.

Status codes: `201`, `400`, `401`, `422`.

### `GET /api/v1/objects/trash`

Lists soft-deleted objects.

Query parameters: `page`, `limit`, optional `kind`.

Request body: none.

Response: paginated object response.

Status codes: `200`, `401`, `422`.

### `GET /api/v1/objects/{id}`

Returns one non-deleted object.

Request body: none.

Response: object shape.

Status codes: `200`, `401`, `403`, `404`.

### `PATCH /api/v1/objects/{id}`

Updates common object metadata.

Request:

```json
{
  "title": "Updated title",
  "description": "Updated description",
  "tags": ["project", "draft"],
  "metadata": {"source": "manual"},
  "is_pinned": true,
  "is_archived": false
}
```

All fields are optional. Omitted fields are unchanged.

Response: object shape.

Status codes: `200`, `400`, `401`, `403`, `404`, `422`.

### `DELETE /api/v1/objects/{id}`

Soft-deletes an object by setting `deleted_at`.

Request body: none.

Response: object shape with `deleted_at` set.

Status codes: `200`, `401`, `403`, `404`.

### `POST /api/v1/objects/{id}/restore`

Restores a soft-deleted object.

Request body: none.

Response: object shape with `deleted_at: null`.

Status codes: `200`, `401`, `403`, `404`.

## Page Endpoints

### `POST /api/v1/pages`

Creates a page object and page content row.

Request:

```json
{
  "title": "New page",
  "content": {
    "type": "doc",
    "content": []
  },
  "tags": [],
  "metadata": {}
}
```

Response:

```json
{
  "id": "uuid",
  "kind": "page",
  "title": "New page",
  "description": null,
  "tags": [],
  "metadata": {},
  "content": {
    "type": "doc",
    "content": []
  },
  "content_text": "",
  "created_at": "2026-05-14T00:00:00Z",
  "updated_at": "2026-05-14T00:00:00Z"
}
```

Status codes: `201`, `400`, `401`, `422`.

### `GET /api/v1/pages/{id}`

Returns a page and its Tiptap document JSON.

Request body: none.

Response: page response shape.

Status codes: `200`, `401`, `403`, `404`.

### `PUT /api/v1/pages/{id}`

Replaces page content and updatable page metadata.

Request:

```json
{
  "title": "Updated page",
  "content": {
    "type": "doc",
    "content": [
      {
        "type": "paragraph",
        "content": [{"type": "text", "text": "Hello"}]
      }
    ]
  },
  "tags": ["draft"],
  "metadata": {}
}
```

Response: page response shape.

Status codes: `200`, `400`, `401`, `403`, `404`, `422`.

### `PATCH /api/v1/pages/{id}`

Partially updates a page.

Request:

```json
{
  "title": "Partially updated page",
  "content": {
    "type": "doc",
    "content": []
  }
}
```

All fields are optional. Omitted fields are unchanged.

Response: page response shape.

Status codes: `200`, `400`, `401`, `403`, `404`, `422`.

## Asset Endpoints

### `POST /api/v1/assets/upload`

Uploads a file and creates an asset object.

Request content type: `multipart/form-data`.

Form fields:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `file` | file | yes | Original file |
| `title` | string | no | Defaults to filename |
| `description` | string | no | Optional |
| `tags` | string / JSON | no | Client-dependent tag representation |
| `metadata` | JSON string | no | Optional object metadata |

Response:

```json
{
  "id": "uuid",
  "kind": "asset",
  "title": "paper.pdf",
  "description": null,
  "tags": [],
  "metadata": {},
  "filename": "paper.pdf",
  "content_type": "application/pdf",
  "size_bytes": 123456,
  "sha256": "hex_digest",
  "storage_path": "~/KnowledgeOS/library/assets/ab/ab12.../original.pdf",
  "status": "ready",
  "width": null,
  "height": null,
  "duration_secs": null,
  "created_at": "2026-05-14T00:00:00Z",
  "updated_at": "2026-05-14T00:00:00Z"
}
```

Status codes: `201`, `400`, `401`, `413`, `422`.

### `GET /api/v1/assets/{id}`

Returns asset metadata.

Request body: none.

Response: asset response shape.

Status codes: `200`, `401`, `403`, `404`.

### `GET /api/v1/assets/{id}/download`

Downloads the original file.

Request body: none.

Response: binary file stream with appropriate `Content-Type` and download headers.

Status codes: `200`, `401`, `403`, `404`.

### `DELETE /api/v1/assets/{id}`

Soft-deletes the asset object. The stored original is retained so the asset can be restored or audited.

Request body: none.

Response: object shape with `deleted_at` set.

Status codes: `200`, `401`, `403`, `404`.

## Source Endpoints

Sources are first-class knowledge objects that wrap rich media files and URLs. They always have `kind="source"` in the base object table.

### `POST /api/v1/sources`

Creates a source from an asset or URL and enqueues an ingestion job.

Request (file-backed):

```json
{ "source_type": "pdf", "asset_id": "uuid", "title": "My Paper" }
```

Request (URL-backed):

```json
{ "source_type": "youtube", "url": "https://youtu.be/..." }
```

`source_type` must be one of: `pdf`, `image`, `video`, `audio`, `csv`, `file`, `youtube`, `web`.
File-backed types require `asset_id`. URL-backed types (`youtube`, `web`) require `url`.

Response: SourceOut (see below). `ingestion_status` will be `"pending"`.

Status codes: `201`, `401`, `422`.

### `GET /api/v1/sources`

Lists non-deleted sources for the current user.

Query parameters:

| Name | Type | Notes |
| --- | --- | --- |
| `source_type` | string | Optional filter |
| `ingestion_status` | string | Optional filter |
| `q` | string | Optional title search |
| `skip` | integer | Default `0` |
| `limit` | integer | Default `100` |

Response: `list[SourceOut]`.

Status codes: `200`, `401`.

### SourceOut shape

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "kind": "source",
  "title": "My Paper",
  "description": null,
  "tags": [],
  "is_pinned": false,
  "is_archived": false,
  "created_at": "2026-05-14T00:00:00Z",
  "updated_at": "2026-05-14T00:00:00Z",
  "deleted_at": null,
  "source_type": "pdf",
  "url": null,
  "asset_id": "uuid",
  "ingestion_status": "pending",
  "extracted_text": null,
  "page_count": null,
  "thumbnail_path": null,
  "preview_data": null,
  "error_message": null
}
```

### `GET /api/v1/sources/{id}`

Returns one non-deleted source. Status codes: `200`, `401`, `404`.

### `PATCH /api/v1/sources/{id}`

Updates `title`, `description`, or `tags`. Status codes: `200`, `401`, `404`, `422`.

### `DELETE /api/v1/sources/{id}`

Soft-deletes the source. Status codes: `200`, `401`, `404`.

### `POST /api/v1/sources/{id}/restore`

Restores a soft-deleted source. Status codes: `200`, `401`, `404`.

### `GET /api/v1/sources/{id}/text`

Streams `extracted_text` as `text/plain`. Returns `404` if no text has been extracted yet.

### `GET /api/v1/sources/{id}/thumbnail`

Serves the thumbnail JPEG. Returns `404` if no thumbnail exists.

### `POST /api/v1/assets/upload?create_source=true`

Uploads a file and immediately creates a source. The source type is inferred from the MIME type. A `derives_from` edge is created linking the source to the asset.

Response when `create_source=true`:

```json
{ "object": AssetOut, "source": SourceOut }
```

## Edge Endpoints

Edges are typed, directed relationships between any two objects.

### `POST /api/v1/edges`

Creates an edge. Duplicate edges (same `source_id` + `target_id` + `kind`) are idempotent.

Request:

```json
{
  "source_id": "uuid",
  "target_id": "uuid",
  "kind": "cites",
  "weight": 1.0,
  "metadata": {}
}
```

Canonical kinds: `"links_to"`, `"cites"`, `"derives_from"`, `"mentions"`, `"supports"`, `"contradicts"`, `"related_to"`, `"summarizes"`, `"belongs_to_project"`, `"evidence_for"`, `"created_from"`.

Legacy accepted kinds: `"link"`, `"related"`, `"citation"`, `"embed"`, `"child"`, `"tag"`.

Response: EdgeOut. Status codes: `200`, `201`, `401`, `422`.

### `GET /api/v1/edges`

Lists edges, optionally filtered by `source_id`, `target_id`, `kind`, or `include_deleted`.

Response: `list[EdgeOut]`. Status codes: `200`, `401`.

### `DELETE /api/v1/edges/{id}`

Soft-deletes an edge by setting `deleted_at`. Status codes: `200`, `401`, `404`.

### `GET /api/v1/objects/{id}/edges`

Lists graph edges touching one object.

Query parameters:

| Name | Type | Notes |
| --- | --- | --- |
| `direction` | `incoming`, `outgoing`, `both` | Default `both` |
| `kind` | string | Optional edge kind filter |
| `include_deleted` | boolean | Default `false` |

Response items include the edge, source object summary, target object summary, and direction relative to `{id}`.

Status codes: `200`, `401`, `404`, `422`.

### `GET /api/v1/objects/{id}/backlinks`

Lists incoming edges for one object. This is equivalent to object edges with `direction=incoming`.

Query parameters: optional `kind`.

Status codes: `200`, `401`, `404`, `422`.

### `GET /api/v1/objects/{id}/related`

Returns related objects by traversing Postgres edges.

Query parameters:

| Name | Type | Notes |
| --- | --- | --- |
| `depth` | integer | Default `1`; max `2` |
| `edge_types` | repeated string | Optional edge kind filter |
| `direction` | `incoming`, `outgoing`, `both` | Default `both` |
| `limit` | integer | Default `20`; max `100` |

Response items include object summary, traversal distance, score, and the edge path used.

Status codes: `200`, `401`, `404`, `422`.

### `GET /api/v1/objects/{id}/index-status`

Returns the chunk and embedding status for an object. Useful for diagnosing why an object does not appear in vector or hybrid search results.

Response:

```json
{
  "object_id": "uuid",
  "total_chunks": 12,
  "embedded_count": 12,
  "status": "done",
  "last_embedded_at": "2026-05-15T09:12:00Z"
}
```

`status` values:

| Value | Meaning |
| --- | --- |
| `not_indexed` | No chunks found; object has never been chunked |
| `pending` | Chunks exist but none are embedded yet |
| `partial` | Some chunks embedded; worker may still be running |
| `done` | All chunks have embeddings in Qdrant |

Status codes: `200`, `401`, `404`.

## Search Endpoints

Search requires the same `kos_session` cookie as other KnowledgeOS endpoints. Keyword search is always available offline. Vector search requires embeddings to be enabled with `OPENAI_API_KEY`; hybrid search falls back to keyword-only when embeddings are disabled.

Search results share this shape:

```json
{
  "id": "uuid",
  "kind": "page",
  "title": "Quantum Computing",
  "snippet": {
    "text": "Quantum entanglement and superposition appear in this research note",
    "highlights": [[0, 7], [23, 35]]
  },
  "tags": [],
  "score": 0.42,
  "updated_at": "2026-05-14T00:00:00Z",
  "source_type": null,
  "ingestion_status": null
}
```

`snippet` is `null` when no content is available. When present, `text` is a plain string (no HTML) and `highlights` is a list of `[start, end]` character-index pairs marking matched terms. The frontend renders highlights as `<mark>` elements via React nodes — no `dangerouslySetInnerHTML` is used.

Hybrid search accepts an optional `debug: true` body parameter. When set, each result includes `keyword_score` and `vector_score` breakdowns for diagnostic use.

## Chats

Chats require the same `kos_session` cookie as other endpoints. All reads are scoped to the current user. Delete is a soft delete on the base object and never removes raw files.

### `POST /api/v1/chats/import`

Imports a chat from either multipart upload or pasted JSON.

Multipart fields:

| Name | Type | Notes |
| --- | --- | --- |
| `file` | file | Required; `.json`, `.md`, `.markdown`, or `.txt` |
| `provider` | string | Optional; `auto`, `chatgpt`, `claude`, `markdown`, `plain_text`, `unknown` |
| `title` | string | Optional title override |

JSON body:

```json
{
  "content": "User: hello\nAssistant: hi",
  "provider": "plain_text",
  "title": "Imported transcript",
  "raw_format": "txt"
}
```

Response:

```json
{
  "imported": [
    {
      "id": "uuid",
      "kind": "chat",
      "title": "Imported transcript",
      "provider": "plain_text",
      "raw_storage_path": "chats/plain_text/uuid/raw.txt",
      "raw_format": "txt",
      "turn_count": 2,
      "parsed_turns": [],
      "content_text": "[User] hello\n\n[Assistant] hi",
      "metadata": {}
    }
  ],
  "total": 1
}
```

ChatGPT batch exports return one item per conversation. Malformed JSON returns `422`; oversized imports return `413`.

### Chat CRUD

| Method | Path | Notes |
| --- | --- | --- |
| `GET` | `/api/v1/chats?provider=&q=&skip=&limit=` | List non-deleted chats |
| `GET` | `/api/v1/chats/{id}` | Read chat detail |
| `GET` | `/api/v1/chats/{id}/raw` | Stream raw imported transcript |
| `DELETE` | `/api/v1/chats/{id}` | Soft-delete the chat object |
| `POST` | `/api/v1/chats/{id}/restore` | Restore and enqueue reindex |
| `POST` | `/api/v1/chats/{id}/reindex` | Enqueue chat reindex |

### Structured Chat Summaries

Structured summaries are Phase 6B AI-backed endpoints. They require `OPENAI_API_KEY` and
return `503 {"detail":"ai_disabled"}` when AI is not configured. No transcript content leaves
the machine until the user clicks Generate in the chat detail UI or calls the preview endpoint.

| Method | Path | Notes |
| --- | --- | --- |
| `POST` | `/api/v1/chats/{id}/structured-summary` | Generate and store a validated preview; creates `agent_runs` and `object_revisions` rows |
| `GET` | `/api/v1/chats/{id}/structured-summary` | Read the current preview/applied summary |
| `POST` | `/api/v1/chats/{id}/structured-summary/apply` | Apply a preview or supplied summary, create/reuse claims/tasks, link edges, enqueue reindex |

Preview response:

```json
{
  "structured_summary": {
    "title": "Structured planning chat",
    "summary": "Concise grounded summary.",
    "date_range": {"start": null, "end": null},
    "topics": ["structured import"],
    "key_decisions": [
      {
        "decision": "Use explicit apply before creating objects.",
        "rationale": "AI writes must be auditable.",
        "turn_refs": [1],
        "confidence": "high"
      }
    ],
    "open_questions": [],
    "action_items": [],
    "claims": [],
    "concepts": [],
    "suggested_links": [],
    "warnings": []
  },
  "agent_run_id": "uuid",
  "status": "previewed"
}
```

Apply request:

```json
{
  "structured_summary": null,
  "create_claims": true,
  "create_tasks": true,
  "create_concepts": false,
  "link_existing_objects": true
}
```

When `structured_summary` is `null`, the server applies the stored preview. Claims are linked
to the chat with `derives_from`; tasks are linked with `created_from`. Concept object creation
is deferred; concepts stay in the stored summary.

### `GET /api/v1/search/keyword`

Runs Postgres full-text search across pages, sources, chats, and generic claim/task objects.

Query parameters:

| Name | Type | Notes |
| --- | --- | --- |
| `q` | string | Required; minimum length `1` |
| `kind` | string | Optional object kind filter, for example `page`, `source`, `chat`, `claim`, or `task` |
| `source_type` | string | Optional source type filter when searching sources |
| `limit` | integer | Default `20`; min `1`; max `100` |
| `offset` | integer | Default `0`; min `0` |

Response:

```json
{
  "results": [],
  "total": 0,
  "query": "quantum",
  "mode": "keyword"
}
```

Status codes: `200`, `401`, `422`.

### `POST /api/v1/search/vector`

Embeds the query and searches Qdrant by cosine similarity.

Request:

```json
{
  "q": "semantic search query",
  "kind": "page",
  "source_type": null,
  "limit": 20,
  "score_threshold": 0.2
}
```

Response:

```json
{
  "results": [],
  "total": 0,
  "query": "semantic search query",
  "mode": "vector"
}
```

When `OPENAI_API_KEY` is not set, the endpoint returns:

```json
{
  "detail": "embeddings_disabled"
}
```

Status codes: `200`, `401`, `422`, `503`.

### `POST /api/v1/search/hybrid`

Combines keyword, vector, and recency scores. When embeddings are disabled, this endpoint still returns keyword results and sets `embeddings_used` to `false`.

Request:

```json
{
  "q": "combined search query",
  "kind": null,
  "source_type": null,
  "limit": 20,
  "debug": false
}
```

Response:

```json
{
  "results": [
    {
      "id": "uuid",
      "kind": "page",
      "title": "Research Notes",
      "snippet": { "text": "combined search results with highlights", "highlights": [[0, 8]] },
      "tags": [],
      "score": 0.55,
      "updated_at": "2026-05-14T00:00:00Z",
      "source_type": null,
      "ingestion_status": null,
      "keyword_score": 1.0,
      "vector_score": 0.0,
      "recency_boost": 1.0
    }
  ],
  "total": 1,
  "query": "combined search query",
  "mode": "hybrid",
  "embeddings_used": false
}
```

Status codes: `200`, `401`, `422`.

---

## AI Endpoints

All AI endpoints require authentication and degrade gracefully — they return `503 Service Unavailable` when `OPENAI_API_KEY` is not configured. Every AI call that writes data also creates an `agent_runs` row and an `object_revisions` row (for existing object mutations).

### POST /api/v1/ai/summarize

Summarize a page or source. Writes the result to `metadata_["ai_summary"]` and creates an `object_revisions` record.

**Request**: `{ "object_id": "uuid", "force": false }` — set `force: true` to re-summarize even when a cached summary exists.

**Response**: `{ "summary": "...", "agent_run_id": "uuid", "cached": false }`

Status codes: `200`, `401`, `404`, `422`, `503`.

### POST /api/v1/ai/extract-claims

Extract factual claims from content, create `claim` objects + `mentions` edges.

**Request**: `{ "object_id": "uuid" }` **Response**: `{ "items": [{"id": "uuid", "title": "..."}], "agent_run_id": "uuid" }`

### POST /api/v1/ai/extract-tasks

Same as extract-claims but creates `task` objects.

### POST /api/v1/ai/suggest-links

Return ranked link suggestions (read-only — user must call `POST /edges` to confirm).

**Request**: `{ "object_id": "uuid", "limit": 5 }` **Response**: `{ "suggestions": [{target_id, target_title, target_kind, reason, confidence}], "agent_run_id": "uuid" }`

### POST /api/v1/ai/answer

Answer a question grounded in the KB. **Request**: `{ "q": "...", "kind": null, "limit": 8 }` **Response**: `{ "answer": "...", "citations": [...], "agent_run_id": "uuid", "context_count": 4 }`

### POST /api/v1/ai/triage

Analyze an inbox item and suggest tags/title/summary (read-only).

**Request**: `{ "object_id": "uuid" }` **Response**: `{ "suggested_tags": [...], "suggested_title": "...", "summary": "...", "agent_run_id": "uuid" }`

### GET /api/v1/ai/inbox

Objects from last 30 days with no tags and no description. **Query**: `limit` (default 20), `offset` (default 0). Returns `PaginatedResponse<ObjectOut>`.

### POST /api/v1/ai/extract-project

Draft (and optionally persist) a **project** object from an existing **page**, **chat**, or **source** object. Uses OpenAI JSON mode; writes an `agent_runs` row (`agent_type`: `extract-project`). Requires `OPENAI_API_KEY`; returns `503` with detail `AI features disabled — set OPENAI_API_KEY` when unset.

**Request** (JSON):

```json
{
  "source_id": "uuid",
  "create": true,
  "period_hint": ["2023-01-01", null]
}
```

- `source_id` (required): object id whose `kind` is `page`, `chat`, or `source`.
- `create` (default `true`): when `true`, inserts `objects` + `projects` rows with `confidence` `ai_extracted` and lineage fields; when `false`, returns the draft only (`project_id` is `null`).
- `period_hint` (optional): two ISO dates or `null` entries `[start, end]` to steer extraction.

**Response** (200):

```json
{
  "draft": {
    "title": "...",
    "description": null,
    "period_start": null,
    "period_end": null,
    "role": null,
    "organization": null,
    "problem": null,
    "actions": null,
    "results": null,
    "metrics": {},
    "skills": [],
    "confidence": 0.85
  },
  "project_id": "uuid-or-null",
  "agent_run_id": "uuid",
  "source_id": "uuid"
}
```

**Errors**: `400` if `source_id` is not a page/chat/source; `404` if the object is missing or not owned by the user; `502` if the model returns non-JSON or malformed payload (failed `agent_run` is persisted); `503` if AI is disabled.

### Career AI Generators

Both endpoints are read-only for project data: they return generated content and audit the LLM call in `agent_runs`, but they do not write bullets, stories, or metadata back onto the project. Evidence is gathered from `projects.extracted_from` plus incoming `belongs_to_project` edges, capped by `max_evidence_objects`.

#### POST /api/v1/ai/generate-resume-bullets

Generate evidence-linked resume bullet variants for an owned, non-deleted project.

**Request**:

```json
{
  "project_id": "uuid",
  "target_role": "Senior Backend Engineer",
  "emphasis": "distributed systems and measurable user impact",
  "count": 3,
  "max_evidence_objects": 10
}
```

**Response**:

```json
{
  "project_id": "uuid",
  "bullets": [
    {
      "text": "Built...",
      "evidence_object_ids": ["uuid"],
      "confidence": "high",
      "metrics_cited": ["latency_ms"]
    }
  ],
  "agent_run_id": "uuid",
  "evidence_count": 3
}
```

#### POST /api/v1/ai/generate-interview-story

Generate one STAR-format interview story for an owned, non-deleted project.

**Request**:

```json
{
  "project_id": "uuid",
  "question_type": "behavioral",
  "target_role": "Senior Backend Engineer",
  "max_words": 400,
  "max_evidence_objects": 10
}
```

`question_type` is `behavioral`, `technical`, or `leadership`.

**Response**:

```json
{
  "project_id": "uuid",
  "story": {
    "situation": "...",
    "task": "...",
    "action": "...",
    "result": "...",
    "evidence_object_ids": ["uuid"]
  },
  "agent_run_id": "uuid",
  "word_count": 380
}
```

**Errors**: `404` if the project is missing, soft-deleted, or not owned by the user; `422` for invalid bounds such as `count > 5`, `max_words < 100`, or invalid `question_type`; `502` if the model returns malformed JSON (failed `agent_run` is persisted with raw output); `503` if AI is disabled before any `agent_runs` row is created.

## Projects (career memory)

Projects are `KosObject` rows with `kind="project"` plus a row in the `projects` table (migration `0007`). Soft-delete uses `objects.deleted_at`; restore with `POST /api/v1/objects/{id}/restore` (same as other objects).

### POST /api/v1/projects

Create a project. **Body**: `ProjectCreate` — required `title`; optional `description`, `period_start`, `period_end`, `role`, `organization`, `problem`, `actions`, `results`, `metrics` (flat primitives only), `skills` (normalized to unique lowercase strings), `status` (`active` \| `paused` \| `completed` \| `archived`), `tags`, `extracted_from`, `confidence` (`manual` \| `ai_extracted` \| `verified`). Returns `ProjectOut` (`201`).

### GET /api/v1/projects

List projects for the current user. **Query**: `limit` (1–200, default 50), `offset` (default 0), optional `status`, optional `skill` (substring match against `skills` containment), `include_archived` (default `false` — when `true`, includes rows with `objects.deleted_at` set, i.e. soft-deleted projects; does not filter on `objects.is_archived`). Returns `PaginatedResponse[ProjectOut]` (`items`, `total`, `page`, `limit`, `pages`).

### GET /api/v1/projects/{project_id}

Fetch one project (`200`). `404` if missing, deleted (unless listed via `include_archived` and not applicable here), or not owned by the user.

### PATCH /api/v1/projects/{project_id}

Partial update (`ProjectUpdate`). Omitted fields are unchanged; explicit `null` clears nullable object/project fields where supported. `404` if not found.

### DELETE /api/v1/projects/{project_id}

Soft-delete the project (`204`). Subsequent `GET` returns `404` until `POST /api/v1/objects/{id}/restore`.

## Workspaces

Workspaces are user-owned saved UI layouts for the future multi-pane research environment. They are stored in their own `workspaces` table, not as `KosObject` rows. All endpoints require an authenticated session and return `404` for missing, deleted, or not-owned workspaces.

### Layout shape

```json
{
  "version": 1,
  "split": "horizontal",
  "panes": [
    {
      "id": "pane-1",
      "object_id": "00000000-0000-0000-0000-000000000000",
      "object_kind": "page",
      "size_pct": 50,
      "mode": "read"
    },
    {
      "id": "pane-2",
      "object_id": null,
      "object_kind": null,
      "size_pct": 50,
      "mode": "read"
    }
  ],
  "active_pane_id": "pane-1"
}
```

Validation requires `version: 1`, 1-4 panes, unique pane ids, an `active_pane_id` that matches a pane, total size near 100, and object kinds limited to `page`, `source`, `asset`, `chat`, or `project`. Multi-pane layouts require `split` and each pane size must be between 5 and 95; single-pane layouts may omit `split` and use `size_pct: 100`. `object_id` is syntax-checked as a UUID but is not FK-validated, so stale references can still be loaded and handled by the UI.

### POST /api/v1/workspaces

Create a workspace. Returns `WorkspaceOut` (`201`).

```json
{
  "name": "Research board",
  "description": "Pages and source notes for a report",
  "is_pinned": true,
  "layout": {
    "version": 1,
    "split": "horizontal",
    "panes": [
      {"id": "pane-1", "object_kind": "page", "size_pct": 50},
      {"id": "pane-2", "object_kind": "source", "size_pct": 50}
    ],
    "active_pane_id": "pane-1"
  }
}
```

### GET /api/v1/workspaces

List the current user's workspaces. **Query**: `limit` (1-200, default 50), `offset` (default 0), `pinned_only` (default `false`), and `include_deleted` (default `false`). Returns `PaginatedResponse[WorkspaceOut]`.

### GET /api/v1/workspaces/{workspace_id}

Fetch one workspace and update its `last_used_at` timestamp. Returns `WorkspaceOut` (`200`).

### PATCH /api/v1/workspaces/{workspace_id}

Partial update. Body fields are optional: `name`, `description`, `layout`, `is_pinned`. Invalid layouts return `422`.

### DELETE /api/v1/workspaces/{workspace_id}

Soft-delete a workspace by setting `deleted_at` (`204`). Repeating the delete is idempotent and also returns `204`.

### POST /api/v1/workspaces/{workspace_id}/restore

Restore a soft-deleted workspace. Returns `WorkspaceOut` with `deleted_at: null`; returns `404` if the workspace does not exist, is not owned by the current user, or is not currently deleted.
