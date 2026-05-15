# Security Model

## Local Auth

- Simple email/password login
- Session token = `secrets.token_urlsafe(32)`, stored as `sha256(token)` in DB
- HTTP-only cookie `kos_session`, SameSite=Lax, 30-day expiry
- Optional `Secure` flag via env `COOKIE_SECURE=true` when the API is served over HTTPS
- All services bind to `127.0.0.1` by default

## Registration policy

- Env `ALLOW_OPEN_REGISTRATION` (default `true`): when `false`, `POST /auth/register` returns **403** for a closed appliance.
- Duplicate registration attempts return a generic **400** (`Unable to complete registration`) to avoid email enumeration via status codes.

## Web ingestion and SSRF

- URL-backed sources (`web`, `youtube`) are validated at create time and again before the worker fetches them.
- Only `http`/`https` are allowed; URLs with embedded credentials are rejected; hosts must resolve only to **globally routable** addresses (private, loopback, and link-local ranges are blocked). Redirects are followed manually with a small hop limit and response size cap.
- DNS rebinding between validation and connect is not fully eliminated (acceptable residual risk for local-first; use egress controls if the API is exposed beyond localhost).

## Session model

Sessions are DB-backed opaque tokens — not signed cookies.

- Login creates a `secrets.token_urlsafe(32)` value, stores `sha256(token)` in `sessions.token_hash`, and sets an HTTP-only `kos_session` cookie with the raw token.
- Each authenticated request looks up the hash in Postgres; if the row is missing or expired the request is rejected.
- 30-day TTL enforced server-side; logout deletes the row immediately.
- `SESSION_SECRET` in `infra/.env` is **not currently used** — it is reserved for future CSRF tokens or signed password-reset URLs. It does not affect session cookie integrity. Leaving it unset is safe.

## Optional secrets

- `SESSION_SECRET`: reserved for future CSRF or signed URLs; sessions are DB-backed and do not depend on it (see Session model above).

## API Key Storage

- OpenAI and other keys stored in `infra/.env` (gitignored)
- Never committed to the repository
- Never exposed through MCP tools or API responses (redacted before any return value)

## Offline and AI Provider Degradation

- Core app features (CRUD, keyword search, asset upload) work with no API keys and no internet
- AI-backed features (vector embeddings, summarization, Q&A) return graceful errors when `OPENAI_API_KEY` is absent — not 500s
- Hybrid search falls back to keyword-only; response includes `"embeddings_disabled": true`
- No user data is sent to external AI providers unless the user explicitly invokes an AI feature
- Structured chat summaries send parsed chat turns to the configured AI provider only after an explicit Generate action. Applying a summary is a separate explicit action.
- See `docs/ARCHITECTURE.md` for the full degradation table

## Agent Safety

- No arbitrary shell execution through MCP
- No file access outside `~/KnowledgeOS`
- All agent actions logged in `agent_runs` table
- Helpers for MCP: `app/services/agent_run_service.py` (`create_agent_run` / `finish_agent_run`) and `app/core/redaction.py` (`redact_mapping`) for audit rows and safe outbound payloads
- Soft delete only — no hard deletes
- Rate limits on ingestion and AI calls (Phase 5+)
- MCP tools return redacted content: never `api_keys`, session secrets, or password hashes

## Revision History (Planned — Phase 5/7)

Before MCP write tools (`update_page`, `archive_object`) are enabled, a revision history system must be in place so any agent-authored change is fully auditable and reversible.

Implemented `object_revisions` table:

```sql
object_revisions (
  id uuid primary key,
  user_id uuid not null references users(id),
  object_id uuid not null references objects(id),
  agent_run_id uuid null references agent_runs(id),
  change_type text not null,       -- 'create', 'update', 'soft_delete', 'restore'
  before_json jsonb null,
  after_json jsonb null,
  changed_by text not null,        -- 'user:<user_id>' or 'agent:<agent_name>'
  change_summary text null,
  created_at timestamptz not null
)
```

