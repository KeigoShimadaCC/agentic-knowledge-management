# Phase 11C — Proactive Background AI Processing

> **Status:** ✅ Complete (merged to `feat/phase-11c-background-ai`, 2026-05-16)
> **Owner:** Backend-heavy (worker pipeline + thin frontend status indicator)
> **Audience:** AI coder (Codex). Read end-to-end before writing a single line.
> **Estimated effort:** 1 PR, ~9 commits, ~700–900 LOC including tests.
> **Worktree branch:** `feat/phase-11c-background-ai`
> **Blocks:** nothing (standalone enhancement).
> **Blocked by:** Phase 5 (AI endpoints), Phase 2 (ingestion pipeline with RQ). Both live on `main`.
> **Parallel-safe with:** PHASE-11A-TUTORIAL (in progress), PHASE-11B-INLINE-EDITOR-AI (planned). Conflict map verified in §2.

---

## 0. North Star

Today every AI action in KnowledgeOS is user-initiated. You have to open a page, scroll to the AI Panel, and click "Summarize". Nothing happens automatically when you save a note or when a source finishes ingesting.

Phase 11C flips this: when a page is saved or a source finishes processing, a background job automatically runs a configurable set of AI tasks (summarize, extract claims, suggest links) and writes the results into the same metadata fields that Phase 5 already defines. The user sees the results passively the next time they open the AI Panel — or they're notified via the Inbox when the batch completes.

This is a pure backend enhancement. The AI Panel already renders whatever metadata it finds. No new frontend components are required; the only UI change is a small status badge in `AiPanel.tsx` and a new inbox item type. All AI processing remains opt-out — a global flag (`AI_AUTO_PROCESS=true`) controls whether jobs are enqueued, and individual objects can opt out via `metadata_["ai_auto_process"] = false`.

**What Phase 11C adds:**

| Surface | What changes |
|---|---|
| Worker service | 3 new background task functions + shared dispatcher |
| Page save hook | Enqueues background AI job after successful page PATCH/PUT |
| Source ingest hook | Enqueues background AI job when ingestion_status → `ready` |
| Config | `AI_AUTO_PROCESS`, `AI_AUTO_PROCESS_TASKS` flags |
| Inbox API | New inbox item type `ai_batch_complete` surfaced when a job finishes |
| `AiPanel.tsx` | Tiny "AI processed X min ago" timestamp shown if `ai_processed_at` metadata exists |
| Tests | 10+ backend integration and worker unit tests |

**What Phase 11C does NOT do:**

