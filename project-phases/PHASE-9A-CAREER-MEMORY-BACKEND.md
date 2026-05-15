# Phase 9A — Career Memory (Backend Foundation)

> **Status:** Complete (backend shipped to `main`)
> **Owner:** Backend
> **Audience:** AI coder (Codex / Claude). Read end-to-end before writing code.
> **Estimated effort:** 1 PR, ~10 commits, ~600–800 LOC including tests.
> **Blocks:** none. **Blocked by:** none. **Parallel-safe with:** PHASE-7B-MCP-WRITE, PHASE-ENHANCE-02-TESTING-INFRA, PHASE-ENHANCE-03-UX-POLISH (all verified file-by-file in Section 2 below).

---

## 0. North Star

KnowledgeOS's long-term Phase 9 vision is **career and project memory** — the user's professional life as a first-class object: projects with timeframes and metrics, evidence-linked claims, AI-generated resume bullets, AI-generated interview stories, all derived from existing pages, sources, and chats already in the knowledge base.

Phase 9A is the **smallest useful, conflict-free slice**: the data foundation. It introduces the `project` object kind, the `projects` table, REST CRUD endpoints, and one AI endpoint (`extract-project`) that drafts a `Project` from an existing source/page/chat using the AI plumbing already built in Phase 5.

**What this phase does NOT do:** no MCP tools, no resume bullet generator, no interview story generator, no frontend. Those are Phase 9B / 9C / 9D and depend on this foundation.

---

## 1. Non-breakage contract

Read this section twice. The whole reason this phase is small and tightly scoped is to guarantee parallel safety with three live worktrees.

### 1.1 Files this phase MAY NOT touch

| File / dir | Why off-limits |
|---|---|
| `services/api/app/api/v1/objects.py` | PHASE-7B is editing it (archive endpoints). |
| `services/api/app/services/{agent_run_service,audited_write_service,revision_service}.py` | New in PHASE-7B; we may import from them but not edit. |
| `services/api/app/core/{library,rate_limit}.py` | PHASE-7B owns. |
| `services/api/app/config.py` | PHASE-7B is editing (rate-limit config). |
| `services/mcp/**` | PHASE-7B owns. MCP integration for projects is Phase 9B. |
| `services/worker/**` | Out of scope; no worker pipeline for projects in 9A. |
| `apps/web/**` | Owned by PHASE-ENHANCE-03 (planned) and read by PHASE-ENHANCE-02. Frontend is Phase 9C/D. |
| `tests/api/test_archive_restore.py`, `tests/api/test_rate_limit.py` | New in PHASE-7B. |
| `tests/e2e/**`, `tests/worker/**` | Owned by PHASE-ENHANCE-02. |
| `infra/**` | No env vars or infra changes needed for 9A. |
| `apps/web/src/types/**` | Frontend types update is Phase 9C. |
| Any existing alembic migration `0001_*.py` … `0006_*.py` | Never edit applied migrations. |

### 1.2 Files this phase MAY edit (small, additive only)

