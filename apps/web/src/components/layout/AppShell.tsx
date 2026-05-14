"use client";

import { useEffect, useState } from "react";
import { SearchModal } from "@/components/search/SearchModal";
import { WorkspaceSidePane } from "@/components/workspace/WorkspaceSidePane";
import { Sidebar } from "./Sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [searchOpen, setSearchOpen] = useState(false);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSearchOpen(true);
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-gray-950">
      <Sidebar />
      <main className="min-w-0 flex-1 overflow-y-auto">{children}</main>
      <WorkspaceSidePane />
      <SearchModal isOpen={searchOpen} onClose={() => setSearchOpen(false)} />
    </div>
  );
}
