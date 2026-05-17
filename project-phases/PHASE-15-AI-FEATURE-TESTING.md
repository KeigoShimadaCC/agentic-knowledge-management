# Phase 15 — AI Feature Testing

## Goal

Four E2E Playwright scenarios that exercise the AI features end-to-end with real API calls and no mocks. These build on Phase 14 (scenario simulation) but go deeper: every test asserts that actual AI-generated content appeared in the browser, not just that a button rendered or a graceful error appeared.

The fourth scenario adds a **Context7 MCP integration** — connecting the Context7 documentation MCP server so the `enrich-page` AI feature can pull live library docs into the knowledge base. This requires implementing SSE transport support (currently stubbed out as `"not yet supported"`).

---

## What We Know Works (Pre-Phase API Recon)

Confirmed against live Docker stack (`kos-api` at `127.0.0.1:8001`):

| Endpoint | Latency | Key Inputs | Key Outputs |
|---|---|---|---|
| `POST /api/v1/ai/generate-resume-bullets` | ~1.3s | project with problem/actions/results | `bullets[]` array |
| `POST /api/v1/ai/generate-interview-story` | ~3.4s | project with any content | `story.situation/task/action/result` |
| `POST /api/v1/ai/summarize` | ~2.3s | object with `content_text` populated | `summary` string |
| `POST /api/v1/ai/extract-claims` | ~2.5s | object with `content_text` populated | `items[]` array |
| `POST /api/v1/ai/triage` | ~1.6s | inbox item object_id | `summary`, `suggested_tags[]` |
| `POST /api/v1/ai/enrich-page` | TBD | page_id + query + Context7 connected | enriched sources + edge to page |

**Infrastructure state for S-AI-04:**
- `McpClientSession.__aenter__` raises `McpConnectionError("SSE transport not yet supported")` for SSE connections — must be fixed before the scenario can run
- `mcp.client.sse.sse_client` IS available in the container's uv environment — the fix is straightforward
- Context7 public SSE endpoint: `https://mcp.context7.com/sse`
- Context7 tool patterns that the `Context7Adapter` matches: `context7*`, `get_library_docs*`, `resolve_library*`

**Not used in this phase:**
- `answer` — internal server error (Qdrant/vector issue, separate bug)
- `suggest-links` — returns empty without a sufficiently indexed KB

**Content seeding requirement:**
Pages need `content_json` (Tiptap doc format) AND `content_text` set via `PATCH /api/v1/pages/{page_id}`. Object ID and page ID are the same UUID. See `tests/e2e/fixtures/pages.ts` for the pattern.

Projects need `problem`, `actions`, `results` fields populated for resume bullets to generate non-empty output.

---

## Scenarios

### S-AI-01 — Career AI: Resume Bullets & Interview Story

**What it tests:** Full career AI workflow from browser UI. Phase 14 S02 proved the mechanism works — this goes further by asserting specific content shapes.

**Setup (beforeAll):**
- `createTestUser()` → store as `seedApi`
- Create project via API with full STAR content:
  ```json
  {
    "title": "E-commerce Platform Rebuild {TAG}",
    "problem": "Legacy PHP app had 4s average page load and 40% cart abandonment",
    "actions": "Decomposed monolith into 6 FastAPI microservices, migrated frontend to Next.js with Redis caching",
    "results": "Reduced page load to 800ms, decreased cart abandonment by 22%, shipped on time",
    "role": "Lead Engineer",
    "organization": "RetailCo"
  }
  ```
- Tag the project with TAG

**Tests:**

