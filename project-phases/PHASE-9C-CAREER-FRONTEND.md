# Phase 9C — Career Memory Frontend

> **Status:** ✅ Complete (merged to `main` — branch `phase-9c-career-frontend`, 21 commits)
> **Owner:** Codex (implementation) under Claude orchestration
> **Audience:** AI coder — read end-to-end before writing code.
> **Estimated effort:** ~1 PR, ~12–15 commits, ~2,500–3,000 LOC including tests.
> **Blocks:** PHASE-9D-CAREER-MCP (stacks on 9C).
> **Blocked by:** Phase 9A (shipped on `main`), Phase 9B (shipped on `main`), Phase 7B (`audited_write_service` + rate limiter on `main`).
> **Branch:** `phase-9c-career-frontend` (worktree: `../akm-phase-9c`).

---

## 0. North Star

Phase 9A shipped the `project` object kind, CRUD API, and `POST /ai/extract-project`. Phase 9B shipped `POST /ai/generate-resume-bullets` and `POST /ai/generate-interview-story`. Neither phase touched the frontend.

Phase 9C closes every remaining frontend gap:

- `/app/projects` list page (career memory dashboard — timeline view, filters, completeness badges)
- `/app/projects/[id]` detail page (overview, evidence, resume bullets, interview stories, export)
- Evidence linking UI (`belongs_to_project` edge create/delete from within the project view)
- Generate → preview → save flow for bullets and stories (artifacts persisted as first-class objects)
- Markdown + PDF + copy-to-clipboard export
- Workspace side-pane support for projects
- Frontend types, API client functions, SWR hooks
- ≥ 6 Vitest component/hook tests + 1 Playwright E2E spec
- Docs: `docs/API.md`, `docs/AGENT_GUIDE.md`, `PROGRESS.md`

**What this phase does NOT do:**

- No MCP tools — that is Phase 9D.
- No retrofit of `project_service` mutations to `audited_write_service` (low-priority follow-up).
- No in-place editing of generated bullets/stories — user regenerates.
- No public sharing links. Local-only.
- No new search providers; new object kinds get chunked via existing `reindex_service` pipeline.

---

## 1. Architecture decisions

### AD-1 — Generated artifacts are first-class KosObject kinds

Resume bullet sets and interview stories are stored as **new object kinds** (`resume_bullet_set`, `interview_story`), not as JSONB on the project. Rationale: queryable, search-indexable, MCP-accessible, supports multiple variants per project, aligns with the universal `KosObject` pattern.

Each artifact is linked to its project via a `belongs_to_project` edge and to evidence via `cites` edges.

### AD-2 — Persist on save, not on generate

The 9B generate endpoints stay read-only (preview). The frontend offers a **"Save"** action after generation that calls `POST /api/v1/projects/{id}/resume-bullet-sets` or `/interview-stories`. This keeps regeneration cheap and avoids stale artifacts accumulating silently.

### AD-3 — Dashboard = enriched projects list

The career memory dashboard (original Phase 9 subtask 6) is **the projects list page**, sorted by `period_start desc`, with status/skill filters and a completeness badge per card. No separate route.

### AD-4 — Export is browser-side

- Markdown: pure string assembly, download via anchor blob.
- PDF: `jspdf`. If bundle impact > 150 kB gzipped, fall back to `window.print()` with a print stylesheet and note the choice in the commit.
- Copy-to-clipboard: `navigator.clipboard.writeText`.

---

## 2. Non-breakage contract

- All existing backend tests (`pytest api/` ~135, `unit/` 16, `worker/` 29, MCP 20) pass unchanged.
- All existing frontend tests (`pnpm test:run` ~27 files) pass unchanged.
- All existing Playwright specs (10) pass unchanged.
- `pnpm typecheck`, `pnpm lint`, `pnpm build` green.
- `ruff check services/api && ruff format --check services/api` clean.
- Object kind expansion strictly additive — no existing kind changes behavior.
- Soft-delete preserved for new kinds; restore via existing `POST /objects/{id}/restore`.
- 503 degradation contract: no `OPENAI_API_KEY` → AI panels show disabled-state banner, never crash.

---

## 3. Files inventory

### MAY NOT touch

| File / dir | Why |
|---|---|
| `services/api/alembic/versions/0001..0007*.py` | Never edit applied migrations. |
| `services/api/app/services/{agent_run_service,audited_write_service,revision_service}*.py` | 7B-owned; 9C imports only. |
| `services/api/app/api/v1/{objects,pages,workspaces}.py` | 7B/8B-owned. |
| `services/api/app/services/career_ai_service.py`, `career_ai_prompts.py`, `schemas/career_ai.py` | 9B-owned; 9C imports only. |
| `services/mcp/**` | 9D owns. |
| `services/worker/**` | Out of scope. |
| `infra/**` | No env or compose changes for 9C. |
| `apps/web/src/app/(app)/app/{pages,sources,assets,chats,inbox,trash,workspaces}/**` | Reference only; no edits. |

### MAY edit (additive only)

