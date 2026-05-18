# Phase PHONE-01A — Mobile Backend Auth & API

**Status:** Complete
**Goal:** Add bearer-token auth for native clients AND fix the stub `get_current_user()` so the existing cookie path actually validates sessions.
**Wave:** 1 (parallel with 01B, 01C)
**Branch:** `phase-phone-01a-backend-auth`
**Worktree:** `worktrees/kos-phone-01a`
**Depends on:** PHASE-PHONE-00
**Blocks:** PHASE-PHONE-02A

## Scope

Only `services/api/`, `tests/api/`, and `docs/` (API.md + SECURITY.md). Do **not** touch `apps/`, `infra/`, or `scripts/`.

## Critical context

`services/api/app/core/deps.py:9-16` currently returns the first non-deleted user with no real validation. Cookie auth in `auth.py:21-30` writes the cookie but the dependency never reads it. This phase **fixes that bug** as part of the bearer-token work — same code path resolves either auth surface.

## Files likely touched

- `services/api/app/core/deps.py` — real `get_current_user`
- `services/api/app/api/v1/auth.py` — add mobile endpoints
- `services/api/app/api/v1/router.py` — wire `/mobile/*` route
- `services/api/app/models/session.py` — add `client_type` column (`"web" | "ios"`), `device_name`, nullable
- `services/api/app/schemas/auth.py` (new or extended) — mobile login/bootstrap shapes
- `services/api/app/services/auth_service.py` (new or extended) — token issue/hash/verify
- `services/api/alembic/versions/<new>_mobile_sessions.py` — migration
- `tests/api/test_auth_mobile.py` (new)
- `tests/api/test_auth.py` — regression for cookie path now that it actually validates
- `docs/API.md`, `docs/SECURITY.md`

## Endpoints to add

- `POST /api/v1/auth/mobile-login` → returns `{ token, user, expires_at }` (raw token returned **once**)
- `POST /api/v1/auth/mobile-logout` → revokes the bearer token
- `GET  /api/v1/mobile/bootstrap` → returns `{ user, capabilities: { ai_enabled, embeddings_enabled, upload_enabled, mobile_api_version } }`

## Tasks

1. Alembic migration: add `client_type` (default `"web"`), `device_name` (nullable) to `sessions`. Backfill existing rows to `"web"`.
2. Token model: opaque 32-byte URL-safe random; store SHA-256 hash; `token_hash` is already unique-indexed in the table.
3. Service helpers: `issue_mobile_session(user, device_name) -> raw_token`, `revoke_session(token_hash)`, `resolve_session(raw_token | cookie) -> Session`.
4. Rewrite `get_current_user` in `core/deps.py`:
   - Prefer `Authorization: Bearer <token>` if present.
   - Else fall back to `kos_session` cookie.
   - Validate hash, expiry, and `deleted_at IS NULL`.
   - On failure: 401 with `{"detail": "Not authenticated", "code": "unauthenticated"}`.
   - Update `last_seen`.
5. Wire mobile-login/logout/bootstrap. Do not log raw tokens. Do not return raw tokens after issuance.
6. Capabilities probe in bootstrap: read `OPENAI_API_KEY` presence, embedding flag, etc. Keep it boolean-only — no secret leakage.
7. Tests:
   - mobile-login success, wrong password, missing email
   - mobile-logout (revoked token returns 401 next call)
   - bearer token in Authorization header authenticates `/auth/me`
   - cookie still authenticates `/auth/me` (regression)
   - other-user access returns 404 not 403 (no enumeration)
   - token never appears in response bodies after creation
   - token never appears in logs (assert via caplog)
8. Update `docs/API.md` with the three new endpoints + Auth header section.
9. Update `docs/SECURITY.md` with token storage rules (hash-only, one-time issuance, revocation).

## Definition of done

- `cd tests && uv run pytest api/ -q` passes (full suite).
- Alembic migration applies cleanly forward and backward.
- No raw token in logs (verified with `caplog` assertion).
- `MCP_INTERNAL_TOKEN` is **not** referenced anywhere new.
- Docs updated.
- `PROGRESS.md` updated.

## Validation

```bash
cd tests && uv run pytest api/test_auth.py api/test_auth_mobile.py -q
cd services/api && uv run ruff check . && uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head
```

## Out of scope

- iOS app changes (PHASE-PHONE-02A).
- Docker exposure (PHASE-PHONE-01B).
- MCP_INTERNAL_TOKEN refactor.
