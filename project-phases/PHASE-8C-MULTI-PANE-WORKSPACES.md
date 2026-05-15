# PHASE-8C — Multi-Pane Workspaces

> **Type:** Feature phase
> **Status:** Planned
> **Branch:** `phase-8-multi-pane-workspaces`
> **Worktree:** `../agentic-knowledge-management-8`
> **Depends on:** Phase 8A (Workspace Lite), Phase 8B (Workspaces backend)

---

## Context

Phase 8A shipped a single read-only side pane (React context, no DB). Phase 8B shipped the full workspaces DB schema and REST CRUD API. Phase 8C completes the remaining 7 planned Phase 8 subtasks:

1. **Pane layout engine** — extend from 1 side pane to 2–4 resizable panes
2. ~~Workspace data model~~ ✅ done in Phase 8B
3. **Save/restore workspace UI** — connect the Phase 8B API to the frontend
4. **Drag text between panes** — drag selected text from a source pane into a page pane as a quote block with a citation edge
5. **Link pane to pane** — typed edge creation between objects open in different panes
6. **AI scoped to workspace** — "Ask about this pane / all panes / all KB" context picker
7. **Workspace-scoped search** — "Search workspace only" toggle filters to open pane objects
8. **Tests + docs** — backend tests for scoped search/AI, frontend component tests, architecture docs

---

## Non-Goals

- No new object kinds or DB schema migrations
- No MCP write tool changes
- No Kùzu graph engine work
- No full E2E test suite expansion beyond smoke checks for new behavior

---

## What Phase 8A/8B Already Delivered (do not re-implement)

| Asset | Location |
|---|---|
| `WorkspaceLiteProvider` (single pane context) | `apps/web/src/components/workspace/WorkspaceLiteProvider.tsx` |
| `WorkspaceSidePane` (fixed 384px pane) | `apps/web/src/components/workspace/WorkspaceSidePane.tsx` |
| `ObjectPaneViewer` (kind dispatcher) | `apps/web/src/components/workspace/ObjectPaneViewer.tsx` |
| `PagePaneView`, `SourcePaneView` | `apps/web/src/components/workspace/` |
| Workspace CRUD API (6 endpoints) | `services/api/app/api/v1/workspaces.py` |
| `WorkspaceLayout` Pydantic schema | `services/api/app/schemas/workspace.py` |
| `workspace_service` (full CRUD + restore + touch) | `services/api/app/services/workspace_service.py` |
| `Workspace` ORM + migration 0008 | `services/api/app/models/workspace.py` |
| 17 workspace API tests | `tests/api/test_workspaces.py` |

---

## Subtask 1 — Pane layout engine (2–4 resizable panes)

### Goal
Replace the single fixed side pane with a resizable multi-pane container (max 4 panes). Maintain backward compatibility so all existing `openSidePane`/`closeSidePane` callsites continue to work.

### Install
```bash
pnpm --filter @kos/web add react-resizable-panels
```

### WorkspaceLiteProvider rewrite

New context shape:
```ts
interface PaneState {
  id: string;           // nanoid
  objectId: string | null;
  objectKind: string | null;
  title: string;
  mode: 'read' | 'edit';
  sizePct: number;
}
interface WorkspaceCtx {
  panes: PaneState[];
  activePaneId: string;
  split: 'horizontal' | 'vertical';
  openInPane(paneId: string, obj: { id: string; kind: string; title: string }): void;
  addPane(): void;             // adds empty pane, redistributes sizePct evenly
  removePane(paneId: string): void;
  setActivePaneId(id: string): void;
  setSplit(dir: 'horizontal' | 'vertical'): void;
  // Backward-compat aliases (used by SearchResultCard, BacklinksPanel, etc.)
  openSidePane(obj: SidePaneObject): void;    // → opens in panes[1], adds if needed
  closeSidePane(): void;                       // → removes all panes except panes[0]
  sidePaneObject: SidePaneObject | null;       // → derived from panes[1]
}
```

Initial state: one pane with `{ id: 'main', objectId: null, objectKind: null, title: '', mode: 'read', sizePct: 100 }`.

`openSidePane(obj)` alias behavior:
- If `panes.length === 1`: add second pane at 40%, resize first to 60%
- Set `panes[1]` to the given object

`closeSidePane()` alias: filter panes to `panes[0]`, reset its `sizePct` to 100.

