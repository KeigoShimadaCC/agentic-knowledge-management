# Phase 7B — MCP Write Tools

> **Status:** Planned  
> **Branch:** `phase-7b-mcp-write`  
> **Depends on:** Phase 7A MCP Read/Search, Phase 5 `object_revisions`, and `agent_runs` audit logging.

---

## Context

Phase 7A ships a local stdio MCP server with read/search tools only. Phase 5 is now also shipped: `object_revisions` exists, page and AI writes can create revision rows, and `agent_runs` records AI/agent actions. That unblocks a careful MCP write phase.

Phase 7B should add write tools without weakening the local-first safety model. Every write still goes through FastAPI service functions; MCP must not write directly to Postgres or the filesystem.

---

## Goal

Expose a small set of MCP write tools for trusted local agents:

- `create_page`
- `update_page`
- `create_edge`
- `archive_object`
- `ingest_url`
- `ingest_file`

All tools must validate agent identity, produce auditable database rows, preserve soft-delete semantics, and reject access outside `LIBRARY_ROOT`.

---

## Non-Goals

- Public or remote MCP transport.
- Arbitrary SQL, shell, or filesystem tools.
- Hard-delete tools.
- Bulk destructive actions.
- Workspace persistence or Phase 8 layout features.
- Autonomous background writes without explicit tool calls.

---

## Safety Constraints

- Write tools are disabled by default behind `MCP_ALLOW_WRITE_TOOLS=false`.
- Every successful write creates an `agent_runs` row and at least one `object_revisions` row for each modified object.
- Failed writes finish the `agent_runs` row with `status="error"` and a redacted error payload.
- Deletes are archive/soft-delete only.
- File-backed tools normalize and validate paths under `LIBRARY_ROOT`; any `..`, symlink escape, absolute outside path, or non-library target is rejected.
- Rate limits apply per agent identity and action. Start with conservative local limits in API/service code before considering persistent policy.
- Tool responses are redacted with the same policy as Phase 7A read tools.
- All writes use existing FastAPI endpoints or new FastAPI endpoints; MCP never mutates the database directly.

---

## Tool Plan

| Tool | FastAPI endpoint | Notes |
|---|---|---|
| `create_page` | `POST /api/v1/pages` | Create object + page row, revision `rev_num=1`, agent run linked. |
| `update_page` | `PATCH /api/v1/pages/{id}` | Preserve omitted fields, snapshot before/after, enqueue reindex. |
| `create_edge` | `POST /api/v1/edges` | Use existing idempotent edge service; revision/audit strategy should record graph mutation. |
| `archive_object` | `DELETE /api/v1/objects/{id}` | Soft-delete only. May need an explicit archive endpoint if semantics diverge from delete. |
| `ingest_url` | `POST /api/v1/sources` | `source_type=web|youtube`; URL safety validation stays in API and worker. |
| `ingest_file` | `POST /api/v1/assets/upload?create_source=true` | Accept only client-provided file content or validated library paths; never arbitrary host paths. |

---

## API Work Needed

- Add an explicit agent identity dependency for MCP write requests. The Phase 7A token currently maps to the first active user; write tools need a stable `agent_name`.
- Extend existing page/object/edge/source services to accept optional `agent_run_id` and `changed_by="agent:<name>"`.
- Confirm object revision snapshots cover page content, object metadata, soft-delete/restore changes, and graph mutations.
- Add `MCP_ALLOW_WRITE_TOOLS` config to both API and MCP packages; default false.
- Consider a dedicated `POST /api/v1/objects/{id}/archive` endpoint if `DELETE` is too ambiguous for an agent-facing archive tool.

---

## Subtask Checklist

- [ ] **Subtask 0** — Confirm API write audit invariants and update this plan if endpoint semantics change.
- [ ] **Subtask 1** — Add config flags: `MCP_ALLOW_WRITE_TOOLS`, conservative per-agent rate-limit settings.
- [ ] **Subtask 2** — Add MCP write client methods for pages, edges, archive, URL ingestion, and file ingestion.
- [ ] **Subtask 3** — Register tools only when both `MCP_ENABLED` and `MCP_ALLOW_WRITE_TOOLS` are true.
- [ ] **Subtask 4** — Implement `create_page` and `update_page` with revision assertions in tests.
- [ ] **Subtask 5** — Implement `create_edge` with idempotency and audit coverage.
- [ ] **Subtask 6** — Implement `archive_object` as soft-delete only.
- [ ] **Subtask 7** — Implement `ingest_url` and `ingest_file` with URL/path safety tests.
- [ ] **Subtask 8** — Add MCP unit tests, API integration tests, and redaction/error-path tests.
- [ ] **Subtask 9** — Update `docs/MCP_TOOLS.md`, `docs/SECURITY.md`, and `docs/AGENT_GUIDE.md`.

---

## Validation Commands

```bash
cd services/mcp && uv run pytest tests/ -v
cd tests && PYTHONPATH=../services/api uv run pytest api/test_mcp_auth.py api/test_pages.py api/test_edges.py api/test_sources.py -v
cd services/api && uv run ruff check .
```

Before enabling write tools by default in any environment, run the full API and MCP suites and manually inspect revision rows for one create, one update, one edge create, and one archive action.
