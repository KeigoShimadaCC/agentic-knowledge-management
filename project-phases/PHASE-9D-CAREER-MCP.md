# Phase 9D — Career MCP Tools

> **Status:** ✅ Complete (merged to `main` — branch `phase-9d-career-mcp`, 2 commits)
> **Owner:** Codex (implementation) under Claude orchestration
> **Audience:** AI coder — read end-to-end before writing code.
> **Estimated effort:** ~1 PR, ~4 commits, ~600–800 LOC including tests.
> **Blocks:** nothing (final phase in the Phase 9 sequence).
> **Blocked by:** Phase 9C (`resume_bullet_set` / `interview_story` REST endpoints must be live on `main` before 9D begins), Phase 7B (`audited_write_service` + rate limiter on `main`).
> **Branch:** `phase-9d-career-mcp` (worktree: `../akm-phase-9d`, stacked on merged 9C).

---

## 0. North Star

Phase 9C shipped the full frontend for career memory (projects, evidence, resume bullets, interview stories, export). Phase 9D exposes these capabilities to **AI agents via the MCP server**, following the exact same patterns established in Phase 7A (read tools) and Phase 7B (audited write tools).

After this phase, an agent can:
1. `list_projects` / `get_project` to discover the user's project records.
2. `create_project` / `update_project` / `archive_project` to manage projects.
3. `link_to_project` to attach evidence objects.
4. `extract_project` to draft a project from an existing page/source/chat.
5. `generate_and_save_resume_bullets` to produce and persist bullets.
6. `generate_and_save_interview_story` to produce and persist a STAR story.
7. `list_resume_bullet_sets` / `get_resume_bullet_set` and `list_interview_stories` / `get_interview_story` to read saved artifacts.

**What this phase does NOT do:**

- No frontend changes — 9C owns the frontend.
- No new DB migrations — all tables were created in 9C (migration 0009).
- No new object kinds — `resume_bullet_set` and `interview_story` were added in 9C.
- No new API endpoints — all REST endpoints were created in 9C.

---

## 1. Non-breakage contract

- All existing MCP tests (`pytest services/mcp/tests/` ~20) pass unchanged.
- All existing API integration tests (~149 after 9C) pass unchanged.
- All existing frontend tests pass unchanged.
- `ruff check services/mcp && ruff format --check services/mcp` clean.
- Tool gating: read tools always available; write tools require `MCP_ALLOW_WRITE_TOOLS=true` (same mechanism as 7B).
- Rate-limit contract: write tools use the same 60/min + 600/hour Redis sliding window (same `rate_limit.py` as 7B).
- Audit contract: every write tool call produces an `agent_runs` row via `audited_write_service.audited_write()`.
- Redaction contract: no `api_keys`, `session_secret`, or password hashes returned in any tool response.

---

## 2. Files inventory

### MAY NOT touch

| File / dir | Why |
|---|---|
| `services/mcp/kos_mcp/core/rate_limit.py` | 7B owns; import only. |
| `services/api/**` | All API work done in 9A/9B/9C. MCP calls REST via internal token. |
| `apps/web/**` | 9C owns frontend. |
| `services/api/alembic/versions/0001..0009*.py` | Never edit applied migrations. |
| `tests/api/**`, `tests/e2e/**`, `tests/worker/**` | Other phases own. |

### MAY edit (additive only)

| File | Allowed change |
|---|---|
| `services/mcp/kos_mcp/tools.py` | Append new tool definitions (read + write). |
| `services/mcp/kos_mcp/server.py` | Register new tools in `call_tool` dispatcher. |
| `services/mcp/kos_mcp/client.py` | Append new API client methods for project/artifact endpoints. |
| `docs/MCP_TOOLS.md` | Append Career section. |
| `docs/SECURITY.md` | Append Career tools subsection. |
| `docs/AGENT_GUIDE.md` | Append "Career via MCP" example. |
| `PROGRESS.md` | Flip Phase 9 to ✅ Complete. |

### MUST create

```
services/mcp/tests/test_project_tools.py
```

---

## 3. Existing patterns to reuse (read before coding)

| Pattern | File |
|---|---|
| Read tool definition + handler | `services/mcp/kos_mcp/tools.py` — `get_object`, `get_page`, `search_objects` |
| Write tool + `MCP_ALLOW_WRITE_TOOLS` gate | `services/mcp/kos_mcp/tools.py` — `create_page`, `update_page`, `archive_object` |
| `audited_write_service` import | `services/api/app/services/audited_write_service.py` (called via REST, not imported directly in MCP; MCP calls the REST endpoints) |
| Rate limit check pattern | `services/mcp/kos_mcp/tools.py` — see `create_page` handler for rate-check before REST call |
| Internal token auth | `services/mcp/kos_mcp/client.py` — `X-KOS-Internal-Token` header |
| Redaction helper | `services/mcp/kos_mcp/core/security.py` — `redact_dict()` |
| MCP test fixture | `services/mcp/tests/conftest.py` |
| Phase 9A endpoint shapes | `services/api/app/schemas/project.py` |
| Phase 9B endpoint shapes | `services/api/app/schemas/career_ai.py` |
| Phase 9C artifact shapes | `services/api/app/schemas/career_artifacts.py` |

