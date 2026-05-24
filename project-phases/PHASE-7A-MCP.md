# Phase 7A — MCP Read/Search + Safety Foundation

> **Status:** ✅ Complete (superseded by PHASE-7C stabilization sweep; see `PROGRESS.md` Phase 7A section for verification details)  
> **Branch:** `phase-7a-mcp` (merged)  
> **Depends on:** Phases 1–4 (all complete). Phase 5 AI endpoint NOT required (answer_from_kb deferred).

---

## Context

KnowledgeOS has a complete search, graph, and CRUD API. External agents (Claude Desktop, Claude Code, Cursor, Codex) cannot query it without a browser session. Phase 7A exposes a **safe local-only stdio MCP server** so agents can search and read the knowledge base — with no write tools, no shell execution, and no filesystem access beyond what the API already mediates.

Phase 5 AI Assistant is not yet implemented, so `answer_from_kb` is registered as a disabled stub with a clear error message.

---

## Goal

Implement a read-only local MCP server backed by the existing FastAPI API. Agents can search objects, read pages/sources/assets, and traverse the knowledge graph. No writes. No shell. No arbitrary filesystem access.

---

## Non-Goals

- Write tools (create_page, update_page, create_edge, archive_object, import_chat)
- Shell execution
- Arbitrary filesystem read
- Public HTTP binding
- Cloud auth or remote deployment
- Phase 6A chat import tools (already complete separately, but no MCP import tool)
- Phase 5 AI tools (answer_from_kb deferred until AI endpoint exists)
- Update/archive tools (requires object_revisions table from Phase 5)

---

## Definition of Done

- [x] `project-phases/PHASE-7A-MCP.md` created
- [x] `PROGRESS.md` updated with Phase 7A section
- [x] `services/mcp/` has working MCP server with stdio transport
- [x] FastAPI accepts `X-KOS-Internal-Token` header as alternative auth for MCP
- [x] MCP disabled by default (`MCP_ENABLED=false`)
- [x] Tool allowlist enforced at startup
- [x] No write tools registered (7A scope; write tools added in 7B behind `MCP_ALLOW_WRITE_TOOLS`)
- [x] No shell/file tools
- [x] `search_objects` works (calls keyword search API)
- [x] `hybrid_search` works (calls hybrid search API, falls back gracefully)
- [x] `get_object` works (returns compact metadata, no secrets)
- [x] `get_page` works (returns title + content_text, omits editor JSON by default)
- [x] `get_source` works (returns metadata + truncated extracted_text)
- [x] `get_related_objects` works (depth capped at 2)
- [x] `answer_from_kb` wired to live AI endpoint (the disabled-stub was replaced once Phase 5 shipped; see `PROGRESS.md`)
- [x] Secrets never in tool responses
- [x] MCP config tests pass
- [x] Tool unit tests pass (mocked API client)
- [x] Existing 85+ backend tests still pass
- [x] `docs/MCP_TOOLS.md` updated
- [x] `docs/SECURITY.md` updated
- [x] `docs/AGENT_GUIDE.md` updated
- [x] `infra/.env.example` updated with MCP_* vars

---

## MCP Architecture

```
External Agent (Claude Desktop / Claude Code / Cursor)
  │  stdio (stdin/stdout)
  ▼
kos_mcp.server  (MCP SDK Server, stdio transport)
  │
  ├── kos_mcp.config    (McpSettings, tool allowlist, safety flags)
  ├── kos_mcp.tools     (register_tools → per-tool async functions)
  ├── kos_mcp.client    (KosApiClient, httpx, X-KOS-Internal-Token)
  │    │
  │    ▼  HTTP to 127.0.0.1:8000
  │   FastAPI /api/v1/*
  │    │  (get_current_user: token path → first active user)
  │    ▼
  │   Postgres + Qdrant
  └── kos_mcp.redaction (strips secrets from all tool responses)
```

**stdio transport** — MCP server is a subprocess spawned by the agent client. No persistent HTTP server, no new exposed port. Compatible with Claude Desktop and Claude Code MCP config.

---

## Auth Strategy: X-KOS-Internal-Token

FastAPI's `get_current_user` is extended to accept a `X-KOS-Internal-Token` header as an alternative to the `kos_session` cookie. The token is validated with `secrets.compare_digest` (timing-safe), then the first non-deleted user is loaded. Cookie auth is unchanged.

- Token must be configured and non-empty on both sides to be active
- Empty token = auth path disabled (safe default)
- Limitation: maps to first user only (single-user local appliance)

---

## Tool Plan

