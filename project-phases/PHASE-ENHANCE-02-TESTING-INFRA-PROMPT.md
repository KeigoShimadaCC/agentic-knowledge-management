# Prompt — Build the KnowledgeOS Testing Infrastructure

> **For:** A coding agent (Codex, Claude Code, Cursor) running against this repo.
> **Goal:** Add Vitest unit/component tests for the frontend, fill backend test gaps, and stand up Playwright E2E covering full-stack golden paths. Do not regress the existing 147+ tests.
> **Audit basis:** This prompt assumes the repo state as of the 2026-05-15 audit recorded in `PROGRESS.md`. The relevant gaps are also tracked in `project-phases/PHASE-FIX-01` (F4 worker tests) and `PHASE-FIX-03` (F19 E2E smoke).

Paste this entire document into the agent session. Do not summarize it for the agent — the explicit constraints matter.

---

## 1. Your role and what this repo is

You are a senior test engineer pair-programming on **KnowledgeOS**, a local-first personal AI knowledge OS. The architecture lives in `CLAUDE.md`, `AGENTS.md`, `README.md`, and `docs/ARCHITECTURE.md`. You must read those four files first.

Key facts (do not assume otherwise):

- **Monorepo:** `apps/web` (Next.js 14 + React 18 + Tailwind + Tiptap), `services/api` (FastAPI + SQLAlchemy 2.0 async + Alembic), `services/worker` (RQ + sync SQLAlchemy), `services/mcp` (stdio MCP server).
- **Infra:** `docker compose -f infra/docker-compose.yml up -d` brings up Postgres 16, Redis 7, Qdrant, the API (host `127.0.0.1:8001`, in-container `:8000`), and the web app (`127.0.0.1:3000`). The Postgres host port is `5433`, in-container `5432`.
- **Primary source of truth:** Postgres + the local filesystem under `~/KnowledgeOS/library/`. Qdrant and Kùzu are re-buildable indexes.
- **Soft-delete only.** Every user-owned table uses `deleted_at`. **Tests must not hard-delete.**
- **Audit invariant.** Every agent write produces an `agent_runs` row; every mutation of an existing object also produces an `object_revisions` row. Tests must assert this when exercising AI / MCP write paths.

## 2. Current testing state (do not duplicate, do not break)

| Layer | What exists | Where | Count |
|---|---|---|---|
| Backend integration | pytest-asyncio + httpx ASGITransport against real Postgres `knowledgeos_test` (auto-created per test) | `tests/api/test_*.py` | 112 |
| Backend unit | Pure-function tests (parsers, URL safety, structured chat) | `tests/unit/test_*.py` | 16 |
| MCP package | mocked `KosApiClient`, registry/dispatch tests | `services/mcp/tests/test_*.py` | 19 |
| Worker | **none** | `tests/worker/` does not exist | 0 |
| Frontend unit / component | **none** | no test runner installed | 0 |
| E2E | **none** | `tests/e2e/.gitkeep` only | 0 |

Ship target after this work: **~210+ tests** (147 today + frontend unit/component + worker + E2E).

## 3. Mission

Deliver, in this order:

1. **Frontend unit + component tests with Vitest** (no E2E yet).
2. **Worker extractor unit tests under `tests/worker/`** (closes `PHASE-FIX-01` F4).
3. **Playwright E2E suite under `tests/e2e/`** covering ~10 golden paths.
4. **A single `pnpm test:all` / `make test` entry point** that runs everything sensibly and a CI workflow file under `.github/workflows/` that runs the same on push.

Land each in its own PR. Do **not** combine.

## 4. Hard constraints

