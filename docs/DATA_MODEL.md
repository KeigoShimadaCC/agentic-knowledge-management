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
| `chat` | Phase 6A | `chats` table |
| `claim` | Phase 6B | Generic `objects` row |
| `task` | Phase 6B | Generic `objects` row |
| `project` | Phase 9A | `projects` table |
| `resume_bullet_set` | Phase 9 | `resume_bullet_sets` table |
| `interview_story` | Phase 9 | `interview_story_records` table |

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
| `user_agent` | text | Optional; recorded at login time |
| `ip_address` | text | Optional; recorded at login time |
| `expires_at` | timestamptz | Required expiration time |
| `created_at` | timestamptz | Required |
| `last_seen` | timestamptz | Required; updated on each authenticated request |

### `objects`

| Field | Type | Constraints / Notes |
| --- | --- | --- |
| `id` | UUID | Primary key |
| `user_id` | UUID | Required FK to `users.id`; all queries must scope by user |
| `kind` | text (String 32) | Required; validated in application code — no DB CHECK constraint. Current valid kinds: `page`, `asset`, `source`, `chat`, `project`, `claim`, `task`, `resume_bullet_set`, `interview_story`, `note`, `bookmark`, `collection` |
| `title` | text | Required display title |
| `description` | text | Optional summary or user-authored description |
| `tags` | text[] | Required array, default empty |
| `metadata` | JSONB | Required object, default `{}` |
| `is_pinned` | boolean | Required, default `false` |
| `is_archived` | boolean | Required, default `false` |
| `ai_generated` | boolean | Required, default `false`; marks AI-created claims, tasks, and career artifacts |
| `created_at` | timestamptz | Required |
| `updated_at` | timestamptz | Required |
| `deleted_at` | timestamptz | Optional soft-delete marker |

### `pages`

| Field | Type | Constraints / Notes |
| --- | --- | --- |
| `id` | UUID | Primary key and FK to `objects.id` |
| `content_json` | JSONB | Tiptap document JSON |
| `content_text` | text | Plain-text projection used for search and previews |
| `word_count` | integer | Required; updated on every save |
| `version` | integer | Monotonically increasing; used for optimistic-locking in `update_page` |
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
| `links_to` | Canonical generic user-authored link |
| `derives_from` | Phase 2: a source derives from an uploaded asset or another source |
| `cites` | Phase 2: a page cites a source |
| `mentions` | One object mentions a person, organization, concept, source, or other object |
| `supports` | One object supports another object's claim or interpretation |
| `contradicts` | One object contradicts another object's claim or interpretation |
| `related_to` | Canonical generic related-object relationship |
| `summarizes` | One object summarizes another object |
| `belongs_to_project` | Object belongs to a project memory |
| `evidence_for` | Object is evidence for another object |
| `created_from` | Object was created from another object or import |

Legacy accepted kinds:

| Kind | Meaning |
| --- | --- |
| `link` | Legacy alias for `links_to`; do not rewrite existing rows automatically |
| `related` | Legacy alias for `related_to`; do not rewrite existing rows automatically |
| `citation` | Legacy citation relationship; prefer `cites` for page-to-source citations |
| `embed` | Legacy embedded-object relationship |
| `child` | Legacy parent-child hierarchy relationship |
| `tag` | Legacy object-to-tag relationship |

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

### `chats`

Phase 6A adds a `chats` specialization table for imported conversations with `objects.kind="chat"`. The raw transcript remains on disk; `content_text` is the canonical searchable text projection.

