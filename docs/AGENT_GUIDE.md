# KnowledgeOS Agent Guide

This guide is for AI agents such as Claude, Codex, GPT, and local assistants operating against a KnowledgeOS instance. Agents must treat the API as the only supported write boundary.

## Operating Rules

Agents must follow these rules:

| Rule | Requirement |
| --- | --- |
| Use the API | All reads and writes should go through the FastAPI boundary. Host-side Docker Compose clients use `http://127.0.0.1:8001/api/v1`; native API runs commonly use `http://127.0.0.1:8000/api/v1`. |
| No direct DB writes | Do not connect to Postgres or mutate tables directly. |
| Soft-delete only | Delete through API endpoints that set `deleted_at`; never hard-delete records or files. |
| No shell execution | Do not run shell commands as part of normal KnowledgeOS operation. |
| Stay inside the library | Do not read or write files outside `~/KnowledgeOS`. |
| Identify yourself | Send a `User-Agent` header identifying the agent and version. |
| Preserve user intent | Do not overwrite page content, tags, metadata, or source links unless the user explicitly asked for that change. |

For chat histories, agents must use `/api/v1/chats/import` and related chat endpoints. Do not write transcript files directly into `~/KnowledgeOS/library/chats`; the API owns object creation, path layout, metadata, and reindex enqueueing.

For structured chat summaries, agents must use:

```text
POST /api/v1/chats/{id}/structured-summary
POST /api/v1/chats/{id}/structured-summary/apply
GET  /api/v1/chats/{id}/structured-summary
```

Do not directly mutate `chats.structured_summary` or create extracted claim/task objects by
hand. The API validates AI JSON, writes `agent_runs` and `object_revisions`, preserves turn
references, creates graph edges, and queues reindexing.

Recommended agent header:

```text
User-Agent: KnowledgeOS-Agent/Codex
```

Agents that perform multi-step tasks should also create or update audit records when that API surface is available. Until then, the `User-Agent` header and normal server logs are the minimum audit trail.

## MCP Server (Phase 7A — Recommended for AI Agents)

The MCP server is the preferred interface for AI agents (Claude Desktop, Claude Code, Cursor). It runs as a local stdio subprocess and provides typed, safe read/search tools.

### Quick start

See `docs/MCP_TOOLS.md` for full setup instructions. In brief:

1. Generate a random token and add to `infra/.env`: `MCP_INTERNAL_TOKEN=<token>`
2. Set `MCP_ENABLED=true`, `MCP_INTERNAL_TOKEN=<same-token>` in the MCP server env.
3. Run: `uv run --project services/mcp kos-mcp`
4. Register in your MCP client config (Claude Desktop, etc.)

### Available tools

| Tool | Purpose |
|---|---|
| `search_objects` | Keyword search — works offline, no embeddings needed |
| `hybrid_search` | Keyword + semantic search; falls back to keyword-only |
| `get_object` | Metadata for any object by ID |
| `get_page` | Page title + plain-text content (≤50k chars) |
| `get_source` | Source metadata + extracted text |
| `get_related_objects` | Graph traversal, depth 1–2 |

### Usage patterns

- **Discovery first**: always run `search_objects` or `hybrid_search` to find relevant objects before fetching full content.
- **Follow up with get_***: search returns compact summaries with IDs; call `get_page` or `get_source` for full content.
- **Graph traversal**: use `get_related_objects` at `depth: 1` before `depth: 2` to avoid over-fetching.
- **Write tools require `MCP_ALLOW_WRITE_TOOLS=true`** in the server's environment. They are disabled by default.
- **Read then write**: always call `get_object` or `get_page` before calling `update_page` so you have the current `version` for optimistic locking.
- **Idempotency**: `archive_object` is idempotent — calling it twice on the same object returns the already-archived state without creating a duplicate audit row.
- **Rate limits**: write tools are capped at 60 calls/minute and 600 calls/hour per agent identity. If you hit the limit, back off and retry — the error text includes the retry window in seconds.

### Write tool selection guide

| Goal | Tool |
|---|---|
| Capture a new idea or note | `create_page` |
| Update a page you just read | `update_page` with `expected_version` from `get_page` |
| Link two objects | `create_edge` with an appropriate `kind` |
| Remove an object from view | `archive_object` (reversible) |
| Ingest a URL for later analysis | `ingest_url` — creates a `Source` object in `pending` state |
| Ingest a local file | `ingest_file` — path must be under `LIBRARY_ROOT` |

### What MCP tools will never do

- Execute shell commands
- Access files outside `~/KnowledgeOS`
- Return `api_key`, `password`, session secrets, or token hashes
- Hard-delete data (archive = soft-hide, not delete)

---

## Authentication

KnowledgeOS uses an httponly `kos_session` cookie. Browser-based agents inherit the browser session. HTTP clients must log in through `POST /api/v1/auth/login` or register through `POST /api/v1/auth/register`, then preserve the returned cookie for subsequent requests.

For the MCP server, use the `X-KOS-Internal-Token` header instead of a cookie. See `docs/SECURITY.md` for the token auth design.

Never ask the user for raw database credentials when the API can perform the task.

## Read a Page

Use:

```text
GET /api/v1/pages/{id}
```

Example:

```http
GET /api/v1/pages/8b7b8b2a-0000-4000-9000-000000000001 HTTP/1.1
Host: 127.0.0.1:8001
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
Host: 127.0.0.1:8001
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

## Search (Phase 3 — Live)

Agents should use the search endpoints rather than listing all objects:

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

## Career Module

Career memory is project-centered. Agents should work through the API and leave generated artifacts previewable and auditable.

End-to-end flow:

1. Search for source material with `POST /api/v1/search/hybrid` or `GET /api/v1/search/keyword` using terms from the user's project, role, or employer.
2. Extract a project record from a page, source, or chat with `POST /api/v1/ai/extract-project` and `create: true`.
3. Generate resume bullets with `POST /api/v1/ai/generate-resume-bullets`; this returns a preview only and does not write artifacts.
4. Let the frontend save approved bullets with `POST /api/v1/projects/{project_id}/resume-bullet-sets`.
5. Generate interview prep with `POST /api/v1/ai/generate-interview-story`; save approved STAR stories with `POST /api/v1/projects/{project_id}/interview-stories`.

Evidence should be linked with `belongs_to_project` edges from pages, sources, chats, or claims to the project. Saved bullets and stories are first-class objects and cite their evidence with `cites` edges.

## Workspace Lite State

`WorkspaceLiteProvider` manages which object is shown in the side pane. This state is local React UI state — it is **not** persisted to Postgres, Redis, or any API. Do not:

- Add a `workspaces` table or API endpoint in the `phase8a-workspace-lite` branch.
- Store side-pane state in the URL or localStorage.
- Attempt to restore the side pane from a previous session.

Workspace persistence belongs to Phase 8 proper. The provider is isolated in `components/workspace/` so its internals can be swapped without breaking consumers.

## Scope Boundaries

Agents may work with:

```text
~/KnowledgeOS
http://127.0.0.1:8001/api/v1
```

Agents must not:

| Forbidden action | Reason |
| --- | --- |
| Write outside `~/KnowledgeOS` | Preserves local-first safety boundary |
| Execute shell commands | Prevents unreviewed system changes |
| Connect directly to Postgres | Bypasses validation, auth, and audit |
| Edit files behind the API's back | Desynchronizes database state and filesystem state |
| Hard-delete records | Breaks recovery and audit expectations |
