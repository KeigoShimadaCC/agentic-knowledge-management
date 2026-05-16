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

- `OPENAI_API_KEY` stored in `infra/.env` (gitignored). Used for vector embeddings (`text-embedding-3-small`) and all LLM calls. No Anthropic key is currently in use — Anthropic is a planned future option behind the `EmbeddingProvider`/`call_ai()` abstraction.
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

## Revision History (Phase 5+)

Revision history is implemented and is required before MCP write tools (`update_page`, `archive_object`) are enabled. Any agent-authored change must be fully auditable and reversible.

Implemented `object_revisions` table:

```sql
object_revisions (
  id uuid primary key,
  user_id uuid not null references users(id),
  object_id uuid not null references objects(id),
  agent_run_id uuid null references agent_runs(id),
  rev_num integer not null,
  changed_by varchar(64) not null, -- 'user:<user_id>' or 'agent:<agent_name>'
  before_snapshot jsonb not null,
  after_snapshot jsonb not null,
  created_at timestamptz not null
)
```

Design decisions:
- `before_snapshot` and `after_snapshot` store a diff-friendly snapshot of the affected row
- Every MCP write that modifies a page or object must create an `object_revisions` row
- `agent_run_id` links the revision to the audit log for the triggering agent action
- Rollback means copying the previous snapshot back to the live row and creating a new revision row
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
- **`answer_from_kb`** — wired to `POST /api/v1/ai/answer`. Returns a structured `{error: "ai_disabled"}` dict (not an exception) when the server has no `OPENAI_API_KEY` (503 from the API layer). All other `httpx` errors propagate normally.

### Write-Tool Safety Invariants (Phase 7B)

1. **Rate limiting** — Redis sliding-window counter per agent identity (`X-KOS-Agent-Id` header). Default: 60 writes/minute, 600 writes/hour. Rate-limit rejection never touches the database.
2. **Audit trail** — Every write call creates an `agent_runs` row with tool name, input summary (content stripped), agent identity, and completion status (`success`/`failed`).
3. **Revision history** — Mutating writes (`update_page`, `archive_object`, `restore_revision`) capture a before/after snapshot in `object_revisions`, linked to the `agent_runs` row by `agent_run_id`.
4. **Soft-delete only** — `archive_object` sets `is_archived=true`; it never calls `DELETE` or sets `deleted_at`. Data is always recoverable.
5. **`LIBRARY_ROOT` enforcement** — `ingest_file` validates the path with `validate_path_under_library_root()`: resolves symlinks, checks `is_relative_to(LIBRARY_ROOT)`, rejects escapes.
6. **URL safety** — `ingest_url` rejects `file://`, `localhost`, loopback IPs (`127.0.0.0/8`), and link-local ranges before calling the API.
7. **Optimistic locking** — `update_page` accepts an optional `expected_version`; returns 409 Conflict if the page was modified between read and write.

### Career Tools (Phase 9D)

Career write tools (`create_project`, `update_project`, `archive_project`, `link_to_project`, `unlink_from_project`, `extract_project`, `generate_and_save_resume_bullets`, `generate_and_save_interview_story`) share all seven invariants above.

Additional notes specific to career tools:

- **No new secrets** — career tools use the same `X-KOS-Internal-Token` auth. No extra credentials are introduced.
- **AI generation + save atomicity** — `generate_and_save_*` tools call the AI endpoint then save only if generation succeeds. A 503 from the AI endpoint is caught client-side and returned as an error dict; no audit row is written for the failed generation.
- **Edge idempotency** — `link_to_project` calls `POST /api/v1/edges` which is idempotent on `(source_id, target_id, kind)`. Repeated links to the same project produce one edge row.
- **Project mutations** — `create_project` and `update_project` call `POST/PATCH /api/v1/projects`. Project mutations are audited via `agent_runs` rows; `object_revisions` rows are written for mutations on pages and sources but not yet for projects (planned follow-up). Revision history for pages and sources is unaffected.

## External MCP Connection Env Var Encryption (Phase 12A)

Secrets stored in `mcp_connections.env_vars` (API keys for external MCP servers such as GitHub or Brave Search) are encrypted at rest using Fernet symmetric encryption from the `cryptography` library.

**Key management:**
- Set `MCP_ENV_ENCRYPTION_KEY` in `infra/.env` to a Fernet key generated with:
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
- If the key is absent or empty, any create/update request that includes `env_vars` returns HTTP 400. Connections without env vars can still be saved.
- The key must be rotated manually (no automated rotation in 12A). To rotate: decrypt all rows with the old key, re-encrypt with the new key, then update `MCP_ENV_ENCRYPTION_KEY`.

**What is encrypted:** only JSONB column values (`env_vars.{key}` values). Column keys remain plaintext so row inspection shows which vars are configured without revealing their contents.

**API responses:** all `GET /api/v1/mcp-connections/*` responses redact env var values to `"*****"` regardless of the caller. The plaintext values are never returned over the API.

**Subprocess env passing:** the `/test` endpoint decrypts env vars in memory, merges them with a whitelist of inherited env vars (`PATH`, `HOME`, `TMPDIR`, `TEMP`, `TMP`), and passes the result directly to the subprocess environment. The decrypted values are never written to disk or logged.

## Search Output Encoding (XSS Mitigation)

The keyword and hybrid search endpoints return snippets as a structured `{text, highlights}` object — not raw HTML. `ts_headline` output is parsed with sentinel characters (`\x01` / `\x02`) server-side; the resulting plain text and character ranges are delivered as JSON. The frontend renders highlighted segments via React text nodes (not `dangerouslySetInnerHTML`), so user-supplied `<script>` or other HTML in page content cannot execute in the browser. Regression tests verify this with a `<script>` payload in page content.

## Backups

- Manual local backups are available through `bash scripts/backup.sh`.
- The script writes to `~/KnowledgeOS/backups/<timestamp>/` and includes a custom-format Postgres dump plus a compressed copy of `~/KnowledgeOS/library/`.
- Qdrant snapshot creation is best-effort because Qdrant is a rebuildable index, not canonical storage.
- Restore Postgres and the library together. A database-only restore can leave object rows pointing at missing files; a file-only restore can leave orphaned originals with no object metadata.
