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
| `source` | Phase 2 | `sources` table, migration pending |

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

| Field | Type | Constraints / Notes |
| --- | --- | --- |
| `id` | UUID | Primary key |
| `user_id` | UUID | Required FK to `users.id` |
| `object_id` | UUID | Required FK to `objects.id` |
| `content` | text | Chunk text |
| `metadata` | JSONB | Required object, default `{}` |
| `position` | integer | Required order within the object |
| `created_at` | timestamptz | Required |
| `updated_at` | timestamptz | Required |

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

## Phase 2 Sources Preview

Phase 2 adds a `sources` specialization table for objects with `kind="source"`. The exact fields will be defined in the Phase 2 migration, but expected fields include source type, URL or asset reference, extraction status, extracted metadata, derivative paths, and timestamps.

Sources will connect to other objects through edges. Examples:

| Relationship | Edge |
| --- | --- |
| A PDF source derives from an uploaded PDF asset | `source -> asset`, `kind="derives_from"` |
| A research page cites a web article source | `page -> source`, `kind="cites"` |