- **Do not mock the database in integration tests.** The pattern in `tests/api/conftest.py` (real test Postgres, auto-created/torn-down) is the standard. Match it for any new backend tests you add.
- **Do not introduce Jest.** Use Vitest. Reason: Vitest is Vite-native, ESM-first, ~3× faster than Jest with this codebase, and matches Next 14's bundler ergonomics.
- **Do not introduce Cypress.** Use Playwright. Reason: it is what the user asked for, it has first-class TypeScript and request-fixtures, and it can drive both browser and API tests from one runner.
- **Do not commit recorded fixtures larger than 200 KB.** Generate fixtures programmatically in `conftest.py` / `setup.ts` instead.
- **Do not mock OpenAI by patching individual call sites.** Reuse the existing pattern in `tests/api/test_ai.py` (patch `openai.AsyncOpenAI` once via fixture).
- **Do not skip a test with `xfail` / `.skip` / `test.skip` without an inline TODO comment that names the issue / blocker.**
- **Do not lower the existing test count.** If you delete a test, you must replace it with at least one that covers the same path.
- **Do not introduce snapshot tests for component output.** They produce churn without signal in this codebase. Assert on roles, text, and behavior instead.
- **Do not test private internals.** If a hook or service is exported, test it through its public surface.
- **Do not run E2E against a shared `~/KnowledgeOS/` directory.** The E2E stack must use a sandbox `LIBRARY_ROOT` under `tests/e2e/.tmp/`.
- **Do not add network-dependent tests** (no real `youtube.com`, no real OpenAI). Mock external HTTP with `respx` / `pytest-httpx` (Python) or Playwright's `route()` (browser) or MSW (web unit tests).

## 5. Stack you will install

### Frontend (`apps/web/`)

```jsonc
{
  "devDependencies": {
    "vitest": "^2",
    "@vitest/coverage-v8": "^2",
    "@vitejs/plugin-react": "^4",
    "jsdom": "^25",
    "@testing-library/react": "^16",
    "@testing-library/jest-dom": "^6",
    "@testing-library/user-event": "^14",
    "msw": "^2"
  }
}
```

