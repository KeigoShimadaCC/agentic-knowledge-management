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

## Create a Source in Phase 2

Source creation is coming in Phase 2. Expected endpoint:

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

Expected behavior:

1. API creates a `source` object.
2. API creates the `sources` specialization row.
3. API enqueues an RQ ingestion job.
4. Worker extracts text and metadata.
5. Source status changes from `pending` to `running` to `ready` or `error`.

Agents should not simulate source ingestion by writing files or database rows themselves.

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
