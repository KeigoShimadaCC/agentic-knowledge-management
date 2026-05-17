# Phase 14: Scenario Simulation & User Journey Testing

## Context

All phases through 13 are complete and on `main`. The codebase has 76 E2E specs covering individual features, but no test has ever walked through the app as a real user would — end-to-end, across multiple features, in a single coherent session. This phase fills that gap.

Instead of testing "does the search box render", Phase 14 asks: "Can a PhD student who just uploaded 5 papers and 2 YouTube lectures actually get a useful answer from the AI?" Each of the five scenarios below represents a realistic user type with a real motivation. Playwright drives a real browser against the live Docker stack. Codex writes and runs every spec. Claude orchestrates, reviews output, and gates bug fixes before they land.

This phase has four tracks run in dedicated worktrees:

| Track | Goal |
|---|---|
| 14A | Environment setup, shared fixtures, and seeding strategy |
| 14B | Execute all five scenario suites; produce structured bug audit |
| 14C | Fix every confirmed bug found in 14B |
| 14D | Final regression pass across all 76 existing specs + new scenario specs |

---

## Agent Operating Model

| Agent | Role |
|---|---|
| Claude | Orchestrate tracks, write Codex task briefs, review diffs, enforce architecture rules, gate merges |
| Codex | Write Playwright specs, seed test data via API, run suites, return handoff notes with bug IDs |

**Before each Codex task:** Claude writes a brief with: goal, affected files, acceptance criteria, what Codex must NOT change.
**After each Codex task:** Claude checks for architecture drift, missing audit entries, undocumented API changes, and ruff/typecheck clean.

---

## Testing Methodology

### Philosophy

These are **scenario tests**, not unit or integration tests. Each spec simulates the cognitive arc of a specific user:

> *"I have this problem → I use this feature → I get this outcome → I trust the system."*

A scenario spec fails if any step in that arc breaks — even if the underlying unit passes in isolation. The goal is to catch integration gaps, missing loading states, confusing error messages, and data-flow bugs that only appear when features are used together.

### Tooling

**Playwright CLI** (`pnpm exec playwright test`) is the sole browser driver. All specs live in `tests/e2e/scenarios/`. No mocks, no stubs — every spec runs against the real Docker stack (`api`, `worker`, `postgres`, `redis`, `qdrant`).

```
tests/e2e/
  scenarios/
    s01-researcher.spec.ts
    s02-freelance-engineer.spec.ts
    s03-pm-chat-mining.spec.ts
    s04-ai-developer-mcp.spec.ts
    s05-bootcamp-grad.spec.ts
  fixtures/
    scenario-fixtures.ts      ← shared auth, seed helpers
    seed-data/
      papers/                 ← sample PDFs for S01
      chats/                  ← sample ChatGPT JSON for S03
      projects/               ← project payloads for S02, S05
```

### Fixture Strategy

Each spec owns its own isolated test user, created at the top of the `test.beforeAll` block via `POST /api/v1/auth/register`. This prevents cross-scenario pollution. Teardown is soft-delete — never hard-delete, per the non-negotiable rule.

Shared helpers in `scenario-fixtures.ts`:
- `createTestUser(page, tag)` — register + login; return session cookie
- `seedSource(apiUrl, token, { title, url?, filePath? })` — call `POST /api/v1/sources` then poll `GET /api/v1/sources/{id}` until `status === "ready"` (max 60 s, 2 s interval)
- `seedPage(apiUrl, token, { title, content })` — call `POST /api/v1/pages`
- `seedProject(apiUrl, token, payload)` — call `POST /api/v1/projects`
- `waitForWorker(apiUrl, token, sourceId)` — poll until ingestion complete; fail with a clear message on timeout

### Async Worker Handling

Several scenarios depend on the RQ worker completing ingestion before Playwright can assert results. The canonical approach:

```ts
// Poll until source is ready, with a human-readable timeout message
await expect.poll(
  async () => {
    const res = await fetch(`${API}/api/v1/sources/${id}`, { headers });
    return (await res.json()).status;
  },
  { message: 'Source ingestion timed out after 60 s', timeout: 60_000, intervals: [2_000] }
).toBe('ready');
```

Never use `page.waitForTimeout`. All waiting must be poll-based on real application state.

### Playwright Configuration