| Field | Type | Constraints / Notes |
| --- | --- | --- |
| `id` | UUID | Primary key and FK to `objects.id` (CASCADE delete) |
| `provider` | varchar(32) | `chatgpt`, `claude`, `markdown`, `plain_text`, or `unknown` |
| `external_chat_id` | text | Optional provider/export identifier |
| `source_filename` | text | Optional original upload filename |
| `raw_storage_path` | text | Required relative path under `library/chats` |
| `raw_format` | varchar(16) | `json`, `md`, or `txt` |
| `turn_count` | integer | Number of parsed turns |
| `started_at` / `ended_at` | timestamptz | Optional conversation time range |
| `imported_at` | timestamptz | Import timestamp |
| `parsed_turns` | JSONB | Normalized turn list for UI rendering |
| `content_text` | text | Searchable transcript projection |
| `metadata` | JSONB | Import metadata, including batch raw path when applicable |
| `structured_summary` | JSONB | Phase 6B AI-generated structured summary preview or applied summary |
| `structured_summary_status` | text | `none`, `previewed`, `applied`, or `failed` |
| `structured_summary_agent_run_id` | UUID | Optional FK to the AI run that generated or applied the summary |
| `structured_summary_updated_at` | timestamptz | Last structured summary update time |
| `structured_summary_hash` | varchar(64) | Stable hash used for idempotency/audit |
| `created_at` / `updated_at` | timestamptz | Required timestamps |

Phase 6B stores extracted concepts in `structured_summary.concepts`. It creates generic
`claim` and `task` objects only after the user explicitly applies a preview. Created objects
store `source_chat_id`, `turn_refs`, `confidence`, `agent_run_id`, and an `extraction_key` in
`objects.metadata`.

### `ingestion_jobs`

| Field | Type | Constraints / Notes |
| --- | --- | --- |
| `id` | UUID | Primary key |
| `user_id` | UUID | Required FK to `users.id` |
| `object_id` | UUID | Optional FK to the object being processed; SET NULL on object delete |
| `status` | text | Required; one of `pending`, `running`, `done`, `failed` |
| `job_type` | text | Required job category (e.g. `ingest_source`, `reindex_object`) |
| `payload` | JSONB | Required; job input parameters, default `{}` |
| `result` | JSONB | Optional; written by the worker on completion |
| `error` | text | Optional; last failure message |
| `attempts` | integer | Required, default 0 |
| `max_attempts` | integer | Required, default 3 |
| `enqueued_at` | timestamptz | Required; set when the job is created |
| `started_at` | timestamptz | Optional; set when a worker claims the job |
| `finished_at` | timestamptz | Optional; set when the job reaches `done` or `failed` |
| `created_at` | timestamptz | Required |

### `agent_runs`

| Field | Type | Constraints / Notes |
| --- | --- | --- |
| `id` | UUID | Primary key |
| `user_id` | UUID | Required FK to `users.id` |
| `status` | text | Required; one of `running`, `done`, `failed`, `cancelled` |
| `agent_type` | text | Required; identifies the AI tool or endpoint that ran (e.g. `summarize`, `create_page`) |
| `input` | JSONB | Required; request metadata logged at call time, default `{}` |
| `output` | JSONB | Optional; result metadata written on completion |
| `error` | text | Optional; failure message |
| `model` | text | Optional; model identifier used (e.g. `gpt-4o`) |
| `input_tokens` | integer | Optional; tokens consumed in the prompt |
| `output_tokens` | integer | Optional; tokens generated in the response |
| `cost_usd` | numeric(10,6) | Optional; approximate cost in USD |
| `started_at` | timestamptz | Required; set at row creation |
| `finished_at` | timestamptz | Optional; set when the run reaches a terminal state |
| `created_at` | timestamptz | Required |

### `object_revisions`

Phase 5 adds `object_revisions` for auditable user and agent writes. Phase 6B uses it for structured chat summary preview/apply changes; Phase 7B MCP write tools must link every modified object to a revision row.

| Field | Type | Constraints / Notes |
| --- | --- | --- |
| `id` | UUID | Primary key |
| `object_id` | UUID | Required FK to `objects.id` (`ON DELETE CASCADE`) |
| `user_id` | UUID | Required FK to `users.id` (`ON DELETE CASCADE`) |
| `rev_num` | integer | Monotonic per object; unique with `object_id` |
| `changed_by` | varchar(64) | `user:<id>`, `agent:<name>`, or another explicit actor label |
| `agent_run_id` | UUID | Optional FK to `agent_runs.id` (`ON DELETE SET NULL`) |
| `before_snapshot` | JSONB | Required object snapshot before the change; `{}` for create-like changes |
| `after_snapshot` | JSONB | Required object snapshot after the change; `{}` for terminal changes if ever needed |
| `created_at` | timestamptz | Required |

