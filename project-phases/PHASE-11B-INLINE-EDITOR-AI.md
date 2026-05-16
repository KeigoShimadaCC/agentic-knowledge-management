# Phase 11B — Inline Editor AI (Slash-Command AI Actions)

> **Status:** ✅ Complete (2026-05-16, branch `feat/phase-11b-inline-editor-ai`)
> **Owner:** Full-stack (frontend-heavy, small backend addition)
> **Audience:** AI coder (Codex). Read end-to-end before writing a single line.
> **Estimated effort:** 1 PR, ~8 commits, ~600–800 LOC including tests.
> **Worktree branch:** `feat/phase-11b-inline-editor-ai`
> **Blocks:** nothing (standalone enhancement).
> **Blocked by:** nothing (Phase 5 AI endpoints are live on `main`).
> **Parallel-safe with:** PHASE-11A-TUTORIAL (in progress), PHASE-11C-BACKGROUND-AI (planned). Conflict map verified in §2.

---

## 0. North Star

Today, all AI actions in KnowledgeOS live in the AI Panel sidebar — a user opens a page, scrolls to the panel, and clicks a button. The result appears outside the document. There is no way to trigger AI from inside the editor while writing.

Phase 11B changes this by wiring AI directly into the Tiptap editor's slash-command system. A user types `/` anywhere in the editor, selects an AI command, and the result is inserted or replaces content in-place. Two new backend endpoints back this up: one for open-ended text continuation (`/ai/complete`) and one for transforming selected text (`/ai/transform`).

This is the highest-leverage UX improvement achievable without redesigning any major surface. It requires no new schema migrations, no new database tables, and no changes to any files that Phase 11A or 11C own.

**What Phase 11B adds:**

| Surface | What changes |
|---|---|
| Editor slash menu | 6 new AI command entries below existing commands |
| Editor selection toolbar | "AI Transform" button appears when text is selected |
| Backend `/api/v1/ai` router | 2 new endpoint handlers appended at the end |
| `lib/api.ts` | 2 new client functions |
| Tests | 8+ backend integration tests; 1 frontend component test |

**What Phase 11B does NOT do:**

- No changes to `Sidebar.tsx`, `AppShell.tsx`, `layout.tsx` — those belong to Phase 11A.
- No changes to `AiPanel.tsx` — the sidebar panel is a separate surface and is unchanged.
- No changes to `services/api/app/api/v1/router.py` — both new endpoints attach to the existing `ai_router`.
- No new database tables or migrations.
- No MCP exposure. That would be a future 11B-MCP slice.
- No streaming. Both endpoints return a single JSON response. Streaming is a follow-up.
- No inline diff / accept-reject UI. Insertions happen immediately. A future phase can add undo-aware diffing.

---

## 1. Worktree and delegation model

**All code in this phase is written by Codex, not Claude.** Claude's role is to plan, assign subtasks, review output, and enforce the non-breakage contract below.

### 1.1 Worktree setup (Claude runs this once before handing off)

```bash
# From the repo root on main:
git worktree add ../phase-11b-worktree feat/phase-11b-inline-editor-ai
# Codex works exclusively inside ../phase-11b-worktree
# Claude reviews, merges back to main when all subtasks pass quality gates.
```

### 1.2 Quality gates Codex must pass before each commit

```bash
# Frontend (run from apps/web inside the worktree)
pnpm typecheck          # 0 TypeScript errors
pnpm lint               # 0 ESLint errors

# Backend (run from services/api inside the worktree)
uv run ruff check .
uv run ruff format --check .

# Backend tests
cd tests && uv run pytest api/test_inline_ai.py -v   # target test file
cd tests && uv run pytest api/ -q                     # full regression — must stay green
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
services/api/app/api/v1/__init__.py          ← tutorial router registration
NEW: apps/web/src/components/tutorial/*
NEW: services/api/app/api/v1/tutorial.py
NEW: services/api/app/services/tutorial_seed_service.py
PROGRESS.md
```