| Tool | Backend endpoint | Phase 7A |
|------|-----------------|----------|
| `search_objects` | `GET /api/v1/search/keyword` | ✅ |
| `hybrid_search` | `POST /api/v1/search/hybrid` | ✅ |
| `get_object` | `GET /api/v1/objects/{id}` | ✅ |
| `get_page` | `GET /api/v1/pages/{id}` | ✅ |
| `get_source` | `GET /api/v1/sources/{id}` | ✅ |
| `get_related_objects` | `GET /api/v1/objects/{id}/related` | ✅ |
| `answer_from_kb` | Phase 5 (not yet built) | Disabled stub |
| create_page, update_page, create_edge, etc. | — | **Phase 7B** |

---

## Subtask Checklist

- [x] **Subtask 0** — Audit + plan files: create this doc, update PROGRESS.md
- [x] **Subtask 1** — MCP config + safety foundation: `McpSettings`, `redact_dict`, `pyproject.toml`, `.env.example`
- [x] **Subtask 2** — FastAPI internal token auth: `config.py` + `deps.py` + `test_mcp_auth.py`
- [x] **Subtask 3** — MCP API client: `client.py` (httpx, all 6 methods)
- [x] **Subtask 4** — MCP server scaffold: `server.py` + `tools.py` skeleton + tool registry
- [x] **Subtask 5** — Search tools: `search_objects`, `hybrid_search` (with 503 fallback)
- [x] **Subtask 6** — Object/page/source tools: `get_object`, `get_page`, `get_source` (with truncation + redaction)
- [x] **Subtask 7** — Graph tool + `answer_from_kb` (post-Phase-5 the stub was replaced with the live AI wiring): `get_related_objects` + real `answer_from_kb`
- [x] **Subtask 8** — Tests: `test_config.py`, `test_tools.py` (mocked client); current counts: 7 + 28 + 3 redaction + 21 project = 59 in `services/mcp/tests/`
- [x] **Subtask 9** — Docs: `MCP_TOOLS.md`, `SECURITY.md`, `AGENT_GUIDE.md`, `README.md`, PROGRESS.md complete

---

## Files to Create

| File | Purpose |
|------|---------|
| `services/mcp/kos_mcp/config.py` | McpSettings |
| `services/mcp/kos_mcp/client.py` | KosApiClient (httpx) |
| `services/mcp/kos_mcp/tools.py` | Tool functions + MCP registration |
| `services/mcp/kos_mcp/redaction.py` | Secret redaction |
| `services/mcp/kos_mcp/server.py` | stdio MCP server entry point |
| `services/mcp/tests/__init__.py` | — |
| `services/mcp/tests/conftest.py` | Mock client fixture |
| `services/mcp/tests/test_config.py` | Config/safety tests |
| `services/mcp/tests/test_tools.py` | Tool unit tests |
| `tests/api/test_mcp_auth.py` | FastAPI token auth integration tests |

## Files to Update

| File | Change |
|------|--------|
| `services/mcp/pyproject.toml` | Add mcp, httpx, pydantic-settings deps |
| `services/api/app/config.py` | Add `mcp_internal_token` field |
| `services/api/app/core/deps.py` | Add token auth path |
| `infra/.env.example` | Add MCP_* vars |
| `docs/MCP_TOOLS.md` | Full rewrite |
| `docs/SECURITY.md` | Add MCP section |
| `docs/AGENT_GUIDE.md` | Add MCP usage guidance |
| `README.md` | Add MCP setup pointer |
| `PROGRESS.md` | Add Phase 7A section |

---

## Commit Sequence

1. `docs: add Phase 7A MCP read-only plan`
2. `feat(mcp): add safety-first MCP configuration and redaction utility`
3. `feat(api): add internal MCP token auth for local service access`
4. `feat(mcp): add authenticated local API client`
5. `feat(mcp): add local read-only MCP server scaffold`
6. `feat(mcp): expose read-only search tools`
7. `feat(mcp): expose object page and source read tools`
8. `feat(mcp): expose graph related object tool; stub answer_from_kb`
9. `test: add MCP read-only tool and token auth coverage`
10. `docs: document Phase 7A MCP safety and read-only tools`

---

## Validation Commands

```bash
# MCP package tests
cd services/mcp && uv run pytest tests/ -v

# Backend integration tests (includes new token auth tests)
cd tests && uv run pytest api/ -v

# Frontend typecheck (no frontend changes)
pnpm -F web typecheck

# Smoke: MCP disabled by default
cd services/mcp && MCP_ENABLED=false uv run kos-mcp
# → "MCP server is disabled. Set MCP_ENABLED=true to enable."
```