---

## 4. Subtasks

### Subtask 9D-1 — MCP API client methods

Append to `services/mcp/kos_mcp/client.py`:

```python
# Projects
async def list_projects(self, *, limit=50, offset=0, status=None, skill=None) -> dict
async def get_project(self, project_id: str) -> dict
async def create_project(self, payload: dict) -> dict      # POST /projects
async def update_project(self, project_id: str, payload: dict) -> dict  # PATCH /projects/{id}
async def archive_project(self, project_id: str) -> dict   # POST /objects/{id}/archive
async def get_project_evidence(self, project_id: str) -> list[dict]  # GET /objects/{id}/backlinks filtered

# Career artifacts (read)
async def list_resume_bullet_sets(self, project_id: str, *, limit=50) -> list[dict]
async def get_resume_bullet_set(self, id: str) -> dict
async def list_interview_stories(self, project_id: str, *, question_type=None) -> list[dict]
async def get_interview_story(self, id: str) -> dict

# AI actions (these POST to REST endpoints that call AI + save)
async def extract_project(self, source_id: str, *, create=True) -> dict
async def generate_resume_bullets(self, project_id: str, *, target_role=None, emphasis=None, count=3) -> dict
async def generate_interview_story(self, project_id: str, *, question_type="behavioral", target_role=None, max_words=400) -> dict
async def save_resume_bullet_set(self, project_id: str, payload: dict) -> dict
async def save_interview_story(self, project_id: str, payload: dict) -> dict

# Edge helpers
async def create_edge(self, source_id: str, target_id: str, kind: str) -> dict  # may already exist — inspect
async def delete_edge(self, edge_id: str) -> None
```

Each method calls the corresponding REST endpoint via `self._get`/`self._post`/`self._patch`/`self._delete` helpers already in `client.py`. Apply the existing depth/limit caps where applicable.

**Commit:** `feat(mcp): career API client methods`

---

### Subtask 9D-2 — Tool definitions + handlers

Append to `services/mcp/kos_mcp/tools.py`. Follow the exact structure of existing tools (tool descriptor dict + handler function).

**Read tools** (always available, no `MCP_ALLOW_WRITE_TOOLS` check):

```python
TOOL_LIST_PROJECTS = {
    "name": "list_projects",
    "description": "List the user's career project records. Filter by status (active/paused/completed/archived) or skill.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "default": 50, "maximum": 200},
            "offset": {"type": "integer", "default": 0},
            "status": {"type": "string", "enum": ["active","paused","completed","archived"]},
            "skill": {"type": "string", "description": "Filter to projects containing this skill (case-insensitive)."},
        },
    },
}

TOOL_GET_PROJECT = {
    "name": "get_project",
    "description": "Get a single project record by ID, including STAR narrative, metrics, skills, and dates.",
    "inputSchema": {
        "type": "object",
        "required": ["project_id"],
        "properties": {"project_id": {"type": "string", "format": "uuid"}},
    },
}

TOOL_GET_PROJECT_EVIDENCE = {
    "name": "get_project_evidence",
    "description": "Return objects linked to a project as evidence (belongs_to_project edges).",
    "inputSchema": {
        "type": "object",
        "required": ["project_id"],
        "properties": {"project_id": {"type": "string", "format": "uuid"}},
    },
}

TOOL_LIST_RESUME_BULLET_SETS = {
    "name": "list_resume_bullet_sets",
    "description": "List saved resume bullet sets for a project.",
    "inputSchema": {
        "type": "object",
        "required": ["project_id"],
        "properties": {"project_id": {"type": "string", "format": "uuid"}, "limit": {"type": "integer", "default": 20}},
    },
}

TOOL_GET_RESUME_BULLET_SET = {
    "name": "get_resume_bullet_set",
    "description": "Get a saved resume bullet set by ID.",
    "inputSchema": {"type": "object", "required": ["id"], "properties": {"id": {"type": "string", "format": "uuid"}}},
}

TOOL_LIST_INTERVIEW_STORIES = {
    "name": "list_interview_stories",
    "description": "List saved STAR interview stories for a project. Optionally filter by question_type.",
    "inputSchema": {
        "type": "object",
        "required": ["project_id"],
        "properties": {
            "project_id": {"type": "string", "format": "uuid"},
            "question_type": {"type": "string", "enum": ["behavioral", "technical", "leadership"]},
        },
    },
}

TOOL_GET_INTERVIEW_STORY = {
    "name": "get_interview_story",
    "description": "Get a saved STAR interview story by ID.",
    "inputSchema": {"type": "object", "required": ["id"], "properties": {"id": {"type": "string", "format": "uuid"}}},
}
```

