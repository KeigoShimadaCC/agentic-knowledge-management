# AI Coder Briefing — KnowledgeOS

> **Use this:** Paste the full contents of this file at the start of any new AI coder session working on this repo, **before** the specific task description. Read end-to-end before doing anything.
> **Last refreshed:** 2026-05-15
> **Why this exists:** `CLAUDE.md` and `AGENTS.md` cover the rules. The phase docs cover individual workstreams. This file is the missing **operating context**: what's actually built, what's in flight, what patterns to copy, what mistakes to avoid — distilled from a full repo audit and several weeks of multi-agent parallel development.

---

## 1. What this repository is, in one paragraph

**KnowledgeOS** is a local-first personal AI knowledge base. One user, one Mac, everything in Docker, all data under `~/KnowledgeOS/`. The user dumps pages, sources (PDFs, articles, YouTube), assets, and chat transcripts; the system structures, searches, and reasons over them. AI agents (Claude Code, Codex, ChatGPT, local LLMs) interact via the built-in **MCP server** and the **internal REST API** — they can search, read, and (Phase 7B onwards) safely write knowledge with a complete audit trail. Backend is FastAPI + SQLAlchemy 2.0 async + Postgres 16; workers are RQ on Redis; frontend is Next.js 14 + Tiptap; vector index is Qdrant; graph index is Kùzu. Postgres + the local filesystem are the canonical sources of truth; Qdrant and Kùzu are rebuildable caches.

If you only remember three things from this entire briefing:
1. **Postgres + `~/KnowledgeOS/library/` are canonical. Everything else is a cache.**
2. **Soft-delete only. Never `DELETE FROM` anything user-owned.**
3. **Every agent write writes an `agent_runs` row and (for mutations) an `object_revisions` row.** This is the audit invariant; breaking it breaks the trust contract with the user.

---

## 2. Read these files first, in this order

Spend ~15 minutes here before touching code. The order matters.

| # | File | Why |
|---|---|---|
| 1 | `CLAUDE.md` | Non-negotiable rules. Constitution of the repo. |
| 2 | `AGENTS.md` | Shorter operational guide. Repeats some of #1 with different framing. |
| 3 | `PROGRESS.md` | **The truth table.** What's done, what's in flight, what's planned. Trust this over the README. |
| 4 | `docs/ARCHITECTURE.md` | Service topology + sequence diagrams. |
| 5 | `docs/DATA_MODEL.md` | Postgres schema. Look at `objects` (universal base), `pages`, `sources`, `assets`, `chats`, `edges`, `agent_runs`, `object_revisions`, `chunks`. |
| 6 | `docs/API.md` | REST surface. Search by endpoint name, not by trying to discover. |
| 7 | `docs/MCP_TOOLS.md` | Agent tool surface. |
| 8 | `docs/SECURITY.md` | Auth, sessions, audit, redaction rules. |
| 9 | `project-phases/IDEA-DRAFT.md` | The product vision. North-star use cases. Long but skimmable; appendices contain the long-term schema. |
| 10 | `project-phases/PHASE-FIX-0{1,2,3}-*.md` | The audit findings. Reading these tells you what was *claimed* but wasn't actually true, and what's been since fixed vs. is still pending. |

After those: read the specific `PHASE-N-*.md` for whatever you're working on. Each phase doc is self-contained and has goals, non-goals, schema, endpoints, tests, commit sequence, and risks.

**Do not** read every file in the repo. The codebase is medium-sized but the docs are the right entry points. Use `Grep` and `Glob` for everything else.

---

## 3. Phase truth table (as of 2026-05-15)

The README has been wrong before. **This table is the source of truth.** Cross-check `PROGRESS.md` for any newer state.