| File | Allowed change |
|---|---|
| `services/api/app/core/object_kinds.py` | Append `"resume_bullet_set"`, `"interview_story"`. |
| `services/api/app/models/__init__.py` | Append ORM imports + `__all__` entries. |
| `services/api/app/schemas/__init__.py` | Append re-exports if pattern exists (inspect first). |
| `services/api/app/api/v1/router.py` | Append `include_router(career_artifacts_router)`. |
| `services/api/app/services/reindex_service.py` | Add new kinds to chunking dispatch (inspect first). |
| `apps/web/src/types/index.ts` | Append all project + career-artifact types; extend `ObjectKind`. |
| `apps/web/src/lib/api.ts` | Append project + career-artifact + AI career API functions. |
| `apps/web/src/lib/objectRouting.ts` | Add `"project"`, `"resume_bullet_set"`, `"interview_story"` handlers. |
| `apps/web/src/components/layout/Sidebar.tsx` | Insert "Projects" nav item between Chats and Inbox. |
| `apps/web/src/components/workspace/ObjectPaneViewer.tsx` | Add `case "project"` dispatch. |
| `tests/api/test_projects.py` | May append tests for new artifact endpoints if cleaner than a separate file. |
| `PROGRESS.md` | Append 9C status section. |
| `docs/API.md` | Append "Career Artifacts" section. |
| `docs/AGENT_GUIDE.md` | Append "Career Module" section. |
| `README.md` | One-line pointer to AGENT_GUIDE career section. |

### MUST create

**Backend:**
```
services/api/alembic/versions/0009_add_career_artifacts.py
services/api/app/models/resume_bullet_set.py
services/api/app/models/interview_story_record.py
services/api/app/schemas/career_artifacts.py
services/api/app/services/career_artifact_service.py
services/api/app/api/v1/career_artifacts.py
tests/api/test_career_artifacts.py
```

**Frontend:**
```
apps/web/src/app/(app)/app/projects/page.tsx
apps/web/src/app/(app)/app/projects/[id]/page.tsx
apps/web/src/lib/hooks/useProjects.ts
apps/web/src/components/projects/ProjectCard.tsx
apps/web/src/components/projects/CompletenessBadge.tsx
apps/web/src/components/projects/ProjectForm.tsx
apps/web/src/components/projects/ProjectView.tsx
apps/web/src/components/projects/EvidencePanel.tsx
apps/web/src/components/projects/LinkToProjectModal.tsx
apps/web/src/components/projects/ResumeBulletsPanel.tsx
apps/web/src/components/projects/InterviewStoryPanel.tsx
apps/web/src/components/projects/ExtractProjectModal.tsx
apps/web/src/components/projects/ProjectPaneView.tsx
apps/web/src/lib/export/projectMarkdown.ts
apps/web/src/lib/export/projectPdf.ts
apps/web/src/components/projects/__tests__/ProjectForm.test.tsx
apps/web/src/components/projects/__tests__/ResumeBulletsPanel.test.tsx
apps/web/src/components/projects/__tests__/InterviewStoryPanel.test.tsx
apps/web/src/components/projects/__tests__/EvidencePanel.test.tsx
apps/web/src/lib/hooks/__tests__/useProjects.test.ts
apps/web/src/lib/export/__tests__/projectMarkdown.test.ts
tests/e2e/specs/career-project.spec.ts
```

---

## 4. Existing patterns to reuse (read these files before coding)

| Pattern needed | Reference file |
|---|---|
| List page shell + toolbar + bulk | `apps/web/src/components/lists/{ListPage,ListToolbar,BulkActionBar}.tsx` |
| List selection + keyboard nav | `apps/web/src/lib/hooks/{useListSelection,useListKeyNav}.ts` |
| List page (best template) | `apps/web/src/app/(app)/app/pages/page.tsx` |
| Detail page server component | `apps/web/src/app/(app)/app/pages/[id]/page.tsx` |
| SWR hook pattern | `apps/web/src/lib/hooks/useChats.ts` |
| Object picker for modals | `apps/web/src/components/graph/{ObjectPicker,LinkToModal}.tsx` |
| Toast | `apps/web/src/components/ui/Toast.tsx` |
| Workspace pane dispatch | `apps/web/src/components/workspace/ObjectPaneViewer.tsx` |
| Audited write service | `services/api/app/services/audited_write_service.py` |
| Phase 9A backend (data shape) | `services/api/app/{models,schemas,services,api/v1}/project*.py` |
| Phase 9B AI schemas | `services/api/app/schemas/career_ai.py` |

---

## 5. Subtasks

### Subtask 0 — Audit + branch setup

- Confirm `main` is green: `make test-all`.
- Create worktree: `git worktree add ../akm-phase-9c -b phase-9c-career-frontend`.
- Append "🚧 Phase 9C — In Progress" to PROGRESS.md summary table.

**Commit:** `chore(phase-9c): branch + progress tracker`

---

### Subtask 1 — Migration 0009 + ORM models

**Migration `0009_add_career_artifacts.py`:**

```sql
CREATE TABLE resume_bullet_sets (
    id UUID PRIMARY KEY REFERENCES objects(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
    target_role TEXT,
    emphasis TEXT,
    count SMALLINT NOT NULL,
    bullets JSONB NOT NULL DEFAULT '[]',
    agent_run_id UUID REFERENCES agent_runs(id) ON DELETE SET NULL,
    prompt_version VARCHAR(16),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_resume_bullet_sets_project_id ON resume_bullet_sets(project_id);

CREATE TABLE interview_story_records (
    id UUID PRIMARY KEY REFERENCES objects(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
    question_type VARCHAR(16) NOT NULL DEFAULT 'behavioral',
    target_role TEXT,
    max_words INT NOT NULL DEFAULT 400,
    word_count INT NOT NULL DEFAULT 0,
    story JSONB NOT NULL DEFAULT '{}',
    agent_run_id UUID REFERENCES agent_runs(id) ON DELETE SET NULL,
    prompt_version VARCHAR(16),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_interview_story_records_project_id ON interview_story_records(project_id);
CREATE INDEX ix_interview_story_records_question_type ON interview_story_records(question_type);
```