11B wants:
```
EDIT: apps/web/src/components/editor/SlashMenu.tsx
EDIT: apps/web/src/components/editor/BubbleMenu.tsx
EDIT: apps/web/src/components/editor/extensions/SlashMenuExtension.ts
EDIT: apps/web/src/lib/api.ts                 (append 2 functions)
EDIT: services/api/app/api/v1/ai.py           (append 2 handlers)
NEW:  apps/web/src/components/editor/AiSlashCommand.tsx
NEW:  services/api/app/schemas/inline_ai.py
NEW:  tests/api/test_inline_ai.py
EDIT: docs/API.md, PROGRESS.md
```

**Overlap:** `PROGRESS.md` only (append-merge, trivially resolved). Zero code-file conflict.

`services/api/app/api/v1/__init__.py` is touched by 11A but NOT by 11B — both new 11B endpoints attach to the existing `ai_router` with no router registration needed.

### vs. PHASE-11C-BACKGROUND-AI (planned, other worktree)

11C owns:
```
services/worker/tasks/ai_jobs.py              (new file)
services/worker/tasks/__init__.py             (append import)
services/api/app/services/source_service.py   (post-ingest hook)
services/api/app/api/v1/pages.py              (post-save hook)
services/api/app/config.py                    (new config flags)
NEW: tests/api/test_background_ai.py
EDIT: PROGRESS.md, docs/API.md
```

**Overlap with 11B:**
- `PROGRESS.md` (append-merge, trivial three-way)
- `docs/API.md` (each appends a distinct named section, trivial three-way)
- `apps/web/src/lib/api.ts` — 11B appends 2 functions at the bottom; 11C does not touch `api.ts`. **No conflict.**
- `services/api/app/api/v1/ai.py` — 11B appends 2 handlers; 11C does not touch `ai.py`. **No conflict.**

Zero code-file conflict.

---

## 3. Files this phase MAY NOT touch

| File | Why off-limits |
|---|---|
| `apps/web/src/app/(app)/layout.tsx` | Phase 11A owns. |
| `apps/web/src/components/layout/AppShell.tsx` | Phase 11A owns. |
| `apps/web/src/components/layout/Sidebar.tsx` | Phase 11A owns. |
| `apps/web/src/components/ai/AiPanel.tsx` | Sidebar AI panel — separate surface, out of scope. |
| `services/api/app/api/v1/__init__.py` | Phase 11A owns (tutorial router registration). |
| `services/api/app/api/v1/router.py` | Not needed — new endpoints attach to existing `ai_router`. |
| `services/api/app/services/ai_service.py` | Phase 5 plumbing. New handlers call `call_ai()` from this file but do not edit it. |
| `services/api/app/schemas/ai.py` | Phase 5 schema file. New types live in `schemas/inline_ai.py`. |
| `services/worker/**` | Phase 11C owns. |
| `services/api/app/config.py` | Phase 11C owns (new config flags). |
| `services/mcp/**` | Out of scope for 11B. |
| `tests/api/test_ai.py` | Existing file. New tests live in `test_inline_ai.py`. |
| Any alembic migration | No migrations in this phase. |

---

## 4. New API endpoints

Both endpoints attach to the existing `/api/v1/ai` router. No router changes required.

### 4.1 `POST /api/v1/ai/complete`

**Purpose:** Given a block of text representing the content before the cursor, generate a continuation. Used by "Continue writing" and "Expand" slash commands.

**Request (`AiCompleteRequest`):**

```json
{
  "context_before": "The main limitation of this approach is",
  "context_after": "",
  "instruction": "continue",
  "object_id": "uuid",
  "max_tokens": 200
}
```

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `context_before` | string | yes | — | Text before cursor. Max 4000 chars. |
| `context_after` | string | no | `""` | Text after cursor for fill-in-middle. Max 1000 chars. |
| `instruction` | `"continue"` \| `"expand"` | no | `"continue"` | Biases the completion style. |
| `object_id` | UUID | no | — | If provided, page title is prepended to system prompt as context. |
| `max_tokens` | int | no | 200 | 50–500. |

**Response (`AiCompleteResponse`):**

