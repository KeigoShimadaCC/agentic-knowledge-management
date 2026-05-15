# Phase 9B — Career AI Generators (Resume Bullets + Interview Stories)

> **Status:** Planned (parallel-safe with PHASE-7B-MCP-WRITE and PHASE-8B-WORKSPACES-BACKEND)
> **Owner:** Backend
> **Audience:** AI coder (Codex / Claude). Read end-to-end before writing code.
> **Estimated effort:** 1 PR, ~7 commits, ~500–700 LOC including tests.
> **Blocks:** PHASE-9C-CAREER-FRONTEND (planned), PHASE-9D-CAREER-MCP (planned, post-7B).
> **Blocked by:** PHASE-9A-CAREER-MEMORY-BACKEND (merged on `main`).
> **Parallel-safe with:** PHASE-7B-MCP-WRITE (in progress), PHASE-8B-WORKSPACES-BACKEND (planned). Conflict map verified in §2.

---

## 0. North Star

Phase 9A shipped the `project` object kind, the `projects` table, REST CRUD, and `POST /ai/extract-project` that drafts a project from an existing page/source/chat. The Phase 9 vision goes further: a personal career memory system where projects produce **evidence-linked resume bullets** and **STAR-formatted interview stories** generated from real project data already in the knowledge base.

Phase 9B is the next conflict-free slice: **AI generators on top of the 9A foundation**. It introduces two new endpoints — `POST /ai/generate-resume-bullets` and `POST /ai/generate-interview-story` — both of which read an existing `Project` plus its linked evidence (via `extracted_from` and incoming `belongs_to_project` edges) and produce structured AI output. Every call writes an `agent_runs` row using the Phase 5 plumbing.

**Why this slice, this letter, this order:**

The original `PHASE-9A-CAREER-MEMORY-BACKEND.md` §0 lists three remaining slices — MCP tools, generators, frontend — without assigning letters. The natural mapping by dependency is:

| Letter | Slice | Blocked by |
|---|---|---|
| **9B** (this doc) | Resume + interview AI generators | only 9A |
| **9C** (planned, no doc yet) | Career memory frontend (project form, evidence panel, timeline, export) | only 9A; UI track |
| **9D** (planned, no doc yet) | MCP project tools (`create_project`, `update_project`, `archive_project`, generator wrappers) | 9A **and** 7B's `audited_write_service` + rate limiter |

9B is the only post-9A slice that can run in parallel with both PHASE-7B-MCP-WRITE and PHASE-8B-WORKSPACES-BACKEND, so it earns the next letter.

**What this phase does NOT do:**

