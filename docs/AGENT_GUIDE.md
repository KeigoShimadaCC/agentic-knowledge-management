# KnowledgeOS Agent Guide

This guide is for AI agents such as Claude, Codex, GPT, and local assistants operating against a KnowledgeOS instance. Agents must treat the API as the only supported write boundary.

## Operating Rules

Agents must follow these rules:

| Rule | Requirement |
| --- | --- |
| Use the API | All reads and writes should go through `http://localhost:8000/api/v1`. |
| No direct DB writes | Do not connect to Postgres or mutate tables directly. |
| Soft-delete only | Delete through API endpoints that set `deleted_at`; never hard-delete records or files. |
| No shell execution | Do not run shell commands as part of normal KnowledgeOS operation. |
| Stay inside the library | Do not read or write files outside `~/KnowledgeOS`. |
| Identify yourself | Send a `User-Agent` header identifying the agent and version. |
| Preserve user intent | Do not overwrite page content, tags, metadata, or source links unless the user explicitly asked for that change. |

Recommended agent header:

```text
User-Agent: KnowledgeOS-Agent/Codex
```

Agents that perform multi-step tasks should also create or update audit records when that API surface is available. Until then, the `User-Agent` header and normal server logs are the minimum audit trail.

## Authentication

KnowledgeOS uses an httponly `kos_session` cookie. Browser-based agents inherit the browser session. HTTP clients must log in through `POST /api/v1/auth/login` or register through `POST /api/v1/auth/register`, then preserve the returned cookie for subsequent requests.

Never ask the user for raw database credentials when the API can perform the task.

## Read a Page

Use:

```text
GET /api/v1/pages/{id}
```

Example:

```http
GET /api/v1/pages/8b7b8b2a-0000-4000-9000-000000000001 HTTP/1.1
Host: localhost:8000
Cookie: kos_session=...
User-Agent: KnowledgeOS-Agent/Codex
```

Expected response:

```json
{
  "id": "uuid",
  "kind": "page",
  "title": "Research Notes",
  "tags": ["research"],
  "metadata": {},
  "content": {
    "type": "doc",
    "content": []
  },
  "content_text": "Plain text projection",
  "created_at": "2026-05-14T00:00:00Z",
  "updated_at": "2026-05-14T00:00:00Z"
}
```

Use the Tiptap `content` JSON for faithful editing. Use `content_text` only for quick reading, search snippets, or summaries.

## Create a Page

Use:

```text
POST /api/v1/pages
```

Minimum request:

```json
{
  "title": "New page"
}
```

Preferred request when the agent already has content:

```json
{
  "title": "Meeting summary",
  "content": {
    "type": "doc",
    "content": [
      {
        "type": "paragraph",
        "content": [
          {"type": "text", "text": "Summary text."}
        ]
      }
    ]
  },
  "tags": ["meeting"],
  "metadata": {
    "created_by_agent": "Codex"
  }
}
```

Expected response: the created page object with page content.

## Search Objects

Use:

```text
GET /api/v1/objects?q=keyword&kind=page
```

Example:

```http
GET /api/v1/objects?q=embeddings&kind=page&page=1&limit=20 HTTP/1.1
Host: localhost:8000
Cookie: kos_session=...
User-Agent: KnowledgeOS-Agent/Codex
```

Expected response:

```json
{
  "items": [
    {
      "id": "uuid",
      "kind": "page",
      "title": "Embedding notes",
      "description": null,
      "tags": ["ai"],
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

If the agent needs exact page content, it should call `GET /api/v1/pages/{id}` for each relevant page after search.

## Create a Source (Phase 2 — Live)

```text
POST /api/v1/sources
```

Create a source from an uploaded asset:

```json
{
  "source_type": "pdf",
  "asset_id": "uuid",
  "title": "Uploaded paper"
}
```

Create a source from a URL:

```json
{
  "source_type": "web",
  "url": "https://example.com/article",
  "title": "Optional title"
}
```

Supported `source_type` values: `pdf`, `image`, `video`, `audio`, `youtube`, `web`, `csv`, `file`.

Behavior:
1. API creates a `source` object and `sources` row.
2. API enqueues an RQ ingestion job.
3. Worker extracts text/metadata; status progresses `pending → running → ready | error`.
4. Poll `GET /api/v1/sources/{id}` until `ingestion_status == "ready"` before reading `extracted_text`.

Agents must not simulate ingestion by writing rows or files directly.

## Search (Phase 3 — In Progress)

Once Phase 3 is complete, agents should use the search endpoints rather than listing all objects:

```text
GET /api/v1/search/keyword?q=embeddings&kind=page
POST /api/v1/search/vector  {"q": "semantic similarity", "limit": 10}
POST /api/v1/search/hybrid  {"q": "research notes", "kind": "source"}
```

**Offline-safe:** Keyword search works with no API keys. Vector and hybrid search return graceful errors (`503 embeddings_disabled`) when `OPENAI_API_KEY` is absent — agents should fall back to keyword search in that case.

**User scope:** All search results are scoped to the authenticated user. Agents cannot search across user accounts.

**Citation edges:** When an agent creates a page that references a source, it should create a `cites` edge:

```text
POST /api/v1/edges
{"source_id": "<page_id>", "target_id": "<source_id>", "kind": "cites"}
```

## Graph Lite

Agents should treat Postgres `edges` as the canonical graph and use API endpoints rather than direct DB writes.

Use:

```text
POST /api/v1/edges
GET /api/v1/objects/{id}/edges
GET /api/v1/objects/{id}/backlinks
GET /api/v1/objects/{id}/related
```

Preferred edge kinds are `links_to`, `cites`, `derives_from`, `mentions`, `supports`, `contradicts`, `related_to`, `summarizes`, `belongs_to_project`, `evidence_for`, and `created_from`.

Legacy kinds such as `link`, `related`, and `citation` may appear in older data, but new agent writes should use canonical kinds unless preserving existing semantics requires otherwise.

Do not create Kuzu records directly. Kuzu is a future derived graph index, not canonical storage.

## Updating Content Safely

When editing an existing page:

1. Read the page with `GET /api/v1/pages/{id}`.
2. Modify the Tiptap JSON minimally.
3. Preserve existing fields that are not part of the requested change.
4. Send `PATCH /api/v1/pages/{id}` for partial updates or `PUT /api/v1/pages/{id}` only when replacing the full page representation is intended.
5. Re-read the page if the task requires verification.

Agents should prefer additive edits, explicit citations, and metadata that makes their work inspectable.

## Deletes and Restores

Use soft delete endpoints only:

```text
DELETE /api/v1/objects/{id}
DELETE /api/v1/assets/{id}
```

Restore through:

```text
POST /api/v1/objects/{id}/restore
```

Do not remove rows from Postgres. Do not remove files from `~/KnowledgeOS/library` unless a future API endpoint explicitly supports permanent deletion.

## Scope Boundaries

Agents may work with:

```text
~/KnowledgeOS
http://localhost:8000/api/v1
```

Agents must not:

| Forbidden action | Reason |
| --- | --- |
| Write outside `~/KnowledgeOS` | Preserves local-first safety boundary |
| Execute shell commands | Prevents unreviewed system changes |
| Connect directly to Postgres | Bypasses validation, auth, and audit |
| Edit files behind the API's back | Desynchronizes database state and filesystem state |
| Hard-delete records | Breaks recovery and audit expectations |
