# Phase 13D — Testing Follow-up & Bug Fix Sprint

**Branch:** `phase-13d-follow-up`  
**Status:** Complete  
**Depends on:** Phase 13 (Frontend Health Check)

---

## Goals

Phase 13 surfaced two real bugs and four areas with insufficient E2E coverage. This phase fixes the bugs and closes the gaps.

---

## Track A — Bug Fixes

### Bug 1: `useShortcut` hook fires on every keydown

**File:** `apps/web/src/lib/hooks/useShortcut.ts`

The `key` parameter was never checked — `handler(e)` fired for every keydown event. Fixed by adding `if (e.key !== key) return;` before the handler call.

### Bug 2: MCP delete used `window.confirm`

**File:** `apps/web/src/app/(app)/app/settings/mcp/page.tsx`

`window.confirm()` blocks the browser event loop, freezes Playwright, and is inaccessible. Replaced with a `deletingId` state that shows inline Cancel / Confirm delete buttons in the connection row.

---

## Track B — Coverage Expansion

| Spec file | New test added | What it covers |
|---|---|---|
| `15-inbox.spec.ts` | Triage modal shows AI summary | Mock `POST /api/v1/ai/triage`, click "Analyze with AI", assert summary text |
| `22-asset-upload.spec.ts` | Asset preview overlay | Upload file, click card, assert `.fixed.inset-0` overlay appears |
| `11-career-project.spec.ts` | Copy Markdown shows toast | Generate+save bullets, expand set, click "Copy Markdown", assert "Copied" toast |
| `16-multi-pane.spec.ts` | Workspace save flow | Open side pane, click "Save workspace", fill name, click Save, assert modal closes |
| `21-shortcut-overlay.spec.ts` | Non-matching Meta key doesn't toggle | Dispatch Meta+A, assert sidebar keeps `w-60` |
| `17-mcp-settings.spec.ts` | Delete inline confirm | Click Delete → inline confirm UI → click Confirm → row removed |

---

## Quality Gates

- `pnpm typecheck` ✅
- `pnpm lint` ✅
- `ruff check` ✅
- `pnpm exec playwright test` — all tests pass (82+ tests)