| Phase | Status | What it shipped |
|---|---|---|
| 1 — Foundation | ✅ Complete | Monorepo, Docker stack, auth, objects/pages/assets CRUD, page editor (Tiptap), asset upload, 25 integration tests |
| 2 — Sources & Rich Media | ✅ Complete | `sources` table, ingestion worker (PDF / image / CSV / YouTube / web), citations in editor, `derives_from` edges |
| 3 — Search | ✅ Complete | Postgres FTS keyword, Qdrant vector, hybrid; chunking + embedding pipeline; Cmd+K modal |
| 4 — Graph Lite | ✅ Complete | Edge taxonomy + validation, `/objects/{id}/{edges,backlinks,related}`, frontend BacklinksPanel + RelatedPanel + LinkToModal |
| 5 — AI Assistant | ✅ Complete | `summarize`, `extract-claims`, `extract-tasks`, `suggest-links`, `answer`, `triage`, `inbox`; `agent_runs` + `object_revisions` always written |
| 6A — Chat Import Lite | ✅ Complete | Paste / upload ChatGPT, Claude, Markdown, plain transcripts; `chats` table; structured chat objects |
| 6B — Structured Chat Import | ✅ Complete | AI structured summary on import; `structured_summary` JSONB column |
| 7A — MCP Read | ✅ Complete | stdio MCP server; tools: `search_objects`, `hybrid_search`, `get_object`, `get_page`, `get_source`, `get_related_objects`; `X-KOS-Internal-Token` auth; redaction |
| 7B — MCP Write | 🚧 In flight on `phase-7b-mcp-write` worktree | Rate limiter, `audited_write` helper, archive + restore endpoints, `create_page` / `update_page` / `create_edge` / `archive_object` / `ingest_url` / `ingest_file` MCP tools, all gated behind `MCP_ALLOW_WRITE_TOOLS` |
| 8A — Workspace Lite | ✅ Complete | `WorkspaceLiteProvider`, `WorkspaceSidePane`, "open in side pane" affordances |
| 8 — Multi-pane Workspaces (full) | 📋 Planned, not yet specced | Saved workspace layouts, drag-drop between panes, AI scoped to workspace |
| 9A — Career Memory Backend | 📋 Plan written (`PHASE-9A-CAREER-MEMORY-BACKEND.md`) | `projects` table + CRUD + `extract-project` AI endpoint |
| 9B / 9C / 9D — Career Memory MCP, frontend, AI generators | 📋 Future, deferred | Resume bullets, interview stories, frontend, MCP tools |
| ENHANCE-01 — Hardening (search/quality/multilingual) | ✅ Complete | Snippet sanitization (no more `dangerouslySetInnerHTML` for snippets), multilingual ILIKE fallback, eval fixtures, debug toggle, index-status endpoint |
| ENHANCE-02 — Testing Infrastructure | 🚧 In flight on `phase-enhance-02-testing-infra` worktree | Vitest scaffold, frontend component tests, Playwright E2E, worker tests, CI workflow |
| ENHANCE-03 — UX Polish | 📋 Plan written (`PHASE-ENHANCE-03-UX-POLISH.md`) | Design tokens, primitives, toasts, palette upgrade, light theme, a11y, responsive |
| FIX-01 — Claimed-done gaps | ✅ Resolved | All 7 audit gaps closed |
| FIX-02 — Forgotten / undocumented | ✅ Merged | Cleanup pass |
| FIX-03 — Repo oddities | 📋 Plan written, partial | Some items addressed by FIX-01/02; others tracked in plan doc |

Test counts as of last audit: **112 backend integration + 16 backend unit + 19 MCP package = 147 total.** Worker tests: 0 (closed by ENHANCE-02 T3). Frontend tests: 0 (closed by ENHANCE-02 T1+T2). E2E: 0 (closed by ENHANCE-02 T4+T5).

---

## 4. Active worktrees (critical for parallel safety)

This repo uses `git worktree` to run multiple parallel implementations without context-switching `main`. **Before doing any backend or frontend work, run `git worktree list` and check what files each branch is currently editing.**

Current worktrees (verified 2026-05-15):

| Path | Branch | Owns these files |
|---|---|---|
| `~/Documents/agentic-knowledge-management` | `main` | None — main is the integration point |
| `~/Documents/agentic-knowledge-management-7b` | `phase-7b-mcp-write` | `services/api/app/api/v1/objects.py`, `services/api/app/config.py`, `services/api/app/core/{library,rate_limit}.py`, `services/api/app/services/{agent_run,audited_write,revision}_service.py`, `services/mcp/**`, `tests/api/test_{archive_restore,rate_limit}.py`, `infra/.env.example` |
| `~/Documents/agentic-knowledge-management-enhance-02-testing-infra` | `phase-enhance-02-t3-worker-reconcile` | `apps/web/{package.json,tsconfig.json,vitest.*}`, `apps/web/src/test/**`, `apps/web/src/**/__tests__/**`, `tests/{worker,e2e}/**`, root `package.json`, `pnpm-workspace.yaml`, `.github/workflows/**` |

### Coordination protocol when starting work

1. `cd /Users/keigoshimada/Documents/agentic-knowledge-management && git fetch && git status`
2. `git worktree list` — confirm which paths are active.
3. For each active worktree: `cd <worktree path> && git diff --name-only main...HEAD` — get the exact file list it currently owns.
4. Build a personal **conflict map** of (your work × each worktree). If your work touches any file in any other worktree's diff, **stop and renegotiate scope**: either move that file to a future phase, or wait for the other worktree to merge.
5. `PROGRESS.md` is touched by everyone. Treat it as append-only; resolve conflicts by keeping all sections.
6. If you must coordinate: open a PR against `main` with the plan doc only, and let the other worktrees rebase onto it.

