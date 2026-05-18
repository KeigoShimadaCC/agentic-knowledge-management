# Phase Enhance 03 — UX/UI Polish & Design System (Safe-by-Default)

> **Status:** Plan
> **Owner:** Frontend
> **Audience:** AI coder (Codex / Claude). Read end-to-end before writing code.
> **Estimated effort:** 6 small, independently revertible PRs over ~2 weeks.
> **Design principle:** Every PR is **strictly additive first**. We never delete or rename a public component, file path, prop, behavior, route, env var, keyboard shortcut, or `data-testid` until at least one release after a replacement has shipped behind a feature flag.

---

## 0. Why this rewrite exists

The previous draft of this plan was correct in *what* to build but too aggressive in *how*. It risked colliding with two live worktrees (`PHASE-7B-MCP-WRITE`, `PHASE-ENHANCE-02-TESTING-INFRA`), with the existing 147 tests, and with the user's daily workflow. This rewrite keeps the same vision but reorders and re-scopes the work so that:

- Every PR can be merged or reverted without breaking the next.
- No file paths or component public APIs change.
- No backend, MCP, or worker code is touched.
- The frontend keeps working identically for any user who never opts into the new affordances.
- Phase ENHANCE-02's component test plan continues to pass against the components it explicitly names.

If a tradeoff appears between "looks great" and "guaranteed not to break anything," **always choose not to break anything**. We can polish in a follow-up; we cannot un-break a regression.

---

## 1. Non-breakage contract (read first)

These constraints are absolute. Every PR description must explicitly call out which contract item it touches and how it preserves it.

### 1.1 Files and paths that may not be moved or renamed

The following file paths must continue to exist and export the same default/named symbols. They are referenced by tests that PHASE-ENHANCE-02 will write (see Section 2 of `PHASE-ENHANCE-02-TESTING-INFRA-PROMPT.md`):

| Path | What must remain |
|---|---|
| `apps/web/src/components/search/SearchModal.tsx` | Component must mount on `Cmd+K`, render input, debounce queries, navigate on result click, expose "open in side pane" affordance. |
| `apps/web/src/components/graph/GraphPanel.tsx` | Three tabs: Backlinks, Related, AI. Tab text exactly as today (English, capitalized except "AI"). |
| `apps/web/src/components/ai/AiPanel.tsx` | "Summarize" button text, async loading → result flow, AI-disabled (503) handling. |
| `apps/web/src/components/inbox/TriageModal.tsx` | Title input, suggested-tag toggles, "Apply" button calls `PATCH /api/v1/objects/{id}` exactly once. |
| `apps/web/src/components/workspace/WorkspaceLiteProvider.tsx` | Public hook `useWorkspaceLite()` exports `openSidePane`, `closeSidePane`, `sidePaneObject`. Escape closes. |
| `apps/web/src/components/editor/PageEditor.tsx` | Tiptap mount, `onUpdate` callback signature, autosave debounce of 800ms via `useAutoSave`. |
| `apps/web/src/components/assets/AssetUploader.tsx` | Drag-drop on a labeled dropzone, `POST /api/v1/assets/upload` per file, progress events update local state. |
| `apps/web/src/lib/objectRouting.ts` | `objectRoute(kind, id)` signature and all current branches. |
| `apps/web/src/lib/api.ts` | Public function names and return types. Additions are fine; removals/renames are not. |

If a redesign requires a different shape, **add a new component beside the old one** (e.g., `SearchCommand.tsx` next to `SearchModal.tsx`) and gate the swap behind a feature flag (Section 1.4). Do not delete the old file in this phase.

### 1.2 Behaviors that may not regress

- `Cmd+K` opens search globally. Always.
- Search modal `Esc` closes it.
- Editor autosave fires once after 800ms of typing idle.
- Sign-out works and redirects to `/login`.
- Soft-deleted items can be restored from `/app/trash`.
- Triage modal applies tags + title via a single `PATCH`.
- Cookie-based auth (`kos_session`) continues to work for SSR fetches in `apps/web/src/app/(app)/app/.../page.tsx`.
- Default theme is **dark**. No FOUC. No theme toggle is *required*; the toggle is opt-in additive.
- All current sidebar routes resolve (`/app`, `/app/pages`, `/app/assets`, `/app/sources`, `/app/chats`, `/app/inbox`, `/app/trash`).

### 1.3 Files that may NOT be modified by this phase

- `services/api/**`
- `services/worker/**`
- `services/mcp/**`
- `infra/**`
- `tests/api/**`, `tests/unit/**`, `services/mcp/tests/**`
- `tests/e2e/**` and `tests/worker/**` (owned by PHASE-ENHANCE-02)
- `apps/web/src/types/**` (additive only — append new types, do not remove or rename existing)
- Any Alembic migration, schema file, or env var contract.

### 1.4 Feature-flag policy

When replacing a contractual component (e.g., search modal) with a new implementation:

- Add a single env var `NEXT_PUBLIC_UX_<FEATURE>` (boolean: `"1"` or unset).
- Keep both code paths in the tree. Switch via runtime check, e.g.:
  ```tsx
  const useNewSearch = process.env.NEXT_PUBLIC_UX_SEARCH_V2 === "1";
  return useNewSearch ? <SearchCommand …/> : <SearchModal …/>;
  ```
- Default to the old path. Document the flag in `infra/.env.example` with a comment.
- A future phase (out of scope here) flips defaults and removes the legacy file. We do not flip defaults in PHASE-ENHANCE-03.

### 1.5 `data-testid` and ARIA selectors

