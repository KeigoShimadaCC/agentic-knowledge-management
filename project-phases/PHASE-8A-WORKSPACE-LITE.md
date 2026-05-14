# Phase 8A — Workspace Lite

> **Status:** Complete  
> **Branch:** `phase8a-workspace-lite`  
> **Parallel with:** Phase 5 (AI Assistant) and Phase 6 (Chat Import) in separate branches

---

## Context

Phases 1–4 are complete (Foundation, Sources, Search, Graph Lite). This phase implements the first useful slice of the eventual Phase 8 workspace feature: a lightweight split-pane view that lets the user open any object beside their current context without navigating away.

**No backend schema changes are required.** This is entirely frontend UI state.

---

## Goal

Let the user open a second object beside their current view without losing context. Side pane shows a read-only preview of any page, source, or asset. Accessible from search results, backlinks panel, and related objects panel.

---

## Non-Goals

- Persistent workspaces table in DB
- Saved/named workspace layouts
- Drag text between panes
- AI or MCP features
- More than 2 panes
- Mobile-optimized layout

---

## Definition of Done

- [x] `project-phases/PHASE-8A-WORKSPACE-LITE.md` created
- [x] `PROGRESS.md` updated
- [x] `WorkspaceLiteProvider` wraps app; side pane state available globally
- [x] `objectRoute(kind, id)` helper exists; SearchModal, BacklinksPanel, RelatedPanel use it
- [x] Side pane opens/closes; shows page, source, asset, or fallback
- [x] Search results have "open in side pane" affordance
- [x] BacklinksPanel items have "open in side pane" affordance
- [x] RelatedPanel items have "open in side pane" affordance
- [x] Side pane has header (title, kind badge, close button, "open full page" link)
- [x] Loading and error states in side pane
- [x] Existing navigation unchanged
- [x] `pnpm -F web typecheck` passes
- [x] `pnpm -F web build` passes
- [x] Existing 58+ backend tests still pass (no backend changes)

---

## UI Architecture

```
AppShell (flex h-screen)
  ├── Sidebar (w-60)
  ├── main (min-w-0 flex-1)           ← min-w-0 prevents overflow
  │     └── [route children]
  │           └── PageView (when on /pages/[id])
  │                 ├── EditorToolbar
  │                 ├── flex row:
  │                 │     ├── editor (flex-1)
  │                 │     └── GraphPanel (w-72)   ← unchanged, lives inside PageView
  │                 └── footer
  ├── WorkspaceSidePane (w-96, conditional) ← NEW
  └── SearchModal (fixed overlay)
```

The side pane is at **AppShell level** (not inside PageView), so it doesn't conflict with GraphPanel.

---

## State Management

`WorkspaceLiteProvider` wraps `(app)/layout.tsx` children:

```ts
interface SidePaneObject {
  id: string;
  kind: string;
  title: string;
}

interface WorkspaceLiteContextValue {
  sidePaneObject: SidePaneObject | null;
  openSidePane: (obj: SidePaneObject) => void;
  closeSidePane: () => void;
}
```

No URL params. Side pane state resets on page navigation (correct behavior — no persistence needed).

---

## Object Viewer

| Kind     | Data source       | What to show |
|----------|-------------------|--------------|
| `page`   | `getPage(id)`     | title, content_text as paragraphs, word count |
| `source` | `getSource(id)`   | title, type badge, status badge, thumbnail, extracted_text excerpt (800 chars) |
| `asset`  | title from SidePaneObject | title, kind badge; asset route link |
| other    | title from SidePaneObject | title, kind badge, "Open full page" link |

All viewers show a 3-line loading skeleton and an error state.

---

## Files to Create

| File | Purpose |
|------|---------|
| `apps/web/src/lib/objectRouting.ts` | Centralized routing helper |
| `apps/web/src/components/workspace/WorkspaceLiteProvider.tsx` | Global side-pane state |
| `apps/web/src/components/workspace/WorkspaceSidePane.tsx` | Side pane shell (header + viewer) |
| `apps/web/src/components/workspace/ObjectPaneViewer.tsx` | Dispatcher to kind-specific viewers |
| `apps/web/src/components/workspace/PagePaneView.tsx` | Read-only page viewer |
| `apps/web/src/components/workspace/SourcePaneView.tsx` | Read-only source viewer |

## Files to Update

| File | Change |
|------|--------|
| `apps/web/src/app/(app)/layout.tsx` | Wrap with WorkspaceLiteProvider |
| `apps/web/src/components/layout/AppShell.tsx` | Add WorkspaceSidePane; add min-w-0 to main |
| `apps/web/src/components/search/SearchModal.tsx` | Use objectRoute(); pass onOpenInPane to cards |
| `apps/web/src/components/search/SearchResultCard.tsx` | Add onOpenInPane prop + split icon button |
| `apps/web/src/components/graph/BacklinksPanel.tsx` | Use objectRoute(); add split icon button |
| `apps/web/src/components/graph/RelatedPanel.tsx` | Use objectRoute(); add split icon button |
| `docs/ARCHITECTURE.md` | Document Workspace Lite pattern |
| `docs/AGENT_GUIDE.md` | Note local-only workspace state |
| `PROGRESS.md` | Add Phase 8A section |

---

## Subtask Checklist

- [x] **Subtask 0** — Audit + plan files: create this doc, update PROGRESS.md
- [x] **Subtask 1** — Routing helper + workspace state provider
- [x] **Subtask 2** — ObjectPaneViewer (page, source, asset, fallback)
- [x] **Subtask 3** — Side pane layout (AppShell integration)
- [x] **Subtask 4** — Open in side pane from search results
- [x] **Subtask 5** — Open in side pane from graph panels
- [x] **Subtask 6** — Polish (ESC key, responsive, smooth transition) + docs

---

## Commit Sequence

1. `docs: add Phase 8A Workspace Lite plan`
2. `feat(web): add workspace lite routing helper and side pane state`
3. `feat(web): add object pane viewer for pages and sources`
4. `feat(web): add workspace side pane layout to AppShell`
5. `feat(web): open search results in workspace side pane`
6. `feat(web): open graph objects in workspace side pane`
7. `fix(web): workspace lite pane polish and responsive behavior`
8. `docs: document Workspace Lite architecture`

---

## Validation

```bash
# Frontend types and build
pnpm -F web typecheck
pnpm -F web build

# Backend tests (no backend changes; verify nothing broke)
cd tests && uv run pytest api/ -q
```