```json
{
  "completion": " that it requires careful tuning of the embedding model...",
  "agent_run_id": "uuid"
}
```

**Errors:** 400 if `context_before` is empty. 503 if `OPENAI_API_KEY` unset. 422 on validation failure.

### 4.2 `POST /api/v1/ai/transform`

**Purpose:** Transform a selected block of text according to a specific instruction. Used by "Improve", "Make concise", "Fix grammar", "Summarize selection" slash/bubble commands.

**Request (`AiTransformRequest`):**

```json
{
  "text": "This is the selected text that should be transformed.",
  "instruction": "improve",
  "object_id": "uuid"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `text` | string | yes | Selected text. Max 8000 chars. |
| `instruction` | `"improve"` \| `"concise"` \| `"grammar"` \| `"summarize"` | yes | Transform mode. |
| `object_id` | UUID | no | For page-title context in system prompt. |

**Response (`AiTransformResponse`):**

```json
{
  "result": "This selected text should be transformed.",
  "agent_run_id": "uuid"
}
```

**Errors:** 400 if `text` is empty. 503 if `OPENAI_API_KEY` unset.

---

## 5. Backend schemas (`services/api/app/schemas/inline_ai.py`)

New file. Follow Pydantic v2 conventions from `schemas/ai.py`.

```python
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

CompletionInstruction = Literal["continue", "expand"]
TransformInstruction = Literal["improve", "concise", "grammar", "summarize"]


class AiCompleteRequest(BaseModel):
    context_before: str = Field(..., max_length=4000)
    context_after: str = Field("", max_length=1000)
    instruction: CompletionInstruction = "continue"
    object_id: UUID | None = None
    max_tokens: int = Field(200, ge=50, le=500)


class AiCompleteResponse(BaseModel):
    completion: str
    agent_run_id: UUID


class AiTransformRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=8000)
    instruction: TransformInstruction
    object_id: UUID | None = None


class AiTransformResponse(BaseModel):
    result: str
    agent_run_id: UUID
```

---

## 6. Backend endpoint handlers (appended to `services/api/app/api/v1/ai.py`)

Append only — do not edit any existing handler or import block above the existing imports.

Add one import line at the bottom of the imports block:

```python
from app.schemas.inline_ai import (
    AiCompleteRequest, AiCompleteResponse,
    AiTransformRequest, AiTransformResponse,
)
```

Append two handlers at the bottom of the file:

```python
COMPLETE_SYSTEM: dict[str, str] = {
    "continue": "You are a writing assistant. Continue the text naturally. Return only the continuation, no preamble.",
    "expand":   "You are a writing assistant. Expand the text with more detail. Return only the expanded continuation.",
}

TRANSFORM_SYSTEM: dict[str, str] = {
    "improve":   "You are an editor. Improve the clarity and flow of the text. Return only the improved version.",
    "concise":   "You are an editor. Make the text more concise without losing meaning. Return only the revised version.",
    "grammar":   "You are a proofreader. Fix all grammar and spelling errors. Return only the corrected version.",
    "summarize": "You are an editor. Write a one-paragraph summary of the text. Return only the summary.",
}