**Write tools** (gated by `MCP_ALLOW_WRITE_TOOLS=true`, rate-limited, each call goes through `audited_write_service` via the REST endpoint):

```python
TOOL_CREATE_PROJECT = {
    "name": "create_project",
    "description": "Create a new career project record.",
    "inputSchema": {
        "type": "object",
        "required": ["title"],
        "properties": {
            "title": {"type": "string", "maxLength": 255},
            "description": {"type": "string"},
            "period_start": {"type": "string", "format": "date"},
            "period_end": {"type": "string", "format": "date"},
            "role": {"type": "string", "maxLength": 255},
            "organization": {"type": "string", "maxLength": 255},
            "problem": {"type": "string"},
            "actions": {"type": "string"},
            "results": {"type": "string"},
            "metrics": {"type": "object"},
            "skills": {"type": "array", "items": {"type": "string"}},
            "status": {"type": "string", "enum": ["active","paused","completed","archived"]},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
    },
}

TOOL_UPDATE_PROJECT = {
    "name": "update_project",
    "description": "Update fields on an existing project record. All fields are optional (PATCH semantics).",
    "inputSchema": {
        "type": "object",
        "required": ["project_id"],
        "properties": {"project_id": {"type": "string", "format": "uuid"}, "title": {"type": "string"}, "...": "..."},
    },
}

TOOL_ARCHIVE_PROJECT = {
    "name": "archive_project",
    "description": "Soft-archive a project (sets objects.deleted_at). Reversible via restore.",
    "inputSchema": {"type": "object", "required": ["project_id"], "properties": {"project_id": {"type": "string"}}},
}

TOOL_LINK_TO_PROJECT = {
    "name": "link_to_project",
    "description": "Link an existing object (page, source, chat, claim) to a project as evidence.",
    "inputSchema": {
        "type": "object",
        "required": ["object_id", "project_id"],
        "properties": {"object_id": {"type": "string"}, "project_id": {"type": "string"}},
    },
}

TOOL_UNLINK_FROM_PROJECT = {
    "name": "unlink_from_project",
    "description": "Remove a belongs_to_project evidence link by edge ID.",
    "inputSchema": {"type": "object", "required": ["edge_id"], "properties": {"edge_id": {"type": "string"}}},
}

TOOL_EXTRACT_PROJECT = {
    "name": "extract_project",
    "description": "Use AI to extract a project record from an existing page, source, or chat. Creates the project record if create=true.",
    "inputSchema": {
        "type": "object",
        "required": ["source_id"],
        "properties": {
            "source_id": {"type": "string", "format": "uuid"},
            "create": {"type": "boolean", "default": True},
        },
    },
}

TOOL_GENERATE_AND_SAVE_RESUME_BULLETS = {
    "name": "generate_and_save_resume_bullets",
    "description": "Generate AI resume bullets for a project and save them as a ResumeBulletSet object.",
    "inputSchema": {
        "type": "object",
        "required": ["project_id"],
        "properties": {
            "project_id": {"type": "string"},
            "target_role": {"type": "string"},
            "emphasis": {"type": "string"},
            "count": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3},
        },
    },
}

TOOL_GENERATE_AND_SAVE_INTERVIEW_STORY = {
    "name": "generate_and_save_interview_story",
    "description": "Generate an AI STAR interview story for a project and save it as an InterviewStory object.",
    "inputSchema": {
        "type": "object",
        "required": ["project_id"],
        "properties": {
            "project_id": {"type": "string"},
            "question_type": {"type": "string", "enum": ["behavioral","technical","leadership"], "default": "behavioral"},
            "target_role": {"type": "string"},
            "max_words": {"type": "integer", "minimum": 100, "maximum": 800, "default": 400},
        },
    },
}
```

**Handler logic for `generate_and_save_*`:**

These tools call two REST endpoints in sequence — the generate endpoint (which returns a preview + `agent_run_id`) and then the save endpoint (which creates the artifact object). Expose as one atomic tool call from the agent's perspective.

```python
async def handle_generate_and_save_resume_bullets(args, client):
    gen = await client.generate_resume_bullets(
        args["project_id"], target_role=args.get("target_role"), ...
    )
    if "detail" in gen:  # 503 or error
        return {"error": gen["detail"]}
    saved = await client.save_resume_bullet_set(args["project_id"], {
        "target_role": args.get("target_role"),
        "count": len(gen["bullets"]),
        "bullets": gen["bullets"],
        "agent_run_id": gen["agent_run_id"],
    })
    return saved
```

