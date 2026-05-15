"use client";

import { useEffect, useState } from "react";
import { SearchModal } from "@/components/search/SearchModal";
import { SearchCommand } from "@/components/search/SearchCommand";
import { WorkspaceSidePane } from "@/components/workspace/WorkspaceSidePane";
import { ShortcutOverlay } from "@/components/help/ShortcutOverlay";
import { Sidebar } from "./Sidebar";
import { MobileNav } from "./MobileNav";
import { useSidebarState } from "@/lib/hooks/useSidebarState";

const useV2Search = process.env.NEXT_PUBLIC_UX_SEARCH_V2 === "1";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [searchOpen, setSearchOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const { toggle } = useSidebarState();

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

  return (
    <div className="flex h-screen overflow-hidden bg-gray-950">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <MobileNav onOpen={toggle} />
        <main id="main-content" className="min-w-0 flex-1 overflow-y-auto">{children}</main>
      </div>
      <WorkspaceSidePane />
      {useV2Search
        ? <SearchCommand isOpen={searchOpen} onClose={() => setSearchOpen(false)} />
        : <SearchModal isOpen={searchOpen} onClose={() => setSearchOpen(false)} />
      }
      <ShortcutOverlay open={shortcutsOpen} onOpenChange={setShortcutsOpen} />
    </div>
  );
}