| File | Allowed change |
|---|---|
| `services/api/app/api/v1/router.py` | Append one `include_router(projects_router)` line. |
| `services/api/app/models/__init__.py` | Append `from app.models.project import Project` and add `"Project"` to `__all__`. |
| `services/api/app/schemas/__init__.py` | If the existing pattern re-exports schemas, append project re-exports. (Inspect first; some repos leave this empty — don't introduce a new pattern.) |
| `services/api/app/core/object_kinds.py` | Append `"project"` to the `VALID_OBJECT_KINDS` tuple. |
| `services/api/app/api/v1/ai.py` | Append one new endpoint `POST /ai/extract-project`. Do not modify any existing endpoint. |
| `tests/api/test_ai.py` | Append new test cases for `extract-project`. Do not modify existing tests. |
| `PROGRESS.md` | Append a Phase 9A status section. Trivial 3-way merge; if there's a conflict, resolve by keeping all sections from all worktrees. |

### 1.3 Files this phase MUST create

```
services/api/alembic/versions/0007_add_projects_table.py
services/api/app/models/project.py
services/api/app/schemas/project.py
services/api/app/services/project_service.py
services/api/app/api/v1/projects.py
tests/api/test_projects.py
project-phases/PHASE-9A-CAREER-MEMORY-BACKEND.md   ← this file already exists; do not recreate
```

### 1.4 Behaviors that may not regress

- All 112 existing API integration tests pass unchanged.
- The 16 backend unit tests pass unchanged.
- All existing object kinds (`page`, `asset`, `note`, `bookmark`, `collection`, `source`, `chat`, `claim`, `task`) continue to behave identically. Adding `"project"` to the tuple is strictly additive.
- The `/api/v1/ai/inbox` endpoint signature, `summarize`, `extract-claims`, `extract-tasks`, `suggest-links`, `answer`, `triage` endpoints all unchanged.
- The `KosObject` schema and the `objects` table are not altered (no new columns, no enum changes — `kind` is `String(32)`, validated at the application layer).
- Soft-delete pattern is preserved: deleting a project sets `deleted_at`, never hard-deletes; restore endpoint uses the existing `/api/v1/objects/{id}/restore`.

### 1.5 Dependency policy

No new Python dependencies. The phase uses only what is already in `services/api/pyproject.toml` (FastAPI, SQLAlchemy 2.0 async, Pydantic v2, Alembic, OpenAI SDK already present for Phase 5).

---

## 2. Conflict map (verified file-by-file)

This was confirmed via `git diff --name-only main...HEAD` against both worktrees on 2026-05-15.

### vs. PHASE-7B-MCP-WRITE

7B touches:
```
services/api/app/api/v1/objects.py
services/api/app/config.py
services/api/app/core/{library,rate_limit}.py
services/api/app/services/{agent_run,audited_write,revision}_service.py
services/mcp/**
tests/api/test_{archive_restore,rate_limit}.py
infra/.env.example
PROGRESS.md
```

Phase 9A wants:
```
NEW:        services/api/alembic/versions/0007_*.py, models/project.py,
            schemas/project.py, services/project_service.py,
            api/v1/projects.py, tests/api/test_projects.py
EDIT:       api/v1/router.py, models/__init__.py, schemas/__init__.py,
            core/object_kinds.py, api/v1/ai.py, tests/api/test_ai.py,
            PROGRESS.md
```

**Overlap:** `PROGRESS.md` only (append-merge). Zero code-file conflict.

### vs. PHASE-ENHANCE-02-TESTING-INFRA

ENHANCE-02 touches:
```
apps/web/**, tests/e2e/**, tests/pyproject.toml, tests/uv.lock,
package.json, pnpm-lock.yaml, pnpm-workspace.yaml, .gitignore,
PROGRESS.md, README.md
```

**Overlap:** `PROGRESS.md` only. Zero code-file conflict.

### vs. PHASE-ENHANCE-03-UX-POLISH (planned, not started)

UX-03 will touch only `apps/web/**` and `apps/web/{tailwind.config.ts, package.json}` and `infra/.env.example`.

**Overlap:** none.

### Migration sequencing

Latest applied migration on `main` is `0006_add_structured_chat_summary.py`. Neither active worktree adds migrations. Phase 9A adds `0007_add_projects_table.py` with `down_revision = "0006"`. Safe.

---

## 3. Schema design

### 3.1 Object kind

Add `"project"` to `app/core/object_kinds.py`:

```python
VALID_OBJECT_KINDS = (
    "page",
    "asset",
    "note",
    "bookmark",
    "collection",
    "source",
    "chat",
    "claim",
    "task",
    "project",   # NEW in 9A
)
```

### 3.2 `projects` table

Mirror the `IDEA-DRAFT.md` data model and the existing `chats` / `pages` extension pattern. Every project is a row in `objects` (kind=`'project'`) plus a row in `projects` (PK = `objects.id`).

```sql
CREATE TABLE projects (
    id              UUID PRIMARY KEY REFERENCES objects(id) ON DELETE CASCADE,
    period_start    DATE,                              -- nullable
    period_end      DATE,                              -- nullable; NULL ⇒ ongoing
    role            TEXT,                              -- e.g. "Lead Engineer"
    organization    TEXT,                              -- e.g. "Coral Careers"
    problem         TEXT,                              -- the problem being solved
    actions         TEXT,                              -- what the user did
    results         TEXT,                              -- outcomes
    metrics         JSONB NOT NULL DEFAULT '{}',       -- e.g. {"users_onboarded": 250, "uptime_pct": 99.95}
    skills          TEXT[] NOT NULL DEFAULT '{}',      -- e.g. {"python", "fastapi", "postgres"}
    status          VARCHAR(16) NOT NULL DEFAULT 'active',
                                                       -- one of: active|paused|completed|archived
    confidence      VARCHAR(16) NOT NULL DEFAULT 'manual',
                                                       -- manual|ai_extracted|verified
    extracted_from  UUID NULL REFERENCES objects(id) ON DELETE SET NULL,
                                                       -- the source/chat/page that seeded this project
    extracted_by_agent_run_id UUID NULL REFERENCES agent_runs(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_projects_period_start ON projects (period_start);
CREATE INDEX ix_projects_period_end ON projects (period_end);
CREATE INDEX ix_projects_status ON projects (status);
CREATE INDEX ix_projects_skills ON projects USING gin (skills);
```

**Design choices:**

- `period_start` / `period_end` are nullable so users can create stub projects before pinning down dates.
- `status = 'archived'` is independent of `objects.is_archived`. The latter is the universal soft-archive flag; `status = 'archived'` means "this project ended formally". Both can be true.
- `confidence` records provenance: `manual` (user wrote it), `ai_extracted` (drafted by `extract-project`), `verified` (user reviewed an AI-extracted draft).
- `extracted_from` lets us trace lineage — the page/chat/source the project was derived from. Hard FK with `ON DELETE SET NULL` so deleting the source preserves the project record.
- `extracted_by_agent_run_id` ties to `agent_runs` (already exists) for full auditability.
- GIN index on `skills` enables fast skill-based search later (`WHERE skills @> ARRAY['python']`).
- No `metadata` JSONB on the project row itself — `objects.metadata` already covers cross-cutting metadata.

### 3.3 No edge schema changes

The IDEA-DRAFT vision lists `belongs_to_project` as a typed edge. The existing `edges` table already supports arbitrary `kind` strings, so no schema change is needed. The first time a user links a page to a project via the existing `POST /api/v1/edges`, they pass `kind: "belongs_to_project"`. The frontend (Phase 9C) will surface this with a "Link to project" affordance; the backend just accepts any string today.

---

## 4. Pydantic schemas (`services/api/app/schemas/project.py`)

Match the existing pattern in `schemas/chat.py`, `schemas/page.py`. Pydantic v2 with `model_config = {"from_attributes": True}` for ORM mapping.

```python
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ProjectStatus = Literal["active", "paused", "completed", "archived"]
ProjectConfidence = Literal["manual", "ai_extracted", "verified"]


class ProjectBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    role: str | None = Field(None, max_length=255)
    organization: str | None = Field(None, max_length=255)
    problem: str | None = None
    actions: str | None = None
    results: str | None = None
    metrics: dict = Field(default_factory=dict)
    skills: list[str] = Field(default_factory=list)
    status: ProjectStatus = "active"


class ProjectCreate(ProjectBase):
    tags: list[str] = Field(default_factory=list)
    extracted_from: UUID | None = None
    confidence: ProjectConfidence = "manual"


class ProjectUpdate(BaseModel):
    """All fields optional — PATCH semantics."""
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    role: str | None = Field(None, max_length=255)
    organization: str | None = Field(None, max_length=255)
    problem: str | None = None
    actions: str | None = None
    results: str | None = None
    metrics: dict | None = None
    skills: list[str] | None = None
    status: ProjectStatus | None = None
    tags: list[str] | None = None
    confidence: ProjectConfidence | None = None


class ProjectOut(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    tags: list[str]
    is_pinned: bool
    is_archived: bool
    confidence: ProjectConfidence
    extracted_from: UUID | None
    extracted_by_agent_run_id: UUID | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
```

Validation rules to enforce in the schema:

- `period_end >= period_start` if both set (use a `model_validator`).
- `skills` must be unique and lowercased on input (use a `field_validator`).
- `metrics` keys must be strings; values must be JSON-primitive (string, number, bool, null) — reject nested dicts.

---

## 5. Service layer (`services/api/app/services/project_service.py`)

Mirror `chat_service.py` and `page_service.py` patterns. All functions are `async def`, take `db: AsyncSession`, and return ORM objects (the endpoint layer handles serialization).

Required functions:

```python
async def create_project(
    db: AsyncSession,
    *,
    user_id: UUID,
    payload: ProjectCreate,
) -> tuple[KosObject, Project]: ...

async def get_project(
    db: AsyncSession,
    *,
    project_id: UUID,
    user_id: UUID,
) -> tuple[KosObject, Project] | None: ...

async def list_projects(
    db: AsyncSession,
    *,
    user_id: UUID,
    limit: int = 50,
    offset: int = 0,
    status: ProjectStatus | None = None,
    skill: str | None = None,
    include_archived: bool = False,
) -> tuple[list[tuple[KosObject, Project]], int]:
    """Returns (rows, total_count). Joins objects + projects, filters deleted_at IS NULL."""
    ...

async def update_project(
    db: AsyncSession,
    *,
    project_id: UUID,
    user_id: UUID,
    payload: ProjectUpdate,
) -> tuple[KosObject, Project] | None: ...

async def soft_delete_project(
    db: AsyncSession,
    *,
    project_id: UUID,
    user_id: UUID,
) -> bool:
    """Sets objects.deleted_at = now(). Returns True if project existed and was deleted."""
    ...
```

**Implementation notes:**

- `create_project` inserts a `KosObject` row with `kind='project'` and a `Project` row in one transaction.
- `update_project` updates the user-controlled fields on both rows (e.g. `title`, `description`, `tags` on `objects`; everything else on `projects`). Bumps `objects.updated_at` and `projects.updated_at`.
- All queries filter `KosObject.user_id == user_id` and `KosObject.deleted_at.is_(None)` (unless `include_archived` flips the latter).
- Use `selectinload(Project.kos_object)` or an explicit `JOIN` — pick whichever matches `chat_service.py`'s style for consistency.
- Do not import or call anything from PHASE-7B's `audited_write_service` — it may not be merged yet. Plain SQLAlchemy writes are fine for 9A. A future commit (after 7B merges) will retrofit project endpoints to use the audited helper.

---

## 6. REST endpoints (`services/api/app/api/v1/projects.py`)

```python
router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project_endpoint(
    payload: ProjectCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectOut: ...


@router.get("", response_model=PaginatedResponse[ProjectOut])
async def list_projects_endpoint(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: ProjectStatus | None = Query(None),
    skill: str | None = Query(None, min_length=1, max_length=64),
    include_archived: bool = Query(False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ProjectOut]: ...


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project_endpoint(
    project_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectOut: ...


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project_endpoint(
    project_id: UUID,
    payload: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectOut: ...


@router.delete("/{project_id}", status_code=204)
async def delete_project_endpoint(
    project_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete. Use the existing POST /api/v1/objects/{id}/restore to undo."""
    ...
```

**Wiring** in `services/api/app/api/v1/router.py`:

```python
from app.api.v1.projects import router as projects_router
# ...
api_router.include_router(projects_router)
```

(Do not pass `prefix=` again — the router defines its own.)

**Error contract:**

- 401 if no user (handled by `get_current_user` dep).
- 404 if project not found, deleted, or owned by another user.
- 422 on validation errors (Pydantic emits these automatically).
- 400 on `period_end < period_start` (raised in schema validator).

---

## 7. AI endpoint: `POST /api/v1/ai/extract-project`

Append a single new endpoint to `services/api/app/api/v1/ai.py`. Do not modify the existing 7 endpoints.

### 7.1 Request / response

```python
class ExtractProjectRequest(BaseModel):
    source_id: UUID                           # the object to extract from (page/chat/source)
    create: bool = True                       # if True, persist a new Project; if False, dry-run preview
    period_hint: tuple[date | None, date | None] | None = None
                                              # optional user-supplied period to anchor extraction


class ExtractedProjectDraft(BaseModel):
    title: str
    description: str | None
    period_start: date | None
    period_end: date | None
    role: str | None
    organization: str | None
    problem: str | None
    actions: str | None
    results: str | None
    metrics: dict
    skills: list[str]
    confidence: float = Field(..., ge=0.0, le=1.0)
                                              # model self-reported confidence; mapped to confidence='ai_extracted' on persist


class ExtractProjectResponse(BaseModel):
    draft: ExtractedProjectDraft
    project_id: UUID | None                   # populated only if create=True succeeded
    agent_run_id: UUID
    source_id: UUID
```

### 7.2 Endpoint

```python
@router.post("/extract-project", response_model=ExtractProjectResponse)
async def extract_project_endpoint(
    payload: ExtractProjectRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExtractProjectResponse: ...
```

### 7.3 Behavior

1. Load the source object (must be `kind in ('page', 'chat', 'source')`; reject otherwise with 400).
2. Pull its text:
   - For `page`: `pages.content_text`.
   - For `chat`: `chats.content_text` (or the first 12k chars of `parsed_turns` joined).
   - For `source`: `sources.extracted_text`.
3. Truncate to 12k chars (model context budget).
4. Build a prompt (see Section 7.5) and call OpenAI via the existing helper used by `extract-claims` / `triage` (look at how `services/api/app/ai/extractor.py` or the inline call in `api/v1/ai.py` already does it — match that pattern; do not introduce a new client).
5. Parse the model's JSON response into `ExtractedProjectDraft`.
6. Write an `AgentRun` row (status=`success`, agent_type=`extract-project`, input/output/model recorded; matches existing `agent_runs` values from `call_ai`).
7. If `payload.create == True`, call `project_service.create_project` with `confidence='ai_extracted'`, `extracted_from=source_id`, `extracted_by_agent_run_id=agent_run.id`, and the draft fields.
8. Return the response.

### 7.4 AI-disabled handling

Match the existing pattern: if `OPENAI_API_KEY` is missing, return 503 with `detail="AI features disabled — set OPENAI_API_KEY"`. The AI router already has this check; reuse it.

### 7.5 Prompt (system + user)

```
SYSTEM:
You extract a single, well-structured PROJECT record from professional content.

A "project" is a bounded effort the person worked on with measurable scope:
problem solved, actions taken, results achieved, metrics where available,
skills exercised, and a time period.

Return JSON matching this schema (no prose, no markdown, no code fences):
{
  "title": string,                    // <= 80 chars, the project's canonical name
  "description": string | null,       // <= 280 chars one-liner
  "period_start": string | null,      // ISO date YYYY-MM-DD, or null if unknown
  "period_end": string | null,        // ISO date YYYY-MM-DD; null = ongoing
  "role": string | null,              // the person's role (e.g. "Lead Engineer")
  "organization": string | null,      // company / institution / "personal"
  "problem": string | null,           // 1–3 sentences
  "actions": string | null,           // 1–5 sentences, what THE PERSON did
  "results": string | null,           // 1–3 sentences, outcomes
  "metrics": object,                  // flat string→primitive map; empty {} if none
  "skills": string[],                 // lowercase, deduped, <= 12 items
  "confidence": number                // 0.0–1.0; how confident in this extraction
}

Rules:
- If the source mentions multiple distinct projects, pick the one most prominent
  by space/specificity. Do not merge two projects.
- If the source is not about a project (e.g. a generic discussion), return
  confidence <= 0.2 and minimal fields.
- Do not invent dates, employers, or metrics. Use null/empty when unknown.
- Lowercase skills. Strip leading/trailing whitespace.

USER:
Title hint (may be empty): {object.title}
Period hint (may be null): {payload.period_hint}

Source content (truncated to 12k chars):
---
{source_text}
---
```

Use OpenAI's JSON-mode (`response_format={"type": "json_object"}`) to force valid JSON. On parse failure, return 502 with `detail="AI returned malformed JSON"` and record the failure on the `AgentRun` row.

### 7.6 Skill normalization

After parsing, normalize skills server-side:
- lowercase
- strip whitespace
- dedupe preserving order
- drop empty strings
- cap at 12 items

This protects against model output variance independent of the prompt.

---

## 8. Migration (`services/api/alembic/versions/0007_add_projects_table.py`)

Mirror `0005_add_chats.py`'s style. Set `revision = "0007"`, `down_revision = "0006"`. Implement `upgrade()` and `downgrade()` exactly matching Section 3.2.

```python
"""add projects

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-15
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("role", sa.Text(), nullable=True),
        sa.Column("organization", sa.Text(), nullable=True),
        sa.Column("problem", sa.Text(), nullable=True),
        sa.Column("actions", sa.Text(), nullable=True),
        sa.Column("results", sa.Text(), nullable=True),
        sa.Column("metrics", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column(
            "skills",
            postgresql.ARRAY(sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("confidence", sa.String(16), server_default="manual", nullable=False),
        sa.Column("extracted_from", sa.Uuid(), nullable=True),
        sa.Column("extracted_by_agent_run_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["id"], ["objects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["extracted_from"], ["objects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["extracted_by_agent_run_id"], ["agent_runs.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_period_start", "projects", ["period_start"])
    op.create_index("ix_projects_period_end", "projects", ["period_end"])
    op.create_index("ix_projects_status", "projects", ["status"])
    op.create_index(
        "ix_projects_skills",
        "projects",
        ["skills"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_projects_skills", "projects")
    op.drop_index("ix_projects_status", "projects")
    op.drop_index("ix_projects_period_end", "projects")
    op.drop_index("ix_projects_period_start", "projects")
    op.drop_table("projects")
```

Run `cd services/api && uv run alembic upgrade head` locally to verify.

---

## 9. Tests (`tests/api/test_projects.py` — minimum 12 cases)

Match the existing fixture pattern in `tests/api/conftest.py` (real Postgres `knowledgeos_test`, fresh per test, `httpx.AsyncClient` against the FastAPI ASGI transport).

Required test cases:

| # | Test | What it asserts |
|---|---|---|
| 1 | `test_create_project_minimal` | POST with only `title` → 201, returned shape matches `ProjectOut`, `confidence='manual'`, `kind='project'` row exists in `objects`. |
| 2 | `test_create_project_full` | POST with all fields including dates, metrics, skills → all persisted. |
| 3 | `test_create_project_period_validation` | POST with `period_end < period_start` → 422. |
| 4 | `test_create_project_skill_normalization` | POST with `skills=["Python", " python ", "FASTAPI"]` → stored as `["python", "fastapi"]`. |
| 5 | `test_get_project` | GET an existing project → 200, full shape. |
| 6 | `test_get_project_404_when_other_user_owns_it` | A's project is invisible to B. |
| 7 | `test_list_projects_pagination` | Create 5 projects, GET with `limit=2, offset=2` → returns 2 items, `total=5`. |
| 8 | `test_list_projects_filter_by_status` | GET `?status=completed` returns only completed. |
| 9 | `test_list_projects_filter_by_skill` | GET `?skill=python` returns only projects whose `skills` array contains `python`. |
| 10 | `test_update_project` | PATCH partial fields → only those fields change; `updated_at` advances. |
| 11 | `test_soft_delete_project` | DELETE → 204; subsequent GET → 404; row still in DB with `deleted_at` set. |
| 12 | `test_restore_project_via_existing_objects_endpoint` | DELETE then POST `/api/v1/objects/{id}/restore` → project visible again. |

Add to `tests/api/test_ai.py` (do not modify existing tests):

| # | Test | What it asserts |
|---|---|---|
| 13 | `test_extract_project_from_page` | With OpenAI mocked to return a valid JSON draft, POST `/ai/extract-project` with a page source → 200, draft fields populated, `project_id` populated, an `agent_runs` row exists with `agent_type='extract-project'` and `status='success'` (canonical `agent_runs.status` value; same as other AI endpoints). |
| 14 | `test_extract_project_dry_run` | Same as above with `create=False` → response has `project_id=None`, no row in `projects` table. |
| 15 | `test_extract_project_invalid_kind` | source object is an asset → 400 with descriptive detail. |
| 16 | `test_extract_project_ai_disabled` | `OPENAI_API_KEY` env unset → 503. |
| 17 | `test_extract_project_malformed_json` | OpenAI returns non-JSON → 502, `agent_runs` row recorded with `status='failed'`. |

Total: **17 new pytest cases**.

---

## 10. Commit sequence (10 commits, each independently revertible)

| # | Commit message | Files |
|---|---|---|
| 1 | `docs(phase9a): add career memory backend foundation plan` | `project-phases/PHASE-9A-CAREER-MEMORY-BACKEND.md` (this file — already committed; skip if present) |
| 2 | `feat(api): add project to valid object kinds` | `core/object_kinds.py` |
| 3 | `feat(api): projects table migration (0007)` | `alembic/versions/0007_add_projects_table.py` |
| 4 | `feat(api): Project ORM model and __init__ export` | `models/project.py`, `models/__init__.py` |
| 5 | `feat(api): project pydantic schemas` | `schemas/project.py`, `schemas/__init__.py` (if pattern) |
| 6 | `feat(api): project_service for crud operations` | `services/project_service.py` |
| 7 | `feat(api): /projects rest endpoints` | `api/v1/projects.py`, `api/v1/router.py` |
| 8 | `test(api): integration tests for projects crud (12 cases)` | `tests/api/test_projects.py` |
| 9 | `feat(api): ai extract-project endpoint` | `api/v1/ai.py` |
| 10 | `test(api): tests for extract-project endpoint (5 cases)` | `tests/api/test_ai.py` |
| 11 | `docs(progress): mark phase 9a complete` | `PROGRESS.md` |

If running the migration changes anything in `alembic_version` lockfiles or generated artifacts, include those in the migration commit.

---

## 11. Validation commands (run before each commit)

```bash
# Lint + format
cd services/api && uv run ruff check . && uv run ruff format --check .

# Migration up + down on the test DB
cd services/api && uv run alembic upgrade head
cd services/api && uv run alembic downgrade -1
cd services/api && uv run alembic upgrade head

# Targeted tests first
cd tests && uv run pytest api/test_projects.py -v

# Then the AI tests (existing + new)
cd tests && uv run pytest api/test_ai.py -v

# Full suite — must stay green
cd tests && uv run pytest api/ -v
```

The full API suite (existing 112 + new 12 + new 5) should report **129 passing tests** at the end.

---

## 12. Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Adding `"project"` to `VALID_OBJECT_KINDS` regresses an existing test that asserts the tuple length or contents | Low | Search `tests/` for `VALID_OBJECT_KINDS` before commit; expect zero hits. If found, update the test to be a superset assertion. |
| `extracted_from` FK to `objects.id` blocks deletion of a source that seeded a project | Low | `ON DELETE SET NULL` clause handles it; verified in migration. |
| Skill GIN index migration is slow on a non-empty `projects` table | None | Table is brand new; empty at migration time. |
| OpenAI returns non-JSON despite `response_format=json_object` | Low | Wrap parse in `try/except`, write `agent_runs` row with `status='failed'`, return 502. Test #17 covers this. |
| `extract-project` runs against a 200-page source and burns tokens | Medium | Hard-truncate to 12k chars before sending. Log token usage on the `AgentRun` row (input_tokens/output_tokens) so the user can see cost. |
| Future PHASE-7B's audited-write helper isn't applied to project mutations | Medium | Out of scope for 9A; document as a follow-up "9A.x retrofit projects to use audited_write" in `PROGRESS.md`. Tests written today don't depend on the audited helper. |
| `period_end < period_start` validator runs only on full schemas, not partial PATCH | Medium | Add the validator to both `ProjectCreate` (model_validator on full model) and `ProjectUpdate` (only when both fields are present in the partial update). Test #3 covers create; add a 4th update test if desired. |
| `metrics` field accepts deeply nested dicts and breaks downstream consumers | Low | Validator rejects non-primitive values (string/number/bool/null only). |
| `PROGRESS.md` merge conflict with worktrees | Certain (trivial) | Resolve by keeping all sections from all branches. Don't fight the merge. |

---

## 13. Out of scope (Phase 9B / 9C / 9D)

Explicitly deferred:

- **MCP tools.** `get_project` read tool, `create_project` / `update_project` write tools. Wait until 7B merges so the audited-write helper is available.
- **Resume bullet generator.** New endpoint `POST /api/v1/ai/generate-resume-bullets` that takes a `project_id` and returns markdown bullets with citations to underlying pages/sources. Phase 9B.
- **Interview story generator.** New endpoint `POST /api/v1/ai/generate-interview-story` that takes a `project_id` and a question style (STAR, behavioral, technical), returns a structured story. Phase 9B.
- **Project ↔ source/page evidence linking via typed edges.** Frontend will surface "Link this page to project X" via existing `POST /api/v1/edges` with `kind="belongs_to_project"`. No backend work needed; document in 9C.
- **Project list page in frontend** (`/app/projects`, `/app/projects/[id]`). Phase 9C; will adopt `<ListPage>` from PHASE-ENHANCE-03 UX-T4.
- **Project AI panel** (extract-project button, regenerate bullets, etc.). Phase 9D.
- **`belongs_to_project` semantic search boost** (e.g. when searching, prefer evidence linked to a project the user is currently viewing). Phase 9E.
- **CSV export of all projects.** Phase 9D.
- **`projects.status='paused'` reminder workflow.** Out of scope; future.

---

## 14. Definition of Done

- All 11 commits landed on a feature branch and PR opened to `main`.
- 17 new tests pass; existing 112 API tests + 16 backend unit tests still pass.
- `cd services/api && uv run alembic upgrade head` clean from a fresh DB.
- `cd services/api && uv run alembic downgrade base && uv run alembic upgrade head` clean (round-trip).
- `cd services/api && uv run ruff check . && uv run ruff format --check .` clean.
- `PROGRESS.md` updated with a Phase 9A status row pointing at this plan.
- Manual smoke test:
  ```bash
  # With docker compose stack up:
  curl -X POST http://localhost:8001/api/v1/auth/login \
    -d '{"email":"...","password":"..."}' -H 'content-type: application/json' \
    -c /tmp/c.txt
  curl -X POST http://localhost:8001/api/v1/projects \
    -H 'content-type: application/json' -b /tmp/c.txt \
    -d '{"title":"Test project","skills":["python"]}'
  curl http://localhost:8001/api/v1/projects -b /tmp/c.txt
  ```
  Both calls return 2xx with the expected shapes.
- PR description includes:
  - Confirmation that `git diff main...HEAD --name-only` is a strict subset of the file list in Section 1.2 + Section 1.3.
  - Output of `cd tests && uv run pytest api/ -v 2>&1 | tail -10` showing 129 passed.
  - One-paragraph note on what Phase 9B will follow up.

---

## 15. Suggested order of operations for the AI coder

1. Read this file end-to-end. Read Section 1 twice.
2. Read `services/api/app/models/chat.py`, `schemas/chat.py`, `services/chat_service.py`, `api/v1/chats.py`, `alembic/versions/0005_add_chats.py` — these are the closest existing reference for the pattern you'll mirror.
3. Read `tests/api/conftest.py` and `tests/api/test_chats.py` — these are the test-fixture pattern.
4. Read `tests/api/test_ai.py` — the AI-mock pattern for test #13–17.
5. Confirm the worktree state: `git fetch && git status` on `main`. If `main` has moved since this plan was written, rebase.
6. Create branch `phase-9a-career-memory-backend` off latest `main`.
7. Walk commits 2 → 11 in order. Run `cd tests && uv run pytest api/test_projects.py -v` after commit 8 and `…test_ai.py -v` after commit 10. The full `pytest api/ -v` runs once before the PR opens.
8. Open the PR with the description outlined in Section 14.

When in doubt: prefer doing less, prefer matching the existing chat / page implementation pattern over inventing new structure, prefer staying inside the file list in Section 1.2 + 1.3. If something feels like it requires editing `objects.py` or `mcp/tools.py`, **stop** — that's PHASE-7B's territory and should be deferred to 9B.