Configure via `apps/web/vitest.config.ts` (do **not** reuse Next's webpack config — Vitest uses its own Vite pipeline). Use `jsdom` environment. Set `setupFiles: ["./vitest.setup.ts"]` which imports `@testing-library/jest-dom/vitest` and starts the MSW worker.

### Backend (`services/api/`, `services/worker/`)

Already on pytest. Add only:

```toml
# services/worker/pyproject.toml [dependency-groups.dev] (or top-level dev)
respx = ">=0.21"        # for httpx mocking in worker tests
pytest = ">=8"
pytest-asyncio = ">=0.23"
reportlab = ">=4.0"     # generate PDFs in worker fixtures
```

### E2E (`tests/e2e/`)

```jsonc
// new tests/e2e/package.json
{
  "name": "knowledgeos-e2e",
  "private": true,
  "devDependencies": {
    "@playwright/test": "^1.48",
    "typescript": "^5"
  },
  "scripts": {
    "test": "playwright test",
    "test:headed": "playwright test --headed",
    "report": "playwright show-report"
  }
}
```

Browsers installed via `pnpm exec playwright install --with-deps chromium`. Start with Chromium only; add Firefox/WebKit later if needed.

## 6. Phased plan with deliverables

Each phase below = one PR. Do not move to phase N+1 until phase N is merged.

---

### Phase T1 — Vitest scaffold + first 5 frontend unit tests

**Files to create:**

- `apps/web/vitest.config.ts`
- `apps/web/vitest.setup.ts`
- `apps/web/src/test/msw/handlers.ts`           — default MSW handlers for `/api/v1/*`
- `apps/web/src/test/msw/server.ts`             — node MSW server for unit tests
- `apps/web/src/test/render.tsx`                — `renderWithProviders` helper (SWR config, WorkspaceLiteProvider, etc.)
- `apps/web/src/lib/__tests__/api.test.ts`      — covers `apiFetch`, error mapping, cookie handling
- `apps/web/src/lib/__tests__/objectRouting.test.ts` — covers all `objectRoute(kind, id)` branches
- `apps/web/src/lib/hooks/__tests__/useAuth.test.tsx` — login → user populated → logout → user cleared
- `apps/web/src/lib/hooks/__tests__/useSearch.test.tsx` — debounced query, pagination, empty state
- `apps/web/src/lib/hooks/__tests__/useAutoSave.test.tsx` — 800ms debounce, race condition (two rapid edits → one save)

**Files to modify:**

- `apps/web/package.json` — add `"test": "vitest"`, `"test:run": "vitest run"`, `"test:coverage": "vitest run --coverage"`
- `apps/web/tsconfig.json` — add `"types": ["vitest/globals", "@testing-library/jest-dom"]`
- root `package.json` — add `"test:web": "pnpm -F web test:run"`
- `.gitignore` — add `apps/web/coverage/`

**Acceptance:**

- `pnpm -F web test:run` exits 0.
- All 5 tests run in <2s on a developer Mac.
- `pnpm -F web test:coverage` reports >70% on the files touched.
- Coverage report is HTML at `apps/web/coverage/index.html`.

**Commit:** `test(web): vitest scaffold with msw and first lib/hook coverage`

---

### Phase T2 — Frontend component tests for the high-value surface

**Files to create:**

- `apps/web/src/components/search/__tests__/SearchModal.test.tsx`
  - Cmd+K opens it, Esc closes it, typing debounces to one HTTP call, result selection navigates, "open in side pane" calls workspace context.
- `apps/web/src/components/graph/__tests__/GraphPanel.test.tsx`
  - Tabs switch (Backlinks/Related/AI), backlinks list renders, empty state renders.
- `apps/web/src/components/ai/__tests__/AiPanel.test.tsx`
  - Summarize button → loading → result; AI-disabled state when 503.
- `apps/web/src/components/inbox/__tests__/TriageModal.test.tsx`
  - Suggested tags toggle, title editable, Apply button calls `PATCH /objects/{id}` exactly once.
- `apps/web/src/components/workspace/__tests__/WorkspaceLiteProvider.test.tsx`
  - `openSidePane` then `closeSidePane`; `Escape` key closes pane; pane survives a re-render.
- `apps/web/src/components/editor/__tests__/Editor.test.tsx`
  - Mount Tiptap with empty doc; type a heading; word count updates; **autosave fires once after 800ms** of idle.
- `apps/web/src/components/assets/__tests__/AssetUploader.test.tsx`
  - Drag-and-drop a 1KB blob → POST `/api/v1/assets/upload` once → progress event handled.

**Mocking rules for component tests:**

- HTTP: MSW handlers — never mock `fetch` directly with `vi.fn()`.
- Routing: use `next/navigation` mocks via `vi.mock('next/navigation', ...)` to capture `router.push` calls.
- Tiptap: do not stub the editor; mount it for real against jsdom. It works.
- Auth context: helper `renderWithProviders({ user: { id, email, ... } })` to bypass `/api/v1/auth/me`.

**Acceptance:**

- All 7 component tests pass.
- `pnpm -F web test:run` total runtime <15s.
- No test imports a private (underscore-prefixed) function.
- Total frontend test count ≥ 25 after T1 + T2.

**Commit:** `test(web): component tests for search, graph, ai, inbox, workspace, editor, uploader`

---

### Phase T3 — Worker extractor unit tests (closes `PHASE-FIX-01` F4)

**Files to create:**

- `tests/worker/conftest.py` — generates fixtures programmatically:
  - PDF via `reportlab`: 2 pages, known text, 100KB max.
  - PNG via Pillow: 100×60 solid color.
  - CSV via stdlib `csv`: 5 rows × 3 columns.
  - Mocked YouTube oEmbed + transcript responses.
  - Mocked HTML article (BeautifulSoup happy + edge cases).
- `tests/worker/test_pdf_extractor.py` — text extraction; page count; thumbnail file written; corrupt PDF → graceful error.
- `tests/worker/test_image_extractor.py` — width/height; thumbnail size; EXIF stripping; non-image bytes → error.
- `tests/worker/test_csv_extractor.py` — preview JSON shape; quoting; UTF-8 BOM; empty file.
- `tests/worker/test_youtube_extractor.py` — happy path with mocked oEmbed + transcript; missing transcript → empty text + flag.
- `tests/worker/test_web_extractor.py` — happy path; redirect; non-200; non-HTML content-type rejected.
- `tests/worker/test_url_safety.py` — extends existing `tests/unit/test_url_safety.py` checks if not already worker-side.

**Files to modify:**

- `tests/pyproject.toml` — register `worker/` in test discovery if not auto-discovered.
- `services/worker/pyproject.toml` — add `reportlab`, `respx` dev deps.

**Acceptance:**

- `cd tests && uv run pytest worker/ -v` passes — minimum 15 new tests.
- No test hits a real network host (verify with `respx` no-unmatched-routes assertion).
- All extractors covered for happy + at least one error path.

**Commit:** `test(worker): unit coverage for pdf, image, csv, youtube, web extractors`

---

### Phase T4 — Playwright scaffold + first 3 E2E golden paths

**Files to create:**

- `tests/e2e/package.json` (see Section 5).
- `tests/e2e/playwright.config.ts`:
  - `baseURL: "http://localhost:3000"`.
  - `webServer` block that **does not** auto-start the stack — assume `docker compose up -d` was run by the developer or CI step.
  - `use: { trace: "retain-on-failure", screenshot: "only-on-failure", video: "retain-on-failure" }`.
  - Workers: 1 locally, 2 in CI (Postgres can't take more than light parallelism on a single dev DB).
- `tests/e2e/fixtures/test-user.ts` — helper that creates a fresh user via the API for each test, returns the cookie.
- `tests/e2e/fixtures/api.ts` — Playwright `request` fixture preconfigured with the test user's cookie.
- `tests/e2e/specs/01-auth.spec.ts`           — register, log in, log out via the UI; assert `/auth/me` matches.
- `tests/e2e/specs/02-page-crud.spec.ts`      — create page, edit title, type content, autosave, reload, content persists.
- `tests/e2e/specs/03-search.spec.ts`         — create 3 pages with distinct keywords, open Cmd+K, search, click result, lands on `/pages/{id}`.

**Test data isolation:**

- Each test creates a user with a UUID-suffixed email so no two parallel tests collide.
- After the test, soft-delete the user's objects via API (no manual DB cleanup; honor soft-delete invariant).
- Sandbox `LIBRARY_ROOT` for E2E by setting `LIBRARY_ROOT=$PWD/tests/e2e/.tmp/library` in the dev shell before running. **Do not** point E2E at the user's real `~/KnowledgeOS/`.

**Files to modify:**

- root `package.json` — add `"test:e2e": "pnpm --dir tests/e2e test"`.
- `pnpm-workspace.yaml` — add `tests/e2e` as a workspace member.
- `.gitignore` — add `tests/e2e/playwright-report/`, `tests/e2e/test-results/`, `tests/e2e/.tmp/`.
- `README.md` — new "End-to-end tests" subsection under Development.

**Acceptance:**

- `docker compose -f infra/docker-compose.yml up -d` then `pnpm test:e2e` exits 0.
- All 3 specs pass on a clean local stack.
- Playwright HTML report accessible via `pnpm --dir tests/e2e report`.

**Commit:** `test(e2e): playwright scaffold with auth, page-crud, search golden paths`

---

### Phase T5 — Playwright E2E for ingestion + AI + workspace + MCP

**Files to create:**

- `tests/e2e/specs/04-source-ingestion.spec.ts` — create a CSV source via UI, poll `/sources/{id}` until `ingestion_status=success`, assert preview rows render. **Requires `PHASE-FIX-01` F2 (worker container) to be running.**
- `tests/e2e/specs/05-graph-edges.spec.ts` — create page A and page B, link A→B via "Link to..." modal, open page B, assert backlink to A appears.
- `tests/e2e/specs/06-ai-summarize.spec.ts` — create a page with content, open AI panel, click Summarize. **Set `OPENAI_API_KEY=sk-test-stub`** + intercept the OpenAI HTTP call with Playwright `route()` to return a canned response. Assert summary renders and `agent_runs` row exists (queried via API).
- `tests/e2e/specs/07-workspace-side-pane.spec.ts` — open page A, search for page B, click "open in side pane", assert side pane shows B without navigating away.
- `tests/e2e/specs/08-chat-import.spec.ts` — paste a Claude-format markdown export into the import modal, assert chat object created with parsed turns.
- `tests/e2e/specs/09-trash-restore.spec.ts` — soft-delete a page via API, assert it appears in `GET /objects/trash`, restore via API, assert it disappears from trash. (Pure API spec via Playwright `request`; no browser.)
- `tests/e2e/specs/10-mcp-read.spec.ts` — start `kos-mcp` as a subprocess in the test, send `tools/list` over stdio, assert the read tool list. Use `child_process.spawn` directly; this is a Playwright test only because it runs in the same harness.

**Acceptance:**

- All 7 new specs pass.
- Total E2E count = 10 (the limit; do **not** add more in this phase).
- No spec runs longer than 30 seconds individually; suite under 4 minutes total.
- Each spec produces a Playwright trace on failure that can be opened with `pnpm exec playwright show-trace`.

**Commit:** `test(e2e): ingestion, graph, ai, workspace, chat-import, trash, mcp golden paths`

---

### Phase T6 — Single test entry point + CI workflow

**Files to create:**

- `Makefile` (or `scripts/test.sh`) with targets:
  - `test-unit`         → `pnpm -F web test:run`
  - `test-api`          → `cd tests && uv run pytest api/ unit/ -q`
  - `test-worker`       → `cd tests && uv run pytest worker/ -q`
  - `test-mcp`          → `cd services/mcp && uv run pytest tests/ -q`
  - `test-e2e`          → `pnpm test:e2e`
  - `test-all`          → all of the above, in this order
- `.github/workflows/ci.yml`:
  - Triggers: push to any branch, pull_request to main.
  - Jobs:
    - `lint-and-typecheck`: pnpm install, pnpm lint, pnpm typecheck, ruff check, ruff format --check.
    - `backend`: spin up Postgres + Redis service containers, run `make test-api test-worker test-mcp`.
    - `frontend`: pnpm install, `make test-unit`.
    - `e2e`: depends on backend + frontend; spin up full docker compose, install Playwright browsers (`pnpm exec playwright install chromium --with-deps`), run `make test-e2e`. Upload Playwright report as artifact on failure.
  - Cache: pnpm store, uv cache, Playwright browsers.
- `tests/e2e/README.md` — how to run locally, how to debug failures, where reports go.

**Files to modify:**

- root `package.json` — add `"test:all": "make test-all"` for non-make users.
- `README.md` — add a "Testing" section with a table mapping layer → command.
- `PROGRESS.md` — note testing infra in the "Current repo state notes" block.

**Acceptance:**

- `make test-all` exits 0 on a clean local stack.
- A PR opened against main triggers all four CI jobs and they all pass.
- A deliberately broken commit fails CI within 5 minutes.

**Commit:** `ci: unified test runner and github actions workflow for unit/integration/e2e`

---

## 7. Test design principles you must follow

1. **One assertion per behavior, not per call.** If a test verifies "create page returns 201", that's one test. If it also verifies the response body shape, that's a second test, separately named.
2. **Test names describe behavior, not implementation.** `test_create_page_returns_201` ❌ → `test_create_page_persists_and_returns_object` ✅.
3. **Arrange / Act / Assert blocks separated by blank lines.** No single-line tests with multiple actions.
4. **Backend integration tests use a real test DB.** No SQLAlchemy mocks, no in-memory SQLite. Match the existing `conftest.py` pattern.
5. **Frontend component tests assert on roles and text.** `screen.getByRole("button", { name: /save/i })` ✅ → `container.querySelector(".btn-save")` ❌.
6. **Async UI: use `findBy*` not `waitFor` + `getBy*`.** Cleaner and built-in.
7. **E2E tests are golden paths, not unit tests in disguise.** If a path can be tested at the integration layer cheaper, do it there.
8. **No conditional assertions.** `if (foo) expect(...)` is a code smell. Test both branches separately.
9. **Failure messages must be actionable.** Custom `expect.toMatchObject({...}, "audit row should include tool_name")` over bare `.toBe()`.
10. **Flaky tests get fixed or deleted within 24 hours.** Never `retries: 3` to paper over flake.

## 8. Things you must explicitly NOT do

- Do not edit `services/api/app/**/*.py` to make a test pass. If the SUT needs a change, ask first.
- Do not add fixtures larger than 200 KB to git. Generate them in `conftest.py`.
- Do not record real OpenAI responses. Mock them.
- Do not test against the developer's `~/KnowledgeOS/` directory. Use a sandbox.
- Do not add a global `beforeEach` that resets the DB. The test fixtures already isolate per-test.
- Do not ship a `vi.mock(...)` of a hook that you didn't write. Refactor the consumer to take a prop instead.
- Do not introduce `@ts-expect-error` or `as any` to silence test typing issues.
- Do not run E2E tests in parallel with `workers > 2`. Postgres test DB cannot handle it.

## 9. Verification commands the user will run after each PR

After T1: `pnpm -F web test:run` → 0 failures, ≥5 new tests.
After T2: `pnpm -F web test:run` → 0 failures, ≥12 new tests cumulative.
After T3: `cd tests && uv run pytest worker/ -v` → 0 failures, ≥15 tests.
After T4: `pnpm test:e2e` → 0 failures, 3 specs.
After T5: `pnpm test:e2e` → 0 failures, 10 specs, suite <4 min.
After T6: `make test-all` → all green; CI green on a fresh PR.

## 10. Reporting

At the end of each PR, post in the PR description:

1. **Test count delta** — e.g. "frontend: 0 → 12, backend: +15 worker tests".
2. **Coverage delta** — e.g. "apps/web/src/lib coverage 0% → 84%".
3. **Suite runtime** — e.g. "vitest 1.4s, pytest +2s, total CI 6m12s".
4. **Any test that took >5s** — with a one-line reason and a follow-up TODO.
5. **Any constraint in Section 8 you bent** — with justification. Do not silently bend constraints.

## 11. When you are unsure

- **Frontend tooling decisions** (Vitest plugins, MSW v2 setup, jsdom polyfills): make a reasonable call, document in commit message, move on.
- **Backend invariants** (audit-row shape, soft-delete, schema migrations): **stop and ask.** These are load-bearing and a wrong call is expensive.
- **E2E flakiness root causes** (timing, DB collisions, container readiness): **stop and ask** before adding retries.

---

## 12. Definition of Done (full project)

- [ ] T1 merged: Vitest scaffold + 5 lib/hook tests
- [ ] T2 merged: 7 component tests for search, graph, AI, inbox, workspace, editor, uploader
- [ ] T3 merged: 15+ worker extractor tests
- [ ] T4 merged: Playwright scaffold + 3 E2E specs (auth, page-crud, search)
- [ ] T5 merged: 7 more E2E specs (ingestion, graph, AI, workspace, chat, trash, MCP)
- [ ] T6 merged: `make test-all` + GitHub Actions CI
- [ ] Total tests ≥ 210 (147 today + ≥63 new)
- [ ] CI runs end-to-end on every PR
- [ ] No flaky test in the suite (3 consecutive green runs on main after T6)
- [ ] `README.md` has a "Testing" section
- [ ] `PROGRESS.md` reflects the new infra

When all boxes are checked, this prompt is complete. Stop. Do not auto-add Phase T7.