Design decisions:
- `before_json` and `after_json` store a diff-friendly snapshot of the affected row
- Every MCP write that modifies a page or object must create an `object_revisions` row
- `agent_run_id` links the revision to the audit log for the triggering agent action
- Rollback means copying `before_json` back to the live row and creating a new revision row
- Soft-deleted objects can be inspected via revision history even after deletion

See `docs/REVISION_HISTORY.md` for the full design.

## MCP Internal Token Auth (Phase 7A)

FastAPI accepts an `X-KOS-Internal-Token` header as an alternative to the session cookie for local MCP access.

**How it works:**

1. `MCP_INTERNAL_TOKEN` is set in `infra/.env` (gitignored, never committed).
2. FastAPI `get_current_user` in `core/deps.py` checks the header before the cookie.
3. Match is verified with `secrets.compare_digest` (timing-safe).
4. On match: loads the first non-deleted user (single-user local appliance).
5. If token config is empty: header is silently ignored; no authentication bypass.

**Security properties:**
- Token is never logged, returned in API responses, or exposed through MCP tools.
- Empty token = feature disabled (safe default — no header value can match an empty secret).
- Timing-safe comparison prevents oracle attacks.
- User ownership filtering is preserved: all objects queries still filter by `user_id`.

**Limitation:** Multi-user instances are not supported through MCP in Phase 7A. The token grants access as the first active user. Phase 7B will address per-user MCP auth if needed.

## MCP Server Safety (Phases 7A + 7B)

- **Disabled by default** (`MCP_ENABLED=false`). Server exits immediately if not enabled.
- **stdio transport only** — no HTTP server, no new open port.
- **Tool allowlist** (`MCP_ALLOWED_TOOLS`) enforced at startup. Tools not in the list are not registered.
- **Write tools gated** (`MCP_ALLOW_WRITE_TOOLS=false` by default) — even if listed in the allowlist, write tools are not registered unless the flag is `true`.
- **No shell execution** — no tools that run commands or access the filesystem arbitrarily.
- **Secret redaction** — `redact_dict()` applied to every tool response. Keys: `api_key`, `openai_api_key`, `session_secret`, `mcp_internal_token`, `token`, `token_hash`, `password`, `password_hash`, `secret`.
- **`answer_from_kb`** — calls the Phase 5 AI endpoint; returns a structured error when AI is unavailable.

### Write-Tool Safety Invariants (Phase 7B)

1. **Rate limiting** — Redis sliding-window counter per agent identity (`X-KOS-Agent-Id` header). Default: 60 writes/minute, 600 writes/hour. Rate-limit rejection never touches the database.
2. **Audit trail** — Every write call creates an `agent_runs` row with tool name, input summary (content stripped), agent identity, and completion status (`success`/`failed`).
3. **Revision history** — Mutating writes (`update_page`, `archive_object`, `restore_revision`) capture a before/after snapshot in `object_revisions`, linked to the `agent_runs` row by `agent_run_id`.
4. **Soft-delete only** — `archive_object` sets `is_archived=true`; it never calls `DELETE` or sets `deleted_at`. Data is always recoverable.
5. **`LIBRARY_ROOT` enforcement** — `ingest_file` validates the path with `validate_path_under_library_root()`: resolves symlinks, checks `is_relative_to(LIBRARY_ROOT)`, rejects escapes.
6. **URL safety** — `ingest_url` rejects `file://`, `localhost`, loopback IPs (`127.0.0.0/8`), and link-local ranges before calling the API.
7. **Optimistic locking** — `update_page` accepts an optional `expected_version`; returns 409 Conflict if the page was modified between read and write.

## Backups

- Daily local backup of Postgres dump + Qdrant storage + library assets
- Weekly compressed backup
- Manual one-click backup via `scripts/backup.sh`
