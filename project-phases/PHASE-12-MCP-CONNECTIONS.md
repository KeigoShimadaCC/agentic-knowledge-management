# Phase 12 — MCP Connections (App as MCP Consumer)

> **Status:** Planned
> **Sub-phases:** 12A (Registry), 12B (Ingest Bridge), 12C (AI Augmentation)
> **Depends on:** Phases 7A + 7B complete (MCP outbound server live on `main`). Phase 5 AI endpoints live.
> **Blocks:** nothing (standalone capability expansion)
> **Parallel-safe with:** Phase 11A, 11B, 11C (no shared files)

---

## 0. Prior Assessment

> This section records the research and reasoning from the design conversation on 2026-05-16.
> Keep it here so future agents can understand why these decisions were made.

### 0.1 The two directions of MCP

KnowledgeOS already has an **outbound MCP server** (Phases 7A + 7B): external agents — Claude Desktop,
Claude Code, Cursor, Codex — connect to `kos-mcp` via stdio and call its read/write tools to operate
the knowledge base.

Phase 12 adds the **inbound direction**: KnowledgeOS itself becomes an MCP *client* that connects to
external MCP servers and consumes their tools. Data pulled from those MCPs lands in the KB as proper
`KosObject` records (pages, sources). Capabilities from those MCPs can augment KnowledgeOS's own AI
features (KB Q&A, page enrichment).

The key insight is that this is architecturally symmetric to the existing MCP server but in reverse:
instead of exposing tools, we call them.

### 0.2 Current app capabilities (as of 2026-05-16 audit)

| Area | Status |
|---|---|
| Pages, Sources, Assets, Chats, Projects | Complete (Phases 1–9) |
| Keyword + vector + hybrid search | Complete (Phase 3 + Hardening) |
| 11 typed graph edge kinds | Complete (Phase 4) |
| AI: summarize, extract, suggest-links, KB Q&A, inbox, career AI | Complete (Phases 5, 6B, 9) |
| Multi-pane workspaces | Complete (Phases 8A–8C) |
| MCP outbound (21 tools, stdio, rate-limited, audited) | Complete (Phases 7A, 7B, 9D) |
| Background RQ workers (ingestion, reindex, embedding) | Complete (Phase 2+) |
| ~256 tests (frontend + API + worker + MCP + E2E) | Complete (Enhance-02) |

The app is mature. MCP Connections is a capability expansion, not a foundation repair.

### 0.3 Candidate external MCPs evaluated

The following MCPs were evaluated for fit with this app's use cases:

| MCP | Primary value | Integration point | Priority |
|---|---|---|---|
| **Brave Search / Exa** | Live web search when KB has no match | Augment `answer_from_kb` fallback | High |
| **GitHub** | Issues, PRs, discussions → Sources/Projects | Ingest bridge + project extraction AI | High |
| **Context7** | Real-time library docs for code/framework pages | Page citation enrichment | High |
| **Filesystem watcher** | Auto-ingest files dropped into a folder | Trigger `ingest_file` worker job | Medium |
| **Google Drive / Notion** | Private docs from other knowledge systems | Ingest bridge (auth-gated) | Medium |
| **Gmail / Calendar** | Meeting notes, emails → Sources | Ingest bridge; useful with career memory | Medium |
| **Slack / Discord** | Conversation threads → Chats | Chat importer already handles structure | Lower |

**Highest leverage right now:** Brave/Exa (augments existing AI Q&A without new objects), GitHub (complements
Phase 9 project memory), Context7 (immediate value for developer use cases).

### 0.4 Implementation approach selected: on-demand client

Three approaches were considered:

**Option A — Persistent client pool:** A long-running async pool keeps connections to all enabled MCPs
alive. Pro: low latency per call. Con: process supervision complexity, crash isolation hard, Docker
container restarts kill all connections, overkill for a personal local app.

**Option B — HTTP/SSE relay service:** A new microservice proxies MCP calls over HTTP. Pro: clean
separation. Con: a new service to maintain, another Dockerfile, more Docker Compose complexity.

**Option C — On-demand client (selected):** When the user or an AI action triggers an MCP call,
the worker spawns the MCP client process, calls the tool(s), collects results, and terminates. No
persistent daemon, no pool to supervise. Pro: simple, crash-isolated, matches existing RQ worker
pattern. Con: ~1–2s spawn latency per call (acceptable for an ingest action; not for real-time typeahead).

**Decision: Option C.** The app's ingest and AI augmentation flows are already asynchronous (RQ jobs,
500ms AI response times). A spawn-call-kill model fits naturally.