Every component currently used by name in the testing plan must keep a stable selector. Where one doesn't exist today, **add it as the first PR action** so tests written in parallel can rely on it. Required:

- `<SearchModal>` root: `data-testid="search-modal"`
- Input inside it: `role="combobox"` or `data-testid="search-input"`
- `<TriageModal>` root: `data-testid="triage-modal"`
- `<AssetUploader>` dropzone: `data-testid="asset-dropzone"`
- `<AiPanel>` root: `data-testid="ai-panel"`
- `<GraphPanel>` root + tab buttons: `data-testid="graph-panel"`, `data-testid="graph-tab-{backlinks|related|ai}"`
- `<WorkspaceSidePane>` root: `data-testid="side-pane"`

These are the only test hooks required; everything else uses role/text selectors. Adding test ids has zero functional impact and protects the parallel test work.

---

## 2. Coordination with the live worktrees

Two worktrees are active. Treat them as immovable; structure this work around them.

### 2.1 PHASE-7B-MCP-WRITE (`$HOME/Documents/agentic-knowledge-management-7b`)

- Touches: `services/api`, `services/mcp`, `services/worker`, `tests/api`, `services/mcp/tests`, `docs/MCP_TOOLS.md`.
- Conflict surface with this phase: **none**. Safe to develop fully in parallel.
- Coordination action: none required.

### 2.2 PHASE-ENHANCE-02-TESTING-INFRA (`…-enhance-02-testing-infra`)

- Touches `apps/web/package.json`, `apps/web/tsconfig.json`, `apps/web/vitest.config.ts` (new), `apps/web/vitest.setup.ts` (new), `apps/web/src/test/**` (new), `apps/web/src/**/__tests__/**` (new), root `package.json`, `pnpm-workspace.yaml`, `tests/worker/**`, `tests/e2e/**`, `.github/workflows/**`.
- Conflict surface with this phase:
  - `apps/web/package.json` — both phases add dev dependencies.
  - `apps/web/tsconfig.json` — testing infra appends `"types": [...]`.
  - `apps/web/src/components/**` — testing infra reads (does not modify) source files but **adds** sibling `__tests__/` folders.

### 2.3 Merge order rules

1. **PHASE-ENHANCE-02 T1 (Vitest scaffold)** must merge **before** UX-T1 of this phase. Reason: it adds the test runner that we need to verify our primitives. If T1 testing has not landed when UX-T1 is ready, UX-T1 may merge anyway, but it must include a small placeholder change to `package.json` that is forward-compatible (only `dependencies`, never modify `devDependencies` unless rebased on testing T1).
2. **PHASE-ENHANCE-02 T2 (component tests)** must merge **before** UX-T3 (search/editor migrations). Reason: UX-T3 needs the existing test contract pinned so the migration won't silently regress.
3. UX-T2 (toast + shell) must merge before any UX phase that issues toasts (T3+).
4. UX-T4 (list pages refactor) must merge before any UX phase that depends on `<ListPage>`.
5. UX-T6 (a11y sweep) is last and depends on all other UX PRs.
6. If a `package.json` conflict arises between this plan and PHASE-ENHANCE-02, the rule is: **rebase this plan onto testing infra's main, not the other way around.** Tests are higher priority because they protect every other change.

### 2.4 Communication

Each PR opened under this plan must mention in its description:
- Which UX-Tn phase.
- Which non-breakage-contract items (Section 1.1, 1.2) are touched and how they are preserved.
- Whether the PR is rebased onto the latest testing-infra main.
- A screenshot before/after at 1280×800 and 375×812.

---

## 3. Current state — audit (May 2026)