Scenarios run with:
- `headless: false` during development so failures are visually obvious
- `headless: true` in CI (`CI=true` env flag)
- `video: 'retain-on-failure'` — always record video; keep only on failure
- `screenshot: 'only-on-failure'`
- `trace: 'on-first-retry'`
- `timeout: 90_000` per test (scenarios are longer than unit specs)
- `retries: 1` in CI, `0` locally

Project config addition in `playwright.config.ts`:

```ts
{
  name: 'scenarios',
  testDir: './tests/e2e/scenarios',
  use: { baseURL: 'http://localhost:3000' },
}
```

### Bug Classification

Every bug found gets a record in `tests/e2e/AUDIT-14B.md` with:

| Field | Description |
|---|---|
| `ID` | `S0X-BUG-NNN` (scenario number + sequential) |
| `Scenario` | Which of the 5 scenarios |
| `Step` | Which workflow step failed |
| `Severity` | `P0` blocker / `P1` major / `P2` minor / `P3` cosmetic |
| `Symptom` | What Playwright observed (assertion error, timeout, console error) |
| `Root cause hypothesis` | Brief theory (Codex writes this) |
| `Video/trace` | Path to attached artifact |
| `Fix PR` | Filled in during Track 14C |

**P0 (blocker):** The scenario cannot complete at all — core value is broken.
**P1 (major):** The scenario completes but with a confusing or incorrect outcome.
**P2 (minor):** A visual or UX problem that doesn't break the flow.
**P3 (cosmetic):** Wrong copy, spacing, icon — non-functional.

### Fix Gate (Track 14C)

For each bug, the fix process is:

1. Claude reads the `AUDIT-14B.md` entry and writes a bounded Codex task: affected files, root cause to investigate, acceptance test command.
2. Codex fixes, runs `playwright test --grep <scenario-tag>`, and returns a diff + green result.
3. Claude reviews: no architecture drift, quality gates clean (`pnpm typecheck`, `pnpm lint`, `ruff check`), `agent_runs` audit entry present for any write-tool changes.
4. Merge to `phase-14c-bug-fixes`.

P0 and P1 bugs must be fixed before the phase can be marked complete. P2/P3 may be deferred with a tracked issue.

---

## Worktree Structure

| Track | Branch | Worktree path |
|---|---|---|
| 14A | `phase-14a-fixtures` | `~/Documents/akm-phase-14a` |
| 14B | `phase-14b-scenario-audit` | `~/Documents/akm-phase-14b` |
| 14C | `phase-14c-bug-fixes` | `~/Documents/akm-phase-14c` |
| 14D | `phase-14d-regression` | `~/Documents/akm-phase-14d` |

Tracks 14A and 14B run sequentially (14B depends on fixtures from 14A). Track 14C runs concurrently with individual bug tasks assigned to Codex one at a time. Track 14D runs after 14C is merged.

---

## Track 14A — Environment Setup & Shared Fixtures

**Goal:** Docker stack is verified healthy; shared fixture helpers are written and tested with a smoke call; sample seed data (PDFs, chat JSONs) is committed to `tests/e2e/scenarios/fixtures/seed-data/`.

### Subtasks

- [ ] **14A-0** — Branch + worktree created; `playwright.config.ts` gains `scenarios` project block
- [ ] **14A-1** — Write `scenario-fixtures.ts`: `createTestUser`, `seedSource`, `seedPage`, `seedProject`, `waitForWorker`
- [ ] **14A-2** — Commit sample seed data:
  - 3 short PDFs (public-domain academic papers, ~500 KB each) for S01
  - 2 YouTube URLs (creative commons lectures) for S01
  - 1 ChatGPT export JSON (synthetic, ~50 conversations) for S03
  - 2 project JSON payloads for S02 and S05
- [ ] **14A-3** — Write a smoke spec `fixtures.smoke.spec.ts` that calls each helper once and asserts the created objects exist in `GET /api/v1/objects`; confirm the RQ worker processes a source within 60 s
- [ ] **14A-4** — Document any Docker stack issues found (port conflicts, worker not picking up jobs, Qdrant not ready) and fix or note them before 14B begins

**Codex task boundary:** Write fixture module + smoke spec; confirm Docker stack is healthy. Return: fixture file paths, smoke spec result, any infra notes.

**Verification:** `pnpm exec playwright test fixtures.smoke` exits green; all helpers tested once.

---

## Track 14B — Scenario Execution & Bug Audit

**Goal:** Run all five scenario specs against the live stack; produce `tests/e2e/AUDIT-14B.md` with every failure classified.

### Subtasks