### 0.5 Difficulty breakdown

| Layer | Effort | Notes |
|---|---|---|
| `mcp_connections` table + CRUD API | Low (3–4 days) | Standard pattern, same as workspaces/projects |
| Env var encryption at rest | Low (1 day) | Fernet symmetric encryption in API layer |
| Test-connection endpoint | Low (1 day) | Spawn process, call `tools/list`, cache result |
| On-demand `McpClientSession` class | Medium (2–3 days) | Async subprocess + MCP SDK client |
| Generic ingest adapter | Medium (2 days) | Map tool output → KosObject fields |
| Per-MCP typed adapters (GitHub, Brave, Context7) | Medium (1–2 days each) | Schema-specific mapping |
| `ingest_from_mcp` RQ worker job | Low (1 day) | Follows existing `ingest_source` pattern |
| Frontend "From MCP" tab in CreateSourceModal | Low (1–2 days) | Connection picker + tool picker + preview |
| `/app/settings/mcp` admin page | Low (1–2 days) | CRUD + test button |
| AI augmentation (`answer_from_kb` web fallback) | Medium (2–3 days) | Score threshold + MCP call + merge |
| Context7 page enrichment endpoint | Medium (2 days) | New `/ai/enrich-page` endpoint + frontend |

Total estimate: **4–5 weeks** across all three sub-phases for a single developer. Safe to parallelize
12A backend with 12B frontend adapter work once the API shape is stable.

Key risk: **secret handling**. External MCPs need API keys (GitHub token, Brave API key, etc.). These
must be stored encrypted and injected as env vars into spawned processes. They must never appear in
MCP tool responses, API responses, or logs. `redact_dict()` from the existing MCP server applies here.

---

## 1. Goal

Enable KnowledgeOS to connect to external MCP servers (stdio or SSE) as a consumer, pulling data into
the knowledge base and optionally using external MCP capabilities to augment built-in AI features.

**Phase 12A:** MCP connection registry. Users can register, test, and manage external MCP connections.
**Phase 12B:** On-demand ingest bridge. Registered MCPs can be used to pull data into the KB as KosObjects.
**Phase 12C:** AI augmentation. Enabled MCPs (web search, Context7) enhance `answer_from_kb` and introduce
a new `enrich-page` endpoint.

---

## 2. Non-Goals

- Real-time or push-based sync from external MCPs (Phase 12 uses on-demand pull only)
- Persistent MCP connection pool (on-demand spawn-call-kill is sufficient)
- Multi-user MCP sharing (connections are per-user in this single-user app context)
- OAuth/cloud auth flows for MCPs that require browser-based login (basic env var API keys only)
- MCP-to-MCP chaining (KnowledgeOS calling an external MCP that calls another MCP)
- Modifying the outbound KOS MCP server (already complete in Phases 7A/7B/9D)

---

## 3. Architecture

### 3.1 Overall flow

```
User / AI trigger
        │
        ▼
FastAPI  POST /api/v1/mcp-connections/{id}/ingest
        │
        ▼  enqueue RQ job
Redis Queue
        │
        ▼
kos_worker.tasks.mcp_ingest_job(connection_id, tool_name, tool_args)
        │
        ▼  spawn subprocess / connect SSE
McpClientSession (services/api/app/mcp_client/client.py)
        │  calls tools/list, then call_tool
        ▼
External MCP server process (e.g. uvx mcp-server-brave-search)
        │  returns tool result dict
        ▼
McpToolAdapter (services/api/app/mcp_client/adapters.py)
        │  maps result → PageCreateIn or SourceCreateIn
        ▼
page_service.create() / source_service.create()
        │
        ▼
KosObject in Postgres + reindex enqueued
```

### 3.2 AI augmentation flow (Phase 12C)

```
POST /api/v1/ai/answer  { question, use_web_search: true }
        │
        ▼
Hybrid KB search (existing)
        │  if top_score < threshold (0.5)
        ▼
McpClientSession → web search MCP (Brave/Exa) → results
        │
        ▼
Merge KB results + web results → LLM context pack
        │
        ▼
Answer with KB citations + web citations
```

### 3.3 File layout (new files only)

