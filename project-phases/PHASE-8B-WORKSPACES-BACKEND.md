# Phase 8B — Workspaces Backend Foundation

> **Status:** Planned (parallel-safe with PHASE-7B-MCP-WRITE)
> **Owner:** Backend
> **Audience:** AI coder (Codex / Claude). Read end-to-end before writing code.
> **Estimated effort:** 1 PR, ~8 commits, ~500–700 LOC including tests.
> **Blocks:** PHASE-8C-WORKSPACES-FRONTEND (planned), PHASE-8D-WORKSPACES-MCP (planned, post-7B).
> **Blocked by:** none.
> **Parallel-safe with:** PHASE-7B-MCP-WRITE, PHASE-9A follow-ups, PHASE-9*-AI-GENERATORS (planned, no doc yet). Conflict map verified in §2.

---

## 0. North Star

KnowledgeOS's long-term Phase 8 vision is a **multi-pane research environment**: multiple pages, sources, and AI tools open side by side in a named, reusable workspace layout. Phase 8A shipped the smallest useful slice — a single read-only side pane held in React context, no persistence, no schema. The full Phase 8 plan (per `PROGRESS.md`) requires a `workspaces` table with `layout_json` and CRUD, drag-text-between-panes, link-pane-to-pane, workspace-scoped AI and search.

Phase 8B is the **smallest useful, conflict-free slice**: the data foundation. It introduces the `workspaces` table, REST CRUD endpoints, and Pydantic-validated `layout_json` so a frontend (8C) or MCP tool (8D) can persist multi-pane layouts the user has chosen.

