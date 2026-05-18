# Phase PHONE-00 — Mobile Architecture & Contract

**Status:** Complete
**Goal:** Produce the canonical mobile spec docs before any implementation. Solo phase. Docs-only.
**Wave:** 0
**Branch:** `phase-phone-00-mobile-contract`
**Worktree:** `worktrees/kos-phone-00`
**Depends on:** none
**Blocks:** PHASE-PHONE-01A, 01B, 01C

## Scope

Solo, docs-only. No code changes outside `project-phases/` and `docs/`.

## Files to create

- `docs/MOBILE_APP.md` — product spec (MVP user stories, non-goals, screens map)
- `docs/MOBILE_API_CONTRACT.md` — endpoint inventory the phone consumes; bearer-auth request/response shapes; error envelope
- `docs/MOBILE_NETWORKING.md` — three network profiles (Simulator, LAN, Tailscale); ATS rules
- This phase file (already created)

## Tasks

1. Read `project-phases/IDEA-iPHONE-APP.md` end-to-end. Treat as source of truth.
2. Read `docs/API.md`, `docs/SECURITY.md`, `infra/docker-compose.yml`, `services/api/app/api/v1/auth.py`, `services/api/app/models/session.py`, `services/api/app/core/deps.py`.
3. Write `docs/MOBILE_APP.md`. Include:
   - MVP scope (connect, login, search, read, capture text, capture photo, KB Q&A).
   - Non-goals (no offline-first sync, no rich editor, no App Store, no Android, no direct DB).
   - **Backend endpoints intentionally NOT exposed on mobile MVP** (so coders don't accidentally implement them):
     - `POST /api/v1/chats/import` — chat import is a desktop-paste workflow, not MVP.
     - `POST /api/v1/ai/triage` — bulk triage is not a mobile use case for MVP.
     - `DELETE /api/v1/objects/{id}` and `POST /api/v1/objects/{id}/restore` — destructive ops deferred until edit-lite stabilizes.
     - `POST /api/v1/search/vector` and `GET /api/v1/search/keyword?q=` — mobile uses `/search/hybrid` only (degrades to keyword when embeddings are off).
     - Career generators (`/ai/extract-project`, `/ai/generate-resume-bullets`, `/ai/generate-interview-story`) — out of MVP.
   - Screen map: Connect, Login, Home, Search, ObjectDetail (dispatcher), PageDetail, SourceDetail, ChatDetail, ProjectDetail, Capture, AI, Settings.
4. Write `docs/MOBILE_API_CONTRACT.md`. Include:
   - Bearer-token request/response shape for `/auth/mobile-login`, `/auth/mobile-logout`, `/mobile/bootstrap`.
   - Full read-side endpoint table (objects, pages, sources, assets, search/hybrid, chats, projects, ai/*).
   - Error envelope: `{"detail": "...", "code": "..."}`.
   - Pagination conventions.
5. Write `docs/MOBILE_NETWORKING.md`. Include:
   - Simulator profile (`http://127.0.0.1:8001`).
   - Same-Wi-Fi profile (`http://<mac-lan-ip>:8001`) and the `docker-compose.mobile.yml` override design.
   - Tailscale profile.
   - ATS strategy: narrow exceptions only, document removal once HTTPS.
   - Strict rule: only api is exposed; never postgres/redis/qdrant.

## Definition of done

- Three docs committed under `docs/`.
- All assertions about endpoints cross-checked against actual `services/api/app/api/v1/` files (no hallucinated routes).
- `PROGRESS.md` updated with PHASE-PHONE-00 row.
- No code in `services/`, `apps/`, or `infra/` touched.

## Validation

- `git diff --name-only main...HEAD` shows only `docs/MOBILE_*.md`, `project-phases/PHASE-PHONE-00-*.md`, `PROGRESS.md`.
- Each documented endpoint exists in the codebase (`grep -r "@router" services/api/app/api/v1/`).