(Identical to the previous draft; reproduced for completeness so the AI coder doesn't need to cross-reference.)

| Metric | Today |
|---|---|
| `aria-label` / `role=` usages across `apps/web/src` | **3** |
| `focus-visible` / `focus:ring` usages | **7** |
| Responsive breakpoint usages | **5 total** |
| Distinct Tailwind color tokens used | **70** (no theme extension) |
| Most-used token | `text-gray-400` (63x), `border-gray-800` (62x) |
| Custom theme tokens in `tailwind.config.ts` | **0** |
| Custom fonts | **0** |
| Toast / notification system | **none** |
| Keyboard shortcuts | **only `Cmd+K`** |
| Pages with bare `<div>Loading...</div>` | 6 |
| Silent `catch {}` blocks | confirmed in `AiPanel.tsx` |
| Side pane on mobile | hidden (`hidden md:flex`) |
| Animations | only `animate-pulse` and `animate-spin` |

Already-good things to preserve:
- `tailwind-merge` and `clsx` are already installed; we keep them.
- SWR and the `useObjects` / `useChats` / `useSource` hook layer is consistent.
- `objectRoute()` correctly centralizes URL construction.
- Soft-delete + Trash flow is wired and works.
- The audit invariant (agent_runs + object_revisions) is backend-side and unaffected.

---

## 4. Goal & non-goals

### Goal

Lift KnowledgeOS from "functional prototype" to "polished daily-driver" with:

1. A **named design system** (Tailwind tokens layered on top of existing Tailwind colors — no breaking removal).
2. A **toast / notification system** for async feedback, additive to existing inline error rendering.
3. An **expanded keyboard-shortcut layer** with a `?` overlay; existing `Cmd+K` preserved.
4. **Empty / loading / error / success states** standardized via primitives, applied opportunistically.
5. **Responsive behavior** down to 480px without losing any desktop affordance.
6. **Accessibility baseline** (WCAG AA on body text, focus rings, focus-trapped modals, landmark roles).
7. **Editor enhancements** (bubble menu, slash menu, more block types) **behind a feature flag** so the existing editor remains the default until verified.
8. **Search palette upgrade** (filters, recents, kind icons) **behind a feature flag**.
9. **Light theme support**, opt-in, default remains dark.
10. **Subtle motion language**, all motion respecting `prefers-reduced-motion`.

### Non-goals

- No backend changes, no schema changes, no MCP/worker changes.
- No new third-party UI kit (no shadcn/ui CLI, no MUI, no Chakra).
- No CSS-in-JS migration.
- No marketing site.
- No i18n infrastructure.
- No removal of any existing component, file, or behavior.
- No change to `apps/web/src/types/**` other than additions.
- No bulk-action backend (the UI for bulk actions is in scope, but the actual bulk endpoints are not — bulk actions iterate via existing single-object endpoints with a parallelism cap).
- No "real asset metadata" fix — that requires verifying / extending the assets API. Defer to a follow-up phase.

---

## 5. Hard constraints

1. **Dependency budget — explicit and frozen.** The only new packages allowed in this phase, with sizes (gzipped):
   - `@radix-ui/react-dialog` (~6 KB)
   - `@radix-ui/react-dropdown-menu` (~7 KB)
   - `@radix-ui/react-tooltip` (~5 KB)
   - `@radix-ui/react-tabs` (~4 KB)
   - `@radix-ui/react-popover` (~5 KB)
   - `@radix-ui/react-checkbox` (~3 KB)
   - `@radix-ui/react-switch` (~3 KB)
   - `class-variance-authority` (~2 KB)
   - `sonner` (~7 KB)
   - `cmdk` (~6 KB)
   - `next-themes` (~3 KB)
   - **Total budget: ~50 KB gzipped added.** No `framer-motion`, no `react-aria-components`, no `@headlessui/react`, no shadcn.
2. **`tailwind-merge` and `clsx` are already installed.** Use them; do not add a competing alternative.
3. **No new lint rules in this phase.** No eslint-plugin-tailwindcss color ban, no a11y rule changes. Reason: such rules would fail the build for legacy code we haven't migrated yet. Section 11 documents how to introduce them safely in a later phase.
4. **All animations ≤ 200ms.** Honor `prefers-reduced-motion: reduce` everywhere by gating with Tailwind's `motion-safe:` variant.
5. **No font self-host issue.** Use `next/font/google` for Inter + JetBrains Mono — these download at build time and are then served from `/_next/static/media/`, which is local at runtime. Add a comment in `layout.tsx` explaining the build-time dependency. If the user wants offline builds, document `next/font/local` migration as a one-line follow-up (not done in this phase).
6. **No removal of raw color classes.** Tokens live alongside raw Tailwind. Migration is by-screen, opt-in, file-at-a-time. Nothing in `apps/web` blocks compiling because `text-gray-500` exists.
7. **Every PR must pass `pnpm typecheck && pnpm lint && pnpm build` on a clean checkout.** No PR may rely on changes from a future PR.
8. **Every PR ships with a "rollback" note** in its description: what to `git revert` and what side-effects, if any, remain.

---

## 6. Design system foundation (UX-T1)

### 6.1 Tokens — added, never replacing

- New file `apps/web/src/styles/tokens.css` defines CSS variables on `:root` and `[data-theme="light"]`.
- New entries in `tailwind.config.ts` `theme.extend.colors` for `surface`, `fg`, `border` (as `border-DEFAULT|subtle|strong`), `brand`, `success`, `warning`, `danger`, `info`, `ring`. **Do not touch existing default Tailwind colors.** Both `text-gray-100` and `text-fg` must work.
- Verify by inspecting `pnpm build` output — bundle size delta must be < 2 KB after T1 alone.

```css
/* apps/web/src/styles/tokens.css */
:root {
  --surface-0: 9 9 11;       /* zinc-950 */
  --surface-1: 24 24 27;     /* zinc-900 */
  --surface-2: 39 39 42;     /* zinc-800 */
  --surface-3: 63 63 70;     /* zinc-700 */
  --text-primary: 244 244 245;
  --text-secondary: 161 161 170;
  --text-tertiary: 113 113 122;
  --text-disabled: 82 82 91;
  --border-subtle: 39 39 42;
  --border-default: 63 63 70;
  --border-strong: 113 113 122;
  --brand: 99 102 241;       /* indigo-500 */
  --brand-fg: 238 242 255;
  --success: 34 197 94;
  --warning: 234 179 8;
  --danger: 239 68 68;
  --info: 59 130 246;
  --ring: 129 140 248;
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --duration-fast: 120ms;
  --duration-base: 180ms;
  --duration-slow: 280ms;
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
}
[data-theme="light"] {
  --surface-0: 250 250 250;
  --surface-1: 255 255 255;
  --surface-2: 244 244 245;
  --surface-3: 228 228 231;
  --text-primary: 24 24 27;
  --text-secondary: 63 63 70;
  --text-tertiary: 113 113 122;
  --text-disabled: 161 161 170;
  --border-subtle: 228 228 231;
  --border-default: 212 212 216;
  --border-strong: 161 161 170;
  --brand: 79 70 229;
  --brand-fg: 255 255 255;
  --ring: 99 102 241;
}
```

```ts
// apps/web/tailwind.config.ts — additive
theme: {
  extend: {
    colors: {
      surface: {
        0: "rgb(var(--surface-0) / <alpha-value>)",
        1: "rgb(var(--surface-1) / <alpha-value>)",
        2: "rgb(var(--surface-2) / <alpha-value>)",
        3: "rgb(var(--surface-3) / <alpha-value>)",
      },
      fg: {
        DEFAULT: "rgb(var(--text-primary) / <alpha-value>)",
        muted: "rgb(var(--text-secondary) / <alpha-value>)",
        subtle: "rgb(var(--text-tertiary) / <alpha-value>)",
        disabled: "rgb(var(--text-disabled) / <alpha-value>)",
      },
      brand: {
        DEFAULT: "rgb(var(--brand) / <alpha-value>)",
        fg: "rgb(var(--brand-fg) / <alpha-value>)",
      },
      success: "rgb(var(--success) / <alpha-value>)",
      warning: "rgb(var(--warning) / <alpha-value>)",
      danger: "rgb(var(--danger) / <alpha-value>)",
      info: "rgb(var(--info) / <alpha-value>)",
      ring: "rgb(var(--ring) / <alpha-value>)",
    },
    borderRadius: {
      sm: "var(--radius-sm)",
      md: "var(--radius-md)",
      lg: "var(--radius-lg)",
      xl: "var(--radius-xl)",
    },
    transitionDuration: {
      fast: "var(--duration-fast)",
      base: "var(--duration-base)",
      slow: "var(--duration-slow)",
    },
    transitionTimingFunction: {
      out: "var(--ease-out)",
    },
  },
},
```

> Note: we extend `colors` but do not extend `borderColor` separately. Tailwind 3 derives `border-*` utilities from the colors map automatically when no separate `borderColor` extension exists. If `border-subtle` doesn't compile, add a `borderColor` extension that re-exports the same tokens — additive.

### 6.2 Typography (additive, gated)

- Mount `Inter` and `JetBrains_Mono` via `next/font/google` in `apps/web/src/app/layout.tsx`.
- Expose them as CSS variables `--font-sans`, `--font-mono`.
- In `tailwind.config.ts`, **append** `fontFamily: { sans: ["var(--font-sans)", ...defaultTheme.fontFamily.sans], mono: ["var(--font-mono)", ...defaultTheme.fontFamily.mono] }`.
- The body already uses `bg-gray-950 text-gray-100 antialiased` — leave that unchanged. Inter becomes the default sans because we updated the family chain.
- If the build environment is offline (no Google Fonts reachable), document the swap to `next/font/local` in `docs/UX_GUIDE.md`.

### 6.3 Primitive components (`apps/web/src/components/ui/`)

All primitives are **new files**, none replace existing components. Each exports a single component or a small group; each has a brief JSDoc with usage; each has a `data-testid` slot via the standard `…rest` props passthrough.

| File | Purpose | Notes |
|---|---|---|
| `Button.tsx` | `variant: primary\|secondary\|ghost\|destructive\|link`, `size: sm\|md\|lg`, `loading`, `leftIcon`, `rightIcon` | CVA |
| `IconButton.tsx` | `aria-label` required by TS | wraps Button |
| `Input.tsx`, `Textarea.tsx`, `Select.tsx`, `Checkbox.tsx`, `Switch.tsx` | form primitives with `label`, `hint`, `error` | each auto-wires `htmlFor` |
| `Dialog.tsx` | wraps `@radix-ui/react-dialog` | focus-trap free; size variants `sm\|md\|lg` |
| `DropdownMenu.tsx` | wraps `@radix-ui/react-dropdown-menu` | |
| `Tooltip.tsx` | wraps `@radix-ui/react-tooltip` | 600ms default delay; `<Kbd>` slot |
| `Popover.tsx` | wraps `@radix-ui/react-popover` | |
| `Tabs.tsx` | wraps `@radix-ui/react-tabs` | |
| `Badge.tsx` | `variant: kind\|status\|neutral` with `tone` prop | replaces ad-hoc spans gradually |
| `Kbd.tsx` | `<Kbd>⌘K</Kbd>` | |
| `Toast.tsx` | wraps `sonner`'s `<Toaster />` and re-exports a typed `toast` helper | |
| `Skeleton.tsx` | `motion-safe:animate-pulse` | respects reduced-motion |
| `Spinner.tsx` | `size`, `color` props | |
| `EmptyState.tsx` | `icon`, `title`, `description`, `action` | |
| `ErrorState.tsx` | `error`, `onRetry` | |
| `Avatar.tsx` | initials fallback | |

### 6.4 Layout primitives (additive)

| File | Purpose |
|---|---|
| `apps/web/src/components/layout/PageHeader.tsx` | `<PageHeader title={…} actions={…} breadcrumbs={…} />` |
| `apps/web/src/components/layout/ListShell.tsx` | wraps loading skeleton, empty, error states |
| `apps/web/src/components/layout/Section.tsx` | semantic wrapper |

### 6.5 Utilities

- `apps/web/src/lib/cn.ts` — `cn(...inputs) = twMerge(clsx(inputs))`. Re-exports the existing pair into one canonical helper.

> **Important:** This PR does *not* migrate any existing screen onto the new primitives. Migration happens screen-by-screen in T2–T6. T1 only lays the foundation.

---

## 7. Phased delivery — 6 PRs, each independently revertible

Each PR runs:
- `pnpm typecheck` — must pass.
- `pnpm lint` — must pass without disabling rules.
- `pnpm build` — must succeed and bundle size delta documented.
- (When testing infra is merged) `pnpm -F web test:run` and `pnpm test:e2e --grep '@smoke'` — must pass.

### UX-T1 — Foundation (purely additive)

**Adds:**
- `apps/web/src/styles/tokens.css`
- `apps/web/src/lib/cn.ts`
- `apps/web/src/components/ui/{Button,IconButton,Input,Textarea,Select,Checkbox,Switch,Dialog,DropdownMenu,Tooltip,Popover,Tabs,Badge,Kbd,Toast,Skeleton,Spinner,EmptyState,ErrorState,Avatar}.tsx`
- `apps/web/src/components/ui/index.ts`
- `apps/web/src/components/layout/{PageHeader,ListShell,Section}.tsx`

**Modifies (additive only):**
- `apps/web/src/styles/globals.css` — `@import "./tokens.css";` at top.
- `apps/web/src/app/layout.tsx` — load fonts, add CSS-var classes; do **not** change body classes.
- `apps/web/tailwind.config.ts` — extend colors, fontFamily, borderRadius, transitionDuration, transitionTimingFunction.
- `apps/web/package.json` — add the 11 dependencies in Section 5. **Coordinate with PHASE-ENHANCE-02 T1: rebase before merging if test infra has touched `package.json` first.**
- `infra/.env.example` — add commented `NEXT_PUBLIC_UX_SEARCH_V2`, `NEXT_PUBLIC_UX_EDITOR_V2` flags (both default unset = off).

**Adds (test ids only — Section 1.5):**
- `data-testid` on the seven contractual components named in Section 1.5. These are 7 one-line additions; each has zero behavioral effect.

**Acceptance:**
- `pnpm typecheck && pnpm lint && pnpm build` clean.
- Visual diff at 1280×800 of `/login`, `/app`, `/app/pages`, `/app/sources`, `/app/inbox`: **identical** to before T1 (we changed nothing visible).
- A Storybook is **not** required. JSDoc usage example on each primitive is.
- Bundle size delta: ≤ 60 KB gzipped on the largest route.

**Rollback note:** Revert the single PR. Tokens, fonts, and primitives disappear; existing screens are unaffected because they never imported them.

**Commit:** `feat(ui): design tokens, primitives, and font scaffold`

---

### UX-T2 — Toasts, error/loading routes, app shell upgrades (still no contractual changes)

**Adds:**
- `apps/web/src/app/(app)/layout.tsx` — wrap children with `<Toaster />` and a client `<ErrorBoundary>`. **Does not change route structure**; the `(app)` segment already groups the routes today.
- `apps/web/src/app/(app)/error.tsx`, `not-found.tsx`, `loading.tsx`.
- `apps/web/src/components/layout/ErrorBoundary.tsx`.
- `apps/web/src/lib/hooks/useSidebarState.ts` — localStorage-backed collapse, default expanded.
- `apps/web/src/lib/hooks/useShortcut.ts` — generic key handler that respects `<input>`/`<textarea>`/`contenteditable` focus.

**Modifies (preserving public APIs):**
- `apps/web/src/components/layout/Sidebar.tsx` — add collapse toggle (Cmd+\) and Inbox/Trash count badges (using existing `useObjects({kind:undefined, …})` and `useSWR("/api/v1/objects/trash")`). Default is expanded so layout is identical for users who never toggle.
- `apps/web/src/components/layout/AppShell.tsx` — keep current structure; insert `<MobileNav>` only at `<md` viewport width via Tailwind responsive classes; nothing visible at `≥md`.
- `apps/web/src/components/workspace/WorkspaceSidePane.tsx` — keep current `hidden md:flex` desktop behavior; add a `Sheet`-style bottom sheet **only** for `<md` viewports. Existing tests written against the desktop pane keep passing.
- `apps/web/src/components/ai/AiPanel.tsx` — replace the `// ignore` in `handleCreateLink` with `toast.error("Couldn't create link", { description: err.message })`. Keep the existing inline state machine; toast is *additive* feedback.
- `apps/web/src/components/pages/PageView.tsx` — add a `<SaveStatusChip>` rendered alongside (not replacing) the existing bottom-strip "Saving…/Saved" label. On `error` status, also fire `toast.error`.
- `apps/web/src/components/inbox/TriageModal.tsx` — fire `toast.success("Organized")` on Apply success; existing modal close behavior preserved. **Do not** change the title input or tag toggle behavior — tests rely on it.
- `apps/web/src/components/sources/CreateSourceModal.tsx` — toast on success.
- `apps/web/src/components/assets/AssetUploader.tsx` — toast per upload completion (`toast.success(\`${file.name} uploaded\`)`); existing inline progress bar preserved.
- `apps/web/src/app/(app)/app/trash/page.tsx` — toast + `Undo` action on restore.
- `apps/web/src/app/(app)/app/chats/page.tsx` — toast on import success.

**Acceptance:**
- All existing flows work identically. Added: toasts appear on actions; sidebar can collapse via Cmd+\; mobile bottom-bar appears at <md.
- Throwing inside `/app/*` shows a friendly error UI rather than a white screen (verify by injecting `throw` in a list page locally, then revert).
- Existing PHASE-ENHANCE-02 component tests for `AiPanel`, `TriageModal`, `AssetUploader` continue to pass (toast calls are observable as MSW request side effects only when those toasts are async; otherwise they're silent in jsdom).

**Rollback note:** Revert the PR. Toasts vanish, mobile drawer vanishes, sidebar collapse vanishes. No data loss; no behavior change for desktop users.

**Commit:** `feat(ui): toast system, route error boundaries, mobile drawer, sidebar collapse`

---

### UX-T3 — Search palette + editor enhancements (BOTH BEHIND FEATURE FLAGS)

This is the highest-risk PR. The feature flag is mandatory.

**Adds (both new files alongside existing ones):**
- `apps/web/src/components/search/SearchCommand.tsx` — cmdk-based palette.
- `apps/web/src/components/search/SearchFilters.tsx`
- `apps/web/src/components/search/RecentSearches.tsx`
- `apps/web/src/components/editor/extensions/SlashMenuExtension.ts`
- `apps/web/src/components/editor/SlashMenu.tsx`
- `apps/web/src/components/editor/BubbleMenu.tsx`
- `apps/web/src/components/editor/extensions/CalloutExtension.ts`
- `apps/web/src/components/editor/SaveStatusChip.tsx` (introduced as standalone in T2; used here)

**Modifies (flag-gated; no behavior change when flag off):**
- `apps/web/src/components/layout/AppShell.tsx`:
  ```tsx
  const useV2Search = process.env.NEXT_PUBLIC_UX_SEARCH_V2 === "1";
  …
  {useV2Search
    ? <SearchCommand isOpen={searchOpen} onClose={() => setSearchOpen(false)} />
    : <SearchModal isOpen={searchOpen} onClose={() => setSearchOpen(false)} />
  }
  ```
- `apps/web/src/components/pages/PageView.tsx`:
  ```tsx
  const useV2Editor = process.env.NEXT_PUBLIC_UX_EDITOR_V2 === "1";
  // wire bubble menu + slash menu only if useV2Editor
  ```
- Existing `EditorToolbar` component stays mounted in both modes; in V2 mode the bubble menu is in addition, not a replacement (so any user who prefers the toolbar still has it). Do not delete `EditorToolbar`.

**Adds (additive Tiptap extensions, off by default for V1 users):**
- `@tiptap/extension-task-list`, `@tiptap/extension-task-item`, `@tiptap/extension-table`, `@tiptap/extension-table-row`, `@tiptap/extension-table-cell`, `@tiptap/extension-table-header`, `@tiptap/extension-horizontal-rule`. **All five are loaded only in V2 mode** so V1 page bundles are unchanged.

**Acceptance:**
- With both flags unset (default): visual diff vs main is zero, all PHASE-ENHANCE-02 search/editor component tests pass unchanged.
- With `NEXT_PUBLIC_UX_SEARCH_V2=1`: Cmd+K opens the new palette; `/` also opens it (suppressed in editable elements via `useShortcut`); filters and recents work; legacy `SearchModal` remains importable but unused.
- With `NEXT_PUBLIC_UX_EDITOR_V2=1`: text selection shows bubble menu within 100ms; `/` in the editor opens slash menu; existing autosave still fires once after 800ms.
- Bundle size delta with flags off: ≤ 5 KB (just the extension imports tree-shaken away).
- Bundle size delta with flags on: ≤ 80 KB.

**Rollback note:** Unset env vars to disable instantly. Revert PR to remove code; nothing else is touched.

**Commit:** `feat(ui): cmdk search palette and tiptap bubble/slash menus (flag-gated)`

---

### UX-T4 — List pages refactor (incremental, page-by-page)

This refactor extracts a shared `<ListPage>` shell. To stay safe, **each list page is migrated in its own commit within this PR**, and each commit is independently revertible.

**Adds:**
- `apps/web/src/components/lists/ListPage.tsx` — combines `<PageHeader>` + `<ListToolbar>` + `<ListShell>`.
- `apps/web/src/components/lists/ListToolbar.tsx` — search-in-list, kind filter (where applicable), sort dropdown, view-mode toggle.
- `apps/web/src/components/lists/BulkActionBar.tsx` — sticky bottom bar shown when selection > 0.
- `apps/web/src/lib/hooks/useListSelection.ts`.

**Modifies, in this order (one commit per file):**
1. `apps/web/src/app/(app)/app/page.tsx` — adopt `<ListPage>`. Verify `/app` renders identically except for the new toolbar above the list.
2. `apps/web/src/app/(app)/app/pages/page.tsx`
3. `apps/web/src/app/(app)/app/sources/page.tsx`
4. `apps/web/src/app/(app)/app/chats/page.tsx`
5. `apps/web/src/app/(app)/app/inbox/page.tsx` — adopt bulk select; bulk-triage iterates existing single-object `aiTriage()` with `Promise.all` capped at 4 parallel calls. **No new backend endpoints.**
6. `apps/web/src/app/(app)/app/trash/page.tsx` — bulk restore via existing `restoreObject()` with the same 4-parallel cap.
7. `apps/web/src/app/(app)/app/assets/page.tsx` — adopt `<ListPage>`. **Skip the placeholder-metadata fix for now.** Document in the file's TODO comment that asset metadata work is deferred to a future phase.

**Bulk action safety rules:**
- Always cap parallelism at 4. Never fire 100 requests simultaneously.
- Always show a per-item toast or a grouped "8 of 10 succeeded" toast on completion.
- Never silently swallow a partial failure.
- Bulk delete uses existing soft-delete endpoint; never sends `force: true` even if the parameter exists.

**Acceptance:**
- Each list page renders identically pre/post for users with no selection and no filter applied.
- Keyboard nav: `j`/`k` move highlight, `Enter` opens, `o` opens in side pane, `Backspace` soft-deletes with `Undo` toast. These shortcuts are suppressed when focus is inside a typing surface.
- Bulk-select checkbox + bulk-action bar appears only when at least one row is selected.

**Rollback note:** Each file's commit can be reverted in isolation; or revert the whole PR to drop the list refactor entirely. The `<ListPage>` primitive remains importable for future work but unused.

**Commit:** `feat(ui): unified list page shell with filters, sort, keyboard nav, bulk actions`

---

### UX-T5 — Auth screens, theme toggle, motion (opt-in)

**Adds:**
- `apps/web/src/components/auth/AuthLayout.tsx` — split layout for `lg:` and above.
- `apps/web/src/components/brand/Logo.tsx` — inline SVG mark.
- `apps/web/src/app/(auth)/forgot-password/page.tsx` — stub explaining local-first reset via `kos-cli` (out of scope to actually build the CLI flow; the page exists so the link in the form isn't a 404).
- `apps/web/src/lib/theme/ThemeProvider.tsx` — wraps `next-themes`.
- `apps/web/src/components/theme/ThemeToggle.tsx`.

**Modifies:**
- `apps/web/src/app/(auth)/login/page.tsx` and `register/page.tsx` — wrap with `<AuthLayout>`; on small screens layout collapses to single column identical to today.
- `apps/web/src/components/auth/{LoginForm,RegisterForm}.tsx` — add `aria-live="polite"` region for the error message; fire toasts on success in addition to existing redirect.
- `apps/web/src/app/layout.tsx` — wrap children in `<ThemeProvider attribute="data-theme" defaultTheme="dark" enableSystem={false}>`. **Critical:** `defaultTheme="dark"` and `enableSystem={false}` so existing dark-only users see zero change. Users who toggle light enable it explicitly.
- `apps/web/src/components/layout/AppTopBar.tsx` (added in T2) — mount the theme toggle inside a DropdownMenu in the user menu.

**Light-theme verification checklist:**
- Manually load `/login`, `/app`, `/app/pages`, `/app/sources/[id]`, `/app/chats/[id]`, `/app/inbox`, `/app/trash` in light mode. Capture screenshots in PR description.
- Run `pnpm dlx @axe-core/cli http://localhost:3000/app` in both themes. Zero serious/critical issues required.

**Acceptance:**
- Default render is identical to main (dark theme, no toggle interaction).
- Toggling to light renders all primitives correctly (because primitives use tokens).
- Toggling to system follows OS preference.
- Auth screens at `<lg` viewport identical to today; at `≥lg` show split layout.

**Rollback note:** Revert the PR. Theme provider and toggle disappear. Theme stays dark forever again. Auth screens revert to single panel.

**Commit:** `feat(ui): light theme support, auth screen redesign, motion language`

---

### UX-T6 — Accessibility & responsive sweep, shortcut overlay, docs

**Adds:**
- `apps/web/src/components/help/ShortcutOverlay.tsx` — `?` opens a Dialog listing all shortcuts grouped by area.
- `apps/web/src/lib/shortcuts/registry.ts` — single source of truth for shortcut metadata.
- `docs/A11Y.md` — baseline + known limitations.
- `docs/UX_GUIDE.md` — token names, primitive usage, when to toast vs inline error.
- `docs/SHORTCUTS.md` — keyboard shortcuts reference (also linked from README).

**Modifies (surgical):**
- Add `aria-label` to every `<button>` lacking textual children. Verify with `pnpm dlx @axe-core/cli`.
- Add landmark roles to `AppShell`: `<header role="banner">`, `<nav>` (sidebar already implicit), `<main id="main-content">`, `<aside>` (side pane already implicit).
- Add a skip-link in `apps/web/src/app/(app)/layout.tsx`: `<a href="#main-content" className="sr-only focus:not-sr-only …">Skip to content</a>`.
- Convert `text-gray-600` (contrast 2.7:1 on `bg-gray-900`) to `text-gray-500` or `text-fg-subtle` **only at the call sites flagged by axe**. Do not do a global find/replace.
- README.md — add a "Keyboard shortcuts" section pointing at `docs/SHORTCUTS.md`.

**Explicitly NOT done:**
- No new ESLint rule banning raw color classes. (Future phase, after a screen-by-screen migration is complete.)
- No `prefers-reduced-motion` media query test in CI. (Add in a future testing-infra phase.)
- No screen-reader-only audit beyond axe automated checks.

**Acceptance:**
- `pnpm dlx @axe-core/cli http://localhost:3000/app` — zero serious/critical violations.
- `?` opens overlay; lists all registered shortcuts grouped by area (Global, Search, Editor, Lists).
- Manual responsive smoke at 375 / 768 / 1280 in both themes; screenshots in PR description.

**Rollback note:** Revert the PR. ARIA labels and skip link remain (they're additive and harmless); shortcut overlay disappears; docs disappear.

**Commit:** `feat(ui): accessibility baseline, shortcut overlay, ux/a11y docs`

---

## 8. What we're explicitly NOT doing in this phase

Each of these was considered and pushed to a future phase to keep blast radius small:

- **Real asset metadata wiring.** Requires verifying `GET /api/v1/assets` response shape and possibly an extension. Defer.
- **ESLint rule banning raw `gray-*`/`blue-*` classes.** Would fail the build for every unmigrated screen. Introduce only after Phase 4 migration is fully verified.
- **`framer-motion` integration.** Radix's built-in `data-state` attributes plus Tailwind keyframes cover modal/popover/menu transitions. We'd add 30 KB for marginal value.
- **Storybook.** Useful for design review, but adds significant tooling. JSDoc examples on each primitive are enough for now.
- **Snapshot tests for UI.** Out of scope per PHASE-ENHANCE-02's own constraint.
- **i18n.** Out of scope; document in `docs/UX_GUIDE.md` that all new strings should be authored as plain JSX text (not template literals) so a future extractor can find them.
- **PWA / offline manifest.** Out of scope.
- **Drag handles on editor blocks.** Removed from scope; complex Tiptap NodeView work that may regress autosave timing.
- **Onboarding tour / coachmarks.** Future phase.
- **Analytics or telemetry.** Conflicts with local-first principle; not done.
- **Light-theme syntax highlighting in `Source` extracted text.** Use existing `<pre>` with `text-fg` tokens; defer code highlight to future phase.

---

## 9. Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| `package.json` merge conflict with PHASE-ENHANCE-02 T1 | High | Section 2.3 ordering rule: rebase this plan onto testing infra. |
| Adding `next-themes` causes hydration mismatch | Medium | `enableSystem={false}` and `defaultTheme="dark"` keep server and client in sync; verify with `next dev` in clean profile. |
| Tiptap V2 extensions break autosave timing | Medium | Flag-gated; default off. T3 acceptance explicitly verifies 800ms autosave still fires once. |
| New tokens shadow Tailwind defaults and surprise authors | Low | Tokens are namespaced (`surface-*`, `fg-*`, `border-subtle/default/strong`, `brand`, `success`, `warning`, `danger`, `info`, `ring`). They never collide with `gray-*`, `blue-*`, etc. |
| cmdk + custom shortcut handler double-fire | Medium | Single shortcut registry (`lib/shortcuts/registry.ts`) is source of truth; cmdk consumes it via prop, not its own handler. |
| Bulk action overwhelms the API | Medium | Hard parallelism cap of 4; toasts surface partial failures. Never fire > 4 concurrent requests. |
| Light theme reveals contrast issues | Medium | T5 includes a manual axe pass in light mode; T6 fixes leftover violations call-site by call-site. |
| Dependency footprint grows | Low | Section 5 freezes the dependency list; budget is ~50 KB gzipped. CI bundle-size check enforces. |
| Mobile bottom sheet for side pane breaks desktop pane tests | Low | Bottom sheet is rendered at `<md` only via Tailwind responsive class; desktop tests run at default jsdom viewport (1024) where the legacy desktop pane renders unchanged. |
| Skip-link or new landmark roles confuse existing E2E selectors | Low | E2E tests use role/text selectors per PHASE-ENHANCE-02 plan; landmarks are additive and don't displace existing roles. |

---

## 10. Per-PR rollback recipes

| PR | If you need to roll back | Side effects of rollback |
|---|---|---|
| UX-T1 | `git revert <T1 sha>` | Tokens, fonts, primitives gone. Existing screens unaffected. Bundle returns to baseline. |
| UX-T2 | `git revert <T2 sha>` | Toasts gone (silent failures return); mobile drawer gone; sidebar collapse gone; error/loading routes gone. Desktop UX returns to today's state. |
| UX-T3 | Unset `NEXT_PUBLIC_UX_SEARCH_V2` and `NEXT_PUBLIC_UX_EDITOR_V2`; or `git revert <T3 sha>` to also remove the code. | New search palette and editor menus disabled / removed. Legacy SearchModal and EditorToolbar continue to work. |
| UX-T4 | Revert per-file commit, or whole PR. | Affected list page reverts to its previous render; bulk actions disappear; keyboard nav within lists disappears. |
| UX-T5 | `git revert <T5 sha>` | Light theme gone; auth split layout gone. Default dark theme remains. |
| UX-T6 | `git revert <T6 sha>` | Shortcut overlay gone, docs gone, some `aria-label` additions remain (harmless). |

---

## 11. Definition of Done

- All 6 PRs (UX-T1..UX-T6) merged into `main`.
- README.md has a "Keyboard shortcuts" section pointing at `docs/SHORTCUTS.md`.
- `docs/UX_GUIDE.md` and `docs/A11Y.md` exist.
- `pnpm typecheck && pnpm lint && pnpm build` clean on `main`.
- Phase ENHANCE-02 Vitest + Playwright suites green, including the named contractual component tests.
- Lighthouse run on `/app` (logged-in, seeded fixtures): Performance ≥ 85, Accessibility ≥ 95, Best Practices ≥ 95.
- Bundle size: `apps/web` first-load JS for `/app` ≤ 320 KB gzipped (current ≈ 210 KB; ~110 KB headroom for added deps + new code).
- Manual sign-off at 375 / 768 / 1280 in both themes; PR descriptions include screenshots at each.
- Zero changes to `services/**` or `infra/**` from this phase.
- All Section 1.1 file paths still exist; all Section 1.2 behaviors still pass; all Section 1.5 `data-testid`s present.

---

## 12. Suggested order of operations for the AI coder

1. Read this file end-to-end. Read Section 1 twice.
2. Confirm PHASE-ENHANCE-02 T1 status. If not yet merged: pause and ask the human whether to proceed without test infrastructure or wait.
3. Create branch `phase-enhance-03-ux-polish`.
4. **UX-T1** PR. Do not migrate any screens. Get it reviewed and merged.
5. After T1 merges and is confirmed green, **UX-T2** PR.
6. After T2 merges, **UX-T3** PR. Verify both flags off ⇒ identical render to today.
7. **UX-T4** PR. Open as a single PR but commit each list-page migration individually so a single page can be reverted if it regresses.
8. **UX-T5** PR.
9. **UX-T6** PR last. This is the polish/cleanup pass.
10. Each PR description must include the Section 1.1 / 1.2 / 1.5 checklist showing nothing in the contract was broken.

When in doubt: prefer doing less, prefer keeping the legacy code alongside, prefer matching Linear / Raycast / Cursor over inventing something new. Polish is taste applied uniformly; safety is taste applied first.
