# Phase 13: Frontend Health Check & Debug Sprint

## Context

All phases through 12C are complete and on `main`. The frontend has 40+ implemented features across 12 sections, but the existing 12 Playwright specs cover only ~30% of them. Several files also have uncommitted modifications (`layout.tsx`, auth pages, `deps.py`, `main.py`) that need investigation before they are either committed or reverted. This phase systematically verifies that every frontend feature works in a real browser, surfaces bugs, and fixes them — with Codex doing all implementation and Claude orchestrating.

---

## Agent Operating Model

| Agent | Role |
|---|---|
| Claude | Orchestrate, decompose tasks, assign to Codex, review output, gate merges |
| Codex | Write specs, run suites, fix bugs, return handoff notes |

---

## Structure — Three Tracks, Three Worktrees

Each track runs in its own git worktree so work does not collide.

| Track | Branch | Worktree path | Goal |
|---|---|---|---|
| 13A | `phase-13a-playwright-audit` | `~/Documents/akm-phase-13a` | Run all existing specs + produce audit report |
| 13B | `phase-13b-bug-fixes` | `~/Documents/akm-phase-13b` | Fix every bug found in 13A |
| 13C | `phase-13c-coverage` | `~/Documents/akm-phase-13c` | Write new specs for uncovered features |

---

## Track 13A — Playwright Audit

**Goal:** Get a precise pass/fail + screenshot inventory for every existing spec, investigate uncommitted modifications, and output a structured bug list.

### Subtasks

- [ ] **13A-0** — Branch + worktree setup; PROGRESS.md tracking started
- [ ] **13A-1** — Run full suite (`pnpm test:e2e`) against local Docker stack; collect HTML report + failure traces
- [ ] **13A-2** — Investigate uncommitted modifications and decide commit vs revert:
  - `apps/web/src/app/(app)/layout.tsx`
  - `apps/web/src/app/(auth)/forgot-password/page.tsx`
  - `apps/web/src/app/(auth)/login/page.tsx`
  - `apps/web/src/app/(auth)/register/page.tsx`
  - `apps/web/src/components/layout/Sidebar.tsx`
  - `services/api/app/core/deps.py`
  - `services/api/app/main.py`
  - `docs/SECURITY.md`
- [ ] **13A-3** — Codex writes a route-crawl spec that visits every major route and asserts no JS crashes / console errors:
  - `/app`, `/app/pages`, `/app/pages/[id]`, `/app/assets`, `/app/sources`, `/app/sources/[id]`
  - `/app/chats`, `/app/chats/[id]`, `/app/projects`, `/app/projects/[id]`
  - `/app/inbox`, `/app/trash`, `/app/settings/mcp`
  - `/login`, `/register`, `/forgot-password`
- [ ] **13A-4** — Codex writes a feature smoke spec checking render-only (no full interaction) for: slash menu, bubble menu, AI panel tabs, multi-pane add/close, tutorial overlay, shortcut overlay (`?` key), bulk action bar, search filters, workspace-scoped search checkbox, Enrich with Docs input
- [ ] **13A-5** — Produce `tests/e2e/AUDIT-13A.md`: table of every feature → status (✅ pass / ❌ fail / ⚠️ partial), error, screenshot path

**Codex task boundary:** Run suite, write the smoke scripts (13A-3 & 13A-4), commit audit doc. Return: audit table + ordered bug list with reproduction steps.

**Verification:** HTML report accessible; audit doc committed; every spec either passes or carries a bug ID.

---

## Track 13B — Bug Fix Sprint

**Goal:** One bounded Codex task per bug. Claude gates each fix before it lands.

### Process per bug

1. Claude reads the 13A bug entry (route, error message, screenshot).
2. Claude writes a Codex task: affected files, expected vs actual behavior, acceptance test.
3. Codex fixes, runs `playwright test --grep <pattern>`, returns diff + result.
4. Claude reviews: architecture compliance, no new regressions, quality gates pass.
5. Cherry-pick to `phase-13b-bug-fixes`.

### Expected bug categories (refined after 13A)

