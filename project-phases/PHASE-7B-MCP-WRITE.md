# Phase 7B — MCP Write Tools

> **Status:** Planned (unblocked 2026-05-15)
> **Branch:** `phase-7b-mcp-write`
> **Depends on:**
> - Phase 7A (MCP read/search + safety foundation + `X-KOS-Internal-Token`) — ✅ complete
> - Phase 5 (`object_revisions` table, `ai_generated` column, `revision_service`) — ✅ complete
> - `PHASE-FIX-01` F1 (`answer_from_kb` wired) — recommended but not strictly required
> - `PHASE-FIX-01` F2 (RQ worker container in docker-compose) — **required** before `ingest_url` / `ingest_file` are useful

---

## 1. Context

Phase 7A shipped a safe, read-only MCP surface (`search_objects`, `hybrid_search`, `get_object`, `get_page`, `get_source`, `get_related_objects`). External agents can read the knowledge base over stdio with token-authenticated, redaction-filtered, depth-capped responses. They cannot write anything.

This is half of the project's north star. From `CLAUDE.md`:

> KnowledgeOS is **agent-ready**: Claude, Codex, ChatGPT, and local agents can safely **search, read, create, update, and link** knowledge through the built-in MCP server and internal API.

Phase 5 closed the prerequisite gap by shipping the `object_revisions` table, `revision_service.create_revision()`, and the `ai_generated` flag on objects. The audit log table `agent_runs` has been live since Phase 1. Soft-delete is universal.

**What was previously blocking 7B and is now resolved:**

| Blocker (when 7A planned) | Status today |
|---|---|
| No `object_revisions` table | ✅ Migration 0004, model + service both shipped |
| No revision-snapshot pattern | ✅ Used by Phase 5 AI writes and Phase 6B summary apply |
| No way to mark AI-authored objects | ✅ `objects.ai_generated` column |
| No worker container for ingestion | 🚧 Tracked as `PHASE-FIX-01` F2; required for `ingest_url`/`ingest_file` only |

Phase 7B is therefore unblocked. It is the right next phase because it completes the agent-readiness story — every other remaining phase (8 multi-pane, 9 career memory) becomes more powerful when agents can write into the graph instead of only read from it.

---

## 2. Goal

Add a minimal, audited, soft-delete-only MCP write surface so external agents can:

1. **Capture new knowledge:** `create_page`, `ingest_url`, `ingest_file`.
2. **Refine existing knowledge:** `update_page`, `archive_object`.
3. **Connect knowledge:** `create_edge`.

Every write must produce both an `agent_runs` row (who, when, what, model, tokens) and — if it mutated an existing object — an `object_revisions` row (before/after JSONB snapshot). Every write must be soft-delete-only and must respect rate limits per agent identity. No tool may execute shell commands, touch the filesystem outside `LIBRARY_ROOT`, or return secrets.

---

## 3. Non-Goals

- **Hard deletes.** `archive_object` flips `is_archived=true`. `objects.deleted_at` is reserved for the existing user-driven soft delete; MCP does not call it.
- **Bulk operations.** No `bulk_create_pages`, no `delete_all`, no `merge_objects`. One write = one tool call.
- **Update tools for sources/assets/chats.** Only `update_page` and `archive_object` mutate existing objects. Source ingestion still goes through `ingest_url`/`ingest_file` which create *new* sources; existing sources are archived, not edited.
- **Direct embedding/Qdrant writes.** Reindex is automatic via existing save hooks (`reindex_object` worker job). MCP never touches Qdrant directly.
- **Edge deletion.** Out of scope for v1. `archive_object` on a source-only edge endpoint is the workaround. `delete_edge` can be a 7B v2 follow-up if needed.
- **`create_chat`, `update_source`, `create_claim`, `create_task` MCP tools.** Phase 6B and Phase 5 already produce these from the API/AI side. Adding write tools for them is Phase 7B v3 territory.
- **Any change to the cookie auth path.** `kos_session` users are unchanged.

---

## 4. Safety Constraints (non-negotiable)

These rules apply to every tool added in this phase. They are tested explicitly, not assumed.

