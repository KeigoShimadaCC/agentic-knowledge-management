# Phase PHONE-05 — Offline Cache & Queue

**Status:** Planned
**Goal:** Survive a sleeping Mac. Cache recent reads. Queue unsent captures.
**Wave:** 5
**Branch:** `phase-phone-05-offline-cache`
**Worktree:** `../kos-phone-05`
**Depends on:** PHASE-PHONE-03A, 03B
**Blocks:** none

## Scope

Only `apps/ios/KnowledgeOS/Core/Cache/**` (new), `Core/Queue/**` (new), and small additive hooks into existing ViewModels. Do **not** rewrite `APIClient`.

## Tasks

1. **Cache layer** using SQLite (via SQLite.swift or raw `Sqlite3`) stored in the app's `Library/Caches/`. Tables: `recent_objects`, `recent_searches`, `cached_details (object_id, kind, payload_json, fetched_at)`.
2. Read-through cache: ViewModels ask cache first, then API. Stale-while-revalidate: render cached, refresh in background, replace if changed.
3. **Capture queue** SQLite table `pending_uploads (id, kind, payload, retry_count, last_error, created_at)`. On capture failure, enqueue. Background task `BGAppRefreshTask` drains the queue when reachable.
4. **Sync status** UI: small banner on Home showing "N pending" + tap to inspect.
5. **No destructive auto-resolution** — conflicts surface the same way as PHASE-PHONE-04.
6. Tests: cache hit/miss, queue persistence across app relaunch, retry exponential backoff.

## Definition of done

- App is usable for read while backend is unreachable.
- Quick note can be drafted offline; appears in KB once backend is back.
- Sync status banner reflects truth.
- No silent data loss in any test.
- `PROGRESS.md` updated.

## Out of scope

- Full offline-first sync (CRDT/op log) — out of MVP scope forever.
- Conflict auto-merge.
- Cached AI responses.