### When to spin up a new worktree

- New phase / new feature with > ~5 files of changes.
- Work that will take > 1 day.
- Work that you want isolated from `main` while iterating.

```bash
git worktree add ../agentic-knowledge-management-<short-name> <branch-name>
cd ../agentic-knowledge-management-<short-name>
# branch-name should follow pattern: phase-<N>[-<sub>]-<topic>
# e.g., phase-9a-career-memory-backend
```

When the branch merges to `main`: `git worktree remove <path>` from the main checkout.

---

## 5. Architectural invariants — never break these

These are surfaced as PR-blocking review items.

### 5.1 Soft-delete only

Every user-owned table has a `deleted_at TIMESTAMPTZ` nullable column. Deletion sets it; never issue `DELETE FROM`. Every read query filters `WHERE deleted_at IS NULL` (or uses a service layer that does). Restore = `UPDATE ... SET deleted_at = NULL`.

### 5.2 Audit trail on every agent write

When an AI agent or MCP tool writes:
1. Insert an `agent_runs` row with `agent_type`, `status`, `input` (JSONB), `output` (JSONB), `created_objects` (UUID[]), `updated_objects` (UUID[]), token counts, timestamps.
2. For every mutation of an existing object, insert an `object_revisions` row capturing the prior state.

The wrapper `services/api/app/services/audited_write_service.py` (added in PHASE-7B) makes this transactional. Use it once 7B merges. Until then, write the rows by hand inside the same transaction.

### 5.3 LIBRARY_ROOT is the only filesystem write target

All file IO must go through `services/api/app/core/library.py` helpers. Never construct paths with string concat. Never write outside `LIBRARY_ROOT` (default `~/KnowledgeOS/library/`). Reject any user-supplied path that resolves outside the root.

### 5.4 Content-addressed asset storage

Assets are stored at `LIBRARY_ROOT/assets/<sha256[:2]>/<sha256>/original<ext>`. **Write-once.** SHA-256 of the bytes is computed before write; if the path already exists, the file is deduplicated. Never overwrite.

### 5.5 No secret leakage through API or MCP

`api_keys`, `session_secret`, password hashes, `SESSION_SECRET`, `OPENAI_API_KEY`, `MCP_INTERNAL_TOKEN` — none of these may appear in any API response or MCP tool result. Pydantic schemas for `User`, `Session`, etc. never expose these fields. The MCP redaction layer (`services/mcp/kos_mcp/`) strips them server-side too.

### 5.6 Local-first

No paid SaaS dependencies allowed without explicit user approval. The only external services in use today are OpenAI (for embeddings + LLM calls) and Anthropic (potential, not yet wired). User opt-in via `OPENAI_API_KEY`. If the key is unset, AI endpoints return **503** with a friendly `detail` — they never crash, and they never silently degrade to a worse provider without telling the user.

### 5.7 No arbitrary shell execution via MCP

MCP tools are read / search / write / ingest only. No `exec`, no `shell`, no `eval`. If the tool needs filesystem access it goes through validated `LIBRARY_ROOT` helpers.

### 5.8 Update docs when behavior changes

If you change the schema → update `docs/DATA_MODEL.md`. New endpoint → `docs/API.md`. New MCP tool → `docs/MCP_TOOLS.md`. New ingestion pipeline → `docs/INGESTION.md`. Auth/audit change → `docs/SECURITY.md`. New AI prompt or RAG behavior → `docs/AGENT_GUIDE.md`. **The PR is incomplete without the doc update.**

---

## 6. Patterns to follow when adding new code

The repo has settled patterns. Match them exactly. Inventing new structure is a review-blocker.

### 6.1 Adding a new specialized object kind (the `KosObject` extension pattern)

Existing kinds: `page`, `asset`, `note`, `bookmark`, `collection`, `source`, `chat`, `claim`, `task`. Adding a new one (e.g. `project`) means:

1. Add the string to `services/api/app/core/object_kinds.py::VALID_OBJECT_KINDS`.
2. New ORM model `services/api/app/models/<kind>.py` with PK = `ForeignKey("objects.id", ondelete="CASCADE")`. Mirror `models/chat.py` style.
3. Register in `services/api/app/models/__init__.py` (one import + one entry in `__all__`).
4. New Alembic migration `services/api/alembic/versions/<NNNN>_add_<kind>_table.py`. Number it after the latest applied. Include `upgrade()` and `downgrade()`.
5. Pydantic schemas `services/api/app/schemas/<kind>.py`: `<Kind>Base`, `<Kind>Create`, `<Kind>Update`, `<Kind>Out`. Pydantic v2 with `ConfigDict(from_attributes=True)`. Mirror `schemas/chat.py`.
6. Service layer `services/api/app/services/<kind>_service.py`. Pure async functions, take `db: AsyncSession`, return ORM tuples. Mirror `chat_service.py`.
7. REST router `services/api/app/api/v1/<kind>s.py` (plural). 5 endpoints: `POST /<kinds>`, `GET /<kinds>` (paginated, filter), `GET /<kinds>/{id}`, `PATCH /<kinds>/{id}`, `DELETE /<kinds>/{id}` (soft).
8. Wire in `services/api/app/api/v1/router.py` with one `api_router.include_router(<kind>s_router)` line.
9. Tests `tests/api/test_<kinds>.py`. Mirror `test_chats.py` style. Minimum 8 cases: create, list (paginated), get, get-not-found, get-other-user-404, update, soft-delete, restore.
10. Update `docs/DATA_MODEL.md` with the new table + columns. Update `docs/API.md` with the new endpoints.

### 6.2 Adding a new AI endpoint

Look at `services/api/app/api/v1/ai.py`. The 7 existing endpoints (`summarize`, `extract-claims`, `extract-tasks`, `suggest-links`, `answer`, `triage`, `inbox`) all share:

1. The OpenAI client wrapper in `services/api/app/ai/client.py::call_ai()` — auto-creates an `agent_runs` row, captures input/output/tokens, sets status. **Always use this; never call OpenAI directly from the endpoint.**
2. Prompts live in `services/api/app/ai/prompts.py` as constants. JSON outputs use `response_format={"type": "json_object"}`.
3. Pydantic request/response in `services/api/app/schemas/ai.py`.
4. AI-disabled handling: if `OPENAI_API_KEY` is missing or empty, return 503 with `detail="AI features disabled — set OPENAI_API_KEY"`. There's a helper.
5. If the endpoint mutates an existing object → also write an `object_revisions` row.
6. If it creates new objects (e.g. `extract-claims` creates `claim` objects), the agent_run's `created_objects` array records the new IDs.

### 6.3 Adding a new MCP tool

Read `docs/MCP_TOOLS.md`, then `services/mcp/kos_mcp/tools.py` and `config.py`. Pattern:

1. Define the tool's input schema as a Pydantic model.
2. Implement an async function that calls the internal API via `KosApiClient` (it talks to `MCP_API_BASE_URL` with `X-KOS-Internal-Token`). **Never reach into Postgres directly from MCP.** All writes and reads go through the API.
3. Register the tool in `services/mcp/kos_mcp/tools.py` with its name, description (clear enough for an LLM to know when to call it), and handler.
4. Add to `DEFAULT_ALLOWED_TOOLS` in `config.py` (read-only tools) or behind `MCP_ALLOW_WRITE_TOOLS=1` (write tools — gated since 7B).
5. Tests in `services/mcp/tests/test_tools.py`. The pattern is: mock the `KosApiClient` and assert on the requests it would make.
6. Update `docs/MCP_TOOLS.md`.

### 6.4 Adding a frontend route

Routes live under `apps/web/src/app/(app)/app/`. Pattern:

1. SSR shell for data fetching (cookie auth via `cookies()` and forwarding to FastAPI). See `app/(app)/app/pages/[id]/page.tsx` for the canonical pattern.
2. Client component for interactivity. Co-locate under `apps/web/src/components/<feature>/`.
3. Data fetching uses **SWR** with hooks like `useObjects`, `useSource`, `useChat`. Add a new hook in `apps/web/src/lib/hooks/` if needed.
4. Routing helpers — never construct URLs by string concat. Use `objectRoute(kind, id)` from `apps/web/src/lib/objectRouting.ts`.
5. After ENHANCE-03 UX-T1 lands: prefer primitives in `apps/web/src/components/ui/` over inline Tailwind. Until then: match the existing inline-Tailwind style of the file you're editing.

### 6.5 Adding an Alembic migration

```bash
cd services/api
uv run alembic revision -m "add foo table"
# edit the generated file; set down_revision to the previous head
uv run alembic upgrade head        # apply locally
uv run alembic downgrade -1        # verify it rolls back cleanly
uv run alembic upgrade head        # re-apply
```

**Never edit a migration that has been applied to `main`.** Add a new migration that fixes the previous one.

---

## 7. Patterns to follow when writing tests

### 7.1 Backend integration tests (`tests/api/`)

- Real Postgres `knowledgeos_test` database (auto-created/torn-down per test). **Never mock the DB.**
- pytest-asyncio + httpx ASGITransport hitting the FastAPI app directly. No HTTP server.
- Fixtures in `tests/api/conftest.py`: `client`, `db`, `auth_user`, `auth_client`. Use them; don't reinvent.
- Each test creates its own data; tests run in random order; **no shared mutable state between tests.**
- Soft-delete invariant applies in tests too: never `DELETE FROM`. Cleanup is automatic via DB teardown.