**ORM models** (`resume_bullet_set.py`, `interview_story_record.py`): mirror the `Project` model pattern — FK to `objects(id)`, no `user_id` column (derive via KosObject parent join).

**`core/object_kinds.py`:** append `"resume_bullet_set"` and `"interview_story"` to `VALID_OBJECT_KINDS`.

**`models/__init__.py`:** import and export the two new ORM classes.

**Commit:** `feat(api): migration 0009 + resume_bullet_set and interview_story ORM kinds`

---

### Subtask 2 — Pydantic schemas + career artifact service

**`schemas/career_artifacts.py`:**

```python
class SaveResumeBulletSetRequest(BaseModel):
    target_role: str | None = Field(None, max_length=255)
    emphasis: str | None = Field(None, max_length=500)
    count: int = Field(..., ge=1, le=5)
    bullets: list[ResumeBullet]          # reuse ResumeBullet from career_ai.py
    agent_run_id: UUID | None = None
    prompt_version: str | None = None

class ResumeBulletSetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; user_id: UUID; project_id: UUID
    target_role: str | None; emphasis: str | None; count: int
    bullets: list[dict]   # raw JSONB
    agent_run_id: UUID | None; prompt_version: str | None
    created_at: datetime; updated_at: datetime; deleted_at: datetime | None

class SaveInterviewStoryRequest(BaseModel):
    question_type: InterviewQuestionType = "behavioral"
    target_role: str | None = Field(None, max_length=255)
    max_words: int = Field(..., ge=100, le=800)
    word_count: int = Field(..., ge=0)
    story: StarStory                     # reuse StarStory from career_ai.py
    agent_run_id: UUID | None = None
    prompt_version: str | None = None

class InterviewStoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; user_id: UUID; project_id: UUID
    question_type: str; target_role: str | None
    max_words: int; word_count: int; story: dict
    agent_run_id: UUID | None; prompt_version: str | None
    created_at: datetime; updated_at: datetime; deleted_at: datetime | None
```

**`services/career_artifact_service.py`** — async SQLAlchemy 2.0 pattern (mirror `project_service.py`):

- `save_resume_bullet_set(db, *, user_id, project_id, payload)`:
  1. Load project; 404 if not found/deleted/not owned.
  2. Call `audited_write_service.audited_write(db, user_id=user_id, tool_name="save_resume_bullet_set", agent_type="user_action", fn=_do_save_rbs, ...)`.
  3. Inside `_do_save_rbs`: create `KosObject(kind="resume_bullet_set", title=f"Bullets · {project.title}")`, create `ResumeBulletSet` row, create `belongs_to_project` edge to project, create `cites` edges to each unique `evidence_object_id` in bullets. Return ResumeBulletSet ORM row.

- `save_interview_story(db, *, user_id, project_id, payload)` — analogous, `kind="interview_story"`, `title=f"Story · {project.title} ({payload.question_type})"`.

- `list_resume_bullet_sets(db, *, user_id, project_id, limit=50, offset=0)` — join KosObject; filter `deleted_at IS NULL`; order by `created_at DESC`.

- `get_resume_bullet_set(db, *, user_id, id)` — ownership-checked via KosObject.user_id.

- `delete_resume_bullet_set(db, *, user_id, id)` — soft-delete KosObject.deleted_at.

- Mirror set for `interview_story`.

**Commit:** `feat(api): career_artifact_service with audited_write for bullet sets and stories`

---

### Subtask 3 — REST endpoints

**`api/v1/career_artifacts.py`** — new APIRouter, prefix `/api/v1`:

| Method | Path | Status | Body | Returns |
|---|---|---|---|---|
| POST | `/projects/{project_id}/resume-bullet-sets` | 201 | SaveResumeBulletSetRequest | ResumeBulletSetOut |
| GET | `/projects/{project_id}/resume-bullet-sets` | 200 | — | list[ResumeBulletSetOut] |
| GET | `/resume-bullet-sets/{id}` | 200 | — | ResumeBulletSetOut |
| DELETE | `/resume-bullet-sets/{id}` | 204 | — | — |
| POST | `/projects/{project_id}/interview-stories` | 201 | SaveInterviewStoryRequest | InterviewStoryOut |
| GET | `/projects/{project_id}/interview-stories` | 200 | ?question_type= | list[InterviewStoryOut] |
| GET | `/interview-stories/{id}` | 200 | — | InterviewStoryOut |
| DELETE | `/interview-stories/{id}` | 204 | — | — |

Restore: existing `POST /objects/{id}/restore` already handles all object kinds.

Register in `api/v1/router.py`: `router.include_router(career_artifacts_router)`.

**Commit:** `feat(api): REST endpoints for career artifacts (bullet sets + stories)`

---

### Subtask 4 — Reindex integration

Inspect `services/api/app/services/reindex_service.py`. Add `"resume_bullet_set"` and `"interview_story"` to the kind dispatch so:

- `resume_bullet_set`: chunk the concatenated bullet texts.
- `interview_story`: chunk the concatenated STAR section texts (situation + task + action + result).

Call `reindex_object(object_id)` in `career_artifact_service.py` after each successful save (same pattern as `project_service.py` post-create).