| # | Rule | Where it's enforced |
|---|---|---|
| S1 | Every MCP write creates exactly one `agent_runs` row in the same transaction as the write. If the write fails, the audit row is rolled back. If the audit row fails, the write is rolled back. | `services/api/app/services/agent_run_service.py` + transaction boundary in each write endpoint |
| S2 | Every MCP mutation of an existing object creates exactly one `object_revisions` row with full before/after JSONB snapshot, linked to the `agent_runs.id`. | `services/api/app/services/revision_service.py` |
| S3 | No tool may write outside `LIBRARY_ROOT`. `ingest_file` validates the path is `pathlib.Path.resolve()`-relative-to `LIBRARY_ROOT` before any IO. Symlinks resolved before the check. | `services/api/app/core/library.py` |
| S4 | No tool may execute a shell command. The MCP server has no `subprocess`/`os.system` import. | `services/mcp/kos_mcp/` (lint rule + grep guard in CI) |
| S5 | All tool responses pass through `redact_dict`. Secrets (`api_keys`, `session_secret`, `password_hash`, `token_hash`) are never returned. | `services/mcp/kos_mcp/redaction.py` |
| S6 | Per-agent rate limit: max 60 writes/minute and 600 writes/hour, default. Exceeding either returns `RateLimitError` with retry hint; no `agent_runs` row is created for rejected calls. | new `services/api/app/core/rate_limit.py` (Redis-backed sliding window) |
| S7 | Write tools are gated by `MCP_ALLOW_WRITE_TOOLS=false` by default. Setting it to `true` is the single switch that unlocks any write. | `services/mcp/kos_mcp/config.py` (already present) + tool registration filter |
| S8 | `archive_object` and `update_page` are reversible. Archive un-archives via `PATCH /objects/{id}` with `is_archived=false`. Updates roll back from the latest `object_revisions.before_snapshot`. | new `POST /api/v1/objects/{id}/revisions/{rev_id}/restore` endpoint |
| S9 | `ingest_url` validates the URL with the existing `tests/unit/test_url_safety.py` rules (no `file://`, no localhost, no link-local) before enqueuing. | `services/api/app/services/source_service.py` (already partially present; verify) |
| S10 | All write tools return the new/updated object's `id` in their response, but never the full content of any other object the user owns. No cross-object data leaks. | per-tool response shape |

---

## 5. Definition of Done

- [ ] `project-phases/PHASE-7B-MCP-WRITE.md` exists (this file)
- [ ] `PROGRESS.md` Phase 7B section updated to "🚧 In Progress" then "✅ Complete"
- [ ] `MCP_ALLOW_WRITE_TOOLS=false` is the default in `infra/.env.example` and in `McpSettings`
- [ ] All 6 write tools register only when `MCP_ALLOW_WRITE_TOOLS=true`
- [ ] `create_page` works end-to-end (smoke test from `kos-mcp` against a live API)
- [ ] `update_page` writes both `agent_runs` and `object_revisions` rows in the same transaction
- [ ] `create_edge` is idempotent on `(source_id, target_id, kind)` (matches existing `POST /edges`)
- [ ] `archive_object` flips `is_archived=true`, never sets `deleted_at`
- [ ] `ingest_url` enqueues an RQ job and returns the source `id` immediately (does not block on extraction)
- [ ] `ingest_file` rejects any path outside `LIBRARY_ROOT` with a clear error
- [ ] Rate limiter rejects the 61st write in a minute from the same agent identity, with a `RateLimitError` text response
- [ ] `agent_runs.input` JSONB contains the redacted call arguments; `output` contains the response shape
- [ ] Existing 24 MCP tests + ~112 API integration tests still pass
- [ ] At least 18 new tests across `services/mcp/tests/` and `tests/api/`
- [ ] `docs/MCP_TOOLS.md`, `docs/SECURITY.md`, `docs/AGENT_GUIDE.md`, and `docs/REVISION_HISTORY.md` updated
- [ ] `CLAUDE.md` "MCP & Agent Safety Rules" section reviewed and updated if any rule changes
- [ ] No write tool path imports `subprocess`, `os.system`, `shutil.rmtree`, or `pathlib.Path.unlink`

---

## 6. MCP Architecture (delta from 7A)

```
External Agent (Claude Desktop / Cursor / Codex)
  │  stdio
  ▼
kos_mcp.server  (unchanged)
  │
  ├── kos_mcp.config        ← + write-tool allowlist gate
  ├── kos_mcp.tools          ← + 6 write tools (read tools unchanged)
  ├── kos_mcp.client         ← + 6 new HTTP methods
  ├── kos_mcp.redaction      (unchanged)
  │
  ▼  HTTP to 127.0.0.1:8001 (or 8000 per F9)
FastAPI /api/v1/*
  │
  ├── deps.get_current_user   ← unchanged (token path = first user)
  ├── core.rate_limit         ← NEW (Redis sliding window per agent id)
  ├── services.agent_run      ← invoked by every write
  ├── services.revision       ← invoked by update + archive
  └── existing CRUD services  ← reused as-is
```

