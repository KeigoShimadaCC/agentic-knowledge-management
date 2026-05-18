# PHASE-FIX-05 — Next.js 15 Migration (follow-up)

> **Type:** Forward-looking migration plan (filed during PHASE-FIX-04 / S9)
> **Status:** Not scheduled. Pick up any time after PHASE-FIX-04 lands.
> **Trigger:** Remaining pnpm-audit advisories that require Next 15+ (see PHASE-FIX-04 commit `chore(web): bump next 14.2.3 -> 14.2.35`: 5 high, 8 moderate, 2 low advisories were still open against the 14.2.x line).
> **Out of scope:** Anything outside the Next + React upgrade path (e.g., Tailwind 4, Radix major bumps) — those are separate phases.

---

## Context

PHASE-FIX-04 closed the critical Next.js middleware-bypass CVE with a within-major patch (`14.2.3 → 14.2.35`). That brought the advisory count down from 27 to 15, but the remaining 5 highs and 8 moderates are only patched in Next ≥ 15. The 14.2.x line is the right place to *stay* for a security-only phase; a major upgrade introduces breaking changes that deserve their own scope.

This file captures what that migration looks like so a future agent (or human) can pick it up without re-deriving the landscape.

---

## Migration scope

| Layer | Change |
|---|---|
| `next` | `^14.2.35` → `^15.x` (pick the latest 15.x patch at pickup time) |
| `react` / `react-dom` | `^18.3.1` → `^19.x` (Next 15 requires React 19) |
| `eslint-config-next` | Track the chosen Next 15.x |
| `@types/react` / `@types/react-dom` | Bump to React 19 types |
| Other `react-*` deps (`@tiptap/react`, `react-resizable-panels`, `next-themes`, `sonner`, `swr`, etc.) | Verify each supports React 19; bump where needed |

---

## Known breaking changes to handle

1. **Async request APIs.** `cookies()`, `headers()`, `params`, and `searchParams` become async in Next 15. Every route handler / page that consumes them needs `await`. Use the official codemod: `npx @next/codemod@latest next-async-request-api .` Then audit each call site — codemods cover the common cases but miss conditional access.
2. **`fetch()` caching default flipped.** Server `fetch` is no longer cached by default. Search the repo for server-side `fetch(` calls and decide explicitly: `cache: "force-cache"` for static data, default (no-store) for fresh data. The dashboard's data-fetch hooks are the place to focus.
3. **GET route handlers no longer cached by default.** Same flip — every `app/api/*/route.ts` with a GET handler that returns identical data per request should opt into caching explicitly.
4. **React 19 migration.** Run `npx types-react-codemod@latest preset-19 .`. Audit `ref` handling — React 19 changes `forwardRef` semantics. Watch for `useFormState` / `useFormStatus` renames.
5. **Removed deprecations.** Next 15 drops several Next 13-era APIs. Build will tell you.

---

## Suggested execution order

1. Branch off `main`. Bump `next` and `react`/`react-dom` together in `apps/web/package.json`. `pnpm install`.
2. Run `npx @next/codemod@latest next-async-request-api .` — review each diff.
3. Run `npx types-react-codemod@latest preset-19 .` — review each diff.
4. `pnpm typecheck` — fix surfacing type errors.
5. `pnpm lint` — fix any new ESLint rule failures.
6. `pnpm build` — fix any runtime/build errors that the typecheck missed.
7. Manual browser smoke: dashboard, page editor, search, MCP settings, login/register flows.
8. `pnpm audit --prod --audit-level=high` — confirm remaining 5 highs are closed.
9. Flip the `security-audit` CI job from `continue-on-error: true` to `continue-on-error: false` (see `.github/workflows/ci.yml`).

---

## Verification

- `pnpm typecheck`, `pnpm lint`, `pnpm build` all green.
- `pnpm audit --prod --audit-level=high` returns zero advisories of high or critical severity.
- Browser smoke covers every route family: dashboard, pages, projects, chats, sources, assets, settings, MCP, auth.
- CI `security-audit` job runs without `continue-on-error`.

---

## Commit suggestion

`chore(web): migrate next 14.2.x -> 15.x + react 18 -> 19`