- [ ] **14B-0** — Write all five spec files (see Scenarios section below); each spec is self-contained with its own user
- [ ] **14B-1** — Run S01 (Researcher); record results
- [ ] **14B-2** — Run S02 (Freelance Engineer); record results
- [ ] **14B-3** — Run S03 (PM Chat Mining); record results
- [ ] **14B-4** — Run S04 (AI Developer + MCP); record results
- [ ] **14B-5** — Run S05 (Bootcamp Grad); record results
- [ ] **14B-6** — Compile `tests/e2e/AUDIT-14B.md`: full bug table, ordered by severity; attach video/trace paths

**Codex task boundary:** Write and run all five specs; write the audit doc. Return: AUDIT-14B.md committed; ordered bug list with reproduction steps; pass/fail summary table.

**Verification:** All specs have run to completion (pass or documented failure); audit doc committed and readable.

---

## Track 14C — Bug Fix Sprint

Run after 14B. One Codex task per bug, sequenced P0 → P1 → P2.

- [ ] **14C-0** — Claude reads audit, writes Codex brief for each bug
- [ ] **14C-N** — One fix task per `S0X-BUG-NNN` entry (IDs filled in after 14B)
- [ ] **14C-final** — Run `playwright test tests/e2e/scenarios/` in full; all scenarios green

**Verification:** All P0 and P1 bugs resolved; `pnpm typecheck` ✅ · `pnpm lint` ✅ · `ruff check` ✅ · all 76 prior specs still green.

---

## Track 14D — Regression Pass

- [ ] **14D-0** — Merge 14C into 14D branch
- [ ] **14D-1** — Run full suite: `pnpm exec playwright test` (all projects, all specs)
- [ ] **14D-2** — Fix any regressions introduced by 14C fixes
- [ ] **14D-3** — Update `PROGRESS.md`; merge to `main`

---

## The Five Scenarios

---

### Scenario 1 — PhD Researcher: "Building a research brain"

**User type:** PhD student in machine learning  
**Core question the scenario answers:** Can a user ingest academic sources and get a meaningful AI answer synthesized across them?

**Playwright spec:** `s01-researcher.spec.ts`  
**Tags:** `@s01` `@researcher`  
**Timeout:** 120 s (PDF ingestion + embedding is slow)

#### Workflow steps

| Step | Action | Playwright assertion |
|---|---|---|
| 1 | Register + login as `researcher@test.local` | Redirect to `/app`; sidebar visible |
| 2 | Upload 3 PDF papers via `POST /api/v1/assets/upload?create_source=true` (fixture helper) | Sources appear in `/app/sources` list with `status: processing` |
| 3 | Ingest 2 YouTube lecture URLs via Sources → "Add Source" → URL input | New source rows appear; `status: processing` |
| 4 | Poll until all 5 sources reach `status: ready` (max 120 s) | `waitForWorker` passes for each |
| 5 | Navigate to `/app/pages` → "New Page" → title: "Attention Mechanisms Notes" | Page saved; URL changes to `/app/pages/{id}` |
| 6 | Open Source detail for one PDF → assert extracted text section visible | Source detail panel shows non-empty text preview |
| 7 | Link the page to a source: Graph → "Add Edge" modal → select source → save | Edge appears in `GET /app/pages/{id}/edges` or graph panel shows relation |
| 8 | Navigate to `/app` (home / AI assistant) → type query: "What do my sources say about the attention mechanism?" | AI answer panel appears; response is non-empty; at least one citation references an ingested source |
| 9 | Assert no console errors throughout | `page.on('console')` listener captures no `error` level messages |

#### What this tests under the hood

- PDF + YouTube ingestion pipeline (worker, extractors, chunk + embed → Qdrant upsert)
- Hybrid search retrieving chunks from multiple source types
- RAG answer synthesis via `POST /api/v1/ai/answer`
- Edge creation and graph panel render
- Long async operation UX (loading states, status polling)

---

### Scenario 2 — Freelance Engineer: "Turning gig work into a job application"

**User type:** Freelance software engineer applying for full-time roles  
**Core question:** Can a user build a career record and get AI-generated resume bullets and interview stories?

**Playwright spec:** `s02-freelance-engineer.spec.ts`  
**Tags:** `@s02` `@career`  
**Timeout:** 90 s

#### Workflow steps

