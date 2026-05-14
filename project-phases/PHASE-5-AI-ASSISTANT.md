# KnowledgeOS — Phase 5 Plan: AI Assistant + Inbox/Triage

## Context

Phases 1–4 are complete and pushed to main.
- 71 integration tests passing
- 33/75 subtasks complete
- Search (keyword + vector + hybrid) is live
- Graph (edges, backlinks, related, ObjectPicker, GraphPanel) is live
- `agent_runs` table exists and is production-ready
- No `ai/` module, no AI endpoints, no `object_revisions` table

**Orchestration model**: Claude Code plans and orchestrates; Codex agents write all code.
**Repo**: `https://github.com/KeigoShimadaCC/agentic-knowledge-management` (branch: main)
**Working directory**: `/Users/keigoshimada/Documents/agentic-knowledge-management`

---

## Phase 4 Audit — Verified Complete

| Area | Status | Notes |
|------|--------|-------|
| 71 integration tests | ✅ | All passing |
| Edges CRUD API | ✅ | POST/GET/DELETE /edges |
| Graph endpoints | ✅ | /objects/{id}/edges, /backlinks, /related |
| GraphPanel UI | ✅ | Backlinks + Related tabs in PageView |
| ObjectPicker + LinkToModal | ✅ | Type-a-link flow in editor |
| Search UI | ✅ | Cmd+K, hybrid/keyword/semantic modes |
| TypeScript clean | ✅ | 0 errors |

---

## Phase 5 — AI Assistant + Inbox/Triage

### Goal

Turn KnowledgeOS into an AI-augmented knowledge base. Users can summarize pages/sources, extract structured knowledge (claims, tasks), discover missing connections, answer questions grounded in their own KB, and triage new inbox items — all via explicitly triggered AI actions with full audit trails.

### Safety Constraints

- No user data sent to AI providers unless user explicitly invokes an AI feature
- AI features degrade gracefully when `OPENAI_API_KEY` is missing (503)
- Core app works offline without AI
- Every AI write: creates `agent_runs` row + `object_revisions` row (if modifying existing object)
- All AI-created objects marked `ai_generated = true` in metadata
- No hard-delete; soft-delete + revision history enables rollback
- No MCP in Phase 5

---

## Definition of Done

- [ ] Existing 71 tests still pass
- [ ] Migration 0004: `object_revisions` table + `ai_generated` column on objects
- [ ] Config: `openai_chat_model`, `openai_max_tokens` settings
- [ ] `services/api/app/ai/` module: client wrapper, prompts
- [ ] `POST /api/v1/ai/summarize` — writes summary to `metadata_["ai_summary"]`
- [ ] `POST /api/v1/ai/extract-claims` — creates Claim objects + edges
- [ ] `POST /api/v1/ai/extract-tasks` — creates Task objects + edges
- [ ] `POST /api/v1/ai/suggest-links` — returns suggestions, no auto-write
- [ ] `POST /api/v1/ai/answer` — KB Q&A with citations
- [ ] `POST /api/v1/ai/triage` — suggest tags/title/summary for inbox item
- [ ] `GET /api/v1/objects/inbox` — recently added untagged/undescribed objects
- [ ] AI Sidebar in PageView (AiPanel, tabbed with Backlinks/Related/AI)
- [ ] Inbox page at `/inbox` with TriageModal
- [ ] All AI endpoints return 503 when `OPENAI_API_KEY` is empty
- [ ] All AI writes create `agent_runs` + `object_revisions` rows
- [ ] ~15 new tests (target: ~86 total)
- [ ] Docs updated: AGENT_GUIDE, ARCHITECTURE, API
- [ ] `project-phases/PHASE-5-AI-ASSISTANT.md` created
- [ ] PROGRESS.md updated
- [ ] `pnpm -F web build` → 0 TypeScript errors

---

## Subtask Checklist

- [ ] Subtask 0 — Migration 0004 + config additions
- [ ] Subtask 1 — AI client module + router scaffold
- [ ] Subtask 2 — Summarize endpoint
- [ ] Subtask 3 — Extract claims + tasks endpoints
- [ ] Subtask 4 — Suggest links endpoint
- [ ] Subtask 5 — KB Q&A answer endpoint
- [ ] Subtask 6 — Inbox API + triage endpoint
- [ ] Subtask 7 — AI Sidebar UI
- [ ] Subtask 8 — Inbox UI
- [ ] Subtask 9 — Tests + documentation

---

## Subtask Details

### Subtask 0 — Migration 0004 + config additions

**Goal**: Add `object_revisions` table, `ai_generated` flag on objects, and chat model config.

**Files to modify**:
- `services/api/app/config.py` — add `openai_chat_model: str = "gpt-4o-mini"` and `openai_max_tokens: int = 2000`
- `services/api/app/models/object.py` — add `ai_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")`