```
services/api/app/
  mcp_client/
    __init__.py
    client.py           ← McpClientSession (spawn + call + close)
    adapters.py         ← McpToolAdapter protocol + GenericAdapter + typed adapters
    crypto.py           ← Fernet encrypt/decrypt for env_vars column
  models/
    mcp_connection.py   ← SQLAlchemy ORM model (new)
  schemas/
    mcp_connection.py   ← Pydantic schemas (new)
  services/
    mcp_connection_service.py  ← CRUD + test_connection + decrypt_env_vars
  api/v1/
    mcp_connections.py  ← REST router (new)

services/worker/tasks/
    mcp_ingest.py       ← ingest_from_mcp RQ job (new)

alembic/versions/
    0011_mcp_connections.py  ← migration (new)

apps/web/src/
  app/(app)/app/settings/mcp/page.tsx  ← connection registry UI (new)
  components/mcp/
    McpConnectionCard.tsx
    CreateMcpConnectionModal.tsx
    McpToolBrowser.tsx            ← picker for test-connection results
  components/sources/
    CreateSourceModal.tsx          ← add "From MCP" tab (edit existing)
  lib/api.ts                       ← add mcp-connections API functions (append)
```

---

## 4. Phase 12A — MCP Connections Registry (Backend)

**Scope:** DB schema, ORM, service, REST API, env var encryption, test-connection endpoint, tests, docs.
No frontend. No worker jobs. No actual MCP spawning yet (test-connection is the only spawn).

### 4.1 DB schema — Migration 0011

```sql
CREATE TABLE mcp_connections (
  id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID         NOT NULL REFERENCES users(id),
  name          TEXT         NOT NULL,         -- display name, e.g. "Brave Search"
  transport     TEXT         NOT NULL          -- 'stdio' | 'sse'
                             CHECK (transport IN ('stdio', 'sse')),
  command       TEXT,                          -- stdio: executable, e.g. "uvx"
  args          JSONB        NOT NULL DEFAULT '[]',  -- stdio: arg array
  url           TEXT,                          -- SSE: endpoint URL
  env_vars      JSONB        NOT NULL DEFAULT '{}',  -- Fernet-encrypted values at app layer
  capabilities  JSONB,                         -- cached [{name, description, inputSchema}] from last test
  enabled       BOOLEAN      NOT NULL DEFAULT true,
  last_tested_at TIMESTAMPTZ,
  last_error    TEXT,
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
  deleted_at    TIMESTAMPTZ                    -- soft-delete
);

CREATE INDEX ix_mcp_connections_user_id ON mcp_connections (user_id)
  WHERE deleted_at IS NULL;
```

**Constraint:** `command` must be non-null when `transport = 'stdio'`; `url` must be non-null when
`transport = 'sse'`. Enforced at service layer (not DB check to keep migration simple).

### 4.2 Env var encryption

External MCP API keys (GitHub token, Brave API key) must never be stored in plaintext. Approach:

- Add `MCP_ENV_ENCRYPTION_KEY` to `infra/.env` (32-byte Fernet key, generated at setup).
- `services/api/app/mcp_client/crypto.py` provides `encrypt_env_vars(dict) -> dict` and
  `decrypt_env_vars(dict) -> dict`. Only values are encrypted; keys are plaintext.
- The service encrypts on write, decrypts in memory just before spawning the subprocess.
- Encrypted values are never returned in API responses — `redact_dict()` is applied to all
  `/mcp-connections` GET responses to mask `env_vars` values.
- If `MCP_ENV_ENCRYPTION_KEY` is absent, env var storage is disabled (connection creation returns 400).

### 4.3 REST API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/mcp-connections` | List user's connections (soft-deleted excluded) |
| `POST` | `/api/v1/mcp-connections` | Create connection (encrypts env_vars) |
| `GET` | `/api/v1/mcp-connections/{id}` | Get one (env_vars values redacted) |
| `PATCH` | `/api/v1/mcp-connections/{id}` | Update (re-encrypt env_vars if changed) |
| `DELETE` | `/api/v1/mcp-connections/{id}` | Soft-delete (set deleted_at) |
| `POST` | `/api/v1/mcp-connections/{id}/test` | Spawn MCP, call `tools/list`, cache `capabilities` |

The `/test` endpoint spawns the MCP subprocess with a 10-second timeout. If successful, writes
`capabilities` and `last_tested_at`. If it fails, writes `last_error` and returns 422 with the error.

### 4.4 Pydantic schemas