The MCP server itself is barely touched. The work is on the API side: rate limiting, audit/revision discipline, and the new `archive_object` + `revision restore` endpoints.

---

## 7. Tool Plan

| Tool | Backend endpoint | New endpoint? | Audit | Revision |
|---|---|---|---|---|
| `create_page` | `POST /api/v1/pages` | No (exists) | `agent_runs` | — (new object) |
| `update_page` | `PATCH /api/v1/pages/{id}` | No (exists) | `agent_runs` | `object_revisions` (before/after) |
| `create_edge` | `POST /api/v1/edges` | No (exists, idempotent) | `agent_runs` | — |
| `archive_object` | `POST /api/v1/objects/{id}/archive` | **NEW** | `agent_runs` | `object_revisions` (is_archived flip) |
| `ingest_url` | `POST /api/v1/sources` (with `url` discriminator) | No (exists) | `agent_runs` | — (new source) |
| `ingest_file` | `POST /api/v1/sources` (with `file_path` discriminator) | No (exists) | `agent_runs` | — (new source) |

The single new HTTP endpoint is `POST /api/v1/objects/{id}/archive`. Everything else reuses Phase 1–6 endpoints.

### Tool input schemas (summary)

```jsonc
// create_page
{ "title": string, "content_text"?: string, "tags"?: string[] }

// update_page
{ "page_id": uuid, "title"?: string, "content_text"?: string,
  "tags"?: string[], "expected_version"?: number }   // optimistic lock

// create_edge
{ "source_id": uuid, "target_id": uuid,
  "kind": "links_to"|"cites"|"mentions"|"supports"|"contradicts"|"related_to"|"derives_from"|"summarizes",
  "weight"?: number, "metadata"?: object }

// archive_object
{ "object_id": uuid, "reason"?: string }

// ingest_url
{ "url": string, "source_type"?: "web"|"youtube"|"pdf",
  "title"?: string, "tags"?: string[] }

// ingest_file
{ "file_path": string,                                // MUST be under LIBRARY_ROOT
  "source_type"?: "pdf"|"image"|"csv"|"audio"|"video",
  "title"?: string, "tags"?: string[] }
```

---

## 8. Audit and Revision Contract

Every write tool wraps the underlying service call in this pattern:

```python
async def write_tool_handler(db, user_id, agent_id, tool_name, args):
    if not await rate_limit_check(agent_id):
        raise RateLimitError(...)

    async with db.begin():        # one transaction
        run = await agent_run_service.create(
            db, user_id=user_id, agent_type=agent_id,
            tool_name=tool_name, input_=redact_for_audit(args),
            status="running",
        )
        try:
            before = await snapshot_if_mutating(db, args)
            result = await underlying_service_call(db, **args)
            after = await snapshot_if_mutating(db, result.id)
            if before is not None:
                await revision_service.create(
                    db, object_id=result.id, agent_run_id=run.id,
                    changed_by="agent", before=before, after=after,
                )
            await agent_run_service.complete(db, run.id, output=result.summary())
            return result
        except Exception as exc:
            await agent_run_service.fail(db, run.id, error=str(exc))
            raise   # transaction rolls back
```

The transaction boundary guarantees S1 + S2: either everything (write + audit + revision) lands, or nothing does.

Snapshot shape for `object_revisions`:

```jsonc
{
  "object": { "title": ..., "description": ..., "tags": [...],
              "metadata_": {...}, "is_pinned": ..., "is_archived": ... },
  "page":   { "content_text": ..., "content_json": {...},
              "word_count": ..., "version": ... }   // only for page kind
}
```

---

## 9. Rate Limiting Design

A new `services/api/app/core/rate_limit.py` implements a Redis-backed sliding window:

```python
async def check_and_increment(agent_id: str, kind: Literal["minute","hour"]) -> bool:
    """Returns True if the call is allowed; False if rate limited."""
    key = f"kos:rl:{kind}:{agent_id}"
    now = time.time()
    window = 60 if kind == "minute" else 3600
    async with redis.pipeline() as pipe:
        await pipe.zremrangebyscore(key, 0, now - window).execute()
        count = await redis.zcard(key)
        if count >= LIMITS[kind]:
            return False
        await pipe.zadd(key, {str(uuid.uuid4()): now}).expire(key, window).execute()
        return True
```