- No new database tables. Results are written into the existing `metadata_` JSONB and the existing `agent_runs` table.
- No streaming. Job results are written on completion; the frontend polls or refreshes.
- No push notifications. The inbox item is discovered on next inbox load.
- No per-object UI toggle to enable/disable auto-processing (that's a follow-up). The opt-out is via a raw metadata key for now.
- No MCP exposure of job triggering. Future.
- No changes to `Sidebar.tsx`, `AppShell.tsx`, `layout.tsx` — those belong to Phase 11A.
- No changes to existing Phase 5 endpoints — `/ai/summarize`, `/ai/extract-claims`, `/ai/suggest-links` are unchanged in signature and behavior. The background jobs call the same service-layer functions, not the HTTP endpoints.

---

## 1. Worktree and delegation model

**All code in this phase is written by Codex, not Claude.** Claude's role is to plan, assign subtasks, review output, and enforce the non-breakage contract below.

### 1.1 Worktree setup (Claude runs this once before handing off)

```bash
# From the repo root on main:
git worktree add ../phase-11c-worktree feat/phase-11c-background-ai
# Codex works exclusively inside ../phase-11c-worktree
# Claude reviews, merges back to main when all subtasks pass quality gates.
```

### 1.2 Quality gates Codex must pass before each commit

```bash
# Backend lint (run from services/api inside the worktree)
uv run ruff check .
uv run ruff format --check .

# Backend tests
cd tests && uv run pytest api/test_background_ai.py -v    # target file
cd tests && uv run pytest api/ unit/ -q                    # full regression — must stay green

# Frontend typecheck (only for the AiPanel change in Subtask 6)
cd apps/web && pnpm typecheck && pnpm lint
```

No commit ships if any gate is red.

---

## 2. Conflict map (verified file-by-file)

### vs. PHASE-11A-TUTORIAL (in progress)

11A owns:
```
apps/web/src/app/(app)/layout.tsx
apps/web/src/components/layout/AppShell.tsx
apps/web/src/components/layout/Sidebar.tsx
services/api/app/api/v1/__init__.py
NEW: services/api/app/api/v1/tutorial.py
NEW: services/api/app/services/tutorial_seed_service.py
NEW: apps/web/src/components/tutorial/*
PROGRESS.md
```

11C wants:
```
EDIT: services/api/app/api/v1/pages.py           (post-save hook)
EDIT: services/api/app/services/source_service.py (post-ingest hook)
EDIT: services/api/app/config.py                  (2 new flags)
EDIT: apps/web/src/components/ai/AiPanel.tsx      (badge, read-only metadata display)
NEW:  services/worker/tasks/ai_jobs.py
EDIT: services/worker/tasks/__init__.py            (append import)
NEW:  tests/api/test_background_ai.py
NEW:  tests/unit/test_ai_jobs.py
EDIT: docs/API.md, PROGRESS.md
```

**Overlap:** `PROGRESS.md` only (append-merge, trivially resolved). Zero code-file conflict.

`services/api/app/api/v1/__init__.py` is touched by 11A but NOT by 11C. The page-save hook goes inside `pages.py`, not the router registry.

### vs. PHASE-11B-INLINE-EDITOR-AI (planned, other worktree)

11B owns:
```
EDIT: apps/web/src/components/editor/SlashMenu.tsx
EDIT: apps/web/src/components/editor/BubbleMenu.tsx
EDIT: apps/web/src/components/editor/extensions/SlashMenuExtension.ts
EDIT: apps/web/src/lib/api.ts
EDIT: services/api/app/api/v1/ai.py
NEW:  apps/web/src/components/editor/AiSlashCommand.tsx
NEW:  services/api/app/schemas/inline_ai.py
NEW:  tests/api/test_inline_ai.py
EDIT: docs/API.md, PROGRESS.md
```

**Overlap with 11C:**
- `PROGRESS.md` (append-merge, trivial three-way).
- `docs/API.md` (each appends a distinct named section, trivial three-way).
- `apps/web/src/components/ai/AiPanel.tsx` — 11B does **not** touch `AiPanel.tsx`. 11C adds a single timestamp line. **No conflict.**
- `services/api/app/api/v1/ai.py` — 11C does **not** touch `ai.py`. Background jobs call service functions directly. **No conflict.**

Zero code-file conflict.

---

## 3. Files this phase MAY NOT touch

| File | Why off-limits |
|---|---|
| `apps/web/src/app/(app)/layout.tsx` | Phase 11A owns. |
| `apps/web/src/components/layout/AppShell.tsx` | Phase 11A owns. |
| `apps/web/src/components/layout/Sidebar.tsx` | Phase 11A owns. |
| `services/api/app/api/v1/__init__.py` | Phase 11A owns (tutorial router). |
| `services/api/app/api/v1/ai.py` | Phase 11B appends to this file. 11C does not touch it. |
| `services/api/app/api/v1/router.py` | No new routes in 11C. |
| `services/api/app/ai/client.py` | Phase 5 plumbing. Used read-only (imported, not edited). |
| `services/api/app/schemas/ai.py` | Phase 5 schema file. Not needed in 11C. |
| `tests/api/test_ai.py` | Existing file. New tests go in `test_background_ai.py`. |
| Any alembic migration | No new schema in 11C. |
| `services/mcp/**` | Out of scope for 11C. |

---

## 4. Configuration flags

**File to modify:** `services/api/app/config.py`

Append two fields to the existing `Settings` class (or equivalent config object):

```python
ai_auto_process: bool = Field(False, description="Enqueue background AI jobs on page save and source ingest.")
ai_auto_process_tasks: list[str] = Field(
    default_factory=lambda: ["summarize", "extract_claims", "suggest_links"],
    description="Which AI tasks to run in background. Subset of: summarize, extract_claims, suggest_links.",
)
```

Inspect `config.py` before modifying — follow the exact `Field` pattern already in use. Do not introduce a new config mechanism.

**Env var names (auto-derived by Pydantic Settings):**
- `AI_AUTO_PROCESS=true`
- `AI_AUTO_PROCESS_TASKS=summarize,extract_claims` (comma-separated, parsed by Pydantic)

When `AI_AUTO_PROCESS=false` (the default), no background jobs are enqueued and the system behaves exactly as it does today.

---

## 5. Worker task module (`services/worker/tasks/ai_jobs.py`)

New file. Contains the RQ task functions that run AI processing in the background.

Inspect the existing worker task files (e.g., ingestion task file) before writing to match the exact module structure, import style, and error-handling pattern used in the worker service.

### 5.1 Module structure

```python
# services/worker/tasks/ai_jobs.py

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import call_ai             # from services/api — shared via PYTHONPATH or installed package
from app.services.ai_service import (
    summarize_object,
    extract_claims,
    suggest_links,
)
from app.core.db import get_session           # adapt to actual session factory pattern
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

AI_TASKS = {
    "summarize":      _run_summarize,
    "extract_claims": _run_extract_claims,
    "suggest_links":  _run_suggest_links,
}

def process_object_ai(object_id: str, user_id: str) -> None:
    """RQ entry point. Runs all enabled AI tasks for one object."""
    ...

def _run_summarize(db, object_id: UUID, user_id: UUID) -> None: ...
def _run_extract_claims(db, object_id: UUID, user_id: UUID) -> None: ...
def _run_suggest_links(db, object_id: UUID, user_id: UUID) -> None: ...
```

### 5.2 `process_object_ai` logic

1. Check `settings.ai_auto_process`. If `False`, return immediately (belt-and-suspenders guard).
2. Load the object from DB. If not found or soft-deleted, log and return.
3. Check `obj.metadata_.get("ai_auto_process")` — if explicitly `False`, skip and return.
4. For each task name in `settings.ai_auto_process_tasks`:
   - Call the corresponding `_run_*` helper inside a try/except.
   - On success: log at INFO level.
   - On failure: log at ERROR level with traceback. Do not re-raise — one failing task must not abort the others.
5. After all tasks run (regardless of individual success/failure), write `metadata_["ai_processed_at"] = datetime.utcnow().isoformat()` to the object and commit.
6. Create an inbox notification item (§7) only if at least one task succeeded.

### 5.3 `_run_summarize` helper

Call the same service-layer function that `POST /api/v1/ai/summarize` calls. Do not call the HTTP endpoint — call the function directly:

```python
from app.services.ai_service import summarize_object  # or however Phase 5 exposes it
```

Inspect `services/api/app/services/ai_service.py` to find the exact function name and signature. The HTTP endpoint is a thin wrapper over it.

Pass `force=False` so already-summarized objects are skipped (the Phase 5 cache check).

### 5.4 `_run_extract_claims` helper

Same pattern: call the service-layer function backing `POST /api/v1/ai/extract-claims`. Skip if claims already extracted for this object (check `metadata_` for `ai_claims_extracted_at`).

### 5.5 `_run_suggest_links` helper

Same pattern: call the service-layer function backing `POST /api/v1/ai/suggest-links`. Write suggestions into `metadata_["ai_link_suggestions"]` (list of `{target_id, reason, confidence}`) instead of auto-creating edges. The user still reviews and approves links manually in the AI Panel.

---

## 6. Enqueue hooks

### 6.1 Page save hook (`services/api/app/api/v1/pages.py`)

After the existing page PATCH and PUT handlers successfully commit, enqueue the background job:

```python
if settings.ai_auto_process:
    from app.core.queue import get_queue   # inspect actual queue module name
    q = get_queue()
    q.enqueue("worker.tasks.ai_jobs.process_object_ai",
               str(page.id), str(current_user.id),
               job_timeout=300)
```

**Important:** The enqueue call must be wrapped in `try/except` so a queue failure never causes the page save to fail. Log the error and continue.

Inspect `pages.py` to find the exact commit/response pattern for PATCH and PUT, and add the hook after the response data is ready (not before commit).

### 6.2 Source ingest hook (`services/api/app/services/source_service.py`)

Find the location where `ingestion_status` is set to `"ready"` (the worker calls into this service or updates the field directly). After that write, enqueue:

```python
if settings.ai_auto_process:
    try:
        q = get_queue()
        q.enqueue("worker.tasks.ai_jobs.process_object_ai",
                   str(source_obj.id), str(source_obj.user_id),
                   job_timeout=300)
    except Exception:
        logger.exception("Failed to enqueue AI job for source %s", source_obj.id)
```

Inspect `source_service.py` and the ingestion worker to find the exact completion point. Do not place the hook in the HTTP endpoint — place it in the service/worker where status is actually flipped to `ready`.

---

## 7. Inbox notification

When `process_object_ai` completes with at least one successful task, write a lightweight notification into `objects` so it surfaces in the inbox:

```python
# Create a KosObject of kind="ai_notification" (or repurpose the existing inbox pattern)
# title: "AI processed: {object_title}"
# metadata_: {
#   "source_object_id": str(object_id),
#   "tasks_run": ["summarize", "extract_claims"],
#   "ai_processed_at": iso_timestamp,
# }
```

**Inspect the existing inbox query (`GET /api/v1/ai/inbox`) and the `InboxView` component before deciding whether to use a new `kind` or extend the existing inbox filter.** Match whatever pattern is already established — do not introduce a new mechanism if the existing inbox can surface this type of item with a small filter change.

If a new `kind` is needed, add it to `app/core/object_kinds.py` (inspect first for the registration pattern).

---

## 8. `AiPanel.tsx` — processed-at badge

**File to modify:** `apps/web/src/components/ai/AiPanel.tsx`

At the top of the panel (above the Summarize section), add a single line if `metadata.ai_processed_at` exists:

```tsx
{metadata?.ai_processed_at && (
  <p className="text-[10px] text-gray-600">
    Auto-processed {formatRelativeTime(metadata.ai_processed_at)}
  </p>
)}
```

Where `formatRelativeTime` is a lightweight helper (e.g., "3 min ago", "2 h ago") — write it inline or reuse an existing date utility already in `apps/web/src/lib/`. Do not add `date-fns` or any new package.

**The `metadata` prop already flows into `AiPanel` from the parent** — inspect the component's existing props before adding a new prop. If `metadata` is not currently exposed, pass it through from `PageView` where the page data is loaded.

---

## 9. Subtask checklist

Each subtask is independently Codex-delegatable and ends with a single conventional commit. Subtasks marked **(blocking)** must land before later ones.

- [x] **Subtask 0** — Worktree setup + plan review **(blocking)**
- [x] **Subtask 1** — Config flags in `config.py` **(blocking)**
- [x] **Subtask 2** — Worker task module `ai_jobs.py` **(blocking)** — actual path: `kos_worker/ai_jobs.py`
- [x] **Subtask 3** — Page save hook in `pages.py`
- [x] **Subtask 4** — Source ingest hook — placed in `kos_worker/tasks.py:ingest_source()` (not `source_service.py` — ingestion_status is set by the worker, not the service)
- [x] **Subtask 5** — Inbox notification write in `ai_jobs.py` (follow-up to Subtask 2)
- [x] **Subtask 6** — `AiPanel.tsx` processed-at badge
- [x] **Subtask 7** — Integration tests (`tests/api/test_background_ai.py`) — 11 tests
- [x] **Subtask 8** — Worker unit tests (`tests/unit/test_ai_jobs.py`) + docs + PROGRESS flip — 8 tests

---

## 10. Subtask details

### Subtask 0 — Worktree setup

```bash
git worktree add ../phase-11c-worktree feat/phase-11c-background-ai
```

Confirm clean branch off `main`. **Commit:** none.

---

### Subtask 1 — Config flags

**Files to modify:**
- `services/api/app/config.py` — per §4.

**Verification:**
```bash
cd services/api && uv run python -c "from app.config import get_settings; s = get_settings(); print(s.ai_auto_process, s.ai_auto_process_tasks)"
# → False ['summarize', 'extract_claims', 'suggest_links']
cd services/api && uv run ruff check . && uv run ruff format --check .
```

**Commit:** `feat(config): ai_auto_process and ai_auto_process_tasks flags`

---

### Subtask 2 — Worker task module

**Files to create:**
- `services/worker/tasks/ai_jobs.py` — per §5.

**Files to modify:**
- `services/worker/tasks/__init__.py` — append `from .ai_jobs import process_object_ai` (inspect existing pattern first).

**Key constraint:** `process_object_ai` must be importable as a string path by RQ: `"worker.tasks.ai_jobs.process_object_ai"`. Verify the module path matches the worker's PYTHONPATH setup by inspecting existing task registrations.

**Verification:**
```bash
cd services/worker && uv run python -c "from tasks.ai_jobs import process_object_ai; print('OK')"
```

**Commit:** `feat(worker): background ai processing task for summarize, extract-claims, suggest-links`

---

### Subtask 3 — Page save hook

**Files to modify:**
- `services/api/app/api/v1/pages.py` — append enqueue call after PATCH and PUT commit per §6.1.

**Verification:**
```bash
cd services/api && uv run ruff check . && uv run ruff format --check .
# Integration: set AI_AUTO_PROCESS=true, PATCH a page, confirm an RQ job is enqueued:
# redis-cli LLEN rq:queue:default  (should increment by 1)
```

**Commit:** `feat(api): enqueue background ai job after page save`

---

### Subtask 4 — Source ingest hook

**Files to modify:**
- `services/api/app/services/source_service.py` — per §6.2. Find the exact `ingestion_status = "ready"` write point.

**Verification:**
```bash
cd services/api && uv run ruff check . && uv run ruff format --check .
```

**Commit:** `feat(worker): enqueue background ai job after source ingestion completes`

---

### Subtask 5 — Inbox notification

**Files to modify:**
- `services/worker/tasks/ai_jobs.py` — add notification write at the end of `process_object_ai` per §7.
- If a new `kind` is needed: `services/api/app/core/object_kinds.py` (inspect first).

**Verification:**
```bash
# With AI_AUTO_PROCESS=true, trigger a page save, let the RQ worker run the job.
# Then: GET /api/v1/ai/inbox → should include an ai_notification item.
```

**Commit:** `feat(worker): write ai_notification inbox item on background processing completion`

---

### Subtask 6 — AiPanel badge

**Files to modify:**
- `apps/web/src/components/ai/AiPanel.tsx` — per §8.

**Verification:**
```bash
cd apps/web && pnpm typecheck && pnpm lint
# Manual: open a page that has been background-processed (has metadata.ai_processed_at),
# confirm the "Auto-processed X min ago" line appears at the top of the AI panel.
```

**Commit:** `feat(web): show ai auto-processed timestamp in ai panel`

---

### Subtask 7 — API integration tests

**Files to create:**
- `tests/api/test_background_ai.py`

**Test cases (10 minimum):**

**Config guard:**
1. `AI_AUTO_PROCESS=false` (default) → page PATCH does not enqueue any RQ job (assert queue is empty after request).
2. `AI_AUTO_PROCESS=true` → page PATCH enqueues exactly one job with the correct object_id and user_id.

**`process_object_ai` called directly (unit-style via `monkeypatch`):**
3. Object not found → returns immediately, no AI calls made.
4. Object has `metadata_["ai_auto_process"] = False` → returns immediately, no AI calls made.
5. `AI_AUTO_PROCESS_TASKS=["summarize"]` → only summarize service function is called, extract-claims and suggest-links are not.
6. One task raises an exception → remaining tasks still run, `ai_processed_at` still written.
7. All tasks succeed → `ai_processed_at` written to object metadata, `agent_runs` rows created.
8. All tasks succeed → inbox notification object created with `kind="ai_notification"` and correct `source_object_id`.
9. Source with `ingestion_status` just set to `"ready"` → job enqueued (mock the queue, assert enqueue called).
10. `AI_AUTO_PROCESS_TASKS=[]` (empty list) → no AI service functions called, `ai_processed_at` still written (or not — decide and document).

**Verification:**
```bash
cd tests && uv run pytest api/test_background_ai.py -v    # ≥10 passing
cd tests && uv run pytest api/ unit/ -q                    # full regression green
```

**Commit:** `test(api): background ai processing hook and job tests`

---

### Subtask 8 — Worker unit tests + docs + PROGRESS

**Files to create:**
- `tests/unit/test_ai_jobs.py` — unit tests for `process_object_ai` dispatch logic, opt-out check, and per-task error isolation. Mock all service functions. 5+ cases.

**Files to modify:**
- `docs/API.md` — append "Background AI Processing" section: config flags, opt-out mechanism, inbox notification schema, `ai_processed_at` metadata key.
- `PROGRESS.md` — flip Phase 11C row to ✅ with the subtask checklist.

**Verification:**
```bash
cd tests && uv run pytest unit/test_ai_jobs.py -v    # ≥5 passing
cd services/api && uv run ruff check . && uv run ruff format --check .
```

**Commits:**
```
test(worker): ai_jobs dispatch logic unit tests
docs(phase11c): background ai processing config, opt-out, and inbox notification
```

---

## 11. Commit sequence

```
1.  docs: phase 11c plan (this file)
2.  feat(config): ai_auto_process and ai_auto_process_tasks flags
3.  feat(worker): background ai processing task
4.  feat(api): enqueue background ai job after page save
5.  feat(worker): enqueue background ai job after source ingestion
6.  feat(worker): write ai_notification inbox item on completion
7.  feat(web): show ai auto-processed timestamp in ai panel
8.  test(api): background ai processing hook and job tests
9.  test(worker): ai_jobs dispatch logic unit tests
10. docs(phase11c): background ai processing documentation
```

---

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| RQ enqueue call signature differs from what §6 assumes | Codex must inspect the existing queue module and match the actual pattern. |
| `call_ai()` and service-layer functions are async; RQ tasks run sync | Inspect the existing ingestion worker for how it handles async service calls (likely `asyncio.run()` or a sync wrapper). Follow the same pattern. |
| Page save latency increases if queue is unavailable | Hook is wrapped in `try/except`. A queue failure never blocks the page save. |
| Background job runs on an already-summarized object, wasting tokens | Pass `force=False` to `summarize_object`. The Phase 5 cache check skips if `ai_summary` already present. |
| `source_service.py` doesn't have a single `status = "ready"` point — might be spread across multiple workers | Codex must audit the actual ingestion flow before placing the hook. May need to hook into the worker's success callback instead. |
| `config.py` is also touched by Phase 11A (minor risk) | 11A only adds tutorial-specific config if any. Verify after 11A merges; the two additions are to different fields. |
| Inbox becomes noisy if many objects are auto-processed | Acceptable for MVP. A future phase can add inbox notification deduplication or a per-user throttle. |
| 11B and 11C both commit to `PROGRESS.md` and `docs/API.md` | Append-only, distinct sections — three-way merge trivial. |
| Worker PYTHONPATH may not include `services/api/app` for service imports | Inspect the existing ingestion worker's import path. Use the same mechanism (installed package, shared volume mount, or PYTHONPATH var). |

---

## 13. Follow-ups (out of scope)

- **Per-object UI toggle:** Let users opt in/out of auto-processing from the AI Panel (writes `metadata_["ai_auto_process"] = false`). Currently only a metadata key set by hand.
- **Smart scheduling:** Debounce rapid page saves — only enqueue if no job for this object is already pending. Use RQ's `job_id` deduplication.
- **Task-level failure reporting:** Surface per-task errors in the inbox notification so the user knows "Summarize failed, Extract Claims succeeded."
- **Streaming completion in AiPanel:** Once background processing is done, update the panel in real time via a websocket or SSE endpoint rather than requiring a manual refresh.
- **MCP exposure:** `trigger_ai_processing(object_id)` MCP write tool so agents can explicitly request background processing for an object they just created.
- **Cost controls:** Track token spend per user per day in `agent_runs`, surface in settings, optionally enforce a daily limit on auto-processing.

---

## 14. Done when

- All 8 subtasks checked in this file.
- `PROGRESS.md` Phase 11C row is ✅.
- `cd tests && uv run pytest api/test_background_ai.py unit/test_ai_jobs.py -v` shows ≥15 tests passing.
- `cd tests && uv run pytest api/ unit/ -q` full regression green.
- `pnpm typecheck && pnpm lint` clean in `apps/web`.
- Manual smoke with `AI_AUTO_PROCESS=true` in `.env`:
  1. Save a page → RQ job enqueued.
  2. Wait for worker → AI Panel shows "Auto-processed X min ago".
  3. Inbox shows an `ai_notification` item for the page.
  4. Ingest a source URL → on completion, same job enqueued and processed.
- Phase 11A tutorial work is unaffected (no shared code files touched).
- Phase 11B inline editor work is unaffected (no shared code files touched).