**Commit:** `feat(api): index career artifacts into keyword + vector search`

---

### Subtask 5 — Backend tests

`tests/api/test_career_artifacts.py` (~14 tests covering):

1. `test_save_resume_bullet_set_201` — POST → 201, audit row created, `belongs_to_project` edge exists, `cites` edges for each evidence_object_id.
2. `test_save_bullet_set_empty_evidence` — bullets with no evidence_object_ids → no cites edges.
3. `test_save_bullet_set_wrong_user_project` — project owned by other user → 404.
4. `test_save_bullet_set_deleted_project` — soft-deleted project → 404.
5. `test_list_bullet_sets_paginated` — create 3 sets, GET with limit=2 → 2 items.
6. `test_get_bullet_set_ownership` — other user GET → 404.
7. `test_delete_bullet_set_soft` — DELETE → 204, GET → 404, `deleted_at` set on KosObject.
8. `test_restore_bullet_set` — DELETE then `POST /objects/{id}/restore` → visible again.
9. `test_save_interview_story_201` — POST → 201, audit row, edges.
10. `test_list_stories_filter_question_type` — two behavioral + one technical; GET ?question_type=technical → 1 item.
11. `test_delete_interview_story_soft`.
12. `test_bullet_set_appears_in_object_list` — GET `/objects?kind=resume_bullet_set` includes the saved set.
13. `test_bullet_set_chunks_created` — after save, chunks table has rows for this object_id.
14. `test_story_chunks_created` — same for interview_story.

Verify full suite: `PYTHONPATH=../services/api uv run --project ../services/api --extra dev pytest api/ unit/ -q` → ~149 tests passing.

**Commit:** `test(api): career artifact endpoints + reindex coverage`

---

### Subtask 6 — Frontend types + API client

**`apps/web/src/types/index.ts`** — append (do not modify existing lines):

```ts
// Extend ObjectKind:
export type ObjectKind =
  | "page" | "asset" | "note" | "bookmark" | "collection"
  | "source" | "chat" | "claim" | "task"
  | "project" | "resume_bullet_set" | "interview_story";

export type ProjectStatus = "active" | "paused" | "completed" | "archived";
export type ProjectConfidence = "manual" | "ai_extracted" | "verified";

export interface ProjectOut {
  id: string; user_id: string; kind: "project";
  title: string; description: string | null; tags: string[];
  is_pinned: boolean; is_archived: boolean;
  period_start: string | null; period_end: string | null;
  role: string | null; organization: string | null;
  problem: string | null; actions: string | null; results: string | null;
  metrics: Record<string, string | number | boolean | null>;
  skills: string[]; status: ProjectStatus; confidence: ProjectConfidence;
  extracted_from: string | null; extracted_by_agent_run_id: string | null;
  created_at: string; updated_at: string; deleted_at: string | null;
}
export interface ProjectCreate {
  title: string; description?: string; tags?: string[];
  period_start?: string; period_end?: string;
  role?: string; organization?: string;
  problem?: string; actions?: string; results?: string;
  metrics?: Record<string, string | number | boolean | null>;
  skills?: string[]; status?: ProjectStatus;
  extracted_from?: string; confidence?: ProjectConfidence;
}
export interface ProjectUpdate extends Partial<ProjectCreate> {}

export interface ResumeBullet {
  text: string; evidence_object_ids: string[];
  confidence: "high" | "medium" | "low"; metrics_cited: string[];
}
export interface StarStory {
  situation: string; task: string; action: string; result: string;
  evidence_object_ids: string[];
}

export interface ResumeBulletSetOut {
  id: string; user_id: string; project_id: string;
  target_role: string | null; emphasis: string | null; count: number;
  bullets: ResumeBullet[]; agent_run_id: string | null; prompt_version: string | null;
  created_at: string; updated_at: string; deleted_at: string | null;
}
export interface InterviewStoryOut {
  id: string; user_id: string; project_id: string;
  question_type: "behavioral" | "technical" | "leadership";
  target_role: string | null; max_words: number; word_count: number;
  story: StarStory; agent_run_id: string | null; prompt_version: string | null;
  created_at: string; updated_at: string; deleted_at: string | null;
}

export interface SaveResumeBulletSetRequest {
  target_role?: string; emphasis?: string; count: number;
  bullets: ResumeBullet[]; agent_run_id?: string; prompt_version?: string;
}
export interface SaveInterviewStoryRequest {
  question_type: "behavioral" | "technical" | "leadership";
  target_role?: string; max_words: number; word_count: number;
  story: StarStory; agent_run_id?: string; prompt_version?: string;
}

export interface GenerateResumeBulletsRequest {
  project_id: string; target_role?: string; emphasis?: string;
  count?: number; max_evidence_objects?: number;
}
export interface GenerateResumeBulletsResponse {
  project_id: string; bullets: ResumeBullet[];
  agent_run_id: string; evidence_count: number;
}
export interface GenerateInterviewStoryRequest {
  project_id: string; question_type?: "behavioral" | "technical" | "leadership";
  target_role?: string; max_words?: number; max_evidence_objects?: number;
}
export interface GenerateInterviewStoryResponse {
  project_id: string; story: StarStory;
  agent_run_id: string; word_count: number;
}
export interface ExtractProjectRequest {
  source_id: string; create?: boolean;
  period_hint?: [string | null, string | null];
}
export interface ExtractedProjectDraft {
  title: string; description: string | null;
  period_start: string | null; period_end: string | null;
  role: string | null; organization: string | null;
  problem: string | null; actions: string | null; results: string | null;
  metrics: Record<string, unknown>; skills: string[]; confidence: number;
}
export interface ExtractProjectResponse {
  draft: ExtractedProjectDraft; project_id: string | null;
  agent_run_id: string; source_id: string;
}
```