### AppShell.tsx refactor

Replace the current `flex` layout with `PanelGroup`:
```tsx
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';

// Inside AppShell render:
<div className="flex h-screen overflow-hidden">
  <Sidebar />
  <PanelGroup direction={split} autoSaveId="kos-workspace" className="flex-1 min-w-0">
    {panes.map((pane, i) => (
      <Fragment key={pane.id}>
        {i > 0 && (
          <PanelResizeHandle className="w-px bg-border data-[resize-handle-active]:bg-brand transition-colors" />
        )}
        <Panel defaultSize={pane.sizePct} minSize={20} id={pane.id}>
          {i === 0 ? (
            <main id="main-content" className="flex flex-col h-full overflow-auto">
              {children}
            </main>
          ) : (
            <PaneContainer pane={pane} />
          )}
        </Panel>
      </Fragment>
    ))}
  </PanelGroup>
</div>
```

### New PaneContainer.tsx

```tsx
interface PaneContainerProps { pane: PaneState }

// Header: [KindBadge] [title] [spacer] [OpenFull↗] [Close×]
// Body:   <ObjectPaneViewer kind={pane.objectKind} id={pane.objectId} mode={pane.mode} />
//         Empty state when objectId is null: "Open an object to view it here"
// Footer: [+ Add pane] shown only in last pane when panes.length < 4
```

### Files changed
| File | Change |
|---|---|
| `apps/web/src/components/workspace/WorkspaceLiteProvider.tsx` | Full rewrite |
| `apps/web/src/components/layout/AppShell.tsx` | Replace layout with PanelGroup |
| `apps/web/src/components/workspace/WorkspaceSidePane.tsx` | Delete (replaced by PaneContainer) |
| `apps/web/src/components/workspace/PaneContainer.tsx` | **NEW** |
| `apps/web/package.json` | Add `react-resizable-panels` |

**Commit:** `feat(workspace): multi-pane resizable layout with react-resizable-panels`

---

## Subtask 3 — Save/restore workspace UI

### Goal
Wire the Phase 8B REST API to the frontend so users can name, save, and restore workspace layouts.

### Frontend API helpers (`apps/web/src/lib/api.ts`)
```ts
export async function listWorkspaces(params?: { limit?: number; pinned_only?: boolean }): Promise<PaginatedResponse<WorkspaceOut>>
export async function createWorkspace(body: WorkspaceCreate): Promise<WorkspaceOut>
export async function getWorkspace(id: string): Promise<WorkspaceOut>
export async function updateWorkspace(id: string, body: WorkspaceUpdate): Promise<WorkspaceOut>
export async function deleteWorkspace(id: string): Promise<void>
export async function restoreWorkspace(id: string): Promise<WorkspaceOut>
```

### Types (`apps/web/src/types/index.ts`)
Add: `WorkspaceOut`, `WorkspaceCreate`, `WorkspaceUpdate`, `WorkspacePane` (mirrors `schemas/workspace.py`).

### WorkspaceLiteProvider additions
```ts
savedWorkspaceId: string | null;
saveWorkspace(name: string, description?: string): Promise<WorkspaceOut>;
loadWorkspace(id: string): Promise<void>;
```

`saveWorkspace`:
1. Build `WorkspaceLayout` from current `panes` state
2. Call `createWorkspace({ name, description, layout_json: layout })`
3. Set `savedWorkspaceId`

`loadWorkspace`:
1. Call `getWorkspace(id)` (updates `last_used_at` server-side)
2. Map `layout_json.panes` → `PaneState[]`
3. Replace current panes state

### New WorkspaceNameModal.tsx
- `Dialog` (from existing `components/ui/Dialog`)
- Name input (required), description textarea (optional)
- "Save" button → calls `saveWorkspace(name, description)` → shows success toast

### AppShell.tsx toolbar additions
- "Save Workspace" button (floppy disk icon, `Columns2` or similar)
  - Opens `WorkspaceNameModal`
  - Only shown when 2+ panes are open
- Workspace name chip (shown when `savedWorkspaceId !== null`)

### Sidebar.tsx additions
Below the nav items, before the footer:
```tsx
<section>
  <h3>Workspaces</h3>
  {workspaces.map(ws => (
    <button onClick={() => loadWorkspace(ws.id)}>{ws.name}</button>
    <button onClick={() => deleteWorkspace(ws.id)}>×</button>
  ))}
</section>
```
Data: `listWorkspaces({ limit: 5 })` called on mount with SWR/React Query or plain `useEffect`.

