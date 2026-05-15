"use client";

import { Fragment, useEffect, useState } from "react";
import { Group as PanelGroup, Panel, Separator as PanelResizeHandle } from "react-resizable-panels";
import { SearchModal } from "@/components/search/SearchModal";
import { SearchCommand } from "@/components/search/SearchCommand";
import { ShortcutOverlay } from "@/components/help/ShortcutOverlay";
import { PaneContainer } from "@/components/workspace/PaneContainer";
import { useWorkspaceLite } from "@/components/workspace/WorkspaceLiteProvider";
import { Sidebar } from "./Sidebar";
import { MobileNav } from "./MobileNav";
import { useSidebarState } from "@/lib/hooks/useSidebarState";

const useV2Search = process.env.NEXT_PUBLIC_UX_SEARCH_V2 === "1";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [searchOpen, setSearchOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const { toggle } = useSidebarState();
  const { panes, split } = useWorkspaceLite();

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement;
      const inInput = target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable;

      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSearchOpen(true);
        return;
      }
      if (event.key === "?" && !inInput && !event.metaKey && !event.ctrlKey) {
        event.preventDefault();
        setShortcutsOpen((v) => !v);
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  const sidePanes = panes.slice(1);
  const handleClass =
    split === "horizontal"
      ? "w-1 bg-gray-800 hover:bg-blue-600 cursor-col-resize transition-colors"
      : "h-1 bg-gray-800 hover:bg-blue-600 cursor-row-resize transition-colors";

  return (
    <div className="flex h-screen overflow-hidden bg-gray-950">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header role="banner">
          <MobileNav onOpen={toggle} />
        </header>
        <PanelGroup orientation={split} className="min-h-0 flex-1">
          <Panel defaultSize={panes[0]?.sizePct ?? 100} minSize={20}>
            <main id="main-content" className="h-full overflow-y-auto">
              {children}
            </main>
          </Panel>
          {sidePanes.map((pane, i) => (
            <Fragment key={pane.id}>
              <PanelResizeHandle className={handleClass} />
              <Panel defaultSize={pane.sizePct} minSize={20}>
                <PaneContainer pane={pane} isLast={i === sidePanes.length - 1} />
              </Panel>
            </Fragment>
          ))}
        </PanelGroup>
      </div>
      {useV2Search
        ? <SearchCommand isOpen={searchOpen} onClose={() => setSearchOpen(false)} />
        : <SearchModal isOpen={searchOpen} onClose={() => setSearchOpen(false)} />
      }
      <ShortcutOverlay open={shortcutsOpen} onOpenChange={setShortcutsOpen} />
    </div>
  );
}