**`apps/web/src/lib/api.ts`** — append all project + career artifact + career AI functions following the existing `request<T>()` pattern:

```ts
// Projects CRUD
export async function listProjects(params?: { limit?: number; offset?: number; status?: string; skill?: string; include_archived?: boolean }): Promise<PaginatedResponse<ProjectOut>>
export async function createProject(data: ProjectCreate): Promise<ProjectOut>
export async function getProject(id: string): Promise<ProjectOut>
export async function updateProject(id: string, data: ProjectUpdate): Promise<ProjectOut>
export async function deleteProject(id: string): Promise<void>

// Career AI (generate = preview, no DB write)
export async function extractProject(payload: ExtractProjectRequest): Promise<ExtractProjectResponse>
export async function generateResumeBullets(payload: GenerateResumeBulletsRequest): Promise<GenerateResumeBulletsResponse>
export async function generateInterviewStory(payload: GenerateInterviewStoryRequest): Promise<GenerateInterviewStoryResponse>

// Career artifacts (save = persist)
export async function listResumeBulletSets(projectId: string, params?: { limit?: number; offset?: number }): Promise<ResumeBulletSetOut[]>
export async function saveResumeBulletSet(projectId: string, payload: SaveResumeBulletSetRequest): Promise<ResumeBulletSetOut>
export async function deleteResumeBulletSet(id: string): Promise<void>
export async function listInterviewStories(projectId: string, params?: { question_type?: string; limit?: number }): Promise<InterviewStoryOut[]>
export async function saveInterviewStory(projectId: string, payload: SaveInterviewStoryRequest): Promise<InterviewStoryOut>
export async function deleteInterviewStory(id: string): Promise<void>
```

**`apps/web/src/lib/objectRouting.ts`** — add before the final `return "/app"`:
```ts
if (kind === "project") return `/app/projects/${id}`;
if (kind === "resume_bullet_set" || kind === "interview_story") return `/app/projects`;
```

**Commit:** `feat(web): types + API client for projects and career artifacts`

---

### Subtask 7 — SWR hooks + Sidebar nav

**`apps/web/src/lib/hooks/useProjects.ts`** — mirror `useChats.ts`:

```ts
import useSWR from "swr";
import { listProjects, getProject, listResumeBulletSets, listInterviewStories } from "@/lib/api";
import type { ProjectOut } from "@/types";

export function useProjects(params?: { status?: string; skill?: string; limit?: number }) {
  const { data, error, isLoading, mutate } = useSWR(["projects", params], () => listProjects({ limit: 100, ...params }));
  return { projects: (data?.items ?? []) as ProjectOut[], total: data?.total ?? 0, error, isLoading, mutate };
}
export function useProject(id: string) {
  const { data, error, isLoading, mutate } = useSWR(["project", id], () => getProject(id));
  return { project: data, error, isLoading, mutate };
}
export function useResumeBulletSets(projectId: string) {
  const { data, error, isLoading, mutate } = useSWR(["bullet-sets", projectId], () => listResumeBulletSets(projectId));
  return { bulletSets: data ?? [], error, isLoading, mutate };
}
export function useInterviewStories(projectId: string, questionType?: string) {
  const { data, error, isLoading, mutate } = useSWR(["stories", projectId, questionType], () => listInterviewStories(projectId, { question_type: questionType }));
  return { stories: data ?? [], error, isLoading, mutate };
}
```

**`apps/web/src/components/layout/Sidebar.tsx`** — insert between Chats and Inbox:
```ts
import { Briefcase } from "lucide-react";
// In navItems array:
{ href: "/app/projects", label: "Projects", icon: Briefcase },
```

**Commit:** `feat(web): useProjects SWR hooks + Projects sidebar nav`

---

### Subtask 8 — Projects list page (career dashboard)

`apps/web/src/app/(app)/app/projects/page.tsx` — pattern from `pages/page.tsx`:

- `"use client"` directive.
- `useProjects({ status: statusFilter, skill: skillFilter, limit: 100 })`.
- `ListPage` + `ListToolbar` (search by title/role/org, sort: newest/period-desc/period-asc/alpha).
- Status filter chips: All / Active / Completed / Paused / Archived (controlled state; passed to `useProjects`).
- Skill filter: text input, comma-separated OR semantics.
- `+` button → opens `<ProjectForm mode="create" onSuccess={...} />` in a modal.
- "Extract" button → opens `<ExtractProjectModal />`.
- Each project rendered via `<ProjectCard project={...} />`.
- Bulk delete via `useListSelection` + `BulkActionBar` (calls `deleteProject` in chunks of 4).
- Keyboard nav via `useListKeyNav`.
- Empty states: "No projects yet" / "No projects match".

**Commit:** `feat(web): projects list page — career dashboard with timeline, filters, bulk actions`

---

### Subtask 9 — ProjectCard + CompletenessBadge

`apps/web/src/components/projects/ProjectCard.tsx`:

Renders: title (linked to `/app/projects/{id}`), role @ organization, period_start → period_end (or "Ongoing"), status badge, top-5 skill chips, `<CompletenessBadge project={project} />`, pinned indicator, updated_at relative time.