```python
# schemas/mcp_connection.py

class McpConnectionTransport(str, Enum):
    stdio = "stdio"
    sse = "sse"

class McpConnectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    transport: McpConnectionTransport
    command: str | None = None          # required for stdio
    args: list[str] = []
    url: str | None = None              # required for sse
    env_vars: dict[str, str] = {}       # plaintext on input, encrypted on write
    enabled: bool = True

class McpConnectionUpdate(BaseModel):
    name: str | None = None
    command: str | None = None
    args: list[str] | None = None
    url: str | None = None
    env_vars: dict[str, str] | None = None
    enabled: bool | None = None

class McpToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: dict = {}

class McpConnectionOut(BaseModel):
    id: UUID
    name: str
    transport: McpConnectionTransport
    command: str | None
    args: list[str]
    url: str | None
    env_vars: dict[str, str]    # values redacted to "*****" before returning
    capabilities: list[McpToolDefinition] | None
    enabled: bool
    last_tested_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime

class McpConnectionTestResult(BaseModel):
    ok: bool
    tools: list[McpToolDefinition]
    error: str | None = None
```

### 4.5 Subtasks — Phase 12A

- [ ] **12A-0** — Audit + plan file (this doc). PROGRESS.md Phase 12 section added.
- [ ] **12A-1** — `mcp_client/crypto.py`: Fernet encrypt/decrypt; unit-tested (4 tests: roundtrip, missing key raises, empty dict, values-only encryption).
- [ ] **12A-2** — Migration 0011: `mcp_connections` table + index. `alembic upgrade head` clean.
- [ ] **12A-3** — ORM model `models/mcp_connection.py` + import in `models/__init__.py`.
- [ ] **12A-4** — Pydantic schemas `schemas/mcp_connection.py` (all types above).
- [ ] **12A-5** — Service `services/mcp_connection_service.py`: list, get, create (encrypt), update (re-encrypt), soft-delete, cache-capabilities helper. Ownership checks on get/update/delete.
- [ ] **12A-6** — REST router `api/v1/mcp_connections.py` + registration in `api/v1/__init__.py`. Redact env_vars on all GET responses.
- [ ] **12A-7** — Test-connection endpoint: spawn subprocess via `asyncio.create_subprocess_exec`, send MCP `initialize` + `tools/list` over stdio, parse JSON-RPC responses, return tool list, handle timeout. Stub via `mcp` SDK client if available.
- [ ] **12A-8** — Integration tests `tests/api/test_mcp_connections.py` (12+ cases):
  - Create stdio connection → 201, env_vars encrypted in DB
  - Create SSE connection → 201
  - Create with missing command (stdio) → 400
  - Get connection → env_vars values redacted in response
  - Update connection → 200
  - Soft-delete → 204, excluded from list
  - Test-connection (mock subprocess) → 200, capabilities cached
  - Test-connection timeout → 422 with error
  - Ownership check: other user cannot get/update/delete → 404
  - Encryption key absent → create returns 400
- [ ] **12A-9** — Docs: `docs/MCP_TOOLS.md` new "External MCP Connections" section; `docs/SECURITY.md` env var encryption section; `infra/.env.example` adds `MCP_ENV_ENCRYPTION_KEY`; PROGRESS.md 12A complete.

---

## 5. Phase 12B — On-Demand Ingest Bridge

**Scope:** `McpClientSession` client class, tool-output adapters, `ingest_from_mcp` RQ job, two new API
endpoints (call + ingest), and the frontend "From MCP" tab.

**Depends on:** Phase 12A complete.

### 5.1 McpClientSession

```python
# mcp_client/client.py

class McpClientSession:
    """
    Context manager that spawns a stdio MCP server process (or connects to SSE),
    negotiates the MCP handshake, and provides tool_list / call_tool methods.
    Terminates the process (or closes the connection) on exit.

    Usage:
        async with McpClientSession(connection, timeout=30) as session:
            tools = await session.list_tools()
            result = await session.call_tool("search", {"query": "..."})
    """
    def __init__(self, connection: MpcConnectionDecrypted, timeout: int = 30): ...

    async def __aenter__(self) -> "McpClientSession": ...
    async def __aexit__(self, *_) -> None: ...

    async def list_tools(self) -> list[dict]: ...
    async def call_tool(self, tool_name: str, args: dict) -> dict: ...
```

**Stdio transport:** `asyncio.create_subprocess_exec(command, *args, env={...decrypted_env_vars...},
stdin=PIPE, stdout=PIPE, stderr=PIPE)`. Communicate via JSON-RPC 2.0 over stdin/stdout per the MCP
spec. Use `asyncio.wait_for` with the configured timeout.

**SSE transport:** Use `httpx.AsyncClient` with SSE streaming to the configured URL. Follow the MCP
HTTP+SSE transport spec.