### Files changed
| File | Change |
|---|---|
| `apps/web/src/lib/api.ts` | Add workspace CRUD helpers |
| `apps/web/src/types/index.ts` | Add workspace types |
| `apps/web/src/components/workspace/WorkspaceLiteProvider.tsx` | Add `saveWorkspace`, `loadWorkspace`, `savedWorkspaceId` |
| `apps/web/src/components/layout/AppShell.tsx` | Add Save Workspace button + workspace name chip |
| `apps/web/src/components/layout/Sidebar.tsx` | Add Workspaces section |
| `apps/web/src/components/workspace/WorkspaceNameModal.tsx` | **NEW** |

**Commit:** `feat(workspace): save and restore named workspaces`

---

## Subtask 4 — Drag text between panes

### Goal
Select text in a source/page pane, drag it to a page pane in edit mode → inserts a `<blockquote>` with attribution and creates a `cites` edge.

### New hook `useCrossPane.ts`
```ts
export interface DragPayload {
  text: string;
  sourceObjectId: string;
  sourceKind: string;
  sourceTitle: string;
}

// Source side: call in drag start handler
export function useCrossPaneDragSource() {
  function onDragStart(e: DragEvent, payload: DragPayload) {
    e.dataTransfer!.setData('application/kos-pane-text', JSON.stringify(payload));
    e.dataTransfer!.effectAllowed = 'copy';
  }
  return { onDragStart };
}

// Target side: returns drop event props
export function useCrossPaneDrop(onDrop: (payload: DragPayload) => void) {
  return {
    onDragOver: (e: DragEvent) => { e.preventDefault(); e.dataTransfer!.dropEffect = 'copy'; },
    onDrop: (e: DragEvent) => {
      e.preventDefault();
      const raw = e.dataTransfer!.getData('application/kos-pane-text');
      if (raw) onDrop(JSON.parse(raw));
    },
  };
}
```

### SourcePaneView.tsx changes
- Wrap each extracted text paragraph with `draggable="true"`
- Listen for `dragstart`: capture `window.getSelection()?.toString()` as text, call `onDragStart`
- Visual: show drag handle icon (GripVertical) on hover

### PagePaneView.tsx changes
- When `mode === 'edit'` accept drops: use `useCrossPaneDrop`
- On drop:
  1. Insert via Tiptap `editor.commands.insertContent(...)`:
     ```json
     {
       "type": "blockquote",
       "content": [
         { "type": "paragraph", "content": [{ "type": "text", "text": "{draggedText}" }] },
         { "type": "paragraph", "content": [{ "type": "text", "marks": [{"type":"italic"}], "text": "— {sourceTitle}" }] }
       ]
     }
     ```
  2. Call `createEdge({ source_id: pageId, target_id: payload.sourceObjectId, kind: 'cites' })`
  3. Toast "Quote inserted + citation created"

### ObjectPaneViewer.tsx
Pass `editorRef` prop down to `PagePaneView` when `mode === 'edit'` so drop handler can call `editor.commands.insertContent`.

### Files changed
| File | Change |
|---|---|
| `apps/web/src/hooks/useCrossPane.ts` | **NEW** |
| `apps/web/src/components/workspace/SourcePaneView.tsx` | Add drag source |
| `apps/web/src/components/workspace/PagePaneView.tsx` | Add drop target + Tiptap insert + citation edge |
| `apps/web/src/components/workspace/ObjectPaneViewer.tsx` | Pass editor ref when mode=edit |

**Commit:** `feat(workspace): drag text from source pane to page pane creates quote block`

---

## Subtask 5 — Link pane to pane

### Goal
When 2+ panes show pages or sources, offer a "Link to…" button in the pane header that creates a typed graph edge between the two objects.

### PaneContainer.tsx header addition
- Show chain icon button when:
  - This pane has `objectId !== null`
  - At least one other pane also has `objectId !== null`
- Click → open `LinkPaneModal`

### New LinkPaneModal.tsx
```tsx
// Props: sourcePane: PaneState, otherPanes: PaneState[]
// UI:
//   "Link [sourcePane.title] to:"
//   List of other open panes with kind badge + title (radio select)
//   Edge kind picker (links_to | cites | mentions | supports | contradicts | related_to)
//   "Create link" button
//   On submit: POST /api/v1/edges → success toast → close
```

