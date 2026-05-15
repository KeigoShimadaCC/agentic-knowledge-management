# MCP Tools — Phase 7A (Read/Search)

KnowledgeOS exposes a local stdio MCP server (`kos-mcp`) that gives AI agents (Claude Desktop, Claude Code, Cursor, Codex) safe read and search access to the knowledge base.

**Phase 7A: read/search tools only.** Write tools are planned for Phase 7B.

---

## Safety Model

| Property | Value |
|---|---|
| Transport | stdio (subprocess) — no open port |
| Enabled by default | No (`MCP_ENABLED=false`) |
| Write tools | None in Phase 7A |
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

### `answer_from_kb` (disabled stub)

**Status: UNAVAILABLE** — `POST /api/v1/ai/answer` is shipped, but MCP wiring is still pending. Calling this tool returns an error.

---

## Phase 7B — Write Tools (Planned)

Phase 7B is unblocked now that Phase 5 `object_revisions` ships. The implementation plan is [`project-phases/PHASE-7B-MCP-WRITE.md`](../project-phases/PHASE-7B-MCP-WRITE.md).

| Tool | Endpoint | Phase |
|---|---|---|
| `create_page` | `POST /api/v1/pages` | 7B |
| `update_page` | `PUT /api/v1/pages/{id}` | 7B |
| `create_edge` | `POST /api/v1/edges` | 7B |
| `archive_object` | `DELETE /api/v1/objects/{id}` | 7B |
| `import_chat` | `POST /api/v1/chats/import` | 7B |
| `ingest_url` | `POST /api/v1/sources` | 7B |
| `ingest_file` | `POST /api/v1/assets/upload?create_source=true` | 7B |

All Phase 7B write tools will validate agent identity, write `agent_runs` audit rows, and require `object_revisions` history.

---

## Recommended Agent Workflow

1. Start with `search_objects` or `hybrid_search` to discover relevant objects.
2. Use `get_object` for quick metadata checks.
3. Use `get_page` for full page content — prefer summary or first N chars if the page is long.
4. Use `get_source` with `include_text: true` for source content.
5. Use `get_related_objects` with `depth: 1` before going to `depth: 2`.

See `docs/AGENT_GUIDE.md` for detailed usage patterns.