**Error handling:**
- Subprocess exits non-zero → raise `McpConnectionError(last_error=stderr[:500])`
- Timeout → raise `McpConnectionError(last_error="timeout after {n}s")`
- Malformed JSON-RPC → raise `McpConnectionError`
- All `McpConnectionError` exceptions update `mcp_connections.last_error` in the DB.

### 5.2 Adapters

```python
# mcp_client/adapters.py

class McpToolAdapter(Protocol):
    """Maps MCP tool call output to KosObject creation inputs."""
    mcp_name_patterns: list[str]  # e.g. ["brave_*", "exa_*"] — matched against tool name

    def to_page_create(self, tool_result: dict) -> PageCreateIn | None: ...
    def to_source_create(self, tool_result: dict) -> SourceCreateIn | None: ...

class GenericAdapter:
    """
    Fallback adapter for unknown MCPs.
    Creates a page with title = first string value and content = longest string value.
    """

class BraveSearchAdapter:
    """
    Maps Brave Search / web_search tool results to Source objects.
    Each result item → one source (source_type="web", url=result.url, title=result.title,
    description=result.description). Batch-creates up to 10 sources.
    """

class GitHubIssueAdapter:
    """
    Maps github_get_issue / issue_read tool results to Page + Source pair.
    Title from issue.title; content from issue.body; url from issue.html_url;
    tags from issue.labels[].name.
    """

class Context7Adapter:
    """
    Maps context7 doc-fetch results to Source objects (source_type="web").
    Title from library + topic; content from the returned documentation block.
    """
```

**Adapter registry:** `ADAPTERS: list[McpToolAdapter] = [BraveSearchAdapter(), GitHubIssueAdapter(),
Context7Adapter(), GenericAdapter()]`. The first adapter whose `mcp_name_patterns` matches the tool
name is used; `GenericAdapter` always matches as the fallback.

### 5.3 Worker job

```python
# services/worker/tasks/mcp_ingest.py

def ingest_from_mcp(
    connection_id: str,
    tool_name: str,
    tool_args: dict,
    target_kind: str,   # "page" | "source"
    tags: list[str] = [],
) -> dict:
    """
    RQ job: spawn MCP client → call tool → adapt result → persist KosObject → enqueue reindex.
    Returns {"object_id": str, "kind": str, "title": str}.
    Writes an agent_runs row on both success and failure.
    """
```

This follows the existing `ingest_source` job pattern in `services/worker/tasks/ingest.py`.

### 5.4 New API endpoints

**`POST /api/v1/mcp-connections/{id}/call`**

Call an external MCP tool and return the raw result (no persistence). Used by the frontend to preview
what a tool returns before committing to ingestion.

```json
// Request
{ "tool_name": "brave_search", "args": { "query": "MCP protocol spec" } }

// Response
{ "result": { ...raw MCP tool output... }, "connection_name": "Brave Search" }
```

Timeout: 30s. Rate-limited: 20 calls/minute per user (shared with write tools). Records `agent_runs`
row with `tool_name = "mcp_client_call"`.

**`POST /api/v1/mcp-connections/{id}/ingest`**

Enqueue an `ingest_from_mcp` RQ job. Returns the job ID immediately (async).

```json
// Request
{
  "tool_name": "brave_search",
  "args": { "query": "LLM inference optimization" },
  "target_kind": "source",
  "tags": ["AI", "research"]
}

// Response
{ "job_id": "...", "status": "pending" }
```

### 5.5 Frontend — Phase 12B

**`/app/settings/mcp` page** — Connection registry:
- List of `McpConnectionCard` entries (name, transport badge, enabled toggle, last-tested status, error).
- "Add Connection" button → `CreateMcpConnectionModal` (name, transport selector, command/args or URL,
  env vars key-value editor, test button).
- "Test" button calls `/test` endpoint and displays the returned tool list in `McpToolBrowser`.
- Delete (soft-delete) with confirmation.
- Nav link in Sidebar settings section.

**`CreateSourceModal` — "From MCP" tab:**
- Connection picker (dropdown of enabled connections with `capabilities` cached).
- Tool picker (from `capabilities` of selected connection).
- Arg form (auto-generated from tool's `inputSchema` — render string fields as text inputs,
  boolean fields as checkboxes, enum fields as selects).
- "Preview" button → calls `/call`, shows raw result in a collapsible code block.
- "Ingest as Page / Source" buttons → calls `/ingest`, shows pending toast, polls for completion.

### 5.6 Subtasks — Phase 12B

