"use client";

import { createContext, useContext, useState, useCallback, type ReactNode } from "react";

export interface SidePaneObject {
  id: string;
  kind: string;
  title: string;
}

interface WorkspaceLiteContextValue {
  sidePaneObject: SidePaneObject | null;
  openSidePane: (obj: SidePaneObject) => void;
  closeSidePane: () => void;
}

const WorkspaceLiteContext = createContext<WorkspaceLiteContextValue | null>(null);

export function WorkspaceLiteProvider({ children }: { children: ReactNode }) {
  const [sidePaneObject, setSidePaneObject] = useState<SidePaneObject | null>(null);

  const openSidePane = useCallback((obj: SidePaneObject) => {
    setSidePaneObject(obj);
  }, []);

  const closeSidePane = useCallback(() => {
    setSidePaneObject(null);
  }, []);

  return (
    <WorkspaceLiteContext.Provider value={{ sidePaneObject, openSidePane, closeSidePane }}>
      {children}
    </WorkspaceLiteContext.Provider>
  );
}

export function useWorkspaceLite(): WorkspaceLiteContextValue {
  const ctx = useContext(WorkspaceLiteContext);
  if (!ctx) throw new Error("useWorkspaceLite must be used inside WorkspaceLiteProvider");
  return ctx;
}