- No MCP exposure of the new endpoints — that's 9D after 7B merges.
- No frontend changes — 9C owns the project UI, evidence panel, and export.
- No new edge kinds. `belongs_to_project` is already accepted by the existing `POST /edges` (free-string `kind`). The frontend will surface "Link to project" in 9C.
- No write to `objects.metadata` or to the `projects` table during generation. Output is returned to the caller and audited via `agent_runs`; nothing is persisted on the Project record itself in 9B. Optional persistence is 9C's call.
- No `object_revisions` rows. Generation is read-only over evidence; nothing is mutated. (If 9C decides to save a generated bullet onto the project, that write will go through 7B's `audited_write_service` and produce a revision then.)
- No `chunks` / Qdrant writes. Generation reuses search retrieval but does not re-index.
- No new model files. The existing `Project`, `KosObject`, `Edge`, `AgentRun` models are sufficient.

---

## 1. Non-breakage contract

Read this section twice. The whole reason this phase is small and tightly scoped is to guarantee parallel safety with two active worktrees (7B in progress, 8B planned to start in parallel).

### 1.1 Files this phase MAY NOT touch

| File / dir | Why off-limits |
|---|---|
| `services/api/app/api/v1/objects.py` | PHASE-7B owns. |
| `services/api/app/api/v1/pages.py` | PHASE-7B owns. |
| `services/api/app/api/v1/workspaces.py` (when created) | PHASE-8B owns. |
| `services/api/app/services/{agent_run_service,audited_write_service,revision_service}.py` | PHASE-7B owns. |
| `services/api/app/services/project_service.py` | Reserved for the post-7B "audited_write retrofit" follow-up. Touching it now creates a 3-way merge with that follow-up. |
| `services/api/app/services/ai_service.py` | Phase 5 plumbing. Edit at your own risk. 9B adds new functions in a separate service file instead (§5). |
| `services/api/app/services/workspace_service.py` (when created) | PHASE-8B owns. |
| `services/api/app/services/chunk_service.py`, `reindex_service.py`, `search_service.py` | Out of scope; generation reuses retrieval read-only. |
| `services/api/app/core/{library,rate_limit,object_kinds}.py` | PHASE-7B and PHASE-8B own / are off-limits. No new object kind in 9B. |
| `services/api/app/config.py` | PHASE-7B owns (rate-limit config). |
| `services/api/app/schemas/ai.py` | Phase 5 schema file. New types live in `schemas/career_ai.py` (§4) to avoid 3-way merge risk. |
| `services/api/app/schemas/project.py` | Already touched by 9A, will be touched again by 9A retrofit. New 9B types go in `schemas/career_ai.py`. |
| `services/api/app/schemas/workspace.py` (when created) | PHASE-8B owns. |
| `services/mcp/**` | PHASE-7B owns. MCP exposure of generators is 9D. |
| `services/worker/**` | Out of scope. No worker pipeline for generation. |
| `apps/web/**` | Reserved for PHASE-9C-CAREER-FRONTEND (planned). |
| `infra/**` | No env vars or infra changes needed for 9B. |
| `tests/api/test_archive_restore.py`, `test_rate_limit.py`, `test_mcp_writes.py` | New in PHASE-7B. |
| `tests/api/test_workspaces.py` | New in PHASE-8B. |
| `tests/api/test_ai.py`, `tests/api/test_projects.py` | Existing files extended by 9A. 9B's tests live in a new file `tests/api/test_career_ai.py` to avoid co-edit risk. |
| `tests/e2e/**`, `tests/worker/**` | Owned by PHASE-ENHANCE-02. |
| Any existing alembic migration `0001_*.py` … `0008_*.py` | Never edit applied migrations. 9B adds zero migrations. |
| `docs/MCP_TOOLS.md`, `docs/SECURITY.md`, `docs/AGENT_GUIDE.md`, `docs/REVISION_HISTORY.md` | PHASE-7B is rewriting these. |
| `README.md` "MCP & Agent Access" section | PHASE-7B is editing. |

### 1.2 Files this phase MAY edit (small, additive only)

| File | Allowed change |
|---|---|
| `services/api/app/api/v1/ai.py` | Append **two** new endpoint handlers at the end of the file. Do not modify any existing endpoint or any import block above the existing imports. Add only the `career_ai_service` import. Trivial conflict surface; PHASE-7B does not touch this file. |
| `services/api/app/schemas/__init__.py` | If the existing pattern re-exports schemas, append `career_ai` re-exports. Inspect first. |
| `PROGRESS.md` | Append a Phase 9B status section. Trivial 3-way merge with 7B/8B; resolve by keeping all sections. |
| `docs/API.md` | Append a "Career AI Generators" section at the end. |
| `docs/AGENT_GUIDE.md` | **Skip — owned by 7B.** Document agent usage of the new endpoints in a follow-up after 7B merges. |

Notable absence: `services/api/app/api/v1/router.py` is **not** edited. Both new endpoints attach to the existing `ai_router`, which is already mounted.

### 1.3 Files this phase MUST create

```
services/api/app/schemas/career_ai.py
services/api/app/services/career_ai_service.py
services/api/app/services/career_ai_prompts.py
tests/api/test_career_ai.py
project-phases/PHASE-9B-CAREER-AI-GENERATORS.md   ← this file already exists; do not recreate
```

### 1.4 Behaviors that may not regress

- All existing API integration tests pass unchanged.
- All existing unit tests pass unchanged.
- `POST /ai/summarize`, `/extract-claims`, `/extract-tasks`, `/suggest-links`, `/answer`, `/triage`, `/extract-project`, `GET /ai/inbox` — all unchanged in signature and behavior.
- 9A's `Project` CRUD and `POST /ai/extract-project` work identically.
- The 503 degradation contract from Phase 5 applies: when `OPENAI_API_KEY` is unset, both new endpoints return **503** with the standard `{"detail": "AI is disabled..."}` body. Never a 500.
- `agent_runs` rows are created exactly as Phase 5 / 9A do: one row per LLM call, with `tool_name="generate_resume_bullets"` or `"generate_interview_story"`, `status="success"` or `"failed"`, `model`, `tokens_used` populated.

### 1.5 Dependency policy

No new Python dependencies. Uses only FastAPI, SQLAlchemy 2.0 async, Pydantic v2, and the existing `openai` SDK already in `services/api/pyproject.toml`.

---

## 2. Conflict map (verified file-by-file)

Verified via `git diff --name-only main...HEAD` against the active PHASE-7B worktree and the planned scope of PHASE-8B-WORKSPACES-BACKEND on 2026-05-15.

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

Phase 9B wants:
```
NEW:   services/api/app/schemas/career_ai.py,
       services/api/app/services/career_ai_service.py,
       services/api/app/services/career_ai_prompts.py,
       tests/api/test_career_ai.py
EDIT:  services/api/app/api/v1/ai.py (append two endpoints),
       services/api/app/schemas/__init__.py (optional re-export),
       PROGRESS.md, docs/API.md
```

**Overlap:** `PROGRESS.md` only (append-merge). Zero code-file conflict. `api/v1/ai.py` is untouched by 7B.

### vs. PHASE-8B-WORKSPACES-BACKEND (planned)

8B touches:
```
NEW:   services/api/alembic/versions/0008_*.py,
       services/api/app/models/workspace.py,
       services/api/app/schemas/workspace.py,
       services/api/app/services/workspace_service.py,
       services/api/app/api/v1/workspaces.py,
       tests/api/test_workspaces.py
EDIT:  api/v1/router.py, models/__init__.py, schemas/__init__.py,
       PROGRESS.md, docs/API.md, docs/DATA_MODEL.md
```

**Overlap with 9B:**
- `PROGRESS.md` (append-merge, three-way trivial)
- `services/api/app/schemas/__init__.py` (both phases may append a re-export line — three-way trivial)
- `docs/API.md` (both phases append sections — three-way trivial)

Zero code-file conflict.

### vs. PHASE-9A-CAREER-MEMORY-BACKEND (merged) and the 9A follow-up

9A is on `main`. The planned 9A follow-up "retrofit project mutations to `audited_write_service`" (deferred until 7B merges) will touch `services/api/app/services/project_service.py` and `tests/api/test_projects.py`. 9B intentionally does not touch either file (§1.1).

**Overlap:** none.

### vs. PHASE-ENHANCE-02 / -03 (both merged)

Neither touches `services/api/app/api/v1/ai.py` or `services/api/app/services/`. No overlap.

### Migration sequencing

9B adds zero migrations. Latest on `main` is `0007_*`. PHASE-8B will add `0008_*`. PHASE-7B adds none. No conflict.

---

## 3. Endpoint specs

Both endpoints attach to the existing `/ai` router (no router changes). Both require an authenticated session. Both validate ownership of `project_id` (404 if the project is missing, deleted, or owned by another user).

### 3.1 `POST /api/v1/ai/generate-resume-bullets`

**Purpose:** produce 1–5 resume bullet variants for a given project, grounded in linked evidence (the project's `extracted_from` row plus all objects connected via incoming `belongs_to_project` edges).

**Request body (`GenerateResumeBulletsRequest`):**

```jsonc
{
  "project_id": "uuid",                  // required, must be project kind, must be owned
  "target_role": "Senior Backend Engineer",  // optional, free text, biases tone + verbs
  "emphasis": "scale, mentorship",       // optional, free text, biases content
  "count": 3,                            // 1–5, default 3
  "max_evidence_objects": 10             // 1–20, default 10
}
```

**Response (`GenerateResumeBulletsResponse`):**

```jsonc
{
  "project_id": "uuid",
  "bullets": [
    {
      "text": "Led the rebuild of the ingestion pipeline, cutting processing time from 12 min to 90 s and onboarding 250 users in the first quarter.",
      "evidence_object_ids": ["uuid", "uuid"],  // subset of evidence corpus
      "confidence": "high",                      // high | medium | low
      "metrics_cited": ["processing_time", "users_onboarded"]   // keys from project.metrics
    }
  ],
  "agent_run_id": "uuid",
  "evidence_count": 12                           // size of corpus considered
}
```

**Errors:**
- 401 — no session.
- 403 — caller is not the project's owner (or 404, per the existing "do not leak existence" convention; reuse what `project_service` does today).
- 404 — project missing or soft-deleted.
- 422 — body validation (count, max_evidence_objects, target_role > 255 chars, etc.).
- 502 — LLM returned malformed JSON. `agent_run` row persisted with `status="failed"` and the raw payload in `output`. Mirrors 9A's `extract-project` behavior.
- 503 — `OPENAI_API_KEY` unset. No `agent_run` row created.

### 3.2 `POST /api/v1/ai/generate-interview-story`

**Purpose:** produce a single STAR-formatted interview story (Situation / Task / Action / Result) for a given project.

**Request body (`GenerateInterviewStoryRequest`):**

```jsonc
{
  "project_id": "uuid",                  // required
  "question_type": "behavioral",         // behavioral | technical | leadership; default behavioral
  "target_role": "Senior Backend Engineer",  // optional
  "max_words": 400,                      // 100–800, default 400
  "max_evidence_objects": 10             // 1–20, default 10
}
```

**Response (`GenerateInterviewStoryResponse`):**

```jsonc
{
  "project_id": "uuid",
  "story": {
    "situation": "...",                  // ~50–100 words
    "task": "...",                       // ~30–60 words
    "action": "...",                     // ~80–200 words
    "result": "...",                     // ~30–80 words
    "evidence_object_ids": ["uuid", "uuid"]
  },
  "agent_run_id": "uuid",
  "word_count": 380                      // actual returned length
}
```

**Errors:** same matrix as §3.1.

---

## 4. Pydantic schemas (`services/api/app/schemas/career_ai.py`)

Match the existing `schemas/project.py` and `schemas/ai.py` styles. Pydantic v2 with explicit min/max constraints. All response models use `model_config = ConfigDict(from_attributes=False)` since responses are constructed by hand.

```python
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

BulletConfidence = Literal["high", "medium", "low"]
InterviewQuestionType = Literal["behavioral", "technical", "leadership"]


class GenerateResumeBulletsRequest(BaseModel):
    project_id: UUID
    target_role: str | None = Field(None, max_length=255)
    emphasis: str | None = Field(None, max_length=500)
    count: int = Field(3, ge=1, le=5)
    max_evidence_objects: int = Field(10, ge=1, le=20)


class ResumeBullet(BaseModel):
    text: str
    evidence_object_ids: list[UUID] = Field(default_factory=list)
    confidence: BulletConfidence = "medium"
    metrics_cited: list[str] = Field(default_factory=list)


class GenerateResumeBulletsResponse(BaseModel):
    project_id: UUID
    bullets: list[ResumeBullet]
    agent_run_id: UUID
    evidence_count: int


class GenerateInterviewStoryRequest(BaseModel):
    project_id: UUID
    question_type: InterviewQuestionType = "behavioral"
    target_role: str | None = Field(None, max_length=255)
    max_words: int = Field(400, ge=100, le=800)
    max_evidence_objects: int = Field(10, ge=1, le=20)


class StarStory(BaseModel):
    situation: str
    task: str
    action: str
    result: str
    evidence_object_ids: list[UUID] = Field(default_factory=list)


class GenerateInterviewStoryResponse(BaseModel):
    project_id: UUID
    story: StarStory
    agent_run_id: UUID
    word_count: int
```

---

## 5. Service layer (`services/api/app/services/career_ai_service.py`)

One file, two public functions. Both follow the 9A `extract_project` shape exactly:

```python
async def generate_resume_bullets(
    db: AsyncSession,
    *,
    user_id: UUID,
    payload: GenerateResumeBulletsRequest,
) -> GenerateResumeBulletsResponse: ...

async def generate_interview_story(
    db: AsyncSession,
    *,
    user_id: UUID,
    payload: GenerateInterviewStoryRequest,
) -> GenerateInterviewStoryResponse: ...
```

**Internal pipeline (shared by both):**

1. Load the `Project` + parent `KosObject` by id. 404 if missing / soft-deleted / not owned.
2. Gather **evidence corpus** (capped by `payload.max_evidence_objects`):
   - The object referenced by `project.extracted_from`, if any.
   - All objects on the source side of incoming edges where `target_id == project_id` and `kind == "belongs_to_project"` and the source object is owned and not deleted.
   - Order: pinned first, then most-recently-updated. Truncate to the cap.
   - For each evidence object, extract a short text snippet (~1500 chars) from page `content_text`, source `extracted_text`, chat `content_text`, or `description` — whichever is available.
3. Call OpenAI in JSON mode via the existing Phase 5 `ai_service.call_ai()` helper, passing the prompt from `career_ai_prompts.py` and the structured input (project record + evidence snippets).
4. Parse the JSON response. On `json.JSONDecodeError`, raise `HTTPException(502)` after marking the `agent_run` failed.
5. Validate against the response Pydantic model (`GenerateResumeBulletsResponse` / `GenerateInterviewStoryResponse`). On validation failure, same as #4.
6. Return the response, including the `agent_run_id` of the successful run.

**Audit:** `call_ai()` already creates and finalizes the `agent_runs` row. Pass `tool_name="generate_resume_bullets"` or `"generate_interview_story"`, and `input` = the redacted request body (project_id + counts + target_role; no full evidence text in the audit row, only the count, to avoid `agent_runs.input` JSONB bloat — mirrors 7B's audit-input policy).

**No DB writes** other than the `agent_runs` row that `call_ai()` produces.

---

## 6. Prompt design (`services/api/app/services/career_ai_prompts.py`)

Two prompt templates, both designed for OpenAI JSON mode (model defaults to whatever Phase 5 already configures via `settings.openai_chat_model`).

### 6.1 Resume bullets prompt

System (sketch):

```
You are a senior career coach helping a software engineer write resume bullets
for one of their projects. You will receive:
- The project record (title, problem, actions, results, metrics, skills, period).
- Up to N evidence excerpts (each with an object_id and a short text snippet).

Produce exactly {count} resume bullet variants that:
- Start with a strong action verb.
- Quantify impact using metrics from the project where possible.
- Are 18–32 words each.
- Cite evidence by including the object_ids that support the claim in
  `evidence_object_ids`.
- Mark `confidence` as "high" if at least one cited evidence excerpt directly
  supports the claim, "medium" if only the project record supports it,
  "low" if neither does.
- List the `metrics_cited` as keys from the project's metrics dict that the
  bullet quantifies.

Bias tone for target_role: {target_role}.
Emphasize: {emphasis}.

Return ONLY a JSON object with shape:
{ "bullets": [ { "text": str, "evidence_object_ids": [uuid], "confidence":
                 "high"|"medium"|"low", "metrics_cited": [str] } ] }
```

User message: JSON-serialized project + evidence corpus (each entry: `{object_id, kind, title, snippet}`).

### 6.2 Interview story prompt

System (sketch):

```
You are a senior career coach helping a software engineer prepare a STAR-format
interview story for one of their projects. STAR = Situation, Task, Action, Result.

Use the project record and up to N evidence excerpts. Produce ONE story:
- `situation`: 50–100 words. Context, scale, stakes.
- `task`: 30–60 words. The specific problem the candidate had to solve.
- `action`: 80–200 words. What the candidate (singular "I") did.
- `result`: 30–80 words. Outcome with metrics where possible.
- `evidence_object_ids`: list of object_ids that support claims in the story.

Total story length must be near {max_words} words (±15%).
Bias tone for question_type "{question_type}" and target_role "{target_role}".

Return ONLY a JSON object with shape:
{ "situation": str, "task": str, "action": str, "result": str,
  "evidence_object_ids": [uuid] }
```

User message: JSON-serialized project + evidence corpus, same shape as 6.1.

### 6.3 Prompt versioning

Both prompts include a `version: "9b.1"` constant in the system message header so future prompt changes are traceable in `agent_runs.input` (which records the prompt version when `call_ai` logs the call).

---

## 7. Subtask checklist

Each subtask is independently codex-delegatable and ends with a single conventional commit. Subtasks marked **(blocking)** must land before later ones.

- [ ] **Subtask 0** — Audit + plan file (this doc) + PROGRESS.md row **(blocking)**
- [ ] **Subtask 1** — Pydantic schemas (`schemas/career_ai.py`) **(blocking)**
- [ ] **Subtask 2** — Prompt templates (`services/career_ai_prompts.py`) **(blocking)**
- [ ] **Subtask 3** — Evidence-gathering helper + `generate_resume_bullets()` in `services/career_ai_service.py`
- [ ] **Subtask 4** — `generate_interview_story()` in same service file
- [ ] **Subtask 5** — Two endpoint handlers appended to `api/v1/ai.py`
- [ ] **Subtask 6** — Integration tests (`tests/api/test_career_ai.py`) — 10+ cases (see §9)
- [ ] **Subtask 7** — Docs: append "Career AI Generators" section to `docs/API.md`; flip PROGRESS row to ✅

---

## 8. Subtask details

### Subtask 1 — Schemas

**Files to create:**
- `services/api/app/schemas/career_ai.py` per §4.

**Files to modify:**
- `services/api/app/schemas/__init__.py` — only if the existing pattern re-exports schemas. Inspect first; do not introduce a new pattern.

**Commit:** `feat(api): career ai request/response schemas`

---

### Subtask 2 — Prompts

**Files to create:**
- `services/api/app/services/career_ai_prompts.py` per §6.

The file exports two constants (or callables): `RESUME_BULLETS_SYSTEM_PROMPT` and `INTERVIEW_STORY_SYSTEM_PROMPT`. Templating placeholders use Python `.format()` (not f-strings) so the prompt strings remain inspectable / loggable.

**Commit:** `feat(api): resume and interview ai prompt templates`

---

### Subtask 3 — Evidence helper + resume bullets

**Files to create:**
- `services/api/app/services/career_ai_service.py` with:
  - `_gather_evidence(db, *, user_id, project, max_evidence_objects) -> list[EvidenceItem]` (private)
  - `generate_resume_bullets(db, *, user_id, payload)` (public)

`EvidenceItem` is a simple `@dataclass` or `TypedDict` with `object_id`, `kind`, `title`, `snippet`. Not a Pydantic model (it doesn't cross the API boundary).

**Evidence query (SQLAlchemy 2.0 async):**

```python
# Incoming belongs_to_project edges
stmt = (
    select(KosObject)
    .join(Edge, Edge.source_id == KosObject.id)
    .where(
        Edge.target_id == project_id,
        Edge.kind == "belongs_to_project",
        Edge.deleted_at.is_(None),
        KosObject.user_id == user_id,
        KosObject.deleted_at.is_(None),
    )
    .order_by(KosObject.is_pinned.desc(), KosObject.updated_at.desc())
    .limit(max_evidence_objects)
)
```

Then merge with `project.extracted_from` (if set and owned) at the head of the list, capped at the same limit.

**Snippet extraction:** per object kind:
- `page` → `Page.content_text[:1500]`
- `source` → `Source.extracted_text[:1500]`
- `chat` → `Chat.content_text[:1500]`
- else → `obj.description[:1500] or ""`

If `content_text` is empty for any kind, fall back to `obj.title + (obj.description or "")`.

**LLM call:** reuse `ai_service.call_ai()` with:
- `tool_name="generate_resume_bullets"`
- `input` = `{ "project_id": str, "target_role": ..., "emphasis": ..., "count": ..., "evidence_object_count": len(evidence), "prompt_version": "9b.1" }` (no full text in audit row)
- `response_format={"type": "json_object"}`

**Tests for this subtask:** covered in Subtask 6.

**Commit:** `feat(api): resume bullet generator with evidence corpus`

---

### Subtask 4 — Interview story

**Files to modify:**
- `services/api/app/services/career_ai_service.py` — append `generate_interview_story()`.

Reuses `_gather_evidence()` from Subtask 3 unchanged.

**Word count enforcement:** the prompt asks for ±15% of `max_words`. Service computes actual word count after parsing and returns it in `word_count`. The API does **not** reject responses outside the band; it just reports `word_count` so a caller (or frontend in 9C) can decide whether to regenerate. Rationale: rejecting and retrying inside the endpoint multiplies LLM cost; let the caller do it.

**Commit:** `feat(api): interview story generator with star format`

---

### Subtask 5 — Endpoint handlers

**Files to modify:**
- `services/api/app/api/v1/ai.py` — append two handlers at the bottom, after `extract_project_endpoint`.

Import addition (single new line in the imports block):

```python
from app.schemas.career_ai import (
    GenerateInterviewStoryRequest,
    GenerateInterviewStoryResponse,
    GenerateResumeBulletsRequest,
    GenerateResumeBulletsResponse,
)
from app.services import career_ai_service
```

Handler bodies are thin wrappers, identical pattern to `extract_project_endpoint`:

```python
@router.post("/generate-resume-bullets", response_model=GenerateResumeBulletsResponse)
async def generate_resume_bullets_endpoint(
    body: GenerateResumeBulletsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GenerateResumeBulletsResponse:
    result = await career_ai_service.generate_resume_bullets(
        db, user_id=user.id, payload=body
    )
    await db.commit()
    return result

@router.post("/generate-interview-story", response_model=GenerateInterviewStoryResponse)
async def generate_interview_story_endpoint(
    body: GenerateInterviewStoryRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GenerateInterviewStoryResponse:
    result = await career_ai_service.generate_interview_story(
        db, user_id=user.id, payload=body
    )
    await db.commit()
    return result
```

**Commit:** `feat(api): resume bullets and interview story endpoints`

---

### Subtask 6 — Tests

**Files to create:**
- `tests/api/test_career_ai.py`

Use the existing async test client fixture pattern from `tests/api/test_ai.py` and `tests/api/test_projects.py`. Mock `openai.AsyncOpenAI.chat.completions.create` via the same `monkeypatch` / `respx` pattern Phase 5 / 9A use.

**Cases (10 minimum):**

**Resume bullets:**

1. Happy path: project + 2 evidence edges → returns 3 bullets, each with non-empty text, `evidence_count == 3`, `agent_run_id` present.
2. `count=1` returns exactly one bullet.
3. `count=5` returns five bullets.
4. `count=6` → 422.
5. Project not owned (created by user B, requested by user A) → 404.
6. Project soft-deleted → 404.
7. `OPENAI_API_KEY` unset → 503, no `agent_run` row created.
8. LLM returns invalid JSON → 502, `agent_run.status == "failed"`, raw response stored in `agent_run.output` or `error`.

**Interview story:**

9. Happy path: project + 1 evidence → returns story with all four STAR fields non-empty, `word_count` plausible (50–600).
10. `question_type="technical"` is accepted and passed to the prompt (assert mock was called with the technical prompt template).
11. `max_words=100` → returns a shorter story; `word_count <= ~150`.
12. `OPENAI_API_KEY` unset → 503.

**Shared:**

13. Evidence cap: 15 `belongs_to_project` edges + `max_evidence_objects=5` → service sees exactly 5 evidence items (assert via mock call args).

**Verification:**
```bash
cd tests && PYTHONPATH=../services/api uv run --project ../services/api --extra dev pytest api/test_career_ai.py -v
```
All ≥10 tests pass. Existing API integration test count unchanged.

**Commit:** `test(api): career ai generators happy paths, 503, 502, ownership`

---

### Subtask 7 — Docs + PROGRESS flip

**Files to modify:**
- `docs/API.md` — append a "Career AI Generators" section listing the two endpoints, request/response example bodies, error codes.
- `PROGRESS.md` — flip the Phase 9B row to ✅ with the subtask checklist mirroring this file.

**Skipped intentionally:** `docs/AGENT_GUIDE.md` (owned by 7B). Add a one-paragraph entry there in a follow-up PR after 7B merges.

**Commit:** `docs(phase9b): career ai generators api`

---

## 9. Tests required

Minimum 10 new tests in `tests/api/test_career_ai.py` (listed in §8 Subtask 6). After Phase 9B: target ~145 API integration tests (135 today on `main` + ~10 new).

---

## 10. Commit sequence

```
1.  docs: phase 9b plan
2.  feat(api): career ai request/response schemas
3.  feat(api): resume and interview ai prompt templates
4.  feat(api): resume bullet generator with evidence corpus
5.  feat(api): interview story generator with star format
6.  feat(api): resume bullets and interview story endpoints
7.  test(api): career ai generators happy paths, 503, 502, ownership
8.  docs(phase9b): career ai generators api
```

8 commits total. Subtask 0 (this plan) is commit 1; the rest map to Subtasks 1–7.

---

## 11. Validation commands

```bash
# Backend lint + format
cd services/api && uv run ruff check . && uv run ruff format --check .

# Target tests
cd tests && PYTHONPATH=../services/api uv run --project ../services/api --extra dev pytest api/test_career_ai.py -v

# Full backend regression
cd tests && PYTHONPATH=../services/api uv run --project ../services/api --extra dev pytest api/ unit/ -q

# Manual smoke (requires OPENAI_API_KEY in infra/.env)
# 1. Create a project via POST /api/v1/projects
# 2. Optionally link a page or source via POST /api/v1/edges with kind="belongs_to_project"
# 3. curl POST /api/v1/ai/generate-resume-bullets with the project id
# 4. Verify the agent_runs row in Postgres: SELECT * FROM agent_runs ORDER BY created_at DESC LIMIT 1;

# Frontend sanity (no UI changes expected)
pnpm typecheck
pnpm lint
```

All must pass before merge.

---

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| 7B, 8B, and 9B all append to `PROGRESS.md` and conflict on merge | Append-only edits in separate sections. Three-way merge resolves cleanly; if conflict markers appear, keep all sections from all three branches. |
| 7B, 8B, and 9B all append to `docs/API.md` | Same: each appends a distinct named section. Resolve by keeping all. |
| 7B, 8B, and 9B all append to `schemas/__init__.py` | Each adds one re-export line at the bottom of distinct named groups. Three-way merge is trivial. |
| LLM returns malformed JSON intermittently | 502 + persisted failed `agent_run`. The 9A pattern is proven. Surface the raw response in `agent_run.output` so the user / future agent can diagnose. |
| LLM hallucinates `evidence_object_ids` that don't exist | The endpoint trusts the LLM here. 9C frontend should render only ids that resolve to known objects; service layer does not validate (a strict filter would slow the response and silently drop links). Document this in the API doc. |
| Evidence corpus too large; LLM context overflow | `max_evidence_objects` capped at 20; per-evidence snippet capped at 1500 chars; total prompt body bounded at ~30k chars in practice. Well under any current model's context. |
| `agent_runs.input` JSONB bloat from large request bodies | Audit input stores only metadata (counts, lengths), never full evidence text. Mirrors 7B's policy for write tools. |
| Cost runaway if an agent loops on generation | No write tool here, so 7B's rate limiter doesn't gate this directly. For now, rely on the OpenAI SDK's per-key quota and on the fact that 9B has no MCP exposure (9D will gate via 7B's limiter). |
| Prompt drift across versions silently changes outputs | `prompt_version` constant stored in `agent_runs.input`. Bump the version when the prompt changes; existing runs remain reproducible. |
| Word-count band missed | Reported in `word_count`, not enforced server-side. Caller decides whether to regenerate. |
| Project with zero evidence still gets bullets | Allowed. Bullets fall back to the project record itself; `confidence` will mostly be `"medium"` or `"low"`. Test 1 in §8 Subtask 6 should cover this. |

---

## 13. Follow-ups (out of scope, but worth flagging)

- **Phase 9C (frontend):** project create/edit form, evidence panel, "Generate bullets" / "Generate interview story" buttons that POST to the new endpoints and render results, Markdown / PDF export of selected bullets, "Save bullets onto project" affordance (which then writes through 7B's `audited_write_service`).
- **Phase 9D (MCP):** `generate_resume_bullets`, `generate_interview_story`, `create_project`, `update_project`, `archive_project` MCP tools. Depends on 7B's `MCP_ALLOW_WRITE_TOOLS` gate and rate limiter. Pure read tools (`get_project`, `list_projects`) can land earlier if needed.
- **Audit-input enrichment:** include the top 3 evidence object_ids in the redacted `agent_runs.input` so post-hoc inspection can see what the agent saw without expanding `input` to include full text. Decide after 7B's audit-input pattern stabilizes.
- **Caching:** if the same `(project_id, target_role, count)` is called repeatedly, consider caching the bullets in `objects.metadata.career_ai.resume_bullets` on the project, keyed by a hash of the request. Out of scope; needs the 9A retrofit to land first.
- **Multiple stories per project:** `generate_interview_story` returns exactly one story. Future "story pack" mode could return 3 stories (technical / behavioral / leadership) in one call.

---

## 14. Done when

- All 7 subtasks checked in this file.
- `PROGRESS.md` Phase 9B row is ✅ with the same checklist.
- `cd tests && uv run pytest api/test_career_ai.py -v` shows ≥10 passing tests.
- Full backend suite (`make test-all` or the targeted commands in §11) is green.
- `docs/API.md` has a "Career AI Generators" section documenting both endpoints with example bodies, error codes, and the 503/502 contract.
- Phase 9C (frontend) can begin against a stable API contract.