`apps/web/src/components/projects/CompletenessBadge.tsx`:

Score 0–5: +1 per filled field (problem, actions, results, `skills.length > 0`, `Object.keys(metrics).length > 0`). Badge colors: red (< 2), amber (2–3), green (≥ 4). Shows score like "3/5".

**Commit:** `feat(web): ProjectCard + CompletenessBadge`

---

### Subtask 10 — ProjectForm (create + edit)

`apps/web/src/components/projects/ProjectForm.tsx` — modal (fixed-position overlay, same pattern as chats import modal):

**Props:** `mode: "create" | "edit"`, `initialData?: ProjectOut`, `onSuccess(project: ProjectOut): void`, `onClose(): void`.

**Fields:**
- title (required, text input)
- description (textarea, optional)
- period_start / period_end (date inputs, optional; validate end ≥ start)
- role (text, optional)
- organization (text, optional)
- problem / actions / results (textarea, optional)
- metrics: dynamic key→value row editor; value type hint ("string / number / bool"); validate primitives client-side
- skills: tag-style input (type + Enter to add; pills with ×); normalize to lowercase, dedupe, cap 12
- status (select: active/paused/completed/archived; default active)
- tags (tag-style input)

**Behavior:** on submit call `createProject` or `updateProject`; on success `toast.success(...)` + `onSuccess(result)` + `onClose()`. Surface 422 errors verbatim. Loading state disables submit.

**Commit:** `feat(web): ProjectForm for create and edit`

---

### Subtask 11 — Project detail page + ProjectView

`apps/web/src/app/(app)/app/projects/[id]/page.tsx` — server component:

```tsx
import { cookies } from "next/headers";
import { notFound } from "next/navigation";
import { ProjectView } from "@/components/projects/ProjectView";

export default async function ProjectDetailPage({ params }: { params: { id: string } }) {
  const cookieHeader = cookies().toString();
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/projects/${params.id}`, {
    headers: { Cookie: cookieHeader },
    cache: "no-store",
  });
  if (res.status === 404) notFound();
  const project = await res.json();
  return <ProjectView project={project} />;
}
```

`apps/web/src/components/projects/ProjectView.tsx` — client component:

**Sections (tab-based using simple state, no tab library):**

1. **Overview** — metadata header (title, role @ org, period, status, confidence badge), description, STAR narrative (problem → actions → results as labeled sections), metrics table, skills pills, tags.
2. **Evidence** — `<EvidencePanel projectId={project.id} />`.
3. **Resume Bullets** — `<ResumeBulletsPanel projectId={project.id} project={project} />`.
4. **Interview Stories** — `<InterviewStoryPanel projectId={project.id} project={project} />`.

**Header actions:** Edit (opens `ProjectForm` in edit mode), Pin/Unpin (`updateObject`), Archive (`POST /objects/{id}/archive`), Delete (soft, `deleteProject`, redirect to `/app/projects`).

**Export bar** (always visible at bottom of page):
- "Download Markdown" → `projectToMarkdown(...)` → blob download
- "Download PDF" → `projectToPdf(...)`
- "Copy text" → `navigator.clipboard.writeText(projectToMarkdown(...))`

**Commit:** `feat(web): project detail page + ProjectView with tabs`

---

### Subtask 12 — EvidencePanel + LinkToProjectModal

`apps/web/src/components/projects/EvidencePanel.tsx`:

- Fetch backlinks: `GET /api/v1/objects/{projectId}/backlinks`; filter `edge.kind === "belongs_to_project"`.
- Group evidence cards by kind (Pages / Sources / Chats / Claims / Other).
- Per card: title (linked via `objectRoute`), kind badge, "Open in pane" button (`openSidePane`), "Unlink" button (calls `DELETE /api/v1/edges/{edge.id}`, then revalidates).
- "Link evidence" button → `<LinkToProjectModal projectId={projectId} onLinked={revalidate} />`.
- Empty state: "No evidence linked yet. Link pages, sources, or chats to this project."

`apps/web/src/components/projects/LinkToProjectModal.tsx`:

- Modal with search input (calls `hybridSearch` or `keywordSearch`).
- Kind filter chips (All / Pages / Sources / Chats).
- On select: `POST /api/v1/edges` with `{ source_id: selectedObjectId, target_id: projectId, kind: "belongs_to_project" }`, then close + notify parent.
- Reuse the layout/styling of `LinkToModal.tsx` from the graph panel.

**Commit:** `feat(web): EvidencePanel + LinkToProjectModal`

---

### Subtask 13 — ResumeBulletsPanel

`apps/web/src/components/projects/ResumeBulletsPanel.tsx`:

**State:** `savedSets` from `useResumeBulletSets(projectId)`; `preview: GenerateResumeBulletsResponse | null`; `isGenerating`; `genForm: { target_role, emphasis, count }`.

**Generate form** (collapsible):
- target_role (text, optional)
- emphasis (text, optional)
- count (select 1–5, default 3)
- "Generate" button → calls `generateResumeBullets({ project_id, ...genForm })`; on 503 show "AI disabled" banner; on success sets `preview`.

**Preview section** (shown when `preview !== null`):
- List bullets with: text, confidence badge (green/amber/red), metrics_cited chips, evidence chips (each clickable → `openSidePane`).
- "Save" button → `saveResumeBulletSet(projectId, { ...genForm, count: preview.bullets.length, bullets: preview.bullets, agent_run_id: preview.agent_run_id })` → reloads `savedSets`, clears preview.
- "Discard" button → clears preview.

**Saved sets list**: each set as a collapsible card showing target_role, emphasis, date, bullet count. Expand to show bullets. Per-set actions: Copy as Markdown, Delete (`deleteResumeBulletSet`).

**Commit:** `feat(web): ResumeBulletsPanel with generate/preview/save/delete flow`

---

### Subtask 14 — InterviewStoryPanel

`apps/web/src/components/projects/InterviewStoryPanel.tsx`:

Same shape as ResumeBulletsPanel but for stories:

- Generate form: question_type (select: behavioral/technical/leadership), target_role, max_words (100–800, default 400).
- Preview: render STAR sections (Situation / Task / Action / Result) as labeled blocks; show word count.
- Save → `saveInterviewStory(projectId, { question_type, target_role, max_words, word_count: preview.word_count, story: preview.story, agent_run_id: preview.agent_run_id })`.
- Saved stories list: collapsible cards filtered by question_type (tab chips: All / Behavioral / Technical / Leadership).
- Per-story: Copy as Markdown, Delete.

**Commit:** `feat(web): InterviewStoryPanel`

---

### Subtask 15 — ExtractProjectModal

`apps/web/src/components/projects/ExtractProjectModal.tsx`:

- Reachable from the projects list "Extract" button and (optionally) from Source/Chat detail pages via a context button.
- Object picker: search input + kind filter (pages/sources/chats only) using `hybridSearch`; reuse picker style from `LinkToModal.tsx`.
- Optional period_hint: start date + end date inputs.
- "Create project from this" button → `extractProject({ source_id: selectedId, create: true, period_hint })`.
- 503 → "AI is disabled. Set OPENAI_API_KEY to use this feature."
- On success: `toast.success("Project created")`, `router.push(/app/projects/${response.project_id})`.

**Commit:** `feat(web): ExtractProjectModal`

---

### Subtask 16 — Export utilities

`apps/web/src/lib/export/projectMarkdown.ts`:

```ts
export function projectToMarkdown(
  project: ProjectOut,
  bulletSets: ResumeBulletSetOut[],
  stories: InterviewStoryOut[]
): string
```

Sections:
```
# {title}
**Role:** {role} @ {organization}  **Period:** {period_start} – {period_end}  **Status:** {status}