- [ ] **13B-1** — Auth page redirect correctness (login/register)
- [ ] **13B-2** — Sidebar modified-state: confirm changes are correct and lint-clean
- [ ] **13B-3** — API `deps.py` / `main.py`: verify startup health, `ruff check` clean
- [ ] **13B-4** — MCP Settings page: connection list, Add modal, Test button
- [ ] **13B-5** — Inbox bulk triage: select → bulk button fires → toast → items updated
- [ ] **13B-6** — Multi-pane: open 2nd/3rd/4th pane, close pane, cross-pane link modal
- [ ] **13B-7** — Slash menu (`NEXT_PUBLIC_UX_EDITOR_V2=1`): `/` → menu appears, arrow nav, AI commands present
- [ ] **13B-8** — Bubble menu: select text → bold/italic/code toolbar appears
- [ ] **13B-9** — Projects AI generators: Resume Bullets generate → preview → save; Interview Story generate → save → copy
- [ ] **13B-10** — AI Panel "Enrich with Docs": input + button visible, success message renders
- [ ] **13B-11** — AI Panel "Ask KB": web search toggle present, `web_citations` section renders
- [ ] **13B-12** — Search workspace-scoped filter: checkbox only visible when pane is open
- [ ] **13B-13** — Shortcut overlay: `?` → overlay opens, Esc closes
- [ ] **13B-14** — Asset upload: drag-and-drop zone accepts file, card appears in grid
- [ ] **13B-15** — Tutorial Replay Tour: button state correct, overlay renders, localStorage flag set

**Quality gates per fix:** `pnpm typecheck` ✅ · `pnpm lint` ✅ · `ruff check` ✅ · targeted spec green ✅

---

## Track 13C — Coverage Expansion

**Goal:** ≥ 8 new spec files covering uncovered features, bringing total E2E test count to ≥ 47.

### New spec files

| File | Features covered |
|---|---|
| `13-inbox.spec.ts` | Inbox list, per-item triage modal, bulk select + bulk triage |
| `14-multi-pane.spec.ts` | 2–4 panes, workspace save/load/delete, cross-pane link modal |
| `15-mcp-settings.spec.ts` | Add connection, test connection (mock subprocess), delete |
| `16-career-ai.spec.ts` | Resume bullets generate+save+copy, interview story generate+save+copy |
| `17-editor-ux.spec.ts` | Slash menu (V2 flag), bubble menu on selection, toolbar bold/cite |
| `18-ai-panel-advanced.spec.ts` | Extract claims, extract tasks, suggest links+create, Ask KB, Enrich Docs |
| `19-shortcut-overlay.spec.ts` | `?` key overlay, Esc close, sidebar toggle via ⌘\ |
| `20-asset-upload.spec.ts` | File drop, grid card appears, preview modal opens |

### Subtasks

- [ ] **13C-0** — Branch + worktree setup; cherry-pick fixes from 13B
- [ ] **13C-1** — Codex writes specs 13–17 (one file per Codex invocation)
- [ ] **13C-2** — Codex writes specs 18–20
- [ ] **13C-3** — Full suite run (`pnpm test:e2e`); fix any flaky assertions
- [ ] **13C-4** — Update `tests/e2e/README.md` with new spec inventory
- [ ] **13C-5** — Update `docs/A11Y.md` and `docs/UX_GUIDE.md` with gaps found
- [ ] **13C-6** — PROGRESS.md Phase 13 section complete; PR to main

**Verification:** `pnpm test:e2e` → all specs pass; `pnpm typecheck` + `pnpm lint` + `ruff check` clean; PROGRESS.md updated with final test count.

---

## Existing E2E Coverage Map

| Spec | Features covered |
|---|---|
| 01-auth | Redirect behavior, /me API |
| 02-page-crud | Create, edit, autosave, reload |
| 03-search | Cmd+K, keyword results, navigate |
| 04-source-ingestion | URL ingest, status polling |
| 05-graph-edges | Backlink create, RelatedPanel |
| 06-ai-summarize | Summarize button, audit row |
| 07-workspace-side-pane | Open in side pane from search |
| 08-chat-import | File import, paste import |
| 09-trash-restore | Soft-delete, restore |
| 10-mcp-read | stdio tools/list |
| 11-career-project | Create project, link evidence |
| 12-tutorial | Seed, tour steps, Esc, localStorage |

**Uncovered:** Inbox triage, multi-pane save/load, MCP settings UI, resume/interview AI generators, slash menu, bubble menu, shortcut overlay, asset upload, AI panel advanced (claims/tasks/links/enrich), workspace search filter.

---

## Acceptance Criteria for Phase 13 Complete

- All 12 existing specs pass (zero regressions)
- ≥ 8 new spec files written and passing
- Every 13A bug either fixed with a test or documented as a known issue
- `pnpm test:e2e` green on a clean Docker stack
- `pnpm typecheck` + `pnpm lint` + `ruff check` + `ruff format --check` all clean
- `PROGRESS.md` Phase 13 section complete with final test totals
- `project-phases/PHASE-13-FRONTEND-HEALTH-CHECK.md` committed to main
