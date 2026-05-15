"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import {
  createWorkspace,
  getWorkspace,
} from "@/lib/api";
import type { WorkspaceOut, WorkspacePaneAPI, WorkspaceLayoutAPI } from "@/types";

export interface SidePaneObject {
  id: string;
  kind: string;
  title: string;
}

export interface PaneState {
  id: string;
  objectId: string | null;
  objectKind: string | null;
  title: string;
  mode: "read" | "edit";
  sizePct: number;
}

export type WorkspaceSplit = "horizontal" | "vertical";

export interface WorkspaceCtx {
  panes: PaneState[];
  activePaneId: string;
  split: WorkspaceSplit;
  openInPane: (paneId: string, obj: SidePaneObject) => void;
  addPane: () => void;
  removePane: (paneId: string) => void;
  setActivePaneId: (id: string) => void;
  setSplit: (dir: WorkspaceSplit) => void;
  savedWorkspaceId: string | null;
  setSavedWorkspaceId: (id: string | null) => void;
  saveWorkspace: (name: string, description?: string) => Promise<WorkspaceOut>;
  loadWorkspace: (id: string) => Promise<void>;
  // Backward-compat aliases
  sidePaneObject: SidePaneObject | null;
  openSidePane: (obj: SidePaneObject) => void;
  closeSidePane: () => void;
}

const WorkspaceLiteContext = createContext<WorkspaceCtx | null>(null);

const MAIN_PANE_ID = "main";
let _counter = 0;
function newPaneId() { return `pane-${++_counter}`; }

function makeMain(): PaneState {
  return { id: MAIN_PANE_ID, objectId: null, objectKind: null, title: "", mode: "read", sizePct: 100 };
}

export function WorkspaceLiteProvider({ children }: { children: ReactNode }) {
  const [panes, setPanes] = useState<PaneState[]>([makeMain()]);
  const [activePaneId, setActivePaneId] = useState<string>(MAIN_PANE_ID);
  const [split, setSplit] = useState<WorkspaceSplit>("horizontal");
  const [savedWorkspaceId, setSavedWorkspaceId] = useState<string | null>(null);

  const openInPane = useCallback((paneId: string, obj: SidePaneObject) => {
    setPanes((prev) =>
      prev.map((p) =>
        p.id === paneId ? { ...p, objectId: obj.id, objectKind: obj.kind, title: obj.title } : p
      )
    );
    setActivePaneId(paneId);
  }, []);

  const addPane = useCallback(() => {
    setPanes((prev) => {
      if (prev.length >= 4) return prev;
      const count = prev.length + 1;
      const newSize = Math.floor(100 / count);
      const rem = 100 - newSize * count;
      return [
        ...prev.map((p, i): PaneState => ({ ...p, sizePct: newSize + (i === 0 ? rem : 0) })),
        { id: newPaneId(), objectId: null, objectKind: null, title: "", mode: "read" as const, sizePct: newSize },
      ];
    });
  }, []);

  const removePane = useCallback((paneId: string) => {
    if (paneId === MAIN_PANE_ID) return;
    setPanes((prev) => {
      const filtered = prev.filter((p) => p.id !== paneId);
      if (filtered.length === 1) return [{ ...filtered[0]!, sizePct: 100 }];
      const total = filtered.reduce((s, p) => s + p.sizePct, 0);
      return filtered.map((p): PaneState => ({ ...p, sizePct: Math.round((p.sizePct / total) * 100) }));
    });
    setActivePaneId((cur) => (cur === paneId ? MAIN_PANE_ID : cur));
  }, []);

  // ── Backward-compat aliases ────────────────────────────────────────────────
  const p1 = panes[1];
  const sidePaneObject: SidePaneObject | null =
    p1 && p1.objectId
      ? { id: p1.objectId, kind: p1.objectKind!, title: p1.title }
      : null;

  const openSidePane = useCallback((obj: SidePaneObject) => {
    setPanes((prev) => {
      if (prev.length === 1) {
        const sid = newPaneId();
        setTimeout(() => setActivePaneId(sid), 0);
        return [
          { ...prev[0]!, sizePct: 60 },
          { id: sid, objectId: obj.id, objectKind: obj.kind, title: obj.title, mode: "read", sizePct: 40 },
        ];
      }
      setTimeout(() => setActivePaneId(prev[1]?.id ?? MAIN_PANE_ID), 0);
      return prev.map((p, i): PaneState =>
        i === 1 ? { ...p, objectId: obj.id, objectKind: obj.kind, title: obj.title } : p
      );
    });
  }, []);

  const closeSidePane = useCallback(() => {
    setPanes((prev) => [{ ...prev[0]!, sizePct: 100 }]);
    setActivePaneId(MAIN_PANE_ID);
  }, []);

  const saveWorkspace = useCallback(
    async (name: string, description?: string): Promise<WorkspaceOut> => {
      const apiPanes: WorkspacePaneAPI[] = panes.map((p) => ({
        id: p.id,
        object_id: p.objectId,
        object_kind: p.objectKind,
        size_pct: Math.max(5, Math.min(95, p.sizePct)),
        mode: p.mode,
      }));
      const layout: WorkspaceLayoutAPI = {
        version: 1,
        split: panes.length >= 2 ? split : null,
        panes: apiPanes,
        active_pane_id: activePaneId,
      };
      const ws = await createWorkspace({ name, description: description ?? null, layout });
      setSavedWorkspaceId(String(ws.id));
      return ws;
    },
    [panes, split, activePaneId]
  );

  const loadWorkspace = useCallback(async (id: string): Promise<void> => {
    const ws = await getWorkspace(id);
    const restored: PaneState[] = ws.layout.panes.map((p) => ({
      id: p.id,
      objectId: p.object_id,
      objectKind: p.object_kind,
      title: "",
      mode: p.mode,
      sizePct: p.size_pct,
    }));
    setPanes(restored);
    if (ws.layout.split) setSplit(ws.layout.split);
    setActivePaneId(ws.layout.active_pane_id);
    setSavedWorkspaceId(String(ws.id));
  }, []);

  return (
    <WorkspaceLiteContext.Provider
      value={{
        panes, activePaneId, split,
        openInPane, addPane, removePane, setActivePaneId, setSplit,
        savedWorkspaceId, setSavedWorkspaceId,
        saveWorkspace, loadWorkspace,
        sidePaneObject, openSidePane, closeSidePane,
      }}
    >
      {children}
    </WorkspaceLiteContext.Provider>
  );
}

export function useWorkspaceLite(): WorkspaceCtx {
  const ctx = useContext(WorkspaceLiteContext);
  if (!ctx) throw new Error("useWorkspaceLite must be used inside WorkspaceLiteProvider");
  return ctx;
}
