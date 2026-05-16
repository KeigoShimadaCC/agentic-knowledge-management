# Phase 11A: Interactive Guided Tutorial

## Context

New users face a blank KnowledgeOS screen with no onboarding. This phase adds a spotlight-driven guided tour that walks users through each major feature using fixed sample data — so the experience is always consistent, repeatable, and doesn't pollute real user data. A single "Start Tour" button launches the tour; users can exit at any time.

---

## Approach

### 1. Entry Point
Add a **"Start Tour"** button in the AppShell sidebar footer (below the nav links, above the theme/user controls). An optional "?" button can also appear in PageHeader on first visit. Clicking either triggers `startTutorial()`.

### 2. Tutorial State — `TutorialProvider`
A new React context (modeled after `WorkspaceLiteProvider`) manages:

```ts
interface TutorialState {
  active: boolean;
  stepIndex: number;
  totalSteps: number;
  seedingStatus: 'idle' | 'loading' | 'ready' | 'error';
}
```

Persisted to `localStorage` key `kos:tutorial:completed` so completed users don't see the prompt again.

**File:** `apps/web/src/components/tutorial/TutorialProvider.tsx`
**Hook:** `useTutorial()` — exposes `{ active, stepIndex, start, next, prev, stop }`

### 3. Sample Data Seeding (Backend)
On `start()`, call `POST /api/v1/tutorial/seed`. The backend idempotently creates tutorial objects tagged `tutorial_v1` for the current user.

**New service:** `services/api/app/services/tutorial_seed_service.py`
Modeled on `demo_seed_service.py`. Seeds:
- 3 **Pages**: "Welcome to KnowledgeOS", "Reading Notes: Getting Things Done", "Project Retrospective"
- 1 **Source**: a short web article (URL ingestion, non-blocking)
- 1 **Project**: "KnowledgeOS Demo" (sample career project)
- 2 **Edges**: Page→Page, Page→Project relationships
- Tag all objects: `tutorial_v1`

**New endpoint:** `services/api/app/api/v1/tutorial.py`
- `POST /api/v1/tutorial/seed` — idempotent seed (tag check)
- `DELETE /api/v1/tutorial/reset` — deletes all `tutorial_v1` objects for the user (soft-delete)

Router registered in `services/api/app/api/v1/__init__.py`.

### 4. Spotlight Overlay Component
Portal-mounted via `ReactDOM.createPortal` into `document.body`.

**Technique:** 4-rectangle approach
- Fixed full-screen container (`z-index: 9999, pointer-events: none`)
- 4 dark panels (top/bottom/left/right) computed from `getBoundingClientRect()` of the target element
- Target element gets a bright ring (`outline: 2px solid hsl(var(--blue-500))`) for the duration of that step
- Popup card positioned adjacent to target element (auto-flips if near screen edge)

**Files:**
- `apps/web/src/components/tutorial/TutorialOverlay.tsx` — spotlight + popup render
- `apps/web/src/components/tutorial/TutorialPopup.tsx` — the card component (title, body, step counter, prev/next/stop)

### 5. Step Configuration
A typed config array in `apps/web/src/components/tutorial/tutorial-steps.ts`.

Each step:
```ts
interface TutorialStep {
  id: string;
  title: string;
  body: string;
  target?: string;       // CSS selector for the element to highlight
  position?: 'top' | 'bottom' | 'left' | 'right' | 'center';
  action?: 'navigate';
  navigateTo?: string;   // e.g. '/app/pages'
}
```

**Planned steps (10 total):**

| # | Title | Target | Notes |
|---|-------|--------|-------|
| 1 | Welcome to KnowledgeOS | — (center modal) | No highlight |
| 2 | Your Sidebar | `[data-tutorial="sidebar"]` | Nav overview |
| 3 | Pages — Your Notes | `[data-tutorial="nav-pages"]` | Navigate to /app/pages |
| 4 | Create a Page | `[data-tutorial="new-page-btn"]` | Highlight + button |
| 5 | Search Everything | `[data-tutorial="search-trigger"]` | Cmd+K shortcut |
| 6 | Sources — Ingest the Web | `[data-tutorial="nav-sources"]` | Navigate to /app/sources |
| 7 | Knowledge Graph | `[data-tutorial="related-panel"]` | Show graph edges panel |
| 8 | AI Assistant | `[data-tutorial="nav-chats"]` | Navigate to /app/chats |
| 9 | MCP Agent Access | `[data-tutorial="sidebar-footer"]` | Brief agent/MCP mention |
| 10 | You're all set | — (center modal) | Summary + "Explore" CTA |