Limits configurable via `MCP_RATE_LIMIT_PER_MINUTE` (default 60) and `MCP_RATE_LIMIT_PER_HOUR` (default 600).

Agent identity comes from a new optional `X-KOS-Agent-Id` header. The MCP server sets it to a stable id per running session (e.g. `"claude-desktop-{client_id}"`). If absent, falls back to a hash of the `MCP_INTERNAL_TOKEN` so all unidentified agents share one bucket.

---

## 10. Subtask Checklist

Each subtask is independently codex-delegatable and ends with a single conventional commit. Subtasks marked **(blocking)** must land before later ones.

- [ ] **Subtask 0** — Audit + plan files: this doc, PROGRESS update **(blocking)**
- [ ] **Subtask 1** — Rate limiter (`core/rate_limit.py`) + Redis test fixture **(blocking for 5–10)**
- [ ] **Subtask 2** — Audit + revision wrapper helper used by all write endpoints **(blocking for 5–10)**
- [ ] **Subtask 3** — `POST /api/v1/objects/{id}/archive` endpoint + `POST /objects/{id}/revisions/{rev_id}/restore` endpoint
- [ ] **Subtask 4** — `MCP_ALLOW_WRITE_TOOLS` gating + per-tool registration filter
- [ ] **Subtask 5** — `create_page` MCP tool + client method + tests
- [ ] **Subtask 6** — `create_edge` MCP tool + client method + tests
- [ ] **Subtask 7** — `update_page` MCP tool + revision write + tests
- [ ] **Subtask 8** — `archive_object` MCP tool + tests
- [ ] **Subtask 9** — `ingest_url` MCP tool + URL safety re-check + tests
- [ ] **Subtask 10** — `ingest_file` MCP tool + LIBRARY_ROOT validation + tests
- [ ] **Subtask 11** — Docs (`MCP_TOOLS.md`, `SECURITY.md`, `AGENT_GUIDE.md`, `REVISION_HISTORY.md`) + `PROGRESS.md` flip
- [ ] **Subtask 12** — End-to-end smoke: spin up local stack, run `kos-mcp` with a fake agent harness, exercise all 6 tools, verify audit + revision rows in Postgres

---

## 11. Subtask Details

### Subtask 1 — Rate limiter

**Goal:** Drop-in async Redis sliding-window limiter usable by both MCP and any future feature.

**Files to create:**
- `services/api/app/core/rate_limit.py`
- `tests/api/test_rate_limit.py`

**Files to modify:**
- `services/api/app/config.py` — add `mcp_rate_limit_per_minute: int = 60`, `mcp_rate_limit_per_hour: int = 600`, `mcp_agent_id_header: str = "X-KOS-Agent-Id"`

**Tests:** allow 60 then reject the 61st in same minute; window slides correctly; expiry works; missing agent id falls back to shared bucket.

**Commit:** `feat(api): redis-backed sliding-window rate limiter for mcp writes`

---

### Subtask 2 — Audit + revision wrapper

**Goal:** A single helper `audited_write(db, user_id, agent_id, tool_name, args, fn, *, mutating_object_id=None)` that:
- Checks the rate limit.
- Opens a transaction.
- Creates a `running` `agent_runs` row.
- If `mutating_object_id` is set: snapshots before.
- Calls `fn(db, args)`.
- If mutating: snapshots after, writes `object_revisions`.
- Marks `agent_runs` `success` or `failed`.
- Re-raises so caller sees the error.

**Files to create:**
- `services/api/app/services/audited_write_service.py`

**Files to modify:**
- `services/api/app/services/revision_service.py` — add `snapshot_object_state(db, object_id) -> dict` helper if missing.
- `services/api/app/services/agent_run_service.py` — add `complete()` and `fail()` helpers.

**Tests:** rollback on inner exception leaves no `agent_runs` row; rollback on audit-row failure leaves no object change; happy path writes both rows linked correctly.

**Commit:** `feat(api): audited write helper with transactional revision logging`

---

### Subtask 3 — `archive_object` + revision restore endpoints

**Goal:** Reversible archive endpoint and a restore-from-revision endpoint.

