# KnowledgeOS Data Model

KnowledgeOS uses a universal object model. Every user-visible knowledge item starts as a row in `objects`, then optionally extends into a specialization table such as `pages`, `assets`, or the Phase 2 `sources` table.

## Universal Object Pattern

`KosObject` is the base record for all knowledge items. It provides common identity, ownership, title, description, tags, metadata, lifecycle flags, and timestamps.

Supported object kinds:

| Kind | Phase | Specialization |
| --- | --- | --- |
| `page` | Phase 1 | `pages` table |
| `asset` | Phase 1 | `assets` table |
| `note` | Reserved | No specialization table yet |
| `bookmark` | Reserved | No specialization table yet |
| `collection` | Reserved | No specialization table yet |
| `source` | Phase 2 | `sources` table |

The specialization table uses the same primary key as the base object row. For example, a page has `objects.id = pages.id`.

## Tables

### `users`

| Field | Type | Constraints / Notes |
| --- | --- | --- |
| `id` | UUID | Primary key |
| `email` | text | Required, unique login identifier |
| `password_hash` | text | Required; stores password hash, never a raw password |
| `display_name` | text | Optional user-facing name |
| `created_at` | timestamptz | Required |
| `updated_at` | timestamptz | Required |

### `sessions`

| Field | Type | Constraints / Notes |
| --- | --- | --- |
| `id` | UUID | Primary key |
| `user_id` | UUID | Required FK to `users.id` |
| `token_hash` | text | Required, unique SHA-256 hash of the browser session token |
| `expires_at` | timestamptz | Required expiration time |
| `created_at` | timestamptz | Required |
| `revoked_at` | timestamptz | Optional; invalidates the session when set |

### `objects`

| Field | Type | Constraints / Notes |
| --- | --- | --- |
| `id` | UUID | Primary key |
| `user_id` | UUID | Required FK to `users.id`; all queries must scope by user |
| `kind` | text / enum | Required; one of `page`, `asset`, `note`, `bookmark`, `collection`, `source` |
| `title` | text | Required display title |
| `description` | text | Optional summary or user-authored description |
| `tags` | text[] | Required array, default empty |
| `metadata` | JSONB | Required object, default `{}` |
| `is_pinned` | boolean | Required, default `false` |
| `is_archived` | boolean | Required, default `false` |
| `created_at` | timestamptz | Required |
| `updated_at` | timestamptz | Required |
| `deleted_at` | timestamptz | Optional soft-delete marker |

### `pages`

| Field | Type | Constraints / Notes |
| --- | --- | --- |
| `id` | UUID | Primary key and FK to `objects.id` |
| `content` | JSONB | Tiptap document JSON |
| `content_text` | text | Plain-text projection used for search and previews |
| `created_at` | timestamptz | Required |
| `updated_at` | timestamptz | Required |

### `assets`

| Field | Type | Constraints / Notes |
| --- | --- | --- |
| `id` | UUID | Primary key and FK to `objects.id` |
| `filename` | text | Original or display filename |
| `content_type` | text | MIME type when known |
| `size_bytes` | bigint | File size in bytes |
| `sha256` | text | Required content digest |
| `storage_path` | text | Required path to the stored original |
| `status` | text | Processing state such as `ready` or `error` |
| `width` | integer | Optional image/video width |
| `height` | integer | Optional image/video height |
| `duration_secs` | numeric | Optional audio/video duration |
| `created_at` | timestamptz | Required |
| `updated_at` | timestamptz | Required |

### `edges`

| Field | Type | Constraints / Notes |
| --- | --- | --- |
| `id` | UUID | Primary key |
| `user_id` | UUID | Required FK to `users.id` |
| `source_id` | UUID | Required FK to `objects.id`; source object in the graph edge |
| `target_id` | UUID | Required FK to `objects.id`; target object in the graph edge |
| `kind` | text | Required relationship kind |
| `weight` | numeric | Optional ranking or confidence value |
| `metadata` | JSONB | Required object, default `{}` |
| `created_at` | timestamptz | Required |
| `deleted_at` | timestamptz | Optional soft-delete marker |

Known edge kinds:

| Kind | Meaning |
| --- | --- |
| `derives_from` | Phase 2: a source derives from an uploaded asset or another source |
| `cites` | Phase 2: a page cites a source |
| `link` | One object links to another |
| `embed` | One object embeds another |
| `child` | Parent-child hierarchy, such as collection membership |
| `related` | User or system marked relationship |
| `citation` | Generic citation relationship when `cites` is too narrow |

### `chunks`

Added in migration `0001`; extended for Phase 3 search in migration `0003`.

| Field | Type | Constraints / Notes |
| --- | --- | --- |
| `id` | UUID | Primary key |
| `user_id` | UUID | Required FK to `users.id`; added in migration 0003 |
| `object_id` | UUID | Required FK to `objects.id` |
| `chunk_idx` | integer | Required; position of this chunk within the object |
| `content` | text | Required; raw text of this chunk |
| `token_count` | integer | Optional; approximate token count for context budgeting |
| `metadata` | JSONB | Required object, default `{}` |
| `source_locator` | JSONB | Optional; e.g. `{"page": 3, "paragraph": 1}` for PDF |
| `content_hash` | text | Optional SHA-256 of `content`; used to skip unchanged chunks on reindex |
| `embedding_status` | varchar(16) | `pending`, `running`, `ready`, or `error`; default `pending` |
| `embedding_model` | text | Optional; model used to generate the Qdrant embedding |
| `embedded_at` | timestamptz | Optional; set when Qdrant point was last written |
| `qdrant_point_id` | text | Optional; Qdrant point ID for this chunk |
| `created_at` | timestamptz | Required |
| `updated_at` | timestamptz | Required; updated whenever chunk or embedding changes |