| # | Name | Action | Assertion |
|---|---|---|---|
| 1 | `@sai01 resume bullets generates ≥3 bullets` | Navigate to project → Resume Bullets panel → click Generate → `waitForResponse(*generate-resume-bullets*)` | Response status 200; ≥3 bullet list items visible in UI |
| 2 | `@sai01 each bullet contains substantive text` | After test 1 resolves | Every visible bullet has ≥ 10 words |
| 3 | `@sai01 interview story generates all STAR sections` | Navigate to project → Interview Stories panel → click Generate → `waitForResponse(*generate-interview-story*)` | Response status 200; all 4 section headings visible: "Situation", "Task", "Action", "Result" |
| 4 | `@sai01 interview story sections are non-empty` | After test 3 resolves | Each STAR section panel contains ≥ 20 words of text |
| 5 | `@sai01 no console errors` | Navigate to `/app/projects` | Zero console error events |

**Timing:** Use `waitForResponse()` with `timeout: 20_000` for all AI calls. Do NOT use `waitForTimeout`.

---

### S-AI-02 — Page Intelligence: Summarize & Extract Claims

**What it tests:** The AI panel on a rich page — summarize and extract-claims via the browser UI. Existing spec 20 mocks these — this spec fires real API calls and asserts real output.

**Setup (beforeAll):**
- `createTestUser()` → store as `seedApi`
- Create page via API with substantial `content_text` (~80 words on a focused topic):
  ```
  TypeScript is a strongly typed programming language that builds on JavaScript,
  developed by Microsoft. It adds optional static typing and class-based
  object-oriented programming. TypeScript catches errors early through its type
  system and makes large codebases more maintainable. Anders Hejlsberg designed
  TypeScript in 2012. Major frameworks like Angular and NestJS use TypeScript as
  their primary language. TypeScript compiles to plain JavaScript and runs
  anywhere JavaScript runs. The TypeScript compiler performs type checking and
  transpilation in a single step.
  ```
  Use the `createPage` fixture helper pattern: POST then PATCH with `content_json` + `content_text`.
- Tag the page object with TAG

**Tests:**

| # | Name | Action | Assertion |
|---|---|---|---|
| 1 | `@sai02 page renders with content` | Navigate to `/app/pages/{pageId}` | Main content area non-empty; page title visible |
| 2 | `@sai02 summarize produces a paragraph` | Open AI panel → click Summarize → `waitForResponse(*summarize*)` | Response status 200; a non-empty paragraph with ≥ 30 words appears in the AI panel |
| 3 | `@sai02 extract claims produces ≥2 claims` | Click Extract Claims → `waitForResponse(*extract-claims*)` | Response status 200; ≥ 2 claim cards/items visible in the UI |
| 4 | `@sai02 claims reference the page topic` | After test 3 | At least one visible claim contains the word "TypeScript" |
| 5 | `@sai02 no console errors` | Navigate to `/app/pages` | Zero console error events |

**Note on UI selectors:** Check `apps/web/src/components/editor/AiPanel*.tsx` for actual data-testid attributes before writing selectors.

---

### S-AI-03 — Inbox AI Triage (Real, No Mock)

**What it tests:** The inbox triage flow with a real AI call. Existing spec 15 mocks the triage endpoint — this spec removes the mock and asserts the real AI response rendered in the browser.

**Setup (beforeAll):**
- `createTestUser()` → store as `seedApi`
- Create a page with substantive `content_text` (product decision, meeting notes, or similar) — ensures triage produces a meaningful summary + tags
- Leave it untagged so it appears in the inbox
- Tag the object with TAG for cleanup

**Tests:**

| # | Name | Action | Assertion |
|---|---|---|---|
| 1 | `@sai03 inbox shows the seeded item` | Navigate to `/app/inbox` | Seeded page title visible in inbox list within 8s |
| 2 | `@sai03 triage modal opens` | Click "Triage with AI" button next to the seeded item | `[data-testid="triage-modal"]` visible |
| 3 | `@sai03 analyze with AI returns real summary` | Click "Analyze with AI" → `waitForResponse(*ai/triage*)` with `timeout: 15_000` | Response status 200; AI-generated summary paragraph appears in modal (non-empty, ≥ 20 words); at least 1 suggested tag chip visible |
| 4 | `@sai03 applying suggested tags dismisses item` | Click the first suggested tag chip → click "Apply" or "Done" | Modal closes; item disappears from inbox or moves to a different section |
| 5 | `@sai03 no console errors` | Navigate to `/app/inbox` | Zero console error events |