**Files to create:**
- (route is added to existing `services/api/app/api/v1/objects.py`)
- `tests/api/test_archive_restore.py`

**New routes:**

```python
@router.post("/{object_id}/archive", response_model=ObjectOut)
async def archive_object(...): ...

@router.post("/{object_id}/revisions/{rev_id}/restore", response_model=ObjectOut)
async def restore_revision(...): ...
```

`archive_object` sets `is_archived=true`. `restore_revision` re-applies the `before_snapshot` of the named revision (validating ownership and that the revision belongs to the object). Both use the audited write wrapper, both create new `object_revisions` rows.

**Tests:** archive idempotent; restore brings back prior title/content; cannot restore a revision belonging to another object; cannot restore beyond a hard-archived object's deletion.

**Commit:** `feat(api): archive and revision-restore endpoints`

---

### Subtask 4 — Write-tool gating

**Goal:** When `MCP_ALLOW_WRITE_TOOLS=false`, none of the 6 write tools are registered with the MCP server. `list_tools` does not advertise them; `call_tool` rejects them with a clear error.

**Files to modify:**
- `services/mcp/kos_mcp/tools.py` — wrap each write-tool registration in `if "create_page" in allowed and settings.mcp_allow_write_tools:`
- `services/mcp/kos_mcp/config.py` — extend `DEFAULT_ALLOWED_TOOLS` with the 6 write tools (still gated by `mcp_allow_write_tools`).
- `infra/.env.example` — `MCP_ALLOW_WRITE_TOOLS=false` with comment.

**Tests:** with flag off, `list_tools` returns 7 read tools (incl. `answer_from_kb` from F1); with flag on, returns 13.

**Commit:** `feat(mcp): gate write tools behind MCP_ALLOW_WRITE_TOOLS flag`

---

### Subtask 5 — `create_page`

