# Phase PHONE-01B — Mac↔iPhone Networking

**Status:** Planned
**Goal:** Make the FastAPI backend reachable from iOS Simulator and physical iPhone safely. Only api gets exposed; postgres/redis/qdrant stay loopback.
**Wave:** 1 (parallel with 01A, 01C)
**Branch:** `phase-phone-01b-networking`
**Worktree:** `../kos-phone-01b`
**Depends on:** PHASE-PHONE-00
**Blocks:** physical-device validation (Wave 6)

## Scope

Only `infra/`, `scripts/`, and `docs/MOBILE_NETWORKING.md` (extending Phase 00's draft). Do **not** touch `services/`, `apps/`, or test code.

## Files to create / touch

- `infra/docker-compose.mobile.yml` (new) — override exposing only api on `0.0.0.0:8001`
- `scripts/mobile_network_check.sh` (new) — preflight reachability + safety audit
- `docs/MOBILE_NETWORKING.md` — extend Phase 00 draft with operator runbook
- `infra/.env.example` — document any new optional env (e.g. `MOBILE_API_BIND_HOST`)

## Tasks

1. Write `infra/docker-compose.mobile.yml`:
   ```yaml
   services:
     api:
       ports:
         - "0.0.0.0:8001:8000"
   ```
   Explicitly does **not** override postgres, redis, qdrant, worker, web. Document the merge command:
   `docker compose -f infra/docker-compose.yml -f infra/docker-compose.mobile.yml up -d`.
2. Write `scripts/mobile_network_check.sh`. Must be `chmod +x`. Checks:
   - api reachable at `http://127.0.0.1:8001/api/v1/health` from Mac.
   - prints suggested LAN URL using `ipconfig getifaddr en0` (and fallback for `en1`).
   - prints suggested Tailscale URL using `tailscale status --json` if `tailscale` is on PATH.
   - asserts postgres/redis/qdrant ports are NOT bound to `0.0.0.0` (parse `docker port`).
   - prints PASS/WARN/FAIL summary with non-zero exit on FAIL.
3. Document three profiles in `docs/MOBILE_NETWORKING.md`:
   - Simulator-only (default).
   - Same-Wi-Fi (uses mobile override).
   - Tailscale (no Docker override needed; api binds via host).
4. Document ATS exception strategy (narrow `NSExceptionDomains` for `127.0.0.1`, LAN range, `*.ts.net`).
5. Document teardown: how to stop the mobile override and return to loopback-only.

## Definition of done

- `bash scripts/mobile_network_check.sh` runs cleanly on the Mac with the default stack up.
- Mobile override merges cleanly with the base compose file (`docker compose ... config` succeeds).
- Postgres/Redis/Qdrant port bindings are loopback in the mobile profile (verified by the script).
- `PROGRESS.md` updated.

## Validation

```bash
docker compose -f infra/docker-compose.yml up -d
bash scripts/mobile_network_check.sh          # simulator profile
docker compose -f infra/docker-compose.yml -f infra/docker-compose.mobile.yml up -d
bash scripts/mobile_network_check.sh          # LAN profile (expect WARN/PASS, never FAIL on safety)
```

## Out of scope

- iOS ATS plist edits (done in PHASE-PHONE-01C scaffold or 02A).
- Auth changes.
- HTTPS / TLS — defer until later phase.