- [ ] **12B-0** — `McpClientSession` implementation (stdio + SSE) with timeout + error handling.
- [ ] **12B-1** — `GenericAdapter` + `BraveSearchAdapter` + `GitHubIssueAdapter` + `Context7Adapter`.
- [ ] **12B-2** — `ingest_from_mcp` RQ worker job: session → call → adapt → persist → reindex.
- [ ] **12B-3** — `/call` endpoint (raw preview, no persistence, 30s timeout).
- [ ] **12B-4** — `/ingest` endpoint (enqueue RQ job, return job_id).
- [ ] **12B-5** — Frontend `/app/settings/mcp` page: connection list + CRUD modal + test.
- [ ] **12B-6** — Frontend "From MCP" tab in `CreateSourceModal`: connection picker + tool picker + arg form + preview + ingest.
- [ ] **12B-7** — Tests: `test_mcp_client.py` (unit, mock subprocess — 8+ cases); `test_mcp_ingest.py` (API integration — 6+ cases); worker unit tests for adapters (4+ cases).
- [ ] **12B-8** — Docs: `docs/INGESTION.md` "MCP ingest" section; `docs/API.md` two new endpoints; PROGRESS.md 12B complete.

---

## 6. Phase 12C — AI Augmentation

**Scope:** Web search MCP integration into `answer_from_kb` when KB confidence is low. Context7
integration for page citation enrichment. Both are opt-in and degrade gracefully.

**Depends on:** Phase 12B complete (McpClientSession available; at least one web search connection tested).

### 6.1 answer_from_kb web search fallback

Add `use_web_search: bool = false` to `POST /api/v1/ai/answer` request body. When `true`:

1. Run normal KB hybrid search (existing behavior).
2. Check `max(result.score for result in kb_results)`. If below `settings.mcp_web_search_threshold`
   (default `0.45`, configurable in `.env` as `MCP_WEB_SEARCH_THRESHOLD`):
   - Find the first enabled connection with a tool matching `mcp_name_patterns` of `BraveSearchAdapter`
     (or a generic web_search adapter).
   - Spawn `McpClientSession`, call the web search tool with the original question as query.
   - Parse results into a list of `{"title", "url", "snippet"}` dicts.
3. Construct LLM context from KB results + web results. Clearly separate them in the prompt:
   `[KB sources]` ... `[Web sources]` ...
4. Add web citations to the response alongside KB citations.

New response field: `web_citations: list[{title, url}]`. Existing `citations` field unchanged.

**MCP tool not configured or call fails:** fall back to KB-only answer, add
`warning: "web_search_unavailable"` to response. Never 500.

New config vars (in `services/api/app/config.py`):
```python
mcp_web_search_threshold: float = 0.45
mcp_web_search_connection_name: str = ""  # empty = use first enabled web-search connection
```

### 6.2 Page enrichment with Context7

New endpoint: `POST /api/v1/ai/enrich-page`

```json
// Request
{
  "page_id": "uuid",
  "query": "FastAPI dependency injection"  // the topic to look up
}

// Response
{
  "sources_created": ["uuid1", "uuid2"],
  "edges_created": ["edge-uuid1", "edge-uuid2"],
  "agent_run_id": "uuid"
}
```

Flow:
1. Resolve page + verify ownership.
2. Find the first enabled connection with a `Context7Adapter`-compatible tool.
3. `McpClientSession` → call Context7 tool with `query`.
4. `Context7Adapter.to_source_create()` → one or more Source objects created via `source_service`.
5. Create `cites` edges from the page to each new source.
6. Enqueue reindex for new sources.
7. Write `agent_runs` row.

Degrades gracefully: if no Context7 connection is configured, returns
`{"error": "no_context7_connection", "message": "Configure a Context7 MCP connection first."}` (not a 500).

Frontend: Add "Enrich with Docs" button to the AI Panel (new subtab or button alongside Summarize).
Shows the found sources and created edges on success. Off by default — only visible when a
Context7 connection is configured.

### 6.3 Subtasks — Phase 12C

- [ ] **12C-0** — Add `mcp_web_search_threshold`, `mcp_web_search_connection_name` to `config.py`.
- [ ] **12C-1** — `answer_from_kb` web search fallback: threshold check → spawn MCP → merge → cite.
- [ ] **12C-2** — `POST /api/v1/ai/enrich-page`: Context7 call → source creation → edge creation → agent_run.
- [ ] **12C-3** — Frontend: `use_web_search` toggle in AI Panel "Ask KB" section; web citations rendered.
- [ ] **12C-4** — Frontend: "Enrich with Docs" button in AI Panel (conditional on Context7 connection).
- [ ] **12C-5** — Tests: `test_mcp_augmentation.py` (8+ API integration tests); mock `McpClientSession`.
- [ ] **12C-6** — Docs: `docs/AGENT_GUIDE.md` updated; `docs/API.md` `enrich-page` endpoint; PROGRESS.md 12C complete.

