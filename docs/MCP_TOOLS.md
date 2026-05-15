# MCP Tools — Phases 7A + 7B

KnowledgeOS exposes a local stdio MCP server (`kos-mcp`) that gives AI agents (Claude Desktop, Claude Code, Cursor, Codex) safe read/search access and optional audited write access to the knowledge base.

---

## Safety Model

| Property | Value |
|---|---|
| Transport | stdio (subprocess) — no open port |
| Enabled by default | No (`MCP_ENABLED=false`) |
| Write tools | 6 (gated by `MCP_ALLOW_WRITE_TOOLS=true`) |
| Shell execution | Never |
| Filesystem access | Never (outside of LIBRARY_ROOT paths returned in metadata) |
| Secret fields | Redacted in all tool responses |
| Token auth | `X-KOS-Internal-Token` header, timing-safe compare, empty = disabled |

Invariants enforced in code, not just config:
- Write tools are never registered regardless of config flags.
- Tools not in `MCP_ALLOWED_TOOLS` are not registered at startup.
- `redact_dict()` is applied to every tool response.

---

## Setup

### 1. Generate a token

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Set env vars in `infra/.env`

```dotenv
MCP_INTERNAL_TOKEN=<your-random-token>
```

### 3. Set env vars for the MCP server (can be in shell profile or `.env` in `services/mcp/`)

```dotenv
MCP_ENABLED=true
MCP_API_BASE_URL=http://127.0.0.1:8001
MCP_INTERNAL_TOKEN=<same-token-as-above>
```

`127.0.0.1:8001` is the host-side default for Docker Compose (`8001 -> api:8000`). If you run the API natively with `uvicorn --port 8000`, point `MCP_API_BASE_URL` at `http://127.0.0.1:8000`. If a future MCP process runs inside the Docker network, use `http://api:8000`.

### 4. Start the API

```bash
docker compose -f infra/docker-compose.yml up -d
```

### 5. Run the MCP server

```bash
uv run --project services/mcp kos-mcp
```

### 6. Configure Claude Desktop / Claude Code