{description}

## Problem
{problem}

## Actions
{actions}

## Results
{results}

## Metrics
| Key | Value |
|...|...|

## Skills
{skills joined by ", "}

## Resume Bullets
### {target_role} ({date})
- {bullet.text} [{confidence}]

## Interview Stories
### {question_type} — {target_role} ({date})
**Situation:** ...
**Task:** ...
**Action:** ...
**Result:** ...
```

`apps/web/src/lib/export/projectPdf.ts`:

- Import `jspdf` (add dep: `pnpm --filter @kos/web add jspdf`).
- `projectToPdf(project, bulletSets, stories)` — render Markdown into jsPDF with a clean monospace layout; trigger `doc.save('{title}.pdf')`.
- If jspdf gzipped bundle impact > 150 kB, use `window.print()` fallback (note in commit).

**Clipboard**: inline `navigator.clipboard.writeText(projectToMarkdown(...))` in `ProjectView` export bar.

**Commit:** `feat(web): project Markdown + PDF export`

---

### Subtask 17 — Workspace side-pane support

`apps/web/src/components/workspace/ObjectPaneViewer.tsx` — add:
```tsx
if (kind === "project") {
  return <ProjectPaneView id={objectId} />;
}
```

`apps/web/src/components/projects/ProjectPaneView.tsx` — client component:
```tsx
// Uses useProject(id) to load data.
// Renders: title, role @ org, period, status badge, STAR text (truncated), "Open full ↗" button.
// Compact: no tabs, no evidence panel, no generation UI.
```

**Commit:** `feat(web): ProjectPaneView for workspace side pane`

---

### Subtask 18 — Vitest tests

Use existing Vitest + RTL + MSW setup from Phase Enhance 02. MSW handlers registered in `apps/web/src/test/msw/handlers.ts`.

**`ProjectForm.test.tsx`:**
- Renders in create mode; submit with empty title → validation error visible.
- Period validation: end < start → error shown.
- Submit calls `createProject` with normalized skills (lowercase, dedupe).

**`ResumeBulletsPanel.test.tsx`:**
- When `generateResumeBullets` mock returns 503 → disabled banner shown.
- After generate succeeds → preview bullets rendered with confidence badges.
- Save button calls `saveResumeBulletSet` with correct payload.

**`InterviewStoryPanel.test.tsx`:**
- Renders STAR sections from mock story.
- Word count displayed.
- question_type filter chips switch visible stories.

**`EvidencePanel.test.tsx`:**
- Groups evidence cards by kind.
- "Unlink" calls `DELETE /api/v1/edges/{id}`.
- "Link evidence" opens modal, selecting an object calls `POST /api/v1/edges`.

**`useProjects.test.ts`:**
- Renders with `{ status: "completed" }` → `listProjects` called with `status=completed`.
- Handles empty response gracefully.

**`projectMarkdown.test.ts`:**
- `projectToMarkdown(fixture, [], [])` → string contains title, role, skills.
- With bullet sets → bullets section present with correct text.

Verify: `pnpm -F @kos/web test:run` → ~33 test files passing.

**Commit:** `test(web): vitest coverage for project components, hooks, and export`

---

### Subtask 19 — Playwright E2E

`tests/e2e/specs/career-project.spec.ts` — follow pattern of `tests/e2e/specs/ai-summarize.spec.ts`:

```ts
test.describe("Career project golden path", () => {
  test.beforeEach(async ({ page, authenticatedPage }) => { /* login fixture */ });

  test("create project and view in list", async ({ page }) => {
    await page.goto("/app/projects");
    await page.getByRole("button", { name: "New project" }).click();
    await page.getByLabel("Title").fill("KnowledgeOS v1");
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText("KnowledgeOS v1")).toBeVisible();
  });

  test("link evidence to project", async ({ page }) => {
    // navigate to project detail, open evidence tab, link an existing page
    // assert evidence card appears
  });

  test("generate and save resume bullets", async ({ page }) => {
    // navigate to project, resume bullets tab
    // click generate (sk-test-stub → mocked AI endpoint)
    // assert preview bullets visible
    // click save
    // assert saved set card appears
  });

  test("markdown export triggers download", async ({ page }) => {
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: "Download Markdown" }).click(),
    ]);
    expect(download.suggestedFilename()).toMatch(/\.md$/);
  });
});
```

Set `OPENAI_API_KEY=sk-test-stub` in compose env (same as existing AI E2E test). Use the `call_ai` stub path already in place.

**Commit:** `test(e2e): career project golden path`

---

### Subtask 20 — Docs + PROGRESS

- `docs/API.md` — append "Career Artifacts" section listing all 8 new endpoints with request/response shapes; cross-link to §Phase 9A (projects CRUD) and §Phase 9B (generators).
- `docs/AGENT_GUIDE.md` — append "Career Module" with an end-to-end agent example:
  ```
  1. search_objects for pages/chats about a project
  2. extract_project to create the project record
  3. generate_resume_bullets to get a preview
  4. (frontend) save the bullets
  5. generate_interview_story to prepare for interviews
  ```
- `README.md` — add one bullet under "AI Features": "Career memory: project records, AI-generated resume bullets & STAR stories — see [AGENT_GUIDE.md](docs/AGENT_GUIDE.md)."
- `PROGRESS.md` — update Phase 9 row to `🚧 (9A+9B+9C done; 9D MCP pending)`; add 9C status block with all acceptance criteria checked.

**Commit:** `docs(phase-9c): API + AGENT_GUIDE + PROGRESS updates`

---

## 6. Verification

### Backend (subtasks 1–5)

```bash
cd tests
PYTHONPATH=../services/api uv run --project ../services/api --extra dev pytest api/ unit/ -q
# Expected: ~149 tests passing (135 prior + ~14 new)
cd ../services/api && uv run ruff check . && uv run ruff format --check .
```

### Frontend (subtasks 6–18)

```bash
pnpm -F @kos/web test:run     # ≥ 33 files, all passing
pnpm -F @kos/web typecheck
pnpm -F @kos/web lint
pnpm -F @kos/web build
```

### E2E (subtask 19)

```bash
LIBRARY_ROOT=$PWD/tests/e2e/.tmp/library docker compose -f infra/docker-compose.yml up -d --build
pnpm test:e2e
# Expected: 10 prior + 1 new spec, all passing
```

### Full suite

```bash
make test-all
```

### Manual smoke (after `docker compose up -d`)

1. Open http://localhost:3000 → login.
2. Sidebar → **Projects** → empty state shown.
3. **+ New Project** → fill title, role, org, dates, problem, actions, results → Save → card appears with completeness badge.
4. Open project → **Evidence** tab → **Link evidence** → pick an existing page → assert it appears.
5. **Resume Bullets** → Generate (3 bullets, behavioral) → preview → Save → saved card appears.
6. **Interview Stories** → Generate (technical, 300 words) → preview → Save.
7. **Export** → Markdown download → open file, verify all sections present.
8. **Export** → PDF download → opens/saves PDF.

---

## 7. Acceptance criteria

- [x] Migration 0009 applied; `resume_bullet_sets` + `interview_story_records` tables exist; `resume_bullet_set` and `interview_story` in `VALID_OBJECT_KINDS`.
- [x] 8 new REST endpoints operational and returning correct shapes.
- [x] ~14 new backend tests; full suite ~149 passing.
- [x] `ObjectKind` union, all project + career-artifact TypeScript types present in `types/index.ts`.
- [x] All API functions added to `lib/api.ts`; no existing functions modified.
- [x] `/app/projects` list page operational (filters, bulk delete, create, extract).
- [x] `/app/projects/[id]` detail page operational (tabs: overview, evidence, bullets, stories).
- [x] `ProjectForm`, `EvidencePanel`, `ResumeBulletsPanel`, `InterviewStoryPanel`, `ExtractProjectModal` all functional; 503 shows disabled banner.
- [x] "Projects" appears in sidebar nav.
- [x] Workspace side pane can open a project via `openSidePane`.
- [x] Markdown download, PDF download, copy-to-clipboard all work.
- [x] ≥ 6 new Vitest test files; `pnpm test:run` green.
- [x] 1 new Playwright spec; `pnpm test:e2e` green.
- [x] `pnpm typecheck`, `pnpm lint`, `pnpm build` green.
- [x] `docs/API.md`, `docs/AGENT_GUIDE.md`, `PROGRESS.md` updated.