```python
async def test_create_project_minimal(auth_client):
    resp = await auth_client.post("/api/v1/projects", json={"title": "Demo"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Demo"
    assert body["confidence"] == "manual"
```

### 7.2 Mocking OpenAI (the canonical pattern)

Look at `tests/api/test_ai.py`. The pattern:

```python
@pytest.fixture
def mock_openai(monkeypatch):
    """Patch openai.AsyncOpenAI globally so all AI endpoints return canned responses."""
    # see existing fixture in test_ai.py for the exact shape
    ...
```

Patch `openai.AsyncOpenAI` once at fixture level — **do not** patch individual call sites. The fixture returns a configurable mock that takes `(prompt, response_text)` mappings.

### 7.3 Frontend component tests (Vitest, after ENHANCE-02 T1 merges)

- Vitest + jsdom + Testing Library. **Never Jest.**
- HTTP mocking via MSW handlers in `apps/web/src/test/msw/handlers.ts`. **Never `vi.fn()` to mock fetch directly.**
- Mount Tiptap for real against jsdom — it works. Don't stub the editor.
- Assert on roles, text, and behavior. **No snapshot tests.**
- Use `renderWithProviders` from `apps/web/src/test/render.tsx` to inject auth + workspace context.

### 7.4 E2E tests (Playwright, after ENHANCE-02 T4 merges)

- Real stack: requires `docker compose -f infra/docker-compose.yml up -d` first.
- Sandbox `LIBRARY_ROOT` to `tests/e2e/.tmp/library` — **never** point at `~/KnowledgeOS/`.
- Each test creates a UUID-suffixed user via the API; cleans up via API soft-delete; never touches the DB directly.
- Tests live in `tests/e2e/specs/`. Numbered `01-`, `02-`, etc. for order-independence + readability.

### 7.5 Worker tests (`tests/worker/`, after ENHANCE-02 T3 merges)