**Files to create**:
- `services/api/alembic/versions/0004_object_revisions.py` — migration

**Migration 0004 SQL**:
```sql
CREATE TABLE object_revisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    object_id UUID NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rev_num INTEGER NOT NULL,
    changed_by VARCHAR(64) NOT NULL DEFAULT 'user',
    agent_run_id UUID REFERENCES agent_runs(id) ON DELETE SET NULL,
    before_snapshot JSONB NOT NULL DEFAULT '{}',
    after_snapshot JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (object_id, rev_num)
);
CREATE INDEX ix_object_revisions_object_id ON object_revisions (object_id);
CREATE INDEX ix_object_revisions_user_id ON object_revisions (user_id);
CREATE INDEX ix_object_revisions_agent_run_id ON object_revisions (agent_run_id);
ALTER TABLE objects ADD COLUMN ai_generated BOOLEAN NOT NULL DEFAULT FALSE;
```

**Commit**: `chore: migration 0004 — object_revisions table and ai_generated column`
**Codex-delegatable**: Yes

---

### Subtask 1 — AI client module + router scaffold

**Goal**: Wrap OpenAI calls behind an async helper that auto-creates AgentRun rows; scaffold empty AI router.

**Files to create**:
- `services/api/app/ai/__init__.py`
- `services/api/app/ai/client.py` — `call_ai()` wrapper
- `services/api/app/ai/prompts.py` — prompt templates
- `services/api/app/models/revision.py` — SQLAlchemy ObjectRevision model
- `services/api/app/services/revision_service.py` — `create_revision()`
- `services/api/app/schemas/ai.py` — Pydantic schemas for all AI endpoints
- `services/api/app/api/v1/ai.py` — router

**`call_ai()` signature**:
```python
async def call_ai(
    db: AsyncSession,
    user_id: uuid.UUID,
    agent_type: str,
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.3,
    input_context: dict | None = None,
) -> tuple[str, AgentRun]:
    # Creates AgentRun, calls OpenAI, updates AgentRun with tokens/cost, returns (text, run)
```

**Files to modify**:
- `services/api/app/api/v1/router.py` — include ai_router at `/ai`
- `services/api/pyproject.toml` — ensure `"openai>=1.0"` present

**Commit**: `feat(ai): AI client module, revision service, and router scaffold`
**Codex-delegatable**: Yes

---

### Subtask 2 — Summarize endpoint

**Goal**: `POST /api/v1/ai/summarize` — reads content, generates summary, writes to `metadata_["ai_summary"]`.

**Flow**:
1. Load object (page content_text or source extracted_text)
2. `call_ai()` with summarize prompt
3. Snapshot before metadata_, write summary fields
4. Create ObjectRevision
5. Return `{summary, agent_run_id, cached}`

**Request/Response**:
```python
class SummarizeRequest(BaseModel):
    object_id: uuid.UUID
    force: bool = False

class SummarizeResponse(BaseModel):
    summary: str
    agent_run_id: uuid.UUID
    cached: bool
```

**Commit**: `feat(ai): summarize endpoint for pages and sources`
**Codex-delegatable**: Yes

---

### Subtask 3 — Extract claims + tasks endpoints

**Goal**: LLM extracts structured items; creates Claim/Task objects + edges.

**Endpoints**: `POST /api/v1/ai/extract-claims`, `POST /api/v1/ai/extract-tasks`

**LLM output format (claims)**:
```json
[{"text": "...", "confidence": "high"}]
```

**LLM output format (tasks)**:
```json
[{"title": "...", "due_hint": "..."}]
```

Each extracted item → `KosObject(kind="claim"|"task")` + `Edge(kind="mentions")`. All objects get `metadata_["ai_generated"] = true`.

**Commit**: `feat(ai): extract-claims and extract-tasks endpoints`
**Codex-delegatable**: Yes

---

### Subtask 4 — Suggest links endpoint

**Goal**: `POST /api/v1/ai/suggest-links` — hybrid search + LLM ranking → suggestions, no auto-write.

**Response**:
```python
class LinkSuggestion(BaseModel):
    target_id: uuid.UUID
    target_title: str
    target_kind: str
    reason: str
    confidence: float

class SuggestLinksResponse(BaseModel):
    suggestions: list[LinkSuggestion]
    agent_run_id: uuid.UUID
```

**Commit**: `feat(ai): suggest-links endpoint using hybrid search + LLM ranking`
**Codex-delegatable**: Yes

---

### Subtask 5 — KB Q&A answer endpoint

**Goal**: `POST /api/v1/ai/answer` — hybrid search → context pack → grounded answer with citations.

**Response**:
```python
class AnswerResponse(BaseModel):
    answer: str
    citations: list[Citation]
    agent_run_id: uuid.UUID
    context_count: int
```

