# PHASE-FIX-04 — Security Audit & Fix

> **Type:** Remediation plan (framework-based security audit)
> **Audit date:** 2026-05-18
> **Frameworks:** OWASP Top 10 (2025), OWASP ASVS 5.0, OWASP MASVS, OWASP LLM/Agentic Top 10
> **Source audit:** Codex read-only audit (criticals + highs + mids)
> **Scope:** Verified findings in MCP connections, web/API surface, mobile profile, and personal-identifier leakage in a now-**public** repository.
> **Out of scope:** Next.js 15 migration (scheduled as a future phase, see S9), Python dependency upgrades beyond what `pip-audit` flags as known-vulnerable.

---

## Context

A framework-based security audit (OWASP Top 10 / ASVS / MASVS / LLM Top 10) surfaced one critical, four high, and three mid-severity findings in the KnowledgeOS codebase, plus personal identifier leakage across tracked files. The repository is **public on GitHub**, so identifier scrub jumps to priority 1 — every fix in this phase should land on an already-scrubbed tree to avoid leaking the maintainer's name/paths through review traffic.

The fixes are surgical and well-scoped. Most are 10–30 line changes that reuse helpers already in the codebase (notably `validate_safe_http_url` in `services/api/app/core/url_safety.py`, which exists but isn't called from the MCP path).

This is a *remediation* phase, not a feature phase. No new product surface; only hardening and hygiene.

---

## Execution Setup

1. **Worktree.** Use a worktree to keep `main` clean while this phase runs.
   ```bash
   git fetch origin
   git worktree add -b phase-fix-04-security ../akm-phase-fix-04 origin/main
   cd ../akm-phase-fix-04
   ```
   *Note: the path `../akm-phase-fix-04` is suggested but contains no personal identifiers — pick any path you prefer. Do **not** commit the worktree path into any doc.*

2. **Copy this plan into the repo** as `project-phases/PHASE-FIX-04-SECURITY-AUDIT-AND-FIX.md` so it lives with the other phase docs.

3. **Verify clean baseline:** `pnpm install && pnpm typecheck` in `apps/web`, `uv sync && uv run pytest -q` in `services/api`. Note any pre-existing failures so we don't blame them on this phase.

4. **Branch off `main`** (worktree above already does this). One commit per task (S1–S9). Push after each commit; open one PR at the end titled `phase-fix-04: security audit & fix`.

---

## Task Order Rationale

Codex recommended Next.js first. The recommendation here is **scrub first** because the repo is public — every subsequent task commit risks adding personal identifiers, and we want the tree clean before merge traffic. After scrub, sequence by severity.

| # | Task | Severity | Effort |
|---|---|---|---|
| S1 | Personal-identifier scrub (public-repo hygiene) | — | M |
| S2 | Next.js 14.x patch (close critical middleware-bypass CVE) | Critical | XS |
| S3 | SSRF validation on MCP HTTP/SSE URLs | High | S |
| S4 | Scope MCP internal token to a single service user | High | S |
| S5 | Mobile profile hardening: disable open-reg + LAN allowlist | High | M |
| S6 | Asset upload size cap | Mid | XS |
| S7 | Filter `deleted_at` in `get_object_or_404` | Mid | XS |
| S8 | Consolidate redaction helpers (case-insensitive, shared) | Mid | S |
| S9 | Add `pip-audit` to CI + file Next 15 migration follow-up | Low | S |

---

## S1 — Personal-identifier scrub (public-repo hygiene)

### Goal
Remove the maintainer's name, absolute home paths, GitHub username, Tailscale hostname, and personal device names from all tracked files before any subsequent commit lands.

### Situation
The repo went public; a pre-scrub grep showed ~28 identifier hits across 14 tracked files. By category:

| Category | Where |
|---|---|
| Maintainer absolute home path | `docs/AI-CODER-BRIEFING.md`, `docs/AGENT_GUIDE.md`-adjacent, `tests/e2e/AUDIT-15A.md`, four `project-phases/PHASE-*.md` headers, `PROGRESS.md` worktree paths (4 lines) |
| GitHub username | Repo URLs in `project-phases/PHASE-2-SOURCES.md`, `PHASE-3-SEARCH.md`, `PHASE-5-AI-ASSISTANT.md`, `PHASE-ENHANCE-04A/B/C-GITHUB-WIKI*.md` |
| Tailscale hostname | `PROGRESS.md` mobile-network smoke output |
| Personal device name | `docs/API.md`, `docs/MOBILE_API_CONTRACT.md`, `project-phases/IDEA-iPHONE-APP.md`, `tests/api/test_auth_mobile.py` (functional fixture) |
| Maintainer first name | `apps/web/src/components/ui/Avatar.tsx` JSDoc example, `tests/api/test_chats.py` assertion fixture, `tests/fixtures/chats/chatgpt_sample.json` |

The test-fixture hits are functional (assertions reference the literal). They need lockstep replacement of fixture + assertion strings.

### Approach
Single sweep, one commit. Replacement scheme:

| Source form | Replacement form |
|---|---|
| absolute path under user home | `$HOME/...` (in shell snippets) or strip to relative path / `<workdir>/...` in prose |
| GitHub username | `OWNER` (works inside URLs and code spans) |
| Tailscale hostname | `your-host.ts.net` |
| device name literal | `"Example iPhone"` (docs) / `"Demo iPhone"` (tests) |
| maintainer first name | `"Demo User"` (component JSDoc + test fixtures + assertions) |

Process:
1. Re-run the inventory grep (see Verification) before editing.
2. Edit file-by-file (don't blanket-sed — review each context).
3. For test fixtures: change the JSON/Python literal **and** the matching assertion in the same edit, then run `cd tests && uv run pytest api/test_chats.py api/test_auth_mobile.py` to confirm green.
4. After all edits, re-run the inventory grep to confirm zero hits.

### Verification
```bash
# Pattern uses regex character classes (e.g. [K]eigo) so the documented pattern
# itself does not contain the literal substring and won't false-positive on this file.
git ls-files | xargs grep -nI '[K]eigo\|[k]eigoshimada\|[k]eigos-mac-mini\|[K]eigoShimadaCC' || echo "scrub clean"
cd tests && uv run pytest api/test_chats.py api/test_auth_mobile.py
```

### Commit
`chore(repo): scrub personal identifiers from public tree`

---

## S2 — Next.js 14.x security patch

### Goal
Close the critical "Authorization Bypass in Next.js Middleware" CVE and the high-severity advisories patched in the 14.2.x line. Do **not** jump to Next 15 in this phase (see S9 for the follow-up).

### Situation
- `apps/web/package.json:42` pins `"next": "14.2.3"`.
- `pnpm audit --prod` reports 1 critical, 9 high, 13 moderate, 4 low.
- The critical advisory is `>=14.2.25` patched. No `middleware.ts` exists in `apps/web/` (reduces blast radius), but the package is still materially stale.
- ESLint plugin `eslint-config-next` is pinned to the same version and should track.

### Approach
Patch within 14.2.x:
1. Bump in `apps/web/package.json`: `"next": "^14.2.32"`, `"eslint-config-next": "^14.2.32"` (or whatever the latest 14.2.x is at install time).
2. `pnpm install` in `apps/web` (regenerates lockfile).
3. `pnpm typecheck && pnpm lint && pnpm build`.
4. Smoke the app in a browser: `pnpm dev`, hit `http://localhost:3000`, navigate to the dashboard, open a page, run a search. Note in commit message that no UI regressions observed.
5. Re-run `pnpm audit --prod` and capture the before/after counts in the commit body.

### Verification
- `pnpm audit --prod` no longer reports the critical advisory.
- Build + typecheck + lint all green.
- Manual smoke: dashboard loads, page open/edit works, search returns results.

### Commit
`chore(web): bump next 14.2.3 → 14.2.32 to close middleware-bypass CVE`

---

## S3 — Validate MCP HTTP/SSE URLs via the existing SSRF helper

### Goal
Route MCP HTTP and SSE connection URLs through `validate_safe_http_url` before opening the client connection, the same way source ingestion already does.

### Situation
- `services/api/app/core/url_safety.py:93–127` defines `validate_safe_http_url(url)` (scheme + blocked hostnames + global-IP enforcement + DNS-rebinding mitigation).
- `services/api/app/api/v1/mcp_connections.py:194–207` calls `streamablehttp_client(url=conn.url)` / `sse_client(url=conn.url)` directly.
- `services/api/app/mcp_client/client.py:36–46` does the same in the runtime client.
- Source ingestion already calls `validate_safe_http_url`; the MCP path is the only consumer that skips it.

### Approach
1. Import `validate_safe_http_url` in `mcp_connections.py` and `mcp_client/client.py`.
2. Call it **at two points**:
   - **On create/update** (in the `mcp_connections.py` route handlers that accept a URL from the user) — fail fast with HTTP 422 on invalid URL.
   - **Immediately before opening the client** in both `_run_sse_test` and the runtime client — defense-in-depth against any URL mutation between create and use.
3. For stdio transport, no URL validation is needed (it's a command).
4. The validator raises `UrlSafetyError`; catch it at the route layer and return 422 with a redacted message.

### Verification
- New unit test `services/api/tests/test_mcp_connections.py::test_create_mcp_connection_rejects_localhost_url` — POST a `http://127.0.0.1:9999` SSE connection, expect 422.
- New unit test `…::test_create_mcp_connection_rejects_metadata_url` — POST `http://169.254.169.254/...`, expect 422.
- Manual smoke: create a legitimate `https://...` HTTP MCP connection, confirm it still works.

### Commit
`fix(mcp): validate HTTP/SSE connection URLs via SSRF helper`

---

## S4 — Scope the MCP internal token to a dedicated service user

### Goal
Replace the "first non-deleted user" lookup with a deterministic mapping to a single, configurable user identity, so the token can't grant access to whichever account happens to have the lowest ID.

### Situation
`services/api/app/services/auth_service.py:93–101`:
```python
async def resolve_mcp_user(db, token):
    if not configured or not token: return None
    if not secrets.compare_digest(token, configured): return None
    result = await db.execute(select(User).where(User.deleted_at.is_(None)).limit(1))
    return result.scalar_one_or_none()
```
No ordering, no scoping. Fine for the current single-user local mode; broken the day a second user exists.

### Approach
Add an optional `mcp_internal_user_id: UUID | None` config field (env: `MCP_INTERNAL_USER_ID`):
1. In `services/api/app/config.py`, add the field (default `None`).
2. In `resolve_mcp_user`:
   - If both `mcp_internal_token` and `mcp_internal_user_id` are set: validate token, then `select(User).where(User.id == settings.mcp_internal_user_id, User.deleted_at.is_(None))`.
   - If only the token is set (legacy/single-user mode): preserve current behavior but log a one-time warning at startup (`logger.warning("MCP token configured without MCP_INTERNAL_USER_ID — falling back to first user. Set MCP_INTERNAL_USER_ID for multi-user safety.")`).
3. Add the env var to `infra/.env.example` with a comment.
4. Document in `docs/SECURITY.md` (the MCP section).

### Verification
- Unit test: with `mcp_internal_user_id` set to a known UUID and two users in DB, `resolve_mcp_user` returns the specified user (not the first-created).
- Unit test: with `mcp_internal_user_id` unset, current fallback behavior preserved + warning logged.

### Commit
`fix(auth): scope MCP internal token to a configured user id`

---

## S5 — Mobile profile hardening: disable open-reg + LAN allowlist

### Goal
When the API runs under the mobile/LAN profile (bound to `0.0.0.0`), refuse open registration by default and reject requests sourced from outside RFC1918/loopback ranges.

### Situation
- `infra/docker-compose.mobile.yml:29` binds API to `0.0.0.0:8001` (intentional — for iPhone access on LAN).
- `services/api/app/config.py:26` `allow_open_registration: bool = True`.
- `apps/ios/.../Info.plist:26–56` allows ATS cleartext for local + Tailscale (this is fine — keep as-is, needed for the on-LAN flow).

Net: today, any device on the LAN (e.g., guest Wi-Fi) can hit `/api/v1/auth/register` and create an account.

### Approach
Two layers (the "both" option):

**Layer 1 — open-reg defaults off in mobile profile.**
1. `infra/docker-compose.mobile.yml`: add `environment: { ALLOW_OPEN_REGISTRATION: "false" }` to the api service.
2. No change to the config.py default (desktop dev keeps `True` for ergonomics).

**Layer 2 — LAN allowlist middleware.**
1. New file `services/api/app/middleware/lan_guard.py`:
   - FastAPI middleware that runs only when `settings.kos_profile == "mobile"` (new config field, default `"desktop"`).
   - Reads `request.client.host`. Uses `ipaddress.ip_address(host).is_private or .is_loopback`.
   - If not allowed, returns 403 with a generic body.
   - Trust `X-Forwarded-For` only if `settings.trusted_proxy_count > 0` (default 0 — don't trust by default).
2. Wire into `services/api/app/main.py` only when `kos_profile == "mobile"`.
3. Add `KOS_PROFILE=mobile` to `docker-compose.mobile.yml` environment.
4. Documentation: update `docs/SECURITY.md` with a "Mobile profile" section explaining both layers and how to add an allowlisted IP for testing.

### Verification
- Unit test (TestClient with `KOS_PROFILE=mobile`): request from `127.0.0.1` → 200; mocked request from `8.8.8.8` → 403.
- Unit test: with `KOS_PROFILE=mobile` and `ALLOW_OPEN_REGISTRATION=false`, `POST /auth/register` returns 403 / disabled response.
- Manual smoke (optional, requires a phone): bring up the mobile compose, confirm iPhone can still authenticate and that registration is blocked.

### Commit
`fix(mobile): disable open-reg and add LAN allowlist for mobile profile`

---

## S6 — Asset upload size cap

### Goal
Reject asset uploads larger than a configurable limit before the body is read into memory. Match the asymmetry that `chat_import` already has.

### Situation
- `services/api/app/api/v1/assets.py:88` does `content = await file.read()` with no cap.
- `chats.py:96` enforces `settings.chat_import_max_bytes` (25 MB default, defined in `config.py:31`).

### Approach
1. Add `asset_upload_max_bytes: int = 100 * 1024 * 1024` to `services/api/app/config.py` (100 MB default; user can tune via env).
2. In `assets.py` upload handler:
   - Check `Content-Length` header first; if present and over limit, return 413.
   - Stream-read in chunks; abort with 413 if accumulated size exceeds limit (handles missing/lying Content-Length).
   - On abort, do not write to library; do not insert any rows.
3. Mirror the chat-import error shape so the frontend can handle both uniformly.

### Verification
- Unit test: POST a 101 MB file → 413.
- Unit test: POST a 1 MB file → 201 (current happy path still works).
- Confirm no asset row + no library file written on the 413 case.

### Commit
`fix(api): cap asset upload size to prevent OOM/DoS`

---

## S7 — Filter `deleted_at` in `get_object_or_404`

### Goal
Soft-deleted objects should not be fetchable by ID through generic object lookups.

### Situation
`services/api/app/services/object_service.py:28–37` does `select(KosObject).where(KosObject.id == object_id, KosObject.user_id == user_id)` with no `deleted_at IS NULL`. Called from 11 sites including `/assets/{id}` GET/download/DELETE and `/objects/{id}` endpoints. The same-file `list_objects` already filters correctly — this is an inconsistency, not a design intent.

### Approach
1. Add `KosObject.deleted_at.is_(None)` to the `get_object_or_404` query.
2. If any caller *needs* deleted objects (e.g., a future restore flow), add a separate `get_object_including_deleted` helper. Audit current callers: none of the 11 currently shown need deleted objects.
3. Add a unit test for each affected endpoint family confirming 404 on a soft-deleted ID.

### Verification
- Unit test: soft-delete an object, then `GET /objects/{id}` → 404.
- Unit test: soft-delete an asset, then `GET /assets/{id}` and `/assets/{id}/download` → 404, and `DELETE /assets/{id}` → 404.

### Commit
`fix(api): exclude soft-deleted objects from get_object_or_404`

---

## S8 — Consolidate redaction helpers (case-insensitive, shared)

### Goal
A single redaction helper used by both the API and the MCP server, with case-insensitive key matching everywhere.

### Situation
- `services/api/app/core/redaction.py:35` — `redact_dict` does exact case-sensitive key match.
- Same file, line 55 — `redact_mapping` does case-insensitive substring match.
- `services/mcp/kos_mcp/redaction.py:20` — only the case-sensitive variant exists.
- Result: `Api_Key`, `Authorization` (uppercase A) can leak through some paths.

### Approach
1. Make `redact_dict` in `core/redaction.py` case-insensitive (it should call the same `_is_sensitive_key` helper used by `redact_mapping`).
2. Make the MCP-side `kos_mcp/redaction.py` either:
   - **Option A:** Import from the shared API helper (preferred if the MCP package already depends on the API package).
   - **Option B:** Mirror the helper inline and add a test that asserts parity with the API version (lighter coupling).
   - Check `services/mcp/pyproject.toml` deps to pick. If MCP is a standalone package, go with Option B.
3. Add a redaction unit test matrix: `api_key`, `API_KEY`, `Api_Key`, `authorization`, `Authorization`, `password`, `session_secret` — all should redact in both helpers.

### Verification
- New test in `services/api/tests/test_redaction.py` covering the case matrix.
- New test in `services/mcp/tests/test_redaction.py` covering the same matrix.

### Commit
`fix(redaction): make key matching case-insensitive across api + mcp`

---

## S9 — CI dependency scanning + Next 15 follow-up

### Goal
Catch the next stale-dependency surprise automatically. Document the Next 15 migration as a separate future phase.

### Situation
- No `pip-audit` or `safety` in tooling (`services/api/pyproject.toml`, `Makefile`, `.github/workflows/ci.yml`).
- Codex couldn't complete the Python-side audit because the tool wasn't installed.
- Next 15 migration is real work (async APIs, caching defaults, React 19) — not appropriate for a security-fix phase.

### Approach
1. Add a `security-audit` job to `.github/workflows/ci.yml`:
   ```yaml
   security-audit:
     runs-on: ubuntu-latest
     steps:
       - uses: actions/checkout@v4
       - uses: pnpm/action-setup@v4
       - uses: actions/setup-node@v4
         with: { node-version: 20, cache: pnpm }
       - run: pnpm install --frozen-lockfile
       - run: pnpm audit --prod --audit-level=high
       - uses: actions/setup-python@v5
         with: { python-version: '3.12' }
       - run: pip install pip-audit
       - run: pip-audit -r services/api/requirements.txt || pip-audit --strict
   ```
   *Tune to actual project layout — uv has its own audit story; if `uv` exposes a vulnerability check, prefer that.*
2. Make the job advisory at first (`continue-on-error: true`) so the existing PR backlog doesn't break. Flip to required after one cleanup pass.
3. Create `project-phases/PHASE-FIX-05-NEXTJS-15-MIGRATION.md` as a stub with:
   - Goal: Next 14.2.x → Next 15.x (and React 18 → 19).
   - Known migration items: async `cookies()`/`headers()`/`params`/`searchParams`, fetch caching defaults flipped, codemods to run.
   - Not scheduled — pickup any time after PHASE-FIX-04 lands.

### Verification
- CI workflow runs on next PR push; `security-audit` job appears (even if advisory).
- `project-phases/PHASE-FIX-05-NEXTJS-15-MIGRATION.md` exists and lists the migration scope.

### Commit
`infra(ci): add dependency vulnerability scan; file Next 15 follow-up`

---

## Accepted-risk notes (deliberately *not* fixed in this phase)

- **MCP stdio command execution** (Codex high). The whole point of stdio MCP servers is to run user-configured local commands (Claude Desktop does the same). The mitigation is upstream: (a) the API must be authenticated, and (b) the user explicitly created the connection. S5 closes the LAN exposure side of this; the stored-command-execution surface remains by design. An optional future hardening is a per-command audit-log entry, but it doesn't change the threat model.
- **Hardcoded dev defaults** (`kospass`, `demo-demo-demo`, `localhost` ports). These are local-dev placeholders in `.env.example` and Docker compose. Leaving as-is; they exist in every Docker tutorial. If we ever publish a hosted version, this needs a separate rotation pass.
- **iOS ATS cleartext exceptions.** Needed for on-LAN access (the actual usage pattern). Already constrained to local + Tailscale hosts in `Info.plist`. Not loosened.

---

## Critical files touched (cheat sheet)

| Task | Files |
|---|---|
| S1 | `docs/AI-CODER-BRIEFING.md`, `docs/API.md`, `docs/MOBILE_API_CONTRACT.md`, `apps/web/src/components/ui/Avatar.tsx`, `PROGRESS.md`, `project-phases/PHASE-{2,3,5,ENHANCE-03,ENHANCE-04A,04B,04C,IDEA-iPHONE-APP}.md`, `tests/api/test_chats.py`, `tests/api/test_auth_mobile.py`, `tests/fixtures/chats/chatgpt_sample.json`, `tests/e2e/AUDIT-15A.md` |
| S2 | `apps/web/package.json`, `apps/web/pnpm-lock.yaml` (regenerated) |
| S3 | `services/api/app/api/v1/mcp_connections.py`, `services/api/app/mcp_client/client.py`, new tests under `services/api/tests/` |
| S4 | `services/api/app/services/auth_service.py`, `services/api/app/config.py`, `infra/.env.example`, `docs/SECURITY.md` |
| S5 | `services/api/app/middleware/lan_guard.py` (new), `services/api/app/main.py`, `services/api/app/config.py`, `infra/docker-compose.mobile.yml`, `docs/SECURITY.md` |
| S6 | `services/api/app/api/v1/assets.py`, `services/api/app/config.py`, new test |
| S7 | `services/api/app/services/object_service.py`, new tests for `/objects` + `/assets` |
| S8 | `services/api/app/core/redaction.py`, `services/mcp/kos_mcp/redaction.py`, new tests |
| S9 | `.github/workflows/ci.yml`, `project-phases/PHASE-FIX-05-NEXTJS-15-MIGRATION.md` (new stub) |

---

## End-to-end verification

After all tasks land, before opening the PR:

```bash
# From repo root
git ls-files | xargs grep -nI '[K]eigo\|[k]eigoshimada\|[k]eigos-mac-mini\|[K]eigoShimadaCC' && exit 1 || echo "scrub clean"

# Frontend
cd apps/web && pnpm install && pnpm typecheck && pnpm lint && pnpm build && pnpm audit --prod --audit-level=high

# Backend
cd ../../services/api && uv sync && uv run ruff check . && cd ../../tests && uv run pytest api/ -q

# Manual smokes
# 1. docker compose -f infra/docker-compose.yml up -d  → http://localhost:3000 → log in, search, open a page
# 2. docker compose -f infra/docker-compose.mobile.yml up -d  → confirm /auth/register returns 403, confirm iPhone client still authenticates from LAN
```

PR title: `phase-fix-04: security audit & fix`
PR body: brief summary per OWASP category + before/after `pnpm audit` counts + confirmation that personal-identifier grep is clean.

---

## Update `PROGRESS.md` at the end

Add a `## PHASE-FIX-04 — Security Audit & Fix` section to `PROGRESS.md` summarizing what shipped, OWASP categories addressed, and the deferred Next 15 follow-up. **Use no absolute paths** in the update.