- Generate fixtures programmatically (PDF via `reportlab`, PNG via Pillow, CSV via stdlib `csv`, mocked YouTube via `respx`). **Never commit large binary fixtures.**
- Mock external HTTP with `respx`. Assert no real network calls escaped (use `respx`'s no-unmatched-routes mode).

---

## 8. Quality gates — exact commands per layer

Run before every commit. Don't skip any gate just because a task "feels small."

| Layer | Command | When |
|---|---|---|
| Frontend types | `pnpm typecheck` | every frontend change |
| Frontend lint | `pnpm lint` | every frontend change |
| Frontend build | `pnpm build` | before any PR that touches `apps/web/` |
| Frontend unit / component (after ENHANCE-02 T1) | `pnpm -F web test:run` | every frontend change |
| API lint + format | `cd services/api && uv run ruff check . && uv run ruff format --check .` | every backend change |
| API unit + integration | `cd tests && uv run pytest api/ -v` | every backend change |
| Single API test file | `cd tests && uv run pytest api/test_pages.py -v` | TDD-style during dev |
| Worker tests (after ENHANCE-02 T3) | `cd tests && uv run pytest worker/ -v` | every worker change |
| MCP tests | `cd services/mcp && uv run pytest tests/ -v` | every MCP change |
| E2E (after ENHANCE-02 T4) | `cd tests/e2e && pnpm test` | before PRs that touch user flows |
| Migration round-trip | `cd services/api && uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head` | every migration |

If a gate fails, **fix it before proceeding**. Don't disable rules. Don't `xfail` without a TODO comment naming the issue.

---

## 9. Git workflow this repo uses

### 9.1 Conventional commits, scoped

Format: `<type>(<scope>): <imperative summary>`

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `infra`.

Scopes seen in this repo: `api`, `web`, `mcp`, `worker`, `phase4`, `phase5`, `phase7b`, `phase8a`, `phase9a`, `search`, `ai`, `ui`, `auth`, `e2e`, `progress`.

Body explains **why**, not what. The diff already shows what.

```
feat(api): projects table migration with skill GIN index

skills array gets queried often via "show all projects with python";
GIN index makes that O(log n) instead of seq scan.
```

### 9.2 One coherent change per commit

Don't mix schema migration + endpoint + UI in one commit. Commit each layer separately so revert is surgical. The phase docs spell out the commit sequence per phase — follow them.

### 9.3 Push after committing

Default policy in this repo is to push to `origin/<branch>` after every commit. Override only if the user explicitly says "don't push yet."

### 9.4 Plan-doc style

Every non-trivial phase ships a markdown plan doc in `project-phases/` first, then implementation. Look at `PHASE-7B-MCP-WRITE.md` and `PHASE-9A-CAREER-MEMORY-BACKEND.md` for the canonical shape:

```
# Phase <N> — <Title>

> Status, Owner, Audience, Estimated effort, Blocks/Blocked-by, Parallel-safe-with

## Non-breakage contract  (what cannot change, who owns what files)
## Coordination with live worktrees  (file-by-file conflict map)
## Goal & non-goals
## Hard constraints
## Schema / API / UI design
## Subtask checklist (codex-delegatable)
## Files to create / modify
## Tests required (specific test names + assertions)
## Commit sequence
## Validation commands
## Risks and mitigations
## Definition of Done
## Suggested order of operations
```

When in doubt: write the plan first, push it as a docs-only commit to `main`, then implement. For small bounded tasks (< 700 LOC, single session), combining plan + implementation in one PR is fine — the plan is commit 1, implementation is commits 2–N.

### 9.5 PR description checklist

Every PR description must include:
- Phase doc link.
- Files touched (subset of the plan's "files to create/modify").
- Quality gate output (`pytest`, `typecheck`, `lint`, `build`).
- Confirmation that no other worktree's files were touched.
- Screenshots (for frontend PRs) at 1280×800 and 375×812.
- Rollback note (what reverting this PR does and doesn't undo).

---

## 10. Repo gotchas — things that have bitten previous agents

### 10.1 Port mappings

| Service | Host port | Container port |
|---|---|---|
| Postgres | **5433** | 5432 |
| API | **8001** | 8000 |
| Web | 3000 | 3000 |
| Redis | 6379 | 6379 |
| Qdrant | 6333 | 6333 |

So `psql` from your laptop uses 5433. The API talks to Postgres in-container as 5432. Tests use the host port.

### 10.2 The MCP base URL

Internal default in `infra/.env.example` should be `http://localhost:8001` (not 8000) because MCP runs on the host and talks to the dockerized API. If you see `8000` there, it's a leftover bug — fix it.

### 10.3 The `kos_session` cookie

Auth is cookie-based. SSR fetches in `apps/web/src/app/(app)/app/.../page.tsx` must forward the cookie:

```tsx
const cookieStore = cookies();
const sessionCookie = cookieStore.get("kos_session");
if (!sessionCookie) return null;
fetch(url, { headers: { Cookie: `kos_session=${sessionCookie.value}` }, cache: "no-store" });
```

Forgetting this is the #1 reason "logged-in pages don't render data on first load."

### 10.4 `next/font` requires network at build time

`next/font/google` downloads at `pnpm build`. For a fully offline build (some CI environments), use `next/font/local` and check the font file into `apps/web/public/fonts/`. Document this when adding fonts.

### 10.5 SQLAlchemy 2.0 async, not 1.x

All ORM queries use `select()`, `await db.execute(stmt)`, `result.scalars().all()`. Old-style `Query` does not work. Look at `services/api/app/services/page_service.py` for the right shape.

### 10.6 Pydantic v2, not v1

`model_config = ConfigDict(from_attributes=True)` not `class Config: orm_mode = True`. Validators are `@field_validator` and `@model_validator`, not `@validator`.

### 10.7 `metadata` is a reserved attribute name on SQLAlchemy `DeclarativeBase`

That's why models use `metadata_: Mapped[dict] = mapped_column("metadata", JSONB, ...)` — Python attribute is `metadata_`, DB column is `metadata`. Match this pattern; do not rename.

### 10.8 Alembic numbering is sequential, not autoincrement

The latest applied migration on `main` is `0006_add_structured_chat_summary.py`. Your new migration is `0007_*.py` with `down_revision = "0006"`. **Never reuse a number** even if a previous migration was reverted.

### 10.9 `tailwind-merge` and `clsx` are already installed

Don't add `classnames`, don't add `tailwind-classnames`, don't add `tailwind-variants`. Use:
```ts
// apps/web/src/lib/cn.ts (after UX-T1 lands)
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
export const cn = (...inputs: ClassValue[]) => twMerge(clsx(inputs));
```

### 10.10 The empty `theme.extend = {}`

`apps/web/tailwind.config.ts` extends nothing today. There are no custom design tokens; everything uses raw Tailwind palette. ENHANCE-03 UX-T1 will introduce tokens. Until then, don't introduce them in passing — that's a coordinated change.

### 10.11 The asset metadata placeholder

`apps/web/src/app/(app)/app/assets/page.tsx` admits in a code comment that asset content_type and size_bytes are hardcoded (`application/octet-stream`, `0`). This is tracked but not yet fixed. **Do not** "fix it" in passing — it requires verifying the assets API response shape and is scheduled for a future phase.

### 10.12 Cmd+K is global; `/` is not yet bound

The only keyboard shortcut today is `Cmd+K` for the search modal (`apps/web/src/components/layout/AppShell.tsx`). ENHANCE-03 UX-T3 will add `/` (suppressed in editable elements) and `?` (shortcut overlay). Don't add new global shortcuts in unrelated PRs.

### 10.13 Worker container in docker-compose was missing

Earlier audit caught that `infra/docker-compose.yml` advertised ingestion but didn't run a worker. Check whether this is still true (`docker compose ps` should show a `worker` container running `rq worker kos-ingest`). If not, that's tracked in `PHASE-FIX-01-CLAIMED-DONE-GAPS.md`.

### 10.14 OpenAI mocking pattern

Patching `openai.AsyncOpenAI` at the `monkeypatch` fixture level is the convention. **Don't** patch `services.api.app.ai.client.AsyncOpenAI` (the import alias) — patch the source module. Look at `tests/api/test_ai.py` for the exact pattern.

### 10.15 The `objects.kind` field is a `String(32)`, not an enum

So adding a new kind (e.g. `project`) requires updating `app/core/object_kinds.py::VALID_OBJECT_KINDS` (application-layer validation), but no DB-level enum migration. There is no DB CHECK constraint on `kind` — validation is enforced in the service layer.

### 10.16 Soft-delete restore endpoint is universal

`POST /api/v1/objects/{id}/restore` works for any kind. Don't add a per-kind `restore` endpoint.

### 10.17 The `terminals/` folder

`~/.cursor/projects/.../terminals/` contains live terminal state files. Don't reference them in commits or PR descriptions; they're local-only.

### 10.18 `agent-transcripts/` (if present)

Past chat transcripts. Useful for context recovery but **never cite them directly** in user-facing output.

---

## 11. North-star use cases (informs design decisions)

When you face a design tradeoff, ask "which choice serves these uses better?":

1. **The user dumps a 50-page PDF, asks Claude to summarize, then later searches for a phrase from page 17 and finds it.** → drives chunking + RAG + citation linking.
2. **The user pastes a ChatGPT transcript; the system extracts claims, links them to existing pages, and pins a structured summary on top.** → drives Phase 6B + AI extraction.
3. **The user asks "what did I do in 2024?" and gets a chronological project summary derived from real evidence.** → drives Phase 9 (career memory).
4. **An external Claude/Codex session uses MCP to search the user's KB, find the right page, and link a new page to it — with a full audit trail the user can review later.** → drives Phase 7A/7B.
5. **The user opens a page beside another in split view, drags evidence between them, and asks AI a question scoped to both panes.** → drives Phase 8 (multi-pane workspaces).
6. **Everything works offline; AI features degrade gracefully when no API key.** → drives the 503-with-friendly-detail pattern.

When designing, prefer features that compound across these use cases. Avoid one-off features that only serve one of them.

---

## 12. When to ask vs when to act

| Situation | Default |
|---|---|
| Wrong assumption is cheap to fix (renamed variable, wrong test name) | **Act.** Make a reasonable call. Document in commit. |
| Wrong assumption is expensive (schema migration, API contract, new dep) | **Ask.** Stop, explain options, wait for direction. |
| Two phase docs disagree on a detail | **Ask** which to follow, then propose updating the wrong one. |
| The user's task touches a file owned by an active worktree | **Ask** whether to renegotiate scope. Don't silently overlap. |
| You can't reproduce a test failure locally | **Ask** before patching the test. Maybe the env is broken. |
| OpenAI returns something unexpected | **Defensive parse + log + return 502.** Don't silently swallow. |
| User says "make it pretty" with no spec | **Ask** for examples / inspiration / brand. Don't invent. |

When you make a judgment call, leave a one-line commit-message note explaining the reasoning so the next agent understands.

---

## 13. The plan-doc template (use this for new phases)

```markdown
# Phase <N> — <Title>

> **Status:** Plan | In flight | Complete
> **Owner:** Backend | Frontend | Full-stack | Testing | DevOps
> **Audience:** AI coder. Read end-to-end before code.
> **Estimated effort:** N PRs over ~N days
> **Blocks:** <other phases waiting on this>
> **Blocked by:** <other phases this needs>
> **Parallel-safe with:** <list active worktrees and verify file overlap>

## 0. North star
(One paragraph: why this matters, how it maps to use cases.)

## 1. Non-breakage contract
1.1 Files this phase MAY NOT touch (with reasons)
1.2 Files this phase MAY edit (with allowed change scope)
1.3 Files this phase MUST create
1.4 Behaviors that may not regress
1.5 Dependency policy

## 2. Conflict map (verified file-by-file)
(git diff --name-only main...HEAD against each active worktree)

## 3. Schema design (if applicable)
(SQL DDL, validation rules, design choices justified)

## 4. Pydantic schemas / API shape
(Verbatim model definitions)

## 5. Service layer
(Function signatures + behavior notes)

## 6. REST / MCP endpoints
(Verbatim route definitions, error contract)

## 7. AI prompts (if applicable)
(Verbatim prompt text, JSON schema, mocking strategy)

## 8. Migration
(Verbatim Alembic skeleton)

## 9. Tests required (numbered table, specific names + assertions)

## 10. Commit sequence (numbered, each independently revertible)

## 11. Validation commands

## 12. Risks and mitigations (table)

## 13. Out of scope (deferred to future sub-phases)

## 14. Definition of Done

## 15. Suggested order of operations for the AI coder
```

If you skip any of these sections, the plan is incomplete. Don't.

---

## 14. Hard "don't do this" list

- ❌ Hard-delete user data. Always soft-delete.
- ❌ Skip the audit trail (`agent_runs` + `object_revisions`) on agent writes.
- ❌ Expose `api_keys`, `session_secret`, `password_hash`, or any other secret.
- ❌ Write outside `LIBRARY_ROOT`.
- ❌ Touch a file currently owned by another worktree.
- ❌ Mutate Postgres or the filesystem directly from MCP tools — go through the internal API.
- ❌ Add a paid SaaS dependency without explicit approval.
- ❌ Mock the database in integration tests.
- ❌ Use Jest. Use Vitest.
- ❌ Use Cypress. Use Playwright.
- ❌ Snapshot test UI output.
- ❌ Patch individual OpenAI call sites. Patch the client at fixture level.
- ❌ Rename or delete files in `Section 1.1 / 1.2 / 1.3` of any phase doc without coordinating.
- ❌ Edit an applied Alembic migration. Add a new one.
- ❌ Disable lint rules to make CI pass.
- ❌ Skip a test with `xfail` / `.skip` / `test.skip` without an inline TODO comment naming the blocker.
- ❌ Commit large binary fixtures. Generate them at runtime.
- ❌ Run E2E tests against the user's real `~/KnowledgeOS/`.
- ❌ Add network-dependent tests. Mock with `respx` (Python) / MSW (web) / Playwright `route()` (E2E).
- ❌ Lower the existing test count without replacing coverage.
- ❌ Break a public component's signature without flag-gating the change.
- ❌ Combine unrelated changes in one commit.
- ❌ Push to `main` directly when working on a non-trivial feature. Use a branch + PR.
- ❌ Force-push to `main` ever.
- ❌ Update `git config`.
- ❌ Cite `agent-transcripts/` files directly to the user.
- ❌ Mention the `terminals/` folder in user-facing output.

---

## 15. Quick orientation: get up to speed in 30 minutes

Before doing anything substantive, run this orientation sequence:

```bash
# 1. Where are we?
cd /Users/keigoshimada/Documents/agentic-knowledge-management
git status
git log --oneline -10
git worktree list

# 2. What's the truth?
head -100 PROGRESS.md
ls project-phases/

# 3. What's actually built? (count active code files, not docs)
find services/api/app -name "*.py" | wc -l
find apps/web/src -name "*.tsx" -o -name "*.ts" | wc -l
ls services/api/alembic/versions/

# 4. Are tests green?
cd tests && uv run pytest api/ -q 2>&1 | tail -5
# Expect: ~112+ passed (whatever the latest count is per PROGRESS.md)

# 5. Does the stack come up?
docker compose -f infra/docker-compose.yml ps
# If services aren't running: docker compose -f infra/docker-compose.yml up -d

# 6. Read these in order (15 min):
#    CLAUDE.md → AGENTS.md → PROGRESS.md (top half) → docs/ARCHITECTURE.md
#    Then the specific phase doc you're implementing.

# 7. Now plan, then code.
```

---

## 16. Closing principles

- **Polish is taste applied uniformly. Safety is taste applied first.** A small, conservative, well-scoped change is always better than a big one that might regress.
- **The repo prefers patterns over invention.** If you need to do X and X has been done for chats/pages/sources before, copy that pattern. Don't be original on structure; be original on the new domain logic.
- **Local-first means no surprises.** No data leaves the machine. No services start up that the user didn't explicitly opt into. No background network calls. If you add a feature that wants to phone home, it's wrong — re-design.
- **Agent-readiness means designing every endpoint twice.** Once for a human clicking buttons, once for an agent choosing tools. Both need to be safe.
- **PROGRESS.md is the journal.** Update it whenever something material changes. The next agent will read it before they read your code.

You are now oriented. Read the specific phase doc, check the worktrees, plan the work, then commit by commit.