| Step | Action | Playwright assertion |
|---|---|---|
| 1 | Register + login as `freelancer@test.local` | On `/app` |
| 2 | Navigate to `/app/projects` → "New Project" → fill form: title, dates, tech stack, outcomes → save | Project card appears in list |
| 3 | Open project detail → Evidence Panel → "Add Evidence" → link to a newly-created page ("Architecture Decision Record") | Evidence entry appears in panel with linked object title |
| 4 | Click "Generate Resume Bullets" button | Loading spinner → bullets appear (at least 3 lines of non-empty text); no error toast |
| 5 | Click "Generate Interview Story" button | STAR-structured story appears in Interview Story Panel; non-empty |
| 6 | Create a second project; add evidence linking to first project's page (cross-project link) | Second project evidence panel shows the page correctly |
| 7 | Navigate to `/app/pages` and confirm the ADR page appears with back-edge to the project visible | Object detail shows correct backlinks |
| 8 | Assert no console errors | No `error` level console messages |

#### What this tests under the hood

- Phase 9 career module: project CRUD, evidence linking, AI generators
- Resume bullet endpoint (`POST /api/v1/projects/{id}/resume-bullets`)
- Interview story endpoint (`POST /api/v1/projects/{id}/interview-story`)
- Cross-object edge display and backlinks
- AI generation failure path: if API key is missing, a graceful error (not a crash) must appear

---

### Scenario 3 — Product Manager: "Mining old AI conversations"

**User type:** Product manager with 2 years of ChatGPT conversations  
**Core question:** Can a user import a large chat export, search it meaningfully, and extract insights into a page?

**Playwright spec:** `s03-pm-chat-mining.spec.ts`  
**Tags:** `@s03` `@chat-import`  
**Timeout:** 90 s

#### Workflow steps

| Step | Action | Playwright assertion |
|---|---|---|
| 1 | Register + login as `pm@test.local` | On `/app` |
| 2 | Navigate to `/app/chats` → "Import Conversations" → upload synthetic ChatGPT JSON (50 conversations from fixture) | Import job starts; progress indicator visible |
| 3 | Poll until all conversations reach `status: ready` | Chat list shows imported conversations with titles (not "Untitled") |
| 4 | Navigate to `/app/inbox` → assert AI inbox shows at least one surfaced conversation | Inbox list non-empty; items have conversation links |
| 5 | Click a conversation → detail view opens → structured summary visible (not raw JSON) | Summary section renders with paragraphs, not raw text |
| 6 | Search: type "pricing strategy" in global search → results include conversation titles | Search results list non-empty; at least one result is a chat object |
| 7 | Open Workspaces → "New Workspace" → add two panes; open two different conversations in each pane | Dual-pane layout renders both conversations side by side |
| 8 | In one pane, select text → "Create Page" → title auto-populated → save | New page created; navigating to `/app/pages` shows the new page |
| 9 | Assert no console errors | No `error` level console messages |

#### What this tests under the hood

- Phase 6B structured chat import with realistic volume (50 conversations)
- Inbox/Triage AI surfacing logic
- Structured summary render (not raw JSON bleed-through)
- Semantic search across chat-derived chunks (cross-type search)
- Multi-pane workspace layout (Phase 8C) under real content
- "Create Page from selection" flow (Phase 11B inline editor AI or text-extract)

---

### Scenario 4 — AI Developer: "Giving Claude Code access to project knowledge"

**User type:** Developer building a SaaS product who uses Claude Code daily  
**Core question:** Can an MCP client read and write to the knowledge base safely, with a full audit trail?

**Playwright spec:** `s04-ai-developer-mcp.spec.ts`  
**Tags:** `@s04` `@mcp`  
**Timeout:** 60 s

> Note: This spec drives the browser for the UI side and calls the MCP-backed API directly (via `fetch` with `X-KOS-Internal-Token`) to simulate what an AI agent would do. The kos-mcp stdio process is not started in this spec; the internal API is hit directly to avoid subprocess management complexity in Playwright.

#### Workflow steps