`data-tutorial` attributes are added inline to existing components — no structural changes needed.

### 6. TutorialPopup UI

```
┌─────────────────────────────────────┐
│  Step 3 of 10  ·  Pages             │
│─────────────────────────────────────│
│  This is where all your notes and   │
│  documents live. You can write in   │
│  rich text, link to sources, or     │
│  let an AI agent create pages.      │
│─────────────────────────────────────│
│  [← Back]    [Stop Tour]  [Next →]  │
└─────────────────────────────────────┘
```

Styled with existing shadcn `Card` + `Button` components. Dark theme consistent with app.

### 7. Tour Exit Behavior
- **Stop button** or **Escape key**: stops tour, removes overlay, stays on current page
- **Backdrop click**: stops tour
- On completion (step 10 → "Explore"): marks `kos:tutorial:completed = true` in localStorage; sidebar button changes to "Replay Tour"

---

## Critical Files to Modify

| File | Change |
|------|--------|
| `apps/web/src/app/(app)/layout.tsx` | Wrap with `TutorialProvider` |
| `apps/web/src/components/layout/AppShell.tsx` | Mount `TutorialOverlay`; add "Start Tour" button |
| `apps/web/src/components/layout/Sidebar.tsx` | Add `data-tutorial="sidebar"` + tour button in footer |
| `services/api/app/api/v1/__init__.py` | Register tutorial router |
| `services/api/app/api/v1/tutorial.py` | New file — seed/reset endpoints |
| `services/api/app/services/tutorial_seed_service.py` | New file — fixture creation |

## New Files

| File | Purpose |
|------|---------|
| `apps/web/src/components/tutorial/TutorialProvider.tsx` | Context + state |
| `apps/web/src/components/tutorial/TutorialOverlay.tsx` | Spotlight rendering |
| `apps/web/src/components/tutorial/TutorialPopup.tsx` | Step card UI |
| `apps/web/src/components/tutorial/tutorial-steps.ts` | Step config |
| `apps/web/src/lib/hooks/useTutorial.ts` | Convenience hook |

---

## Reuse Points

- `WorkspaceLiteProvider` (`apps/web/src/components/workspace/WorkspaceLiteProvider.tsx`) → model `TutorialProvider`
- `Dialog.tsx` and card patterns from `WorkspaceNameModal.tsx`
- `shadcn Button` components for prev/next/stop
- `demo_seed_service.py` (`services/api/app/services/demo_seed_service.py`) → model `tutorial_seed_service.py`
- Existing `data-testid` pattern (extend to `data-tutorial`)
- `agent_runs` audit table — log tutorial seed/reset as agent action

---

## Out of Scope

- No video or animation playback
- No server-side progress tracking (localStorage only)
- No branching tutorial paths
- No auto-play on first login (button-triggered only)

---

## Verification

1. Click "Start Tour" → overlay appears, step 1 shows centered welcome card
2. Click Next → spotlight moves to sidebar, step 2 card positions correctly
3. Click "Stop Tour" at any step → overlay gone, no visual artifacts
4. Complete all 10 steps → completion marker saved, button changes to "Replay Tour"
5. `POST /api/v1/tutorial/seed` → objects appear tagged `tutorial_v1`
6. `DELETE /api/v1/tutorial/reset` → those objects soft-deleted
7. Escape key stops the tour from any step
8. Resize window mid-tour → spotlight recomputes position correctly (ResizeObserver)
9. `pnpm typecheck` and `pnpm lint` pass in `apps/web`
10. `uv run ruff check services/api` passes