Register all 15 tools in `server.py`'s `list_tools` (read tools always included) and `call_tool` dispatcher (write tools check `settings.mcp_allow_write_tools`).

**Commit:** `feat(mcp): project + career artifact tool definitions and handlers`

---

### Subtask 9D-3 — MCP tests

`services/mcp/tests/test_project_tools.py` (~12 tests, mirror `test_tools.py` patterns):

1. `test_list_projects_returns_items` — mock GET /projects → list_projects returns dict with items.
2. `test_get_project_returns_shape` — mock GET /projects/{id} → correct fields present; no api_keys in response.
3. `test_get_project_evidence_returns_backlinks` — mock GET /objects/{id}/backlinks → filtered to belongs_to_project.
4. `test_list_resume_bullet_sets` — mock response → correct item count.
5. `test_get_interview_story`.
6. `test_create_project_blocked_without_write_flag` — `MCP_ALLOW_WRITE_TOOLS=false` → ToolError raised.
7. `test_create_project_with_write_flag` — flag=true, mock POST → returns project dict.
8. `test_create_project_rate_limited` — mock rate limiter raises → 429 propagated.
9. `test_archive_project` — mock POST /objects/{id}/archive → success.
10. `test_link_to_project` — mock POST /edges → edge dict returned.
11. `test_extract_project_propagates_503` — mock AI disabled → error in response.
12. `test_generate_and_save_resume_bullets_happy_path` — mock generate → mock save → saved bullet set returned.

Run: `uv run --project services/mcp --extra dev pytest services/mcp/tests/ -v` → 20 prior + 12 new = 32 passing.

**Commit:** `test(mcp): project and career artifact tool coverage`

---

### Subtask 9D-4 — Docs + PROGRESS

**`docs/MCP_TOOLS.md`** — append "Career Tools" section listing all 15 new tools with input schemas, example calls, and rate-limit notes for write tools.

**`docs/SECURITY.md`** — append "Career tools" subsection: no new secrets; uses same `X-KOS-Internal-Token` auth; write tools obey `MCP_ALLOW_WRITE_TOOLS` gate + rate limiter; `generate_and_save_*` calls two REST endpoints but counted as one rate-limit token.

**`docs/AGENT_GUIDE.md`** — append "Career via MCP" example:

```markdown
## Career memory via MCP

An agent can manage the full career memory lifecycle:

1. **Discover projects:** `list_projects` → see all active projects
2. **Create from evidence:** `extract_project(source_id=<page_id>)` → drafts + creates project
3. **Link more evidence:** `link_to_project(object_id=<chat_id>, project_id=<project_id>)`
4. **Generate bullets:** `generate_and_save_resume_bullets(project_id, target_role="Staff Eng", count=3)`
5. **Generate story:** `generate_and_save_interview_story(project_id, question_type="behavioral")`
6. **Read back:** `list_resume_bullet_sets(project_id)` → retrieve all saved variants
```

**`PROGRESS.md`** — flip Phase 9 row to `✅ Complete`; add 9D status block with acceptance criteria checked; update total subtask count (103 → 108 with 9C+9D subtasks; all complete).

**Commit:** `docs(phase-9d): MCP_TOOLS + SECURITY + AGENT_GUIDE + PROGRESS complete`

---

## 5. Verification

### MCP tests

```bash
uv run --project services/mcp --extra dev pytest services/mcp/tests/ -v
# Expected: 20 prior + 12 new = 32 passing
```

### Full suite

```bash
make test-all
```

### Smoke test (optional, requires running API + Redis)

```bash
MCP_ALLOW_WRITE_TOOLS=true uv run --project services/mcp python scripts/mcp_smoke.py
```

Extend `mcp_smoke.py` with a career project check: `list_projects` → assert no error.

---

## 6. Acceptance criteria

- [x] 15 new MCP tools registered: 7 read + 8 write.
- [x] All write tools gated by `MCP_ALLOW_WRITE_TOOLS=true`; return ToolError when flag is false.
- [x] Write tools rate-limited via existing Redis sliding-window limiter.
- [x] Write calls flow through REST endpoints which call `audited_write_service` → `agent_runs` row created.
- [x] No api_keys / session_secret / password hashes returned in any tool response.
- [x] 56 MCP tests passing (35 prior + 21 new career tool tests).
- [x] `ruff check services/mcp` clean.
- [x] `docs/MCP_TOOLS.md`, `docs/SECURITY.md`, `docs/AGENT_GUIDE.md` updated.
- [x] `PROGRESS.md` Phase 9 row marked ✅ Complete.
- [x] `make test-all` passes end-to-end.