@router.post("/complete", response_model=AiCompleteResponse)
async def ai_complete(
    body: AiCompleteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AiCompleteResponse:
    system = COMPLETE_SYSTEM[body.instruction]
    user_msg = body.context_before
    if body.context_after:
        user_msg += f"\n[TEXT AFTER CURSOR: {body.context_after}]"
    text, run = await call_ai(
        db, user_id=user.id, agent_type="inline_ai_complete",
        messages=[{"role": "user", "content": user_msg}],
        system=system, max_tokens=body.max_tokens,
        input_context={"instruction": body.instruction, "object_id": str(body.object_id)},
    )
    await db.commit()
    return AiCompleteResponse(completion=text, agent_run_id=run.id)


@router.post("/transform", response_model=AiTransformResponse)
async def ai_transform(
    body: AiTransformRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AiTransformResponse:
    system = TRANSFORM_SYSTEM[body.instruction]
    text, run = await call_ai(
        db, user_id=user.id, agent_type="inline_ai_transform",
        messages=[{"role": "user", "content": body.text}],
        system=system,
        input_context={"instruction": body.instruction, "object_id": str(body.object_id)},
    )
    await db.commit()
    return AiTransformResponse(result=text, agent_run_id=run.id)
```

**Note:** Inspect the actual `call_ai` signature in `services/api/app/ai/client.py` before implementing and adapt parameter names accordingly. Do not guess.

---

## 7. Frontend — API client additions (`apps/web/src/lib/api.ts`)

Append two functions at the bottom of the file. Do not edit any existing function.

```ts
export async function aiComplete(
  contextBefore: string,
  instruction: "continue" | "expand" = "continue",
  objectId?: string,
  maxTokens = 200,
): Promise<{ completion: string; agent_run_id: string }> {
  const res = await apiFetch("/ai/complete", {
    method: "POST",
    body: JSON.stringify({
      context_before: contextBefore,
      instruction,
      object_id: objectId ?? null,
      max_tokens: maxTokens,
    }),
  });
  return res.json();
}

export async function aiTransform(
  text: string,
  instruction: "improve" | "concise" | "grammar" | "summarize",
  objectId?: string,
): Promise<{ result: string; agent_run_id: string }> {
  const res = await apiFetch("/ai/transform", {
    method: "POST",
    body: JSON.stringify({ text, instruction, object_id: objectId ?? null }),
  });
  return res.json();
}
```

Inspect the existing `apiFetch` or `fetch` wrapper pattern already in `api.ts` and follow it exactly.

---

## 8. Frontend — Slash command entries (`apps/web/src/components/editor/SlashMenu.tsx`)

The slash menu already renders a list of commands. Append an **"AI" group** below the existing groups. Do not reorder or remove any existing command.

**6 new entries:**

| Command label | Description shown to user | Action |
|---|---|---|
| Continue writing | Let AI complete your thought | Calls `aiComplete(textBefore, "continue", objectId)` → inserts completion at cursor |
| Expand | Expand the current paragraph with more detail | Calls `aiComplete(textBefore, "expand", objectId)` → inserts after cursor |
| Improve writing | Rewrite the current paragraph for clarity | Calls `aiTransform(currentParagraphText, "improve", objectId)` → replaces paragraph |
| Make concise | Shorten the current paragraph | Calls `aiTransform(currentParagraphText, "concise", objectId)` → replaces paragraph |
| Fix grammar | Correct spelling and grammar | Calls `aiTransform(currentParagraphText, "grammar", objectId)` → replaces paragraph |
| Summarize selection | Summarize this page in one paragraph | Calls `aiTransform(fullContentText, "summarize", objectId)` → inserts at cursor |

**UX during loading:** while the API call is in flight, insert a placeholder node `[AI writing…]` at the cursor position, then replace it with the result. Remove the placeholder on error and show a `toast.error("AI failed — try again")`.

**`objectId`** is passed from the parent `PageEditor` props (already available as the page id).

**Inspect `SlashMenu.tsx` and `SlashMenuExtension.ts` before writing.** Follow the exact pattern of existing command entries — do not invent a new registration mechanism.

---

## 9. Frontend — Bubble menu transform button (`apps/web/src/components/editor/BubbleMenu.tsx`)

When the user selects text, the bubble menu appears. Add a single **"AI ▾"** dropdown button to the existing `BubbleMenu` that reveals transform options: Improve, Make concise, Fix grammar, Summarize selection.

On selection, call `aiTransform(selectedText, instruction, objectId)` and replace the selection with the result. Show a loading spinner in the button while in flight.

**Inspect `BubbleMenu.tsx` before writing.** Follow the existing button pattern. Do not add a dependency on a new dropdown library — use a simple `<details>` or `<select>` that matches the existing component patterns.

---

## 10. New component (`apps/web/src/components/editor/AiSlashCommand.tsx`)

Extract the loading-placeholder logic into a small helper so `SlashMenu.tsx` stays readable:

```ts
// Applies an AI action to the editor:
// 1. Inserts a placeholder at cursor / replaces selection
// 2. Calls the provided async action function
// 3. On success: replaces placeholder with result
// 4. On error: removes placeholder, shows toast
export async function applyAiAction(
  editor: Editor,
  placeholder: string,
  action: () => Promise<string>,
): Promise<void>
```

This is the only new component file needed. Keep it focused — no React component, just a utility function.

---

## 11. Subtask checklist

Each subtask is independently Codex-delegatable and ends with a single conventional commit. Subtasks 0–2 are **blocking** — they must merge before 3–6 start.

- [x] **Subtask 0** — Worktree setup + plan review **(blocking)**
- [x] **Subtask 1** — Backend schemas (`schemas/inline_ai.py`) **(blocking)**
- [x] **Subtask 2** — Backend endpoint handlers appended to `api/v1/ai.py` + `lib/api.ts` additions **(blocking)**
- [x] **Subtask 3** — `AiSlashCommand.tsx` utility + SlashMenu entries
- [x] **Subtask 4** — BubbleMenu AI dropdown
- [x] **Subtask 5** — Integration tests (`tests/api/test_inline_ai.py`)
- [x] **Subtask 6** — Frontend component test + docs + PROGRESS flip

---

## 12. Subtask details

### Subtask 0 — Worktree setup

```bash
# Claude runs this from repo root on main:
git worktree add ../phase-11b-worktree feat/phase-11b-inline-editor-ai
```

Confirm the worktree is on a clean branch off `main` before handing off to Codex.

**Commit:** none (no code changes).

---

### Subtask 1 — Backend schemas

**Files to create:**
- `services/api/app/schemas/inline_ai.py` per §5.

**Files to inspect (do not edit):**
- `services/api/app/schemas/ai.py` — follow the same Pydantic v2 pattern exactly.

**Verification:**
```bash
cd services/api && uv run python -c "from app.schemas.inline_ai import AiCompleteRequest, AiTransformRequest; print('OK')"
```

**Commit:** `feat(api): inline ai request/response schemas`

---

### Subtask 2 — Backend endpoints + API client

**Files to modify (append only):**
- `services/api/app/api/v1/ai.py` — per §6.
- `apps/web/src/lib/api.ts` — per §7.

**Verification:**
```bash
# Start the API (requires running Postgres):
cd services/api && uv run uvicorn app.main:app --reload &
# Smoke test:
curl -s -X POST http://127.0.0.1:8000/api/v1/ai/transform \
  -H "Content-Type: application/json" \
  -d '{"text":"This is bad writing.","instruction":"improve"}' | python3 -m json.tool
# Backend lint:
cd services/api && uv run ruff check . && uv run ruff format --check .
# Frontend typecheck:
cd apps/web && pnpm typecheck
```

**Commit:** `feat(api): ai complete and transform endpoints`

---

### Subtask 3 — SlashMenu AI commands

**Files to create:**
- `apps/web/src/components/editor/AiSlashCommand.tsx` — `applyAiAction` utility per §10.

**Files to modify:**
- `apps/web/src/components/editor/SlashMenu.tsx` — append AI command group per §8.
- `apps/web/src/components/editor/extensions/SlashMenuExtension.ts` — register new commands if the existing pattern requires it.

**Verification:**
```bash
cd apps/web && pnpm typecheck && pnpm lint
# Manual: start pnpm dev, open a page, type "/" in the editor, confirm AI group appears.
```

**Commit:** `feat(web): ai slash commands in editor (continue, expand, improve, concise, grammar, summarize)`

---

### Subtask 4 — BubbleMenu AI dropdown

**Files to modify:**
- `apps/web/src/components/editor/BubbleMenu.tsx` — per §9.

**Verification:**
```bash
cd apps/web && pnpm typecheck && pnpm lint
# Manual: select text in the editor, confirm "AI ▾" button appears with 4 options.
```

**Commit:** `feat(web): ai transform button in bubble menu`

---

### Subtask 5 — Backend integration tests

**Files to create:**
- `tests/api/test_inline_ai.py`

**Test cases (8 minimum):**

**`/ai/complete`:**
1. `instruction="continue"` → 200, `completion` non-empty, `agent_run_id` present.
2. `instruction="expand"` → 200.
3. `context_before` empty → 400 (or 422 from Pydantic).
4. `max_tokens=600` → 422 (over limit).
5. `OPENAI_API_KEY` unset → 503, no `agent_runs` row created.

**`/ai/transform`:**
6. Each of the 4 instructions → 200, `result` non-empty, `agent_run_id` present. (Can be a parametrized test counting as 4 cases.)
7. `text` empty → 422.
8. `OPENAI_API_KEY` unset → 503.
9. Mock LLM returns empty string → endpoint still returns 200 with `result = ""` (graceful, not a 500).

Use the same `mock_openai` fixture pattern from `tests/api/test_ai.py`.

**Verification:**
```bash
cd tests && uv run pytest api/test_inline_ai.py -v       # ≥8 passing
cd tests && uv run pytest api/ -q                         # full regression green
```

**Commit:** `test(api): inline ai complete and transform endpoint tests`

---

### Subtask 6 — Frontend test + docs + PROGRESS

**Files to create:**
- `apps/web/src/components/editor/__tests__/AiSlashCommand.test.tsx` — test `applyAiAction`:
  - placeholder inserted then replaced on success.
  - placeholder removed and `toast.error` called on failure.
  - Mock `aiComplete` and `aiTransform` from `lib/api`.

**Files to modify:**
- `docs/API.md` — append "Inline AI Endpoints" section: both endpoints, request/response shapes, 503 contract.
- `PROGRESS.md` — flip Phase 11B row to ✅.

**Verification:**
```bash
cd apps/web && pnpm test -- AiSlashCommand   # test file passes
cd apps/web && pnpm typecheck && pnpm lint
```

**Commit:** `test(web): AiSlashCommand utility tests` then `docs(phase11b): inline ai api and progress update`

---

## 13. Commit sequence

```
1.  docs: phase 11b plan (this file)
2.  feat(api): inline ai request/response schemas
3.  feat(api): ai complete and transform endpoints
4.  feat(web): ai slash commands in editor
5.  feat(web): ai transform button in bubble menu
6.  test(api): inline ai complete and transform endpoint tests
7.  test(web): AiSlashCommand utility tests
8.  docs(phase11b): inline ai api and progress update
```

---

## 14. Risks and mitigations

| Risk | Mitigation |
|---|---|
| `call_ai()` signature in `ai/client.py` differs from what §6 assumes | Codex must inspect the actual function signature first and adapt — do not guess. |
| SlashMenu command registration differs from the assumed pattern | Codex must read `SlashMenu.tsx` and `SlashMenuExtension.ts` in full before writing. |
| Placeholder node causes Tiptap state corruption on network error | `applyAiAction` catches errors and removes the placeholder in the `finally` block. |
| Long completions push content out of view | Max tokens capped at 500. Acceptable for an MVP. |
| `BubbleMenu.tsx` uses a third-party dropdown component not yet in the codebase | Use `<details>/<summary>` or inline `useState` open/close — no new dependency. |
| 11A and 11B both commit to `PROGRESS.md` | Append-only, distinct sections — three-way merge is trivial. |
| LLM returns adversarial or offensive text | Out of scope for this phase — content moderation is a future concern. |

---

## 15. Done when

- All 6 subtasks checked in this file.
- `PROGRESS.md` Phase 11B row is ✅.
- `cd tests && uv run pytest api/test_inline_ai.py -v` shows ≥8 passing.
- `cd tests && uv run pytest api/ -q` full regression green.
- `pnpm typecheck && pnpm lint` clean in `apps/web`.
- Manual smoke: typing `/` in the editor shows an AI command group; selecting "Continue writing" inserts a completion; selecting text and clicking "AI ▾ → Improve" replaces the selection.
- Phase 11A can still complete its tutorial work independently (no shared code files touched).