---

## 7. Security model

| Concern | Mitigation |
|---|---|
| API keys stored in DB | Fernet symmetric encryption in `mcp_client/crypto.py`; key in `MCP_ENV_ENCRYPTION_KEY` env var, never in DB |
| API keys in API responses | `redact_dict()` applied to all `/mcp-connections` GET responses — same function used in outbound MCP server |
| Spawned process escapes sandbox | Subprocess inherits only whitelisted env vars (decrypted MCP vars + minimal PATH). No `--privileged`, no host mounts |
| Spawned process hangs | Hard timeout via `asyncio.wait_for`. Process killed on `__aexit__` via `process.kill()` |
| SSRF via SSE URL | Validate SSE `url` against the same `_BLOCKED_HOSTNAMES` set used in outbound `ingest_url` tool |
| Path traversal via filesystem MCP | Filesystem MCP paths validated against `LIBRARY_ROOT` (same as `ingest_file` tool) |
| Rate abuse (calling expensive external APIs) | `/call` and `/ingest` share the existing MCP write-tool rate limiter (60/min, 600/hour per user) |
| Audit trail | All `/call` and `/ingest` actions write `agent_runs` rows |
| Secret leakage in logs | Worker job logs suppress `env_vars` values; `agent_runs.input_payload` strips env vars |

---

## 8. Recommended MCP configurations (for the docs)

These are the three highest-value connections to document in `docs/MCP_TOOLS.md`:

### Brave Search
```json
{
  "name": "Brave Search",
  "transport": "stdio",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-brave-search"],
  "env_vars": { "BRAVE_API_KEY": "<your-key>" }
}
```
Value: augments `answer_from_kb` when KB has no good match. Free tier: 2,000 queries/month.

### GitHub
```json
{
  "name": "GitHub",
  "transport": "stdio",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env_vars": { "GITHUB_PERSONAL_ACCESS_TOKEN": "<your-pat>" }
}
```
Value: ingest issues, PRs, discussions, READMEs directly into KB as pages/sources.
Especially useful combined with Phase 9 project memory (extract-project from ingested GitHub content).

### Context7
```json
{
  "name": "Context7",
  "transport": "stdio",
  "command": "npx",
  "args": ["-y", "@upstash/context7-mcp"],
  "env_vars": {}
}
```
Value: fetches up-to-date library documentation. No API key required. Use with "Enrich with Docs"
in the AI panel when writing pages about frameworks or APIs.

---

## 9. Definition of Done

### Phase 12A done when:
- [ ] Migration 0011 applies cleanly (`alembic upgrade head`)
- [ ] `MCP_ENV_ENCRYPTION_KEY` in `.env.example`
- [ ] `/api/v1/mcp-connections` CRUD all working with auth
- [ ] env_vars encrypted in DB, redacted in API responses
- [ ] `/test` endpoint spawns a mock subprocess and caches capabilities
- [ ] 12+ integration tests passing in `test_mcp_connections.py`
- [ ] `ruff check/format` clean; full regression `pytest api/ unit/` green

### Phase 12B done when:
- [ ] `McpClientSession` can connect to a real stdio MCP (e.g. `uvx mcp-server-brave-search`)
- [ ] `ingest_from_mcp` worker job creates a real KosObject and enqueues reindex
- [ ] `/call` returns raw tool result within 30s
- [ ] `/ingest` enqueues job and returns `job_id`
- [ ] `/app/settings/mcp` page works: add, test, delete a connection
- [ ] "From MCP" tab in `CreateSourceModal` works end-to-end (preview + ingest)
- [ ] `pnpm typecheck && pnpm lint` clean
- [ ] 18+ new tests across client, adapters, API, worker

### Phase 12C done when:
- [ ] `POST /api/v1/ai/answer { use_web_search: true }` calls web search MCP when KB score is low
- [ ] Graceful degradation when no web search connection configured (`warning` field, no 500)
- [ ] `POST /api/v1/ai/enrich-page` creates Source objects + edges from Context7
- [ ] Frontend AI panel shows web citations and "Enrich with Docs" button
- [ ] 8+ new tests in `test_mcp_augmentation.py`
- [ ] All existing tests still pass