| Step | Action | Playwright assertion |
|---|---|---|
| 1 | Register + login as `ai-dev@test.local` | On `/app` |
| 2 | Ingest 2 web sources (architecture doc URLs) via fixture helper | Sources ready |
| 3 | Create 3 ADR pages via fixture helper | Pages visible in `/app/pages` |
| 4 | Navigate to `/app/settings/mcp` → assert MCP Connections page renders | Connections list visible; "Add Connection" button present |
| 5 | Via direct API call (simulating agent `search_objects`): `POST /api/v1/mcp/search` with query "auth middleware" | Response JSON contains at least one result; no secrets in response (`api_key`, `password`, `session_secret` fields absent) |
| 6 | Via direct API call (simulating agent `answer_from_kb`): `POST /api/v1/ai/answer` | Non-empty answer; cited chunks reference the ingested sources |
| 7 | Via direct API call (simulating agent `create_page`): `POST /api/v1/pages` with agent token | Page created; response includes page `id` |
| 8 | Navigate to `/app/pages` in browser → confirm the agent-created page appears in the list | Page row visible |
| 9 | Via direct API call: `GET /api/v1/agent-runs` → confirm the agent write is logged | At least one `agent_runs` record with the correct `action` and `agent_id` |
| 10 | Attempt a path-traversal write (file path outside `LIBRARY_ROOT`) → assert 400/403 response | API rejects with non-2xx status; no file created |
| 11 | Assert no console errors in browser | No `error` level console messages |

#### What this tests under the hood

- MCP Settings page (Phase 12A)
- MCP read tools via internal API: search, answer
- MCP write tools: create_page with audit trail
- Secret redaction invariant (no keys in any response)
- Path-traversal guard on ingest tools
- Agent runs audit log visible via API and (implicitly) in the DB

---

### Scenario 5 — Bootcamp Grad: "Organizing a job search knowledge base"

**User type:** Self-taught developer preparing for technical interviews  
**Core question:** Can a user save learning resources, get proactive AI nudges, and quickly find their own notes under time pressure?

**Playwright spec:** `s05-bootcamp-grad.spec.ts`  
**Tags:** `@s05` `@proactive-ai`  
**Timeout:** 90 s

#### Workflow steps

| Step | Action | Playwright assertion |
|---|---|---|
| 1 | Register + login as `bootcamp@test.local` | On `/app` |
| 2 | Ingest 5 web URLs (JavaScript tutorial pages) via fixture helper | 5 sources reach `status: ready` |
| 3 | Create a study notes page for each source, linked via edge | 5 pages visible; edges visible in source detail |
| 4 | Navigate to `/app/inbox` → assert AI inbox shows at least one item (unlinked sources or stale content nudge) | Inbox non-empty |
| 5 | Click an inbox item → "Dismiss" → item removed from inbox without page crash | Inbox updates; no error toast |
| 6 | Create a project "Portfolio: Todo App" with 2 evidence links | Project card visible in `/app/projects` |
| 7 | Open the project → "Generate Interview Story" | STAR story appears; non-empty |
| 8 | Use global search: type "async await" → results appear within 2 s | At least one result links to a study notes page |
| 9 | Open a study notes page → select a paragraph → trigger inline AI: "Explain this simply" | Inline AI response appears below the selection; no crash |
| 10 | Disconnect network (simulate offline) → navigate to a previously-viewed page | Page content still renders (cached/local-first behavior); no white screen |
| 11 | Reconnect → assert app recovers without a forced reload | Page still showing; no reload required |
| 12 | Assert no console errors throughout | No `error` level console messages |

#### What this tests under the hood

- Source ingestion at breadth (5 URLs in one session)
- Inbox/Triage proactive AI (Phase 11C background AI surfacing)
- Inbox dismiss flow
- Career module from a learner's angle
- Semantic search recall under time constraint
- Phase 11B inline editor AI ("Explain this simply" command)
- Graceful offline degradation (core local-first value)

---

## Acceptance Criteria

Phase 14 is complete when:

- [ ] All five scenario specs are committed to `tests/e2e/scenarios/`
- [ ] `tests/e2e/AUDIT-14B.md` exists with every bug classified
- [ ] All P0 and P1 bugs have a resolved Fix PR referenced in the audit doc
- [ ] Full suite (`pnpm exec playwright test`) exits with zero failures
- [ ] All existing 76 specs still pass (no regressions)
- [ ] `pnpm typecheck` ✅ · `pnpm lint` ✅ · `ruff check` ✅
- [ ] `PROGRESS.md` updated before merge to `main`

---

## Where Things Live

| Artifact | Path |
|---|---|
| Scenario specs | `tests/e2e/scenarios/` |
| Shared fixtures | `tests/e2e/scenarios/fixtures/scenario-fixtures.ts` |
| Seed data | `tests/e2e/scenarios/fixtures/seed-data/` |
| Bug audit doc | `tests/e2e/AUDIT-14B.md` |
| Playwright config | `playwright.config.ts` (add `scenarios` project) |
| PROGRESS entry | `PROGRESS.md` → Phase 14 section |