Reuse existing `EDGE_KIND_LABELS` constants if they exist in the codebase.

### Files changed
| File | Change |
|---|---|
| `apps/web/src/components/workspace/PaneContainer.tsx` | Add Link button |
| `apps/web/src/components/workspace/LinkPaneModal.tsx` | **NEW** |

**Commit:** `feat(workspace): link pane to pane creates typed graph edge`

---

## Subtask 6 — AI scoped to workspace

### Goal
`AiPanel`'s "Ask KB" feature gains a scope picker. Backend `POST /ai/answer` accepts `object_ids` to restrict the retrieval context.

### Backend changes

**`services/api/app/schemas/ai.py`** — update `AnswerRequest`:
```python
class AnswerRequest(BaseModel):
    q: str
    kind: str | None = None
    limit: int = 5
    object_ids: list[uuid.UUID] | None = None  # NEW: restrict to these objects
```

**`services/api/app/api/v1/ai.py`** — `answer` handler:
- Pass `object_ids` through to the search call in `hybrid_search` / `keyword_search`
- If `object_ids` is set and non-empty, filter search results to those objects (see Subtask 7 backend)

### Frontend changes

**`AiPanel.tsx`** — add scope selector above the Ask input:
```tsx
type AiScope = 'all' | 'this_pane' | 'all_panes';
// Radio group or segmented control:
// ○ All knowledge  ○ This pane  ○ All open panes
```
- When `all`: no `object_ids`
- When `this_pane`: `object_ids = [activePaneId's objectId]`
- When `all_panes`: `object_ids = panes.filter(p => p.objectId).map(p => p.objectId)`
- Pass to `POST /api/v1/ai/answer` body

**`apps/web/src/types/index.ts`** — update `AnswerRequest` type with `object_ids?: string[]`.

### Files changed
| File | Change |
|---|---|
| `services/api/app/schemas/ai.py` | Add `object_ids` to `AnswerRequest` |
| `services/api/app/api/v1/ai.py` | Pass `object_ids` to search in answer handler |
| `apps/web/src/components/graph/AiPanel.tsx` | Add scope picker |
| `apps/web/src/types/index.ts` | Update `AnswerRequest` type |

**Commit:** `feat(workspace): AI answer scoped to active workspace panes`

---

## Subtask 7 — Workspace-scoped search

### Goal
Search can be filtered to objects currently open in workspace panes. Both keyword and hybrid endpoints accept `object_ids`.

### Backend changes

**`services/api/app/api/v1/search.py`:**
- `GET /search/keyword`: add optional query param `object_ids: list[UUID] | None = Query(default=None)`
- `POST /search/hybrid`: add `object_ids: list[UUID] | None = None` to request body

**`services/api/app/search/search_service.py`:**
- In `keyword_search(...)` query: when `object_ids` is not None, add:
  ```sql
  AND objects.id = ANY(:object_ids)
  ```
- Same for hybrid search (applied to both keyword sub-query and vector result hydration)

### Frontend changes

**`apps/web/src/hooks/useSearch.ts`:**
- Add `objectIds?: string[]` param; forward to `hybridSearch` call

**`SearchModal.tsx` + `SearchCommand.tsx`:**
- When `panes.length > 1`: show "Search workspace only" checkbox/toggle
- When checked: pass `objectIds = panes.filter(p => p.objectId).map(p => p.objectId)`

### Files changed
| File | Change |
|---|---|
| `services/api/app/api/v1/search.py` | Add `object_ids` filter param |
| `services/api/app/search/search_service.py` | Add `object_ids` WHERE clause |
| `apps/web/src/hooks/useSearch.ts` | Add `objectIds` param |
| `apps/web/src/components/search/SearchModal.tsx` | Workspace filter toggle |
| `apps/web/src/components/search/SearchCommand.tsx` | Workspace filter toggle |

**Commit:** `feat(workspace): workspace-scoped search filters to open pane objects`

---

## Subtask 8 — Tests + docs

### Backend tests

**`tests/api/test_search.py`** — add:
- `test_keyword_search_with_object_ids_filter` — results contain only specified objects
- `test_keyword_search_object_ids_empty_returns_no_results`
- `test_hybrid_search_with_object_ids_filter`