**Before writing test 4:** Check `apps/web/src/components/inbox/TriageModal.tsx` for the apply/done button name and chip structure.

---

### S-AI-04 — Context7 MCP: Enrich Page with Live Docs

**What it tests:** Full MCP integration flow — register a Context7 SSE connection through the UI, then use the "Enrich with Docs" AI feature to pull live library documentation into the knowledge base and have it linked to a page.

**Prerequisite — SSE transport fix (must happen in Track 15A before this spec runs):**

`services/api/app/mcp_client/client.py` — replace the SSE stub with a real implementation using `mcp.client.sse.sse_client` from the MCP Python SDK (already available in the uv env):

```python
# Current stub (raises):
if self._conn.transport == "sse":
    raise McpConnectionError("SSE transport not yet supported")

# Replace with: use mcp.client.sse.sse_client + ClientSession
# Pattern (from MCP SDK docs):
#
# from mcp.client.sse import sse_client
# from mcp import ClientSession
#
# async with sse_client(url=self._conn.url) as (read_stream, write_stream):
#     async with ClientSession(read_stream, write_stream) as session:
#         await session.initialize()
#         tools = await session.list_tools()
#         result = await session.call_tool(tool_name, args)
#
# The McpClientSession class needs to store the session context managers
# and expose list_tools() and call_tool() methods that work the same
# way as the existing stdio implementation.
```

Also implement SSE test-connection in `services/api/app/api/v1/mcp_connections.py` so the settings UI can populate capabilities:
- Add a branch in `_run_sse_test` (currently returns "not yet supported")
- Use `sse_client + ClientSession.list_tools()` to fetch and store capabilities

**Setup (beforeAll):**
- `createTestUser()` → store as `seedApi`
- Register Context7 connection via API:
  ```ts
  const conn = await seedApi.post("/api/v1/mcp-connections", {
    data: {
      name: "Context7",
      transport: "sse",
      url: "https://mcp.context7.com/sse",
      enabled: true,
    },
  });
  // Store conn id as context7Id
  ```
- Test the connection (which also populates capabilities):
  ```ts
  await seedApi.post(`/api/v1/mcp-connections/${context7Id}/test`);
  // After this, capabilities should include tools like "resolve-library-id", "get-library-docs"
  ```
- Create a page with TAG: `"Setting up TypeScript in a Next.js project"`
- Tag with TAG

**Tests:**

| # | Name | Action | Assertion |
|---|---|---|---|
| 1 | `@sai04 MCP settings shows Context7 connection` | Navigate to `/app/settings/mcp` | A row with "Context7" visible in the connections list |
| 2 | `@sai04 connection has capabilities after test` | After beforeAll setup | `GET /api/v1/mcp-connections/{id}` → `capabilities` array non-empty; at least one tool name matches `get*docs` or `resolve*library` |
| 3 | `@sai04 enrich-page pulls live docs` | Navigate to page → AI panel → "Enrich with Docs" → fill query "TypeScript Next.js" → submit → `waitForResponse(*enrich-page*)` with `timeout: 30_000` | Response status 200; response includes created sources or enriched content; page shows new linked sources or content additions |
| 4 | `@sai04 enriched sources appear in sources list` | Navigate to `/app/sources` | At least one new source with a title related to "TypeScript" or "Next.js" is visible |
| 5 | `@sai04 no console errors` | Navigate to `/app/settings/mcp` | Zero console error events |

**Timing:** enrich-page makes an outbound call to Context7 then writes sources — give it `timeout: 30_000`. If Context7's public SSE endpoint is unreachable, the test should fail clearly, not silently degrade.