**What this phase does NOT do:**
- No frontend changes (8C).
- No MCP write tools (8D, depends on 7B's `audited_write_service`).
- No drag-text-between-panes (8C / 8E).
- No workspace-scoped search or AI context picker (8E).
- No `KosObject` row per workspace — workspaces are personal UI state, not knowledge.
- No audit / revision rows on workspace mutations — these are not knowledge writes.
- No object-reference validation inside `layout_json` (the frontend already handles "object missing" gracefully via existing `WorkspaceSidePane`).

---

## 1. Non-breakage contract

Read this section twice. The whole reason this phase is small and tightly scoped is to guarantee parallel safety with the active PHASE-7B-MCP-WRITE worktree.

### 1.1 Files this phase MAY NOT touch

| File / dir | Why off-limits |
|---|---|
| `services/api/app/api/v1/objects.py` | PHASE-7B is editing it (archive + restore-revision endpoints). |
| `services/api/app/api/v1/pages.py` | PHASE-7B is editing it (optional `expected_version` on PATCH). |
| `services/api/app/api/v1/ai.py` | Reserved for PHASE-9*-AI-GENERATORS (planned, no doc yet). Touching it adds 3-way merge risk. |
| `services/api/app/services/{agent_run_service,audited_write_service,revision_service}.py` | New / modified in PHASE-7B. Workspace writes deliberately do not invoke these. |
| `services/api/app/core/{library,rate_limit}.py` | PHASE-7B owns. |
| `services/api/app/core/object_kinds.py` | Workspaces are not objects. Do not add a `"workspace"` kind. |
| `services/api/app/config.py` | PHASE-7B is editing (rate-limit config). |
| `services/mcp/**` | PHASE-7B owns. MCP exposure for workspaces is Phase 8D. |
| `services/worker/**` | Out of scope. Workspaces have no ingestion pipeline. |
| `apps/web/**` | Phase 8C owns the pane engine and the workspace picker. |
| `infra/**` | No env vars or infra changes needed for 8B. |
| `tests/api/test_archive_restore.py`, `tests/api/test_rate_limit.py`, `tests/api/test_mcp_writes.py` | New in PHASE-7B. |
| `tests/e2e/**`, `tests/worker/**` | Owned by PHASE-ENHANCE-02. |
| Any existing alembic migration `0001_*.py` … `0007_*.py` | Never edit applied migrations. |
| `docs/MCP_TOOLS.md`, `docs/SECURITY.md`, `docs/AGENT_GUIDE.md`, `docs/REVISION_HISTORY.md` | PHASE-7B is rewriting these. |
| `README.md` "MCP & Agent Access" section | PHASE-7B is editing. |

### 1.2 Files this phase MAY edit (small, additive only)

| File | Allowed change |
|---|---|
| `services/api/app/api/v1/router.py` | Append one `include_router(workspaces_router)` line. |
| `services/api/app/models/__init__.py` | Append `from app.models.workspace import Workspace` and add `"Workspace"` to `__all__`. |
| `services/api/app/schemas/__init__.py` | Append workspace re-exports if the existing pattern re-exports schemas (inspect first; don't introduce a new pattern). |
| `PROGRESS.md` | Append a Phase 8B status section. Trivial 3-way merge; if there's a conflict, resolve by keeping all sections from all worktrees. |
| `docs/API.md` | Append a "Workspaces" section at the end. PHASE-7B touches an MCP-adjacent section; coordinate on conflict but the documents diverge naturally. |
| `docs/DATA_MODEL.md` | Append a "Workspaces" subsection at the end. |
| `docs/ARCHITECTURE.md` | If a section already lists tables, append `workspaces` to it. Otherwise leave alone. |

### 1.3 Files this phase MUST create

```
services/api/alembic/versions/0008_add_workspaces_table.py
services/api/app/models/workspace.py
services/api/app/schemas/workspace.py
services/api/app/services/workspace_service.py
services/api/app/api/v1/workspaces.py
tests/api/test_workspaces.py
project-phases/PHASE-8B-WORKSPACES-BACKEND.md   ← this file already exists; do not recreate
```

### 1.4 Behaviors that may not regress

- All existing API integration tests pass unchanged.
- All existing unit tests pass unchanged.
- The `KosObject` schema and the `objects` table are not altered.
- `VALID_OBJECT_KINDS` is not extended.
- Soft-delete pattern is preserved for the new table (`deleted_at`, never hard-delete).
- The existing `WorkspaceLite` React context and `WorkspaceSidePane` component continue to work without consuming this API (8C connects them).
- No new dependency on Redis, Qdrant, OpenAI, or any worker queue.
- No new background job kinds.

### 1.5 Dependency policy

No new Python dependencies. Uses only FastAPI, SQLAlchemy 2.0 async, Pydantic v2, and Alembic — all already in `services/api/pyproject.toml`.

---

## 2. Conflict map (verified file-by-file)

Verified via `git diff --name-only main...HEAD` against the active PHASE-7B worktree and the implied scope of the future PHASE-9*-AI-GENERATORS (planned, no doc yet) on 2026-05-15.

### vs. PHASE-7B-MCP-WRITE (in progress)

7B touches:
```
services/api/app/api/v1/{objects,pages}.py
services/api/app/config.py
services/api/app/core/{library,rate_limit}.py
services/api/app/services/{agent_run,audited_write,revision}_service.py
services/mcp/**
tests/api/test_{archive_restore,rate_limit,mcp_writes}.py
infra/.env.example
docs/{MCP_TOOLS,SECURITY,AGENT_GUIDE,REVISION_HISTORY}.md
README.md
PROGRESS.md
```

Phase 8B wants:
```
NEW:   services/api/alembic/versions/0008_*.py,
       models/workspace.py, schemas/workspace.py,
       services/workspace_service.py, api/v1/workspaces.py,
       tests/api/test_workspaces.py
EDIT:  api/v1/router.py, models/__init__.py, schemas/__init__.py,
       PROGRESS.md, docs/API.md, docs/DATA_MODEL.md
```

**Overlap:** `PROGRESS.md` only (append-merge). Zero code-file conflict.

### vs. PHASE-9A-CAREER-MEMORY-BACKEND (merged) and follow-ups

9A is already on `main`. The 9A follow-up "retrofit project mutations to `audited_write_service`" will edit `services/api/app/services/project_service.py` and `tests/api/test_projects.py` after 7B merges. Neither is touched by 8B.

**Overlap:** none.

### vs. PHASE-ENHANCE-02-TESTING-INFRA (merged) and PHASE-ENHANCE-03-UX-POLISH (merged)

Both shipped to `main`. Phase 8B does not touch `apps/web/**`, `tests/e2e/**`, `infra/**`, root `package.json`, or `tailwind.config.ts`.

**Overlap:** none.

### Migration sequencing

Latest applied migration on `main` is `0007_add_projects_table.py`. PHASE-7B does not add a migration. Phase 8B adds `0008_add_workspaces_table.py` with `down_revision = "0007"`. Safe.

If a future PHASE-7B-vN does add a migration before 8B lands, rebase: rename `0008_add_workspaces_table.py` to whatever index is next free and update `down_revision`. The migration body is independent.

---

## 3. Schema design

### 3.1 No `KosObject` row

Workspaces are personal UI state, not knowledge. They are not searchable, not citable, not graph-linkable. Making them `KosObject`s would pollute `objects.kind` enums, list views, search indexes, soft-delete-trash UI, and the Cmd+K search palette. They get their own top-level table with their own soft-delete column.

This is a deliberate divergence from the `chats` / `pages` / `projects` "specialization table" pattern.

### 3.2 `workspaces` table

```sql
CREATE TABLE workspaces (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name         VARCHAR(255) NOT NULL,
    description  TEXT,
    layout_json  JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_pinned    BOOLEAN NOT NULL DEFAULT FALSE,
    last_used_at TIMESTAMPTZ NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at   TIMESTAMPTZ NULL
);

CREATE INDEX ix_workspaces_user_id        ON workspaces (user_id);
CREATE INDEX ix_workspaces_user_active    ON workspaces (user_id) WHERE deleted_at IS NULL;
CREATE INDEX ix_workspaces_last_used_at   ON workspaces (last_used_at DESC NULLS LAST);
```

**Design choices:**

- `user_id` FK with `ON DELETE CASCADE` — when a user is removed, their workspaces go too. (Consistent with the existing `objects.user_id` semantics; no soft-delete on the user side is in scope.)
- `name` is required and shown in the future "Workspaces" sidebar item. `description` is optional.
- `layout_json` holds the full pane tree (see §3.3). Stored as JSONB so future queries can index specific paths if needed.
- `is_pinned` lets the future UI sort favorite workspaces to the top of a list. Default FALSE.
- `last_used_at` is updated whenever the workspace is loaded (`GET /workspaces/{id}`). Enables a "Recent workspaces" view in Phase 8C.
- Soft-delete via `deleted_at`. Restore uses a dedicated `POST /workspaces/{id}/restore` (we cannot reuse `/objects/{id}/restore` because workspaces are not in the `objects` table).
- No `metadata` JSONB — `layout_json` is the only structured payload; cross-cutting metadata is not in scope.

### 3.3 `layout_json` schema (validated in Pydantic, not DB)

A simple, forward-compatible shape. The DB column is just JSONB; validation lives in `schemas/workspace.py`.

```jsonc
{
  "version": 1,
  "split": "horizontal" | "vertical",
  "panes": [
    {
      "id": "pane-1",                          // local id, unique within workspace
      "object_id": "uuid" | null,              // what this pane shows; null = empty/search pane
      "object_kind": "page" | "source" | "asset" | "chat" | "project" | null,
      "size_pct": 50,                          // sums to 100 across all panes; integer 5–95
      "mode": "read" | "edit"                  // for future use; default "read"
    }
  ],
  "active_pane_id": "pane-1"                   // must reference one of panes[].id
}
```

**Validation rules (enforced by Pydantic, not the database):**

- `version` must be `1`. Future shapes will bump this.
- `panes` length is between 1 and 4 inclusive. (Phase 8 plan caps at 4 panes.)
- Each `pane.id` is unique within the workspace.
- Each `pane.size_pct` is an integer in `[5, 95]`. Sum of all `size_pct` must equal 100. (Loose: if the sum is within ±2 of 100, accept; otherwise 422.)
- `pane.object_kind`, if set, is one of the literal kinds above. (Subset of `VALID_OBJECT_KINDS` — we don't expose `claim` / `task` panes in 8B.)
- `pane.object_id` is a syntactically valid UUID if set. The DB does **not** enforce a FK; we accept stale references so a deleted source doesn't break a saved workspace.
- `active_pane_id` must match one of `panes[].id`.
- `split` is required when `panes.length >= 2`; ignored when length is 1.

**Why no FK on `pane.object_id`:**

A workspace is a saved view, not an integrity contract. If a user deletes a source that's in three saved workspaces, we don't want the workspace to disappear or fail to load. The frontend (already proven by `WorkspaceSidePane` in 8A) renders a "Not available" placeholder.

---

## 4. Pydantic schemas (`services/api/app/schemas/workspace.py`)

Match the existing pattern in `schemas/project.py`. Pydantic v2 with `model_config = ConfigDict(from_attributes=True)` for ORM mapping.

```python
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

PaneKind = Literal["page", "source", "asset", "chat", "project"]
PaneMode = Literal["read", "edit"]
WorkspaceSplit = Literal["horizontal", "vertical"]


class WorkspacePane(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    object_id: UUID | None = None
    object_kind: PaneKind | None = None
    size_pct: int = Field(..., ge=5, le=95)
    mode: PaneMode = "read"


class WorkspaceLayout(BaseModel):
    version: Literal[1] = 1
    split: WorkspaceSplit = "horizontal"
    panes: list[WorkspacePane] = Field(..., min_length=1, max_length=4)
    active_pane_id: str

    @model_validator(mode="after")
    def _validate_layout(self) -> "WorkspaceLayout":
        ids = [p.id for p in self.panes]
        if len(ids) != len(set(ids)):
            raise ValueError("pane ids must be unique within a workspace")
        if self.active_pane_id not in ids:
            raise ValueError("active_pane_id must reference an existing pane")
        total = sum(p.size_pct for p in self.panes)
        if not 98 <= total <= 102:
            raise ValueError(f"pane size_pct must sum to ~100, got {total}")
        return self


class WorkspaceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    layout: WorkspaceLayout
    is_pinned: bool = False


class WorkspaceCreate(WorkspaceBase):
    pass


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    layout: WorkspaceLayout | None = None
    is_pinned: bool | None = None


class WorkspaceOut(WorkspaceBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
```

The `layout` field maps to the `layout_json` column via the service layer (model_dump on write, validate on read).

---

## 5. Service layer (`services/api/app/services/workspace_service.py`)

CRUD with soft-delete and ownership checks. No audit / revision integration — workspaces are not audited writes.

Functions to implement (signatures only; mirror `project_service.py`):

```python
async def create_workspace(db, *, user_id: UUID, payload: WorkspaceCreate) -> Workspace: ...

async def get_workspace(db, *, user_id: UUID, workspace_id: UUID, include_deleted: bool = False) -> Workspace | None: ...

async def list_workspaces(
    db, *, user_id: UUID,
    include_deleted: bool = False,
    pinned_only: bool = False,
    limit: int = 50, offset: int = 0,
) -> tuple[list[Workspace], int]: ...

async def update_workspace(db, *, user_id: UUID, workspace_id: UUID, payload: WorkspaceUpdate) -> Workspace: ...

async def soft_delete_workspace(db, *, user_id: UUID, workspace_id: UUID) -> Workspace: ...

async def restore_workspace(db, *, user_id: UUID, workspace_id: UUID) -> Workspace: ...

async def touch_last_used(db, *, user_id: UUID, workspace_id: UUID) -> Workspace: ...
```

**Ownership:** every function filters by `user_id`. A request that targets another user's workspace returns 404, not 403, to avoid leaking existence.

**`touch_last_used`:** called from the GET-detail endpoint to update `last_used_at = now()`. Use a `flush()` not a `commit()`; let the endpoint's transaction control the commit.

---

## 6. REST API (`services/api/app/api/v1/workspaces.py`)

Mounted at `/api/v1/workspaces` via one new `include_router(workspaces_router)` line in `router.py`.

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/workspaces` | Create a workspace. Body: `WorkspaceCreate`. Returns `WorkspaceOut`, 201. |
| `GET` | `/api/v1/workspaces` | List own workspaces (paginated). Query: `pinned_only`, `include_deleted`, `limit`, `offset`. Returns `PaginatedResponse[WorkspaceOut]`. |
| `GET` | `/api/v1/workspaces/{id}` | Read one. Updates `last_used_at = now()` as a side effect. 404 on not-owned or deleted. |
| `PATCH` | `/api/v1/workspaces/{id}` | Partial update. Body: `WorkspaceUpdate`. 404 on not-owned. 422 on invalid layout. |
| `DELETE` | `/api/v1/workspaces/{id}` | Soft delete (sets `deleted_at`). 404 on not-owned. Idempotent: re-delete is 204. |
| `POST` | `/api/v1/workspaces/{id}/restore` | Restore a soft-deleted workspace. 404 if not deleted or not owned. |

**Auth:** all endpoints use `Depends(get_current_user)` exactly like the projects router.

**Errors:**
- 401 if no session cookie.
- 404 if workspace doesn't exist OR belongs to another user OR is deleted (except restore/list-with-include_deleted).
- 422 on invalid `layout_json` (Pydantic validation fires automatically).

---

## 7. Subtask checklist

Each subtask is independently codex-delegatable and ends with a single conventional commit. Subtasks marked **(blocking)** must land before later ones.

- [ ] **Subtask 0** — Audit + plan file (this doc) + PROGRESS.md row **(blocking)**
- [ ] **Subtask 1** — Alembic migration `0008_add_workspaces_table.py` + `models/workspace.py` + `models/__init__.py` re-export **(blocking)**
- [ ] **Subtask 2** — Pydantic schemas (`schemas/workspace.py`) including `WorkspaceLayout` validators **(blocking)**
- [ ] **Subtask 3** — Service layer (`services/workspace_service.py`) with CRUD + soft-delete + `touch_last_used`
- [ ] **Subtask 4** — REST router (`api/v1/workspaces.py`) wired into `api/v1/router.py`
- [ ] **Subtask 5** — Integration tests (`tests/api/test_workspaces.py`) — 12+ cases (see §9)
- [ ] **Subtask 6** — Docs: append "Workspaces" section to `docs/API.md` and `docs/DATA_MODEL.md`; flip PROGRESS row to ✅

---

## 8. Subtask details

### Subtask 1 — Migration + model

**Files to create:**
- `services/api/alembic/versions/0008_add_workspaces_table.py` (down_revision = `"0007"`)
- `services/api/app/models/workspace.py`

**Files to modify:**
- `services/api/app/models/__init__.py` — append `Workspace` import and `__all__` entry.

**Migration body uses:** `gen_random_uuid()` for the PK default (already used in 0001), `JSONB` for `layout_json`, partial index `WHERE deleted_at IS NULL` on `user_id` for the common list query.

**Verification:**
- `cd services/api && uv run alembic upgrade head` succeeds.
- `uv run alembic downgrade -1` then `upgrade head` succeeds (round-trip).
- `psql ... -c '\d workspaces'` shows the four indexes.

**Commit:** `feat(api): workspaces table and ORM model`

---

### Subtask 2 — Pydantic schemas

**Files to create:**
- `services/api/app/schemas/workspace.py` per §4.

**Files to modify:**
- `services/api/app/schemas/__init__.py` — only if the existing pattern re-exports schemas. Inspect first.

**Tests for the validator (added in Subtask 5 but designed here):**
- Sum of `size_pct` != ~100 → 422.
- Duplicate pane ids → 422.
- `active_pane_id` not in panes → 422.
- 5 panes → 422 (max 4).
- 0 panes → 422 (min 1).

**Commit:** `feat(api): workspace pydantic schemas with layout validation`

---

### Subtask 3 — Service layer

**Files to create:**
- `services/api/app/services/workspace_service.py` per §5.

**Notes:**
- Serialize the Pydantic `WorkspaceLayout` to dict via `layout.model_dump(mode="json")` before storing.
- Deserialize on read by passing the JSONB dict to `WorkspaceLayout.model_validate(...)`.
- `touch_last_used` uses `await db.execute(update(Workspace).where(...).values(last_used_at=func.now()))` and `await db.flush()`, returning the refreshed row.

**Commit:** `feat(api): workspace service with crud, soft delete, and last_used tracking`

---

### Subtask 4 — REST router

**Files to create:**
- `services/api/app/api/v1/workspaces.py` per §6.

**Files to modify:**
- `services/api/app/api/v1/router.py` — append the one `include_router(workspaces_router)` line.

**Pattern reference:** copy the structure of `services/api/app/api/v1/projects.py`. The `_build_workspace_out` helper from a single ORM row is simpler than the projects one because there's no parent `KosObject` to join.

**Commit:** `feat(api): workspace crud endpoints`

---

### Subtask 5 — Tests

**File to create:**
- `tests/api/test_workspaces.py`

Use the existing async test client fixture pattern from `tests/api/test_projects.py`.

**Cases (12 minimum):**

1. `POST /workspaces` happy path → 201, returned id, returned `layout`.
2. `POST /workspaces` with `size_pct` sum = 70 → 422.
3. `POST /workspaces` with duplicate pane ids → 422.
4. `POST /workspaces` with 5 panes → 422.
5. `GET /workspaces` returns only own workspaces (cross-user isolation).
6. `GET /workspaces/{id}` returns 404 for another user's workspace.
7. `GET /workspaces/{id}` updates `last_used_at` (read once, sleep 10ms, read again, assert `last_used_at` advanced).
8. `PATCH /workspaces/{id}` updates name without touching layout.
9. `PATCH /workspaces/{id}` updates layout; old `last_used_at` preserved.
10. `DELETE /workspaces/{id}` sets `deleted_at`; subsequent GET returns 404; GET with `include_deleted=true` returns 200.
11. `POST /workspaces/{id}/restore` clears `deleted_at`; GET returns 200.
12. `POST /workspaces` with `object_id` referencing a non-existent UUID → 201 (no FK validation; lenient by design).

**Verification:**
```bash
cd tests && PYTHONPATH=../services/api uv run --project ../services/api --extra dev pytest api/test_workspaces.py -v
```
All 12+ tests pass. Existing API integration test count unchanged otherwise.

**Commit:** `test(api): workspaces crud, validation, and ownership coverage`

---

### Subtask 6 — Docs + PROGRESS flip

**Files to modify:**
- `docs/API.md` — append a "Workspaces" section listing the six endpoints with example request/response bodies.
- `docs/DATA_MODEL.md` — append a "Workspaces" subsection describing the table and the `layout_json` shape.
- `docs/ARCHITECTURE.md` — if it has a tables list, append `workspaces`.
- `PROGRESS.md` — flip the Phase 8B row to ✅ with the subtask checklist mirroring this file.

**Commit:** `docs(phase8b): workspaces backend api and data model`

---

## 9. Tests required

Minimum 12 new tests in `tests/api/test_workspaces.py` (listed in §8 Subtask 5). After Phase 8B: target ~147 API integration tests (135 today on `main` + ~12 new).

No new unit tests are strictly required, but the layout validator is good unit-test surface and could move to `tests/unit/test_workspace_layout.py` if you prefer to isolate it.

---

## 10. Commit sequence

```
1.  docs: phase 8b plan
2.  feat(api): workspaces table and ORM model
3.  feat(api): workspace pydantic schemas with layout validation
4.  feat(api): workspace service with crud, soft delete, and last_used tracking
5.  feat(api): workspace crud endpoints
6.  test(api): workspaces crud, validation, and ownership coverage
7.  docs(phase8b): workspaces backend api and data model
```

7 commits total. Subtask 0 (this plan) is commit 1; the rest map 1-to-1.

---

## 11. Validation commands

```bash
# Backend lint + format
cd services/api && uv run ruff check . && uv run ruff format --check .

# Migrations round-trip
cd services/api && uv run alembic upgrade head
cd services/api && uv run alembic downgrade -1 && uv run alembic upgrade head

# Target tests
cd tests && PYTHONPATH=../services/api uv run --project ../services/api --extra dev pytest api/test_workspaces.py -v

# Full backend regression
cd tests && PYTHONPATH=../services/api uv run --project ../services/api --extra dev pytest api/ unit/ -q

# Frontend (sanity — no UI changes expected)
pnpm typecheck
pnpm lint
```

All must pass before merge.

---

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| 7B and 8B both edit `PROGRESS.md` and conflict on merge | Append-only edits in separate sections; trivial 3-way merge. If conflict, keep both sections. |
| Future 7B-vN adds a migration before 8B merges | Rename `0008_*` to the next free index, update `down_revision`. Body is independent. |
| `layout_json` schema evolves and breaks saved workspaces | `WorkspaceLayout.version` field. Future versions add a migration step in the service layer (read v1, return v1; read v2, return v2). |
| User saves a workspace, deletes a referenced source, reloads workspace | Frontend already handles "Not available" placeholders (proven in 8A). No FK on `object_id` by design. |
| `last_used_at` updates on every GET create write hotspot | Single-user local-first app; one user, low QPS. If multi-user mode arrives, batch updates to once per minute via Redis. |
| Some agent decides to spam workspace creates via future MCP tool | Out of scope for 8B (no MCP). Phase 8D will route writes through `audited_write_service` and the 7B rate limiter. |
| Workspaces table grows unbounded | Soft-delete + trash UI in 8C; manual `DELETE` from API for hard cleanup. Not a practical concern at one-user scale. |

---

## 13. Follow-ups (out of scope, but worth flagging)

- **Phase 8C (frontend):** generalize `WorkspaceSidePane` into a real pane engine (`react-resizable-panels` or similar), consume `/api/v1/workspaces`, surface "Workspaces" in the sidebar with pinned + recent lists, add "Save current view as workspace" affordance.
- **Phase 8D (MCP):** `create_workspace`, `update_workspace`, `archive_workspace` MCP tools — depends on PHASE-7B's `audited_write_service` and rate limiter. Workspaces become writable by agents only after 7B and 8B both merge.
- **Phase 8E (advanced):** drag selected text between panes, link-pane-to-pane via existing edges API, workspace-scoped AI ("Ask about this pane" / "Ask whole workspace"), workspace-scoped search.
- **Optimistic concurrency:** if multi-device sync becomes a need, add a `version: int` column with optimistic lock on PATCH. Not needed for single-user local-first today.

---

## 14. Done when

- All 7 subtasks checked in this file.
- `PROGRESS.md` Phase 8B row is ✅ with the same checklist.
- `cd tests && uv run pytest api/test_workspaces.py -v` shows ≥12 passing tests.
- Full backend suite (`make test-all` or the targeted commands in §11) is green.
- `docs/API.md` and `docs/DATA_MODEL.md` each have a "Workspaces" section.
- Phase 8C (frontend) can begin against a stable API contract.