Indexes exist on `object_id`, `user_id`, and `agent_run_id`.

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

## Phase 4: Graph Lite

Phase 4A uses the existing Postgres `edges` table as the canonical graph. Kuzu remains a future derived index and is not part of Graph Lite.

Graph Lite rules:

- Edge kinds are validated in application code, not a PostgreSQL enum.
- Edges remain directed, but object-centered APIs expose direction relative to the requested object.
- Creating the same `(source_id, target_id, kind)` is idempotent.
- Soft-deleted matching edges are restored instead of duplicated.
- Both source and target objects must belong to the same authenticated user.
- Deleted objects and deleted edges are excluded from graph APIs by default.
- Related-object traversal is intentionally limited to depth 1 or 2 over Postgres edges.

## Object Type Registry (Design Note)

Search UI, graph UI, MCP tools, and AI context packing should not hardcode every object type. A future centralized object type registry will map each `kind` to routing, display, and search behavior. The contract to follow:

```
objectTypeRegistry = {
  page:              { route, icon, searchableFields: ["title", "content_text"] },
  source:            { route, icon, searchableFields: ["title", "extracted_text"] },
  asset:             { route, icon, searchableFields: ["title", "filename"] },
  chat:              { route, icon, searchableFields: ["title", "content_text"] },
  project:           { route, icon, searchableFields: ["title", "description", "role", "organization"] },
  claim:             { route, icon, searchableFields: ["title", "content"] },
  resume_bullet_set: { route, icon, searchableFields: ["title"] },
  interview_story:   { route, icon, searchableFields: ["title"] },
}
```

The `project` kind is live (Phase 9A). `resume_bullet_set` and `interview_story` are live (Phase 9). The formal registry object in `lib/objectRouting.ts` covers routing; the full registry with searchable fields and display metadata is a planned future consolidation. When adding new object types, design search and display behavior with this contract in mind.

## Phase 8B: Workspaces

Workspaces persist named multi-pane UI layouts. They are personal application state, not knowledge objects, so they do not create rows in `objects`, do not extend `VALID_OBJECT_KINDS`, and are not indexed for search or graph traversal.

### `workspaces`

| Field | Type | Constraints / Notes |
| --- | --- | --- |
| `id` | UUID | Primary key, default `gen_random_uuid()` |
| `user_id` | UUID | Required FK to `users.id` (`ON DELETE CASCADE`) |
| `name` | varchar(255) | Required display name |
| `description` | text | Optional |
| `layout_json` | JSONB | Required validated layout payload, default `{}` |
| `is_pinned` | boolean | Required, default `false` |
| `last_used_at` | timestamptz | Updated when `GET /api/v1/workspaces/{id}` loads the workspace |
| `created_at` | timestamptz | Required |
| `updated_at` | timestamptz | Required |
| `deleted_at` | timestamptz | Soft-delete marker |

Indexes exist on `user_id`, active user workspaces (`user_id WHERE deleted_at IS NULL`), and `last_used_at DESC NULLS LAST`.

### `layout_json`

```json
{
  "version": 1,
  "split": "horizontal",
  "panes": [
    {
      "id": "pane-1",
      "object_id": null,
      "object_kind": null,
      "size_pct": 50,
      "mode": "read"
    },
    {
      "id": "pane-2",
      "object_id": "00000000-0000-0000-0000-000000000000",
      "object_kind": "source",
      "size_pct": 50,
      "mode": "read"
    }
  ],
  "active_pane_id": "pane-1"
}
```

The API validates `version: 1`, 1-4 panes, unique pane ids, active pane membership, size totals near 100, and pane kinds limited to `page`, `source`, `asset`, `chat`, or `project`. Multi-pane layouts require `split` and each pane size must be between 5 and 95; single-pane layouts may omit `split` and use `size_pct: 100`. `object_id` is UUID-validated but deliberately has no database FK, so a workspace can survive deleted or missing referenced objects and let the UI render an unavailable placeholder.