**Cleanup:** In `afterAll`, delete the Context7 MCP connection: `await seedApi.delete("/api/v1/mcp-connections/{context7Id}")`.

---

## Worktree Strategy

```bash
# 15A — SSE fix + all 4 scenario specs
git worktree add ~/Documents/akm-phase-15a -b phase-15a-ai-specs

# 15B — bug fixes from audit
git worktree add ~/Documents/akm-phase-15b -b phase-15b-ai-fixes

# 15C — regression pass
git worktree add ~/Documents/akm-phase-15c -b phase-15c-regression
```

All Codex tasks write to `~/Documents/agentic-knowledge-management/` (main worktree path — Codex sandbox restriction). Claude copies to the correct worktree after each track.

Run stack: `docker compose -f infra/docker-compose.yml up -d` — confirm all services healthy before Codex runs.

---

## Track 15A — SSE Fix + Write Specs + Audit

**Goal:** Fix SSE transport, write specs 29–32, run them, produce `tests/e2e/AUDIT-15A.md`.

### Sub-task 15A-0: Fix SSE transport (prerequisite for S-AI-04)

**Files to modify:**
- `services/api/app/mcp_client/client.py` — implement SSE session using `mcp.client.sse.sse_client`
- `services/api/app/api/v1/mcp_connections.py` — implement `_run_sse_test` to list tools and store capabilities

The SSE `McpClientSession` must expose the same `list_tools()` / `call_tool()` interface as the stdio implementation. Keep the class shape identical — only the transport layer changes.

### Spec files to create

| File | Action |
|---|---|
| `tests/e2e/specs/29-sai01-career-ai.spec.ts` | New |
| `tests/e2e/specs/30-sai02-page-intelligence.spec.ts` | New |
| `tests/e2e/specs/31-sai03-inbox-triage.spec.ts` | New |
| `tests/e2e/specs/32-sai04-context7-mcp.spec.ts` | New |
| `tests/e2e/AUDIT-15A.md` | New — after running |

### Isolation pattern (same as Phase 14)

```ts
const TAG = `sai01-${Date.now().toString(36)}`;
let seedApi: APIRequestContext;

test.beforeAll(async () => {
  const user = await createTestUser();
  seedApi = user.api;
  // seed data using seedApi
});

test.afterAll(async () => {
  await cleanupByTag(seedApi, TAG);
  await seedApi.dispose();
});
```

Never use `{ api }` fixture in test bodies that share cross-test state — it calls `softDeleteAllObjects()` in teardown. Use `seedApi` (module-level) for all within-test API calls.

### waitForResponse pattern (use everywhere, no waitForTimeout)

```ts
const responsePromise = page.waitForResponse(
  (r) => r.url().includes("generate-resume-bullets"),
  { timeout: 20_000 }
);
await page.getByRole("button", { name: "Generate" }).click();
const response = await responsePromise;
expect(response.status()).toBe(200);
const body = await response.json();
expect(body.bullets.length).toBeGreaterThanOrEqual(3);
```

### Content seeding pattern

```ts
const pageResponse = await seedApi.post("/api/v1/pages", { data: { title } });
const { object, page } = await pageResponse.json();
await seedApi.patch(`/api/v1/pages/${page.id}`, {
  data: {
    content_json: {
      type: "doc",
      content: [{ type: "paragraph", content: [{ type: "text", text: CONTENT }] }],
    },
    content_text: CONTENT,
  },
});
// object.id === page.id in this app
```

### Run command
```bash
E2E_WEB_URL=http://127.0.0.1:3000 pnpm --dir tests/e2e test \
  specs/29-sai01-career-ai.spec.ts \
  specs/30-sai02-page-intelligence.spec.ts \
  specs/31-sai03-inbox-triage.spec.ts \
  specs/32-sai04-context7-mcp.spec.ts 2>&1
```

### Audit doc template