Add to your MCP client config (e.g., `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "knowledgeos": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/agentic-knowledge-management/services/mcp", "kos-mcp"],
      "env": {
        "MCP_ENABLED": "true",
        "MCP_API_BASE_URL": "http://127.0.0.1:8001",
        "MCP_INTERNAL_TOKEN": "<your-token>"
      }
    }
  }
}
```

---

## Available Tools

### `search_objects`

Keyword search across all KnowledgeOS objects (pages, sources, assets, chats).

**Input:**
| Field | Type | Required | Default |
|---|---|---|---|
| `query` | string | yes | — |
| `kind` | string | no | all kinds |
| `limit` | integer | no | 10 |

**Output:** list of `{id, kind, title, snippet, tags, updated_at, score, embeddings_used: false}`

---

### `hybrid_search`

Combined keyword + semantic vector search. Falls back to keyword-only when embeddings are unavailable.

**Input:**
| Field | Type | Required | Default |
|---|---|---|---|
| `query` | string | yes | — |
| `kind` | string | no | all kinds |
| `limit` | integer | no | 10 |

**Output:** `{results: [...], embeddings_used: bool, warning?: string}`

---

### `get_object`

Fetch metadata for any object by ID.

**Input:**
| Field | Type | Required |
|---|---|---|
| `object_id` | UUID string | yes |

**Output:** `{id, kind, title, description, tags, metadata, is_pinned, is_archived, created_at, updated_at}`

---

### `get_page`

Fetch a page with its plain-text content.

**Input:**
| Field | Type | Required | Default |
|---|---|---|---|
| `page_id` | UUID string | yes | — |
| `include_json` | boolean | no | false |

**Output:** `{id, title, content_text (≤50k chars), truncated, word_count, version, tags, metadata, created_at, updated_at}`

Content is truncated at 50,000 characters with `truncated: true` flag. Pass `include_json: true` to include the full Tiptap editor JSON (large).

---

### `get_source`

Fetch a source (PDF, YouTube, web, CSV, etc.) with optional extracted text.

**Input:**
| Field | Type | Required | Default |
|---|---|---|---|
| `source_id` | UUID string | yes | — |
| `include_text` | boolean | no | true |
| `max_chars` | integer | no | 12000 |

**Output:** `{id, kind, title, description, tags, source_type, url, ingestion_status, page_count, thumbnail_path, preview_data, created_at, updated_at, extracted_text?, text_truncated?}`

Raw files are never streamed. Local file paths are not exposed.

---

### `get_related_objects`

Traverse the knowledge graph from a given object.

**Input:**
| Field | Type | Required | Default |
|---|---|---|---|
| `object_id` | UUID string | yes | — |
| `depth` | integer | no | 1 (max 2) |
| `limit` | integer | no | 20 (max 50) |
| `direction` | "both" \| "outgoing" \| "incoming" | no | "both" |
| `edge_types` | string[] | no | all types |

**Output:** list of `{id, kind, title, direction, edge_kind, depth}`

---

### `answer_from_kb`

Search the knowledge base and answer a question with citations, using hybrid retrieval + LLM reasoning.

**Input:**
| Field | Type | Required | Default |
|---|---|---|---|
| `question` | string | yes | — |
| `kind` | string | no | all kinds |
| `limit` | integer | no | 10 (max 20) |

**Output (AI enabled):** `{answer: string, citations: string[], context_count: int, agent_run_id: string}`

**Output (AI disabled):** `{error: "ai_disabled", message: "Server has no OPENAI_API_KEY configured."}`

Delegates to `POST /api/v1/ai/answer`. Requires `OPENAI_API_KEY` on the API server. Returns a structured error object (not an exception) when AI is unavailable. Read-only — no writes, no Phase 7B scope.

---

## Phase 7B — Write Tools

Enable by setting `MCP_ALLOW_WRITE_TOOLS=true` in `infra/.env`. All write tools are rate-limited and audited.

| Tool | Endpoint | Rate-limited | Audit row | Revision row |
|---|---|---|---|---|
| `create_page` | `POST /api/v1/pages` | Yes | Yes | No |
| `update_page` | `PATCH /api/v1/pages/{id}` | Yes | Yes | Yes |
| `create_edge` | `POST /api/v1/edges` | Yes | Yes | No |
| `archive_object` | `POST /api/v1/objects/{id}/archive` | Yes | Yes | Yes |
| `ingest_url` | `POST /api/v1/sources` | Yes | Yes | No |
| `ingest_file` | `POST /api/v1/sources` (file-backed) | Yes | Yes | No |

### `create_page`

Create a new page in the knowledge base.

**Input:**
```json
{
  "title": "string (required)",
  "content_text": "string (optional)",
  "tags": ["string"] 
}
```

**Output:** `{id, kind, title, tags, created_at, updated_at}`

**Errors:** 400 if title is empty.

---

### `update_page`

Update title, content, or tags of an existing page.

**Input:**
```json
{
  "page_id": "uuid",
  "title": "string (optional)",
  "content_text": "string (optional)",
  "tags": ["string"],
  "expected_version": 3
}
```

`expected_version` is optional but strongly recommended — if the page has been modified since you read it, the server returns **409 Conflict**.

**Output:** `{id, version, word_count, updated_at, ...}`

**Errors:** 404 not found; 409 version conflict.

---

### `create_edge`

Link two objects with a typed relationship.

**Input:**
```json
{
  "source_id": "uuid",
  "target_id": "uuid",
  "kind": "related_to",
  "weight": 1.0,
  "metadata": {}
}
```

Valid `kind` values: `links_to`, `cites`, `derives_from`, `mentions`, `supports`, `contradicts`, `related_to`, `summarizes`, `belongs_to_project`, `evidence_for`, `created_from`.

**Output:** `{id, source_id, target_id, kind, weight, created_at}`

**Errors:** 400 if kind is invalid.

---

### `archive_object`

Soft-archive an object (sets `is_archived=true`). Idempotent — calling twice is a no-op.

**Input:**
```json
{
  "object_id": "uuid",
  "reason": "string (optional)"
}
```

**Output:** `{id, title, is_archived: true, ...}`

**Note:** Archived objects are hidden from default searches but not deleted. Use `GET /api/v1/objects?include_archived=true` to find them.

---

### `ingest_url`

Ingest a URL as a new source object (starts background extraction).

**Input:**
```json
{
  "url": "https://example.com/article",
  "source_type": "web",
  "title": "string (optional)",
  "tags": ["string"]
}
```

`source_type` must be `"web"` or `"youtube"`.

**URL safety rules (enforced in MCP layer before API call):**
- Scheme must be `https://` or `http://` (no `file://`, `ftp://`, etc.)
- Host must not be `localhost`, `127.0.0.1`, `0.0.0.0`, or any loopback/link-local IP

**Output:** `{id, url, ingestion_status: "pending", ...}`

---

### `ingest_file`

Ingest a file from the local library as a new source object.

**Input:**
```json
{
  "file_path": "/Users/you/KnowledgeOS/library/papers/paper.pdf",
  "source_type": "pdf",
  "title": "string (optional)",
  "tags": ["string"]
}
```

**Path safety rules (enforced in MCP layer):**
- Path must resolve under `LIBRARY_ROOT` (symlinks checked for escape)
- File must exist and be readable

**Output:** `{id, source_type, ingestion_status: "pending", ...}`

---

### Audit trail

Every write tool call creates an `agent_runs` row recording:
- `agent_type`: the value of `X-KOS-Agent-Id` header (or hash of token)
- `tool_name`: which write tool was invoked
- `input_payload`: a summary of the call (secrets and full content stripped)
- `status`: `success` or `failed`
- `created_at` / `completed_at`

Mutating tools (`update_page`, `archive_object`) additionally create an `object_revisions` row with `before_snapshot` and `after_snapshot` of the object state, linked to the `agent_runs` row.

---

### Rate limits

Both rate limit windows use a Redis sliding-window counter keyed by `X-KOS-Agent-Id` (or hash of internal token for unidentified callers):

| Bucket | Default | Env var |
|--------|---------|---------|
| Per minute | 60 | `MCP_RATE_LIMIT_PER_MINUTE` |
| Per hour | 600 | `MCP_RATE_LIMIT_PER_HOUR` |

When either limit is exceeded the tool returns an error text and no database writes occur.

---

## Recommended Agent Workflow

1. Start with `search_objects` or `hybrid_search` to discover relevant objects.
2. Use `get_object` for quick metadata checks.
3. Use `get_page` for full page content — prefer summary or first N chars if the page is long.
4. Use `get_source` with `include_text: true` for source content.
5. Use `get_related_objects` with `depth: 1` before going to `depth: 2`.

See `docs/AGENT_GUIDE.md` for detailed usage patterns.

---

## Career / Project Tools (Phase 9D)

Career tools expose the Phase 9 project memory system to agents. Read tools are always available; write tools require `MCP_ALLOW_WRITE_TOOLS=true`.

### Read tools

| Tool | Description |
|---|---|
| `get_project` | Fetch a project by UUID. Returns title, role, org, period, status, skills, STAR narrative fields, metrics. |
| `list_projects` | List projects. Optional filters: `status` (active/paused/completed/archived), `skill` (case-insensitive), `limit`, `offset`. |
| `get_resume_bullet_set` | Fetch a saved resume bullet set. Returns bullets with confidence, evidence links, metrics cited. |
| `list_resume_bullet_sets` | List saved bullet sets for a project. |
| `get_interview_story` | Fetch a saved STAR interview story. Returns full situation/task/action/result structure. |
| `list_interview_stories` | List saved stories for a project. Optional filter: `question_type`. |
| `get_project_evidence` | List objects linked to a project via `belongs_to_project` edges. |

### Write tools (gated by `MCP_ALLOW_WRITE_TOOLS=true`)

| Tool | Description |
|---|---|
| `create_project` | Create a new project. Required: `title`. Optional: role, org, period dates, STAR fields, metrics, skills, status, tags. |
| `update_project` | Update any field of an existing project. Required: `project_id`. |
| `archive_project` | Archive a project (`is_archived=true`). Reversible. Optional: `reason`. |
| `link_to_project` | Create a `belongs_to_project` edge from an evidence object to a project. Idempotent. |
| `unlink_from_project` | Delete a `belongs_to_project` edge by edge UUID. |
| `extract_project` | Use AI to extract a project from a source/page/chat and create it. Returns `project_id`. 503 if AI disabled. |
| `generate_and_save_resume_bullets` | Generate bullets via AI and save as a `resume_bullet_set` object. Returns the saved set + bullets. 503 → error dict (no save occurs). |
| `generate_and_save_interview_story` | Generate a STAR story via AI and save as an `interview_story` object. Returns the saved story. 503 → error dict. |

### Rate limits

Career write tools share the same sliding-window rate limit as all write tools (60/min, 600/hour per agent identity). The `generate_and_save_*` tools count as one write against the limiter even though they make two API calls internally.

### AI-disabled degradation

When `OPENAI_API_KEY` is not configured on the server, `extract_project`, `generate_and_save_resume_bullets`, and `generate_and_save_interview_story` return:

```json
{"error": "ai_disabled", "message": "Server has no OPENAI_API_KEY configured."}
```

All other career tools (CRUD, link/unlink, list/get) work regardless of AI availability.