## Phase 9A: Projects

`projects` is a specialization table for objects with `kind="project"`. It holds the STAR (Situation/Task/Action/Result) career narrative plus structured metadata for evidence linking and career artifact generation.

### `projects`

| Field | Type | Constraints / Notes |
| --- | --- | --- |
| `id` | UUID | Primary key and FK to `objects.id` (CASCADE delete) |
| `period_start` | date | Optional; start date of the project |
| `period_end` | date | Optional; end date of the project |
| `role` | text | Optional; the user's role during this project |
| `organization` | text | Optional; employer or client organization |
| `problem` | text | Optional; STAR "Situation/Task" narrative |
| `actions` | text | Optional; STAR "Action" narrative |
| `results` | text | Optional; STAR "Result" narrative |
| `metrics` | JSONB | Required; structured metrics object, default `{}` |
| `skills` | text[] | Required; list of skills demonstrated, default `{}` |
| `status` | varchar(16) | Required; one of `active`, `paused`, `completed`, `archived`; default `active` |
| `confidence` | varchar(16) | Required; `manual` (user-authored) or `ai_extracted`; default `manual` |
| `extracted_from` | UUID | Optional FK to `objects.id` (SET NULL); the source object AI extracted this project from |
| `extracted_by_agent_run_id` | UUID | Optional FK to `agent_runs.id` (SET NULL); the AI run that created this project |
| `created_at` | timestamptz | Required |
| `updated_at` | timestamptz | Required |

Indexes exist on `period_start`, `period_end`, `status`, and `skills` (GIN for array queries like "projects with skill python").

Evidence is linked via `belongs_to_project` edges from pages, sources, chats, or claims to the project object.

## Phase 9: Career Artifacts

Career artifacts are generated from projects and stored as first-class objects. Both tables extend `objects` (using `kind="resume_bullet_set"` and `kind="interview_story"` respectively).

### `resume_bullet_sets`

| Field | Type | Constraints / Notes |
| --- | --- | --- |
| `id` | UUID | Primary key and FK to `objects.id` (CASCADE delete) |
| `project_id` | UUID | Required FK to `objects.id` (CASCADE delete); the project this set belongs to |
| `target_role` | text | Optional; the role this bullet set was optimized for |
| `emphasis` | text | Optional; focus area requested (e.g. "scale and reliability") |
| `count` | smallint | Required; number of bullets generated |
| `bullets` | JSONB | Required; array of bullet objects with `text`, `confidence`, `evidence_object_ids`, `metrics_cited`; default `[]` |
| `agent_run_id` | UUID | Optional FK to `agent_runs.id` (SET NULL); the generation run |
| `prompt_version` | varchar(16) | Optional; tracks which prompt template was used |
| `created_at` | timestamptz | Required |
| `updated_at` | timestamptz | Required |

### `interview_story_records`

| Field | Type | Constraints / Notes |
| --- | --- | --- |
| `id` | UUID | Primary key and FK to `objects.id` (CASCADE delete) |
| `project_id` | UUID | Required FK to `objects.id` (CASCADE delete); the project this story belongs to |
| `question_type` | varchar(16) | Required; one of `behavioral`, `technical`, `leadership`; default `behavioral` |
| `target_role` | text | Optional; the role this story was optimized for |
| `max_words` | integer | Required; word limit requested; default 400 |
| `word_count` | integer | Required; actual word count of generated story; default 0 |
| `story` | JSONB | Required; structured STAR story with `situation`, `task`, `action`, `result`, `evidence_object_ids`; default `{}` |
| `agent_run_id` | UUID | Optional FK to `agent_runs.id` (SET NULL); the generation run |
| `prompt_version` | varchar(16) | Optional; tracks which prompt template was used |
| `created_at` | timestamptz | Required |
| `updated_at` | timestamptz | Required |