Constraints and indexes:
- `UNIQUE(object_id, chunk_idx)` — ensures deterministic re-indexing
- Index on `object_id`, `user_id`, `embedding_status`, `content_hash`

### `ingestion_jobs`

| Field | Type | Constraints / Notes |
| --- | --- | --- |
| `id` | UUID | Primary key |
| `user_id` | UUID | Required FK to `users.id` |
| `object_id` | UUID | Optional FK to the object being processed |
| `job_type` | text | Required job category |
| `status` | text | Required lifecycle state such as `pending`, `running`, `ready`, or `error` |
| `error` | text | Optional failure message |
| `metadata` | JSONB | Required object, default `{}` |
| `created_at` | timestamptz | Required |
| `updated_at` | timestamptz | Required |

### `agent_runs`

| Field | Type | Constraints / Notes |
| --- | --- | --- |
| `id` | UUID | Primary key |
| `user_id` | UUID | Required FK to `users.id` |
| `agent_name` | text | Required agent identifier |
| `action` | text | Required high-level action name |
| `status` | text | Required lifecycle state |
| `input` | JSONB | Request or prompt metadata |
| `output` | JSONB | Result metadata |
| `error` | text | Optional failure message |
| `created_at` | timestamptz | Required |
| `updated_at` | timestamptz | Required |

## Soft Deletes

KnowledgeOS uses soft deletes for objects and edges. Deleting a record sets `deleted_at` instead of removing the row. Normal application queries must include:

```sql
deleted_at IS NULL
```

Trash views intentionally query deleted objects. Restore operations clear `deleted_at`.

Specialization rows such as `pages` and `assets` are preserved when the base object is soft-deleted. This keeps restoration cheap and avoids losing file references or page content.

## Content-Addressed Asset Storage

Asset binaries live outside Postgres. On upload, the API computes the file SHA-256 and stores the original at:

```text
~/KnowledgeOS/library/assets/{sha256[:2]}/{sha256}/original{ext}
```

The `assets` row stores the original filename, MIME type, file size, SHA-256 digest, and storage path. The digest path provides stable identity independent of user filenames and enables later deduplication.

## Phase 2: Sources

Phase 2 adds a `sources` specialization table for objects with `kind="source"`. Migration `0002_add_sources` creates the `source_type_enum` PostgreSQL enum and the `sources` table.

### `sources`

| Field | Type | Constraints / Notes |
| --- | --- | --- |
| `id` | UUID | Primary key and FK to `objects.id` (CASCADE delete) |
| `source_type` | source_type_enum | Required; one of `pdf`, `image`, `video`, `audio`, `youtube`, `web`, `csv`, `file` |
| `url` | text | Required for `youtube` and `web` types; null for file-backed sources |
| `asset_id` | UUID | Optional FK to `objects.id` (SET NULL); link to original upload |
| `ingestion_status` | varchar(16) | `pending`, `running`, `ready`, or `error`; default `pending` |
| `extracted_text` | text | Full text: PDF pages, web article body, YouTube transcript |
| `page_count` | integer | PDF page count |
| `thumbnail_path` | text | Relative path under `~/KnowledgeOS/library/` |
| `preview_data` | JSONB | CSV preview rows, YouTube oEmbed JSON |
| `error_message` | text | Last extraction error |
| `created_at` | timestamptz | Required |
| `updated_at` | timestamptz | Required |

Source edge relationships:

| Relationship | Edge |
| --- | --- |
| A PDF source was created from an uploaded asset | `source → asset`, `kind="derives_from"` |
| A research page cites a web article source | `page → source`, `kind="cites"` |

### Source storage

Each source gets a directory under the library:

```text
~/KnowledgeOS/library/sources/{source_id}/
  thumbnail.jpg        # PDF cover image, image thumbnail, YouTube thumbnail, og:image
  extracted_text.txt   # written by extractor (backup; canonical copy is in DB)
```

## Phase 3: Search Indexing

Phase 3 extends the `chunks` table for idempotent search indexing (migration `0003`). Key design rules:

- `chunks` is the canonical record of indexable text. Postgres is the source of truth.
- Qdrant is a derived, re-buildable vector index. Never treat it as canonical.
- `content_hash` enables skip-on-no-change reindexing: if hash matches, skip re-embedding.
- `embedding_status` drives the reindex worker's work queue.
- `source_locator` preserves provenance (e.g., which PDF page a chunk came from).
- Reindexing is always idempotent: `UPSERT` on `(object_id, chunk_idx)`.

## Object Type Registry (Design Note)

Search UI, graph UI, MCP tools, and AI context packing should not hardcode every object type. A future object type registry will map each `kind` to routing, display, and search behavior:

```
objectTypeRegistry = {
  page:    { route, icon, searchableFields: ["title", "content_text"] },
  source:  { route, icon, searchableFields: ["title", "extracted_text"] },
  asset:   { route, icon, searchableFields: ["title", "filename"] },
  chat:    { route, icon, searchableFields: ["title", "summary"] },
  project: { route, icon, searchableFields: ["title", "description"] },
  claim:   { route, icon, searchableFields: ["title", "content"] },
}
```

This registry is not yet implemented. When adding new object types, design search and display behavior with this contract in mind.