```markdown
# Phase 15A — AI Feature Audit

| ID | Scenario | Step | Severity | Symptom | Root Cause Hypothesis |
|---|---|---|---|---|---|
| SAI01-BUG-001 | Career AI | Generate bullets | P1 | 0 bullets returned | Project PATCH not reflected before generate call |
...
```

**Codex task boundary (15A):**
1. First implement SSE fix in `services/api/app/mcp_client/client.py` and `mcp_connections.py`. Run `uv run ruff check services/api` to verify.
2. Study reference files: `tests/e2e/specs/25-s02-freelance-engineer.spec.ts`, `tests/e2e/specs/15-inbox.spec.ts`, `apps/web/src/components/projects/ResumeBulletsPanel.tsx`, `apps/web/src/components/projects/InterviewStoryPanel.tsx`, `apps/web/src/components/editor/AiPanel*.tsx`, `apps/web/src/components/inbox/TriageModal.tsx`, `apps/web/src/app/(app)/app/settings/mcp/page.tsx`.
3. Write specs 29–32. Run them. Write AUDIT-15A.md.
4. Return: SSE fix summary + audit table + pass/fail per spec + full file paths.

---

## Track 15B — Bug Fix Sprint

One Codex task per P0/P1 bug from the audit. Claude writes each brief.

### Brief template

```
Bug: SAI0X-BUG-NNN — {symptom}
Affected files: {list from hypothesis}
Reproduce: E2E_WEB_URL=http://127.0.0.1:3000 pnpm --dir tests/e2e test --grep "@sai0X"
Fix: {bounded instruction}
Acceptance: spec @sai0X exits green; no regressions in other specs
Do NOT touch: other scenario specs, API schemas, migrations
Gates: pnpm typecheck · pnpm lint · ruff check services/api
```

---

## Track 15C — Regression Pass

```bash
E2E_WEB_URL=http://127.0.0.1:3000 pnpm --dir tests/e2e test 2>&1
```

- All 114 existing tests still pass (108 passing + 6 pre-existing skips)
- All 4 new AI scenario specs pass with real AI content in assertions
- `pnpm typecheck` ✅ · `pnpm lint` ✅ · `ruff check services/api` ✅
- Update `PROGRESS.md` before merging to `main`
- Remove worktrees after merge

---

## Files Created / Modified

| Path | Track | Action |
|---|---|---|
| `services/api/app/mcp_client/client.py` | 15A | Modify — SSE transport |
| `services/api/app/api/v1/mcp_connections.py` | 15A | Modify — SSE test-connection |
| `tests/e2e/specs/29-sai01-career-ai.spec.ts` | 15A | Create |
| `tests/e2e/specs/30-sai02-page-intelligence.spec.ts` | 15A | Create |
| `tests/e2e/specs/31-sai03-inbox-triage.spec.ts` | 15A | Create |
| `tests/e2e/specs/32-sai04-context7-mcp.spec.ts` | 15A | Create |
| `tests/e2e/AUDIT-15A.md` | 15A | Create |
| Various bug fix files | 15B | Modify (TBD) |
| `PROGRESS.md` | 15C | Update |

---

## Acceptance Criteria

- [ ] SSE transport implemented in `McpClientSession`; SSE test-connection populates capabilities
- [ ] Specs 29–32 committed in `tests/e2e/specs/`
- [ ] `AUDIT-15A.md` with every test failure classified
- [ ] All P0/P1 bugs fixed and referenced in audit doc
- [ ] All 4 AI specs assert **real generated content** (not graceful-degradation fallbacks)
- [ ] S-AI-04 uses a live Context7 SSE connection and real `enrich-page` call
- [ ] `pnpm --dir tests/e2e test` exits with zero failures across all 118+ specs
- [ ] `pnpm typecheck` ✅ · `pnpm lint` ✅ · `ruff check services/api` ✅
- [ ] `PROGRESS.md` updated before merge