---

## 10. Commit sequence (illustrative, one per subtask)

```
Phase 12A:
1.  docs: add Phase 12 MCP Connections plan
2.  feat(api): Fernet env-var encryption for MCP connection secrets
3.  feat(db): migration 0011 mcp_connections table
4.  feat(api): MCP connection ORM model and Pydantic schemas
5.  feat(api): MCP connection service (CRUD + ownership + redaction)
6.  feat(api): MCP connections REST router registered
7.  feat(api): test-connection endpoint (spawn stdio + list tools + cache capabilities)
8.  test(api): MCP connection CRUD, encryption, ownership, and test-connection coverage
9.  docs: MCP connections security and setup documentation

Phase 12B:
10. feat(api): McpClientSession context manager (stdio + SSE transports)
11. feat(api): MCP tool adapters (Generic, BraveSearch, GitHub, Context7)
12. feat(worker): ingest_from_mcp RQ job
13. feat(api): /call endpoint (preview raw tool result)
14. feat(api): /ingest endpoint (enqueue ingest job)
15. feat(web): /app/settings/mcp connection registry page
16. feat(web): From MCP tab in CreateSourceModal
17. test: MCP client, adapters, call/ingest API, worker coverage
18. docs: ingestion and API docs updated for MCP ingest

Phase 12C:
19. feat(api): web search MCP fallback in answer_from_kb
20. feat(api): enrich-page endpoint (Context7 → sources + edges)
21. feat(web): web search toggle and citations in AI panel
22. feat(web): Enrich with Docs button in AI panel
23. test(api): MCP augmentation coverage
24. docs: agent guide and API docs updated for Phase 12C
```

---

## 11. Validation commands

```bash
# Phase 12A
cd services/api && uv run alembic upgrade head
cd tests && uv run pytest api/test_mcp_connections.py -v   # ≥12 passing
cd tests && uv run pytest api/ unit/ -q                     # full regression green
cd services/api && uv run ruff check . && uv run ruff format --check .

# Phase 12B
# Smoke: real Brave Search MCP (requires BRAVE_API_KEY)
cd services/api && uvicorn app.main:app --reload &
curl -s -X POST http://127.0.0.1:8000/api/v1/mcp-connections/{id}/call \
  -H "Cookie: kos_session=..." \
  -d '{"tool_name": "brave_search", "args": {"query": "MCP protocol"}}' | python3 -m json.tool
# Frontend
pnpm -F @kos/web typecheck && pnpm -F @kos/web lint

# Phase 12C
curl -s -X POST http://127.0.0.1:8000/api/v1/ai/answer \
  -d '{"question": "latest FastAPI docs", "use_web_search": true}' | python3 -m json.tool
cd tests && uv run pytest api/test_mcp_augmentation.py -v   # ≥8 passing
```

---

## 12. Open questions (resolve before 12A implementation starts)

1. **`mcp` SDK version for client use:** The existing outbound server uses `mcp` Python SDK as a
   *server*. Using it as a *client* (to spawn and talk to stdio servers) requires the `ClientSession`
   class. Confirm the installed `mcp` SDK version supports `ClientSession` before writing
   `McpClientSession` — if not, implement raw JSON-RPC over stdio directly.

2. **Subprocess env inheritance:** Decide whether spawned MCP processes inherit the API container's
   full env or a minimal whitelist. Whitelist is safer but may break MCPs that need `PATH` or `HOME`.
   Recommendation: whitelist `PATH`, `HOME`, `TMPDIR`, and the decrypted MCP-specific vars.

3. **SSE transport priority:** SSE MCP clients are less common than stdio in 2026. Consider deferring
   SSE support to a follow-up and marking it as `transport = 'sse'` as a reserved value in 12A,
   implemented only in 12B if time permits.

4. **`npx` availability in Docker:** The API and worker containers are Python-based (no Node.js).
   Stdio MCPs that use `npx` (GitHub, Brave) require Node.js in the container. Options:
   - Add `node` to the API/worker Dockerfiles (simplest, adds ~200MB)
   - Run MCP processes outside Docker (stdio spawned from the host via a Docker exec hack — bad)
   - Add a dedicated lightweight `mcp-bridge` container with Node.js (cleanest separation, more complex)
   
   **Recommended:** Add Node.js to the worker Dockerfile for 12B. Document this in `infra/` notes.
   Evaluate the bridge container approach only if Node MCPs proliferate in 12C+.