**Files to modify:**
- `services/mcp/kos_mcp/client.py` — `async def create_page(self, title, content_text, tags) -> dict`
- `services/mcp/kos_mcp/tools.py` — register tool, add `_create_page` dispatch
- `tests/api/test_mcp_writes.py` — new file (will host all 6 tools' integration tests)

**Audit input shape:** `{ "title": "...", "tags": [...], "content_text_len": <int> }` — do **not** include the full content_text in the audit row; that would balloon `agent_runs` storage. Length is enough for forensics.

**Tests:** happy path returns object id; rate-limited after 60 calls; cannot create with empty title; `agent_runs` row written with `tool_name="create_page"`, `status="success"`, `model=None`.

**Commit:** `feat(mcp): create_page write tool`

---

### Subtask 6 — `create_edge`

**Files to modify:** as Subtask 5.

**Note on idempotency:** the existing `POST /edges` endpoint already handles `(source_id, target_id, kind)` uniqueness with soft-delete restoration. Reuse it; the MCP tool is a thin wrapper. The `agent_runs` row is created either way (creation OR restoration) so the audit trail records the agent's intent.

**Tests:** create new edge; idempotent re-create returns same edge id; create across user-owned objects only (rejects cross-user); rejects unknown edge kind.

**Commit:** `feat(mcp): create_edge write tool with idempotency`

---

### Subtask 7 — `update_page`

**Files to modify:** as Subtask 5, plus the `PATCH /pages/{id}` route may need an optional `expected_version` parameter for optimistic locking.

**Optimistic lock semantics:** if `expected_version` is provided and does not match `pages.version`, the API returns 409 Conflict. The MCP tool surfaces this as a `VersionConflict` text response so the agent can re-fetch and retry. If `expected_version` is omitted, the update proceeds (last-writer-wins; the audit + revision history still allows recovery).

**Tests:** update writes `object_revisions` with full before/after; conflicting version returns 409 + no audit row; update preserves `ai_generated` flag if previously set.

**Commit:** `feat(mcp): update_page write tool with revision logging and optimistic lock`

---

### Subtask 8 — `archive_object`

**Files to modify:** as Subtask 5, depends on Subtask 3.

**Tests:** archive flips `is_archived=true` and creates revision; archiving an already-archived object is a no-op (no new revision); cannot archive other users' objects.

**Commit:** `feat(mcp): archive_object write tool`

---

### Subtask 9 — `ingest_url`

**Files to modify:** as Subtask 5.

**Note:** Reuses `POST /api/v1/sources` with the URL-flavored payload that Phase 2 already validates. Worker container (PHASE-FIX-01 F2) must be running for the resulting RQ job to actually extract content; the MCP tool returns the source `id` and `ingestion_status="pending"` immediately and does not block on extraction.

**URL safety:** delegate to the existing `tests/unit/test_url_safety.py` rules in source_service. Reject `file://`, `localhost`, link-local, and any non-http(s) scheme.

**Tests:** rejects `file:///etc/passwd`; rejects `http://localhost`; happy path with a YouTube URL returns source id; happy path with a normal article URL returns source id.

**Commit:** `feat(mcp): ingest_url write tool`

---

### Subtask 10 — `ingest_file`

**Files to modify:** as Subtask 5, plus `services/api/app/core/library.py` may need a `validate_path_under_library_root(p: str) -> Path` helper if not already present.

**Path validation:** `pathlib.Path(p).resolve()` then assert `is_relative_to(LIBRARY_ROOT.resolve())`. Reject symlinks that escape the root. Reject if file does not exist or is not readable.

**Tests:** rejects `/etc/passwd`; rejects `~/Documents/secret.pdf` (assuming LIBRARY_ROOT != that path); rejects symlink that points outside library; happy path with a real file under LIBRARY_ROOT returns source id.

**Commit:** `feat(mcp): ingest_file write tool with library-root validation`

---

### Subtask 11 — Docs

**Files to modify:**
- `docs/MCP_TOOLS.md` — full spec for all 6 write tools, request/response examples, error codes.
- `docs/SECURITY.md` — write-tool safety section: rate limiter design, audit invariants, revision rollback story, `LIBRARY_ROOT` enforcement.
- `docs/AGENT_GUIDE.md` — when to use which write tool; idempotency notes; how to detect rate-limit responses.
- `docs/REVISION_HISTORY.md` — note that agent writes now produce revision rows automatically.
- `PROGRESS.md` — flip Phase 7B section to ✅ Complete with subtask checklist.
- `README.md` — update the "MCP & Agent Access" section to remove the "Phase 7B planned" note and list the live write tools.

**Commit:** `docs: phase 7b mcp write tools — security model, tool spec, agent guide`

---

### Subtask 12 — End-to-end smoke

**Goal:** A reproducible script that proves the system works against a live local stack.

**Files to create:**
- `scripts/mcp_smoke.py` — spawns `kos-mcp` as a subprocess, sends `tools/list`, then exercises each write tool, then queries Postgres directly to verify `agent_runs` and `object_revisions` rows exist.

**Verification:**
1. Bring up: `docker compose -f infra/docker-compose.yml up -d` (with `MCP_ENABLED=true` and `MCP_ALLOW_WRITE_TOOLS=true` in `.env`).
2. Run: `uv run scripts/mcp_smoke.py`.
3. Expected output: 6 ✓ marks (one per tool), one summary table showing audit + revision row counts.

**Commit:** `test(mcp): end-to-end smoke harness for write tools`

---

## 12. Files to Create

| File | Purpose |
|---|---|
| `services/api/app/core/rate_limit.py` | Redis sliding-window limiter |
| `services/api/app/services/audited_write_service.py` | Transactional audit + revision wrapper |
| `tests/api/test_rate_limit.py` | Limiter unit tests |
| `tests/api/test_archive_restore.py` | Archive + restore endpoint tests |
| `tests/api/test_mcp_writes.py` | Integration tests across all 6 write tools (auth, audit, revision, rate limit) |
| `scripts/mcp_smoke.py` | Live end-to-end harness |

## 13. Files to Modify

| File | Change |
|---|---|
| `services/api/app/config.py` | Rate-limit and agent-id-header settings |
| `services/api/app/api/v1/objects.py` | `+ POST /{id}/archive` + `+ POST /{id}/revisions/{rev_id}/restore` |
| `services/api/app/api/v1/pages.py` | Optional `expected_version` on PATCH |
| `services/api/app/services/agent_run_service.py` | `complete()` / `fail()` helpers |
| `services/api/app/services/revision_service.py` | `snapshot_object_state()` helper if missing |
| `services/api/app/core/library.py` | `validate_path_under_library_root()` if missing |
| `services/mcp/kos_mcp/config.py` | Extend default allowlist, gate by `mcp_allow_write_tools` |
| `services/mcp/kos_mcp/client.py` | 6 new HTTP methods |
| `services/mcp/kos_mcp/tools.py` | 6 new tool registrations + dispatchers |
| `services/mcp/tests/test_tools.py` | Per-tool unit tests with mocked client |
| `services/mcp/tests/test_config.py` | Gate-flag tests |
| `infra/.env.example` | `MCP_ALLOW_WRITE_TOOLS=false`, `MCP_RATE_LIMIT_*` |
| `docs/MCP_TOOLS.md` | Full write-tool spec |
| `docs/SECURITY.md` | Write-tool safety section |
| `docs/AGENT_GUIDE.md` | Agent usage guidance |
| `docs/REVISION_HISTORY.md` | Note agent-write revisions |
| `PROGRESS.md` | Phase 7B section |
| `README.md` | MCP write tools live |

## 14. Tests Required

Minimum 18 new tests across the suite:

- `tests/api/test_rate_limit.py`: 4 (allow, deny on 61st, sliding window, missing agent id)
- `tests/api/test_archive_restore.py`: 4 (archive happy, archive idempotent, restore happy, restore wrong-owner)
- `tests/api/test_mcp_writes.py`: 6 (one happy + audit-row assertion per tool; covers all 6 tools)
- `services/mcp/tests/test_tools.py`: +4 (gate-flag off rejects writes; gate-flag on lists writes; ingest_url URL safety; ingest_file path validation)

After Phase 7B: target ~165 tests (147 today + ~18 new).

## 15. Commit Sequence

```
1.  docs: phase 7b plan
2.  feat(api): redis-backed sliding-window rate limiter for mcp writes
3.  feat(api): audited write helper with transactional revision logging
4.  feat(api): archive and revision-restore endpoints
5.  feat(mcp): gate write tools behind MCP_ALLOW_WRITE_TOOLS flag
6.  feat(mcp): create_page write tool
7.  feat(mcp): create_edge write tool with idempotency
8.  feat(mcp): update_page write tool with revision logging and optimistic lock
9.  feat(mcp): archive_object write tool
10. feat(mcp): ingest_url write tool
11. feat(mcp): ingest_file write tool with library-root validation
12. docs: phase 7b mcp write tools — security model, tool spec, agent guide
13. test(mcp): end-to-end smoke harness for write tools
```

## 16. Validation Commands

```bash
# Backend lint + tests
uv run ruff check services/api
PYTHONPATH=services/api uv run pytest tests/api -q
PYTHONPATH=services/api uv run pytest tests/unit -q

# MCP package tests
cd services/mcp && uv run pytest tests/ -v

# Frontend (no UI changes expected, but verify nothing breaks)
pnpm -F web typecheck
pnpm -F web build

# Live smoke (requires worker container — F2)
docker compose -f infra/docker-compose.yml up -d
MCP_ENABLED=true MCP_ALLOW_WRITE_TOOLS=true uv run scripts/mcp_smoke.py

# Smoke: with write tools disabled, list_tools returns only read tools
MCP_ALLOW_WRITE_TOOLS=false uv run --project services/mcp kos-mcp <<<'{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

---

## 17. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Agent loop creates 10,000 pages in a minute | Rate limit (60/min, 600/hr); also: each `create_page` audited so post-mortem cleanup is scriptable. |
| `update_page` overwrites a user edit they just made | Optional `expected_version` for optimistic lock; revision history allows rollback. |
| `ingest_file` traverses out of LIBRARY_ROOT via symlink | `Path.resolve()` before relative-to check; explicit symlink rejection. |
| Audit row created but write rolled back (or vice versa) | Single transaction boundary covers both; explicit test for inner-exception rollback. |
| `agent_runs.input` JSONB grows unbounded with full page contents | Strip large fields (e.g., `content_text`) from audit input; store length only. |
| MCP server bundles a logic error that bypasses rate limit | Rate limit lives in the API, not MCP. MCP cannot bypass it. |
| Future Phase 8/9 needs different rate limits | Limits are per-agent and configurable via env; Phase 8/9 can register additional buckets. |
| Cross-user write (token-auth maps to "first user" in 7A) | Already tested in 7A `test_mcp_auth.py`; same pattern continues here. |

---

## 18. Done When

- All 12 subtasks checked.
- All quality gates green.
- Smoke harness produces 6 ✓ for all write tools and verified audit + revision rows in Postgres.
- README "MCP & Agent Access" lists the live write tools and removes the "planned" note.
- PROGRESS Phase 7B section is ✅ Complete.
- Phase 8 or Phase 9 work can begin with full agent participation in the knowledge graph.