**`tests/api/test_ai.py`** — add:
- `test_answer_with_object_ids_scoped` — mocked AI, confirms only scoped objects in context

### Frontend tests (`apps/web/src/test/`)
- `WorkspaceLiteProvider.test.tsx` — multi-pane state: add/remove panes, openSidePane compat
- `WorkspaceNameModal.test.tsx` — save flow with mocked `createWorkspace`
- `PaneContainer.test.tsx` — link button visibility rules, add/remove pane

### Docs
- `docs/ARCHITECTURE.md` — add multi-pane workspace section with layout diagram
- `PROGRESS.md` — flip all 8 Phase 8 subtasks to `[x]`, update Summary table

**Commit:** `test(workspace): coverage for multi-pane layout, scoped search, scoped AI`
**Commit:** `docs(workspace): update ARCHITECTURE.md and PROGRESS.md for Phase 8C`

---

## Verification Commands

```bash
# Backend tests
cd tests && PYTHONPATH=../services/api uv run --project ../services/api --extra dev pytest api/ -q

# MCP regression check
uv run --project services/mcp --extra dev pytest services/mcp/tests -v

# Frontend
pnpm -F web typecheck
pnpm -F web build
pnpm -F web test:run
```

### Manual smoke checklist
- [ ] Open app → Cmd+\ opens second pane → objects render side-by-side and resize
- [ ] Open page in left pane + source in right → drag selected source text → quote block appears in page with attribution
- [ ] With 2 panes open → "Link to…" header button → select other pane + edge kind → confirm edge in BacklinksPanel
- [ ] AiPanel scope → "All open panes" → answer only references those objects
- [ ] Cmd+K → "Search workspace only" toggle → results limited to pane objects
- [ ] Save Workspace → name it → reload page → Sidebar shows workspace → click → panes restore
- [ ] `pnpm -F web typecheck` clean
- [ ] `pnpm -F web build` clean

---

## Commit order

```
docs(phase-8): start Phase 8 multi-pane workspaces progress tracking
feat(workspace): multi-pane resizable layout with react-resizable-panels
feat(workspace): save and restore named workspaces
feat(workspace): drag text from source pane to page pane creates quote block
feat(workspace): link pane to pane creates typed graph edge
feat(workspace): AI answer scoped to active workspace panes
feat(workspace): workspace-scoped search filters to open pane objects
test(workspace): coverage for multi-pane layout, scoped search, scoped AI
docs(workspace): update ARCHITECTURE.md and PROGRESS.md for Phase 8C
```

---

## Progress update template (for PROGRESS.md)

### In progress
```markdown
## Phase 8C — Multi-Pane Workspaces 🚧 In Progress
**Goal:** Resizable multi-pane layout, save/restore workspaces, cross-pane drag-to-quote, pane linking, workspace-scoped AI, workspace-scoped search.
See [`project-phases/PHASE-8C-MULTI-PANE-WORKSPACES.md`](project-phases/PHASE-8C-MULTI-PANE-WORKSPACES.md).
- [ ] **Subtask 1** — Pane layout engine (2–4 resizable panes, react-resizable-panels)
- [ ] **Subtask 3** — Save/restore workspace UI (connects Phase 8B API)
- [ ] **Subtask 4** — Drag text between panes (quote block + cites edge)
- [ ] **Subtask 5** — Link pane to pane (typed edge creation)
- [ ] **Subtask 6** — AI scoped to workspace (context picker in AiPanel)
- [ ] **Subtask 7** — Workspace-scoped search (object_ids filter)
- [ ] **Subtask 8** — Tests + docs
```

### Complete
```markdown
## Phase 8C — Multi-Pane Workspaces ✅ Complete
- [x] **Subtask 1** — Resizable 2–4 pane layout; backward-compat `openSidePane`
- [x] **Subtask 3** — Save/restore workspaces; Sidebar workspace list; AppShell save button
- [x] **Subtask 4** — Cross-pane drag-to-quote with `cites` edge auto-creation
- [x] **Subtask 5** — Link pane to pane via `LinkPaneModal` + edges API
- [x] **Subtask 6** — AI scope picker: this pane / all panes / all KB
- [x] **Subtask 7** — Workspace-scoped keyword + hybrid search
- [x] **Subtask 8** — Tests (backend scoped search/AI + frontend workspace components) + docs
```