LLM prompt instructs model to end with `\nSources: [id1], [id2]` for citation parsing. No DB write.

**Commit**: `feat(ai): KB Q&A answer endpoint with citations`
**Codex-delegatable**: Yes

---

### Subtask 6 — Inbox API + triage endpoint

**Goal**: Surface unorganized objects; AI suggests tags/title/summary.

**Inbox query** (`GET /objects/inbox`):
```sql
WHERE user_id = :user_id AND deleted_at IS NULL
  AND (tags = '{}' OR tags IS NULL)
  AND (description IS NULL OR description = '')
  AND created_at > now() - INTERVAL '30 days'
ORDER BY created_at DESC
```

**Triage** (`POST /api/v1/ai/triage`): read-only — returns suggestions, user applies via `PATCH /objects/{id}`.

**Commit**: `feat(api): inbox endpoint and triage AI endpoint`
**Codex-delegatable**: Yes

---

### Subtask 7 — AI Sidebar UI

**Goal**: AiPanel tab in PageView's GraphPanel (alongside Backlinks/Related).

**Actions**: Summarize, Extract Claims, Extract Tasks, Suggest Links, Ask KB (inline Q&A input).

**Files**:
- `apps/web/src/components/ai/AiPanel.tsx`
- `apps/web/src/components/ai/AiActionRow.tsx`
- Modify `GraphPanel.tsx` to add "AI" tab

**Commit**: `feat(web): AI sidebar panel with summarize, extract, suggest-links, and Ask KB`
**Codex-delegatable**: Yes

---

### Subtask 8 — Inbox UI

**Goal**: `/inbox` page + TriageModal.

**InboxView**: list unorganized objects; each card has [Triage with AI] button.
**TriageModal**: shows suggested tags (toggleable), title (editable), summary, related objects; [Apply] → PATCH /objects/{id}.

**Files**:
- `apps/web/src/app/inbox/page.tsx`
- `apps/web/src/components/inbox/InboxView.tsx`
- `apps/web/src/components/inbox/TriageModal.tsx`
- Add Inbox nav link to AppShell

**Commit**: `feat(web): inbox page and triage modal for AI-assisted organization`
**Codex-delegatable**: Yes

---

### Subtask 9 — Tests + documentation

**Goal**: ~15 integration tests for all AI endpoints; updated docs.

**Test mock pattern**:
```python
@pytest.fixture
def mock_openai(monkeypatch):
    mock_completion = AsyncMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content="Test summary."))]
    mock_completion.usage = MagicMock(prompt_tokens=10, completion_tokens=20)
    client_mock = AsyncMock()
    client_mock.chat.completions.create = AsyncMock(return_value=mock_completion)
    monkeypatch.setattr("app.ai.client.AsyncOpenAI", lambda **kw: client_mock)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    return client_mock
```

**15 tests**: summarize page/source/cached/force/disabled, extract-claims, extract-tasks, suggest-links, answer/disabled, inbox (returns-untagged/excludes-tagged/excludes-old), triage, agent_runs row created.

**Docs**: AGENT_GUIDE.md, ARCHITECTURE.md, API.md, PROGRESS.md.

**Commits**:
- `test: Phase 5 AI integration tests (~86 total)`
- `docs: document AI assistant endpoints and audit trail design`
**Codex-delegatable**: Yes

---

## Data Model

### Migration 0004

```
object_revisions: id, object_id→objects, user_id→users, rev_num, changed_by, agent_run_id→agent_runs, before_snapshot (JSONB), after_snapshot (JSONB), created_at
objects: +ai_generated BOOLEAN DEFAULT false
```

### metadata_ JSONB AI conventions

```json
{
  "ai_summary": "...",
  "ai_summary_model": "gpt-4o-mini",
  "ai_summary_at": "2026-05-14T10:00:00Z",
  "ai_generated": true,
  "source_object_id": "<uuid>"
}
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/ai/summarize | Summarize page or source |
| POST | /api/v1/ai/extract-claims | Extract Claim objects + edges |
| POST | /api/v1/ai/extract-tasks | Extract Task objects + edges |
| POST | /api/v1/ai/suggest-links | Suggest connections (read-only) |
| POST | /api/v1/ai/answer | KB Q&A with citations |
| POST | /api/v1/ai/triage | Suggest tags/title/summary (read-only) |
| GET | /api/v1/objects/inbox | Untagged/undescribed objects, last 30 days |

---

## Subtask Dependencies

```
0 (migration + config)
└─ 1 (AI client + router scaffold)
   ├─ 2 (summarize)
   ├─ 3 (extract claims + tasks)
   ├─ 4 (suggest links)
   └─ 5 (answer)
       └─ 6 (inbox API + triage)
           └─ 7 (AI sidebar UI)
               └─ 8 (inbox UI)
                   └─ 9 (tests + docs)
```
