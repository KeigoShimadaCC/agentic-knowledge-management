"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  BookOpen,
  Briefcase,
  FileText,
  Files,
  Image,
  Inbox,
  Layout,
  LogOut,
  MessageSquareText,
  Plug,
  Trash2,
  Trash,
} from "lucide-react";
import { clsx } from "clsx";
import { useEffect, useState } from "react";
import { PanelLeft } from "lucide-react";

import { logout, listWorkspaces, deleteWorkspace } from "@/lib/api";
import type { WorkspaceOut } from "@/types";
import { useAuth } from "@/lib/hooks/useAuth";
import { useSidebarState } from "@/lib/hooks/useSidebarState";
import { useShortcut } from "@/lib/hooks/useShortcut";
import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { useWorkspaceLite } from "@/components/workspace/WorkspaceLiteProvider";

const navItems = [
  { href: "/app", label: "All Objects", icon: Files },
  { href: "/app/pages", label: "Pages", icon: FileText },
  { href: "/app/assets", label: "Assets", icon: Image },
  { href: "/app/sources", label: "Sources", icon: BookOpen },
  { href: "/app/chats", label: "Chats", icon: MessageSquareText },
  { href: "/app/projects", label: "Projects", icon: Briefcase },
  { href: "/app/inbox", label: "Inbox", icon: Inbox },
  { href: "/app/settings/mcp", label: "MCP", icon: Plug },
  { href: "/app/trash", label: "Trash", icon: Trash2 },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isLoading, mutate } = useAuth();
  const [signingOut, setSigningOut] = useState(false);
  const { collapsed, toggle } = useSidebarState();
  const { loadWorkspace } = useWorkspaceLite();
  const [workspaces, setWorkspaces] = useState<WorkspaceOut[]>([]);
  const [wsExpanded, setWsExpanded] = useState(false);

  useEffect(() => {
    if (wsExpanded) {
      listWorkspaces({ limit: 5 })
        .then((res) => setWorkspaces(res.items))
        .catch(() => {});
    }
  }, [wsExpanded]);

  useShortcut("\\", (e) => {
    if (e.metaKey || e.ctrlKey) {
      e.preventDefault();
      toggle();
    }
  });

  async function handleSignOut() {
    setSigningOut(true);
    try {
      await logout();
      await mutate(undefined, { revalidate: false });
      router.push("/login");
      router.refresh();
    } catch {
      setSigningOut(false);
    }
  }

  return (
    <aside className={clsx(
      "flex h-full shrink-0 flex-col border-r border-gray-800 bg-gray-900 transition-all duration-base",
      collapsed ? "w-14" : "w-60"
    )}>
      <div className="flex items-center justify-between border-b border-gray-800 p-4">
        {!collapsed && (
          <span className="text-lg font-bold tracking-tight text-white">KnowledgeOS</span>
        )}
        <button
          type="button"
          onClick={toggle}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          title={collapsed ? "Expand (⌘\\)" : "Collapse (⌘\\)"}
          className={clsx(
            "rounded p-1 text-gray-400 hover:bg-gray-800 hover:text-white transition-colors",
            collapsed && "mx-auto"
          )}
        >
          <PanelLeft size={16} />
        </button>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto p-2">
        {navItems.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            title={collapsed ? label : undefined}
            className={clsx(
              "flex items-center rounded-lg px-3 py-2 text-sm transition-colors",
              collapsed ? "justify-center gap-0" : "gap-2.5",
              pathname === href
                ? "bg-gray-700 text-white"
                : "text-gray-400 hover:bg-gray-800 hover:text-white"
            )}
          >
            <Icon size={16} />
            {!collapsed && label}
          </Link>
        ))}

        {/* Workspaces section */}
        <div className="pt-2">
          <button
            type="button"
            onClick={() => setWsExpanded((v) => !v)}
            title={collapsed ? "Workspaces" : undefined}
            className={clsx(
              "flex w-full items-center rounded-lg px-3 py-2 text-sm text-gray-400 transition-colors hover:bg-gray-800 hover:text-white",
              collapsed ? "justify-center gap-0" : "gap-2.5"
            )}
          >
            <Layout size={16} />
            {!collapsed && (
              <>
                <span className="flex-1 text-left">Workspaces</span>
                <span className="text-xs">{wsExpanded ? "▲" : "▼"}</span>
              </>
            )}
          </button>
          {!collapsed && wsExpanded && (
            <div className="ml-4 mt-1 space-y-0.5">
              {workspaces.length === 0 && (
                <p className="px-3 py-1.5 text-xs text-gray-600">No saved workspaces</p>
              )}
              {workspaces.map((ws) => (
                <div key={ws.id} className="group flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => void loadWorkspace(ws.id)}
                    className="min-w-0 flex-1 truncate rounded px-2 py-1.5 text-left text-xs text-gray-400 hover:bg-gray-800 hover:text-white"
                    title={ws.name}
                  >
                    {ws.name}
                  </button>
                  <button
                    type="button"
                    onClick={async () => {
                      await deleteWorkspace(ws.id);
                      setWorkspaces((prev) => prev.filter((w) => w.id !== ws.id));
                    }}
                    aria-label={`Delete workspace ${ws.name}`}
                    className="hidden shrink-0 rounded p-1 text-gray-600 hover:text-red-400 group-hover:block"
                  >
                    <Trash size={12} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </nav>

      <div className="shrink-0 space-y-2 border-t border-gray-800 p-3">
        <div className={clsx("flex", collapsed ? "justify-center" : "justify-end px-1")}>
          <ThemeToggle />
        </div>
        {!isLoading && user ? (
          <>
            {!collapsed && (
              <p className="truncate px-2 text-xs text-gray-500" title={user.email}>
                {user.display_name?.trim() || user.email}
              </p>
            )}
            <button
              type="button"
              disabled={signingOut}
              onClick={() => void handleSignOut()}
              title={collapsed ? "Sign out" : undefined}
              className={clsx(
                "flex w-full items-center rounded-lg px-3 py-2 text-sm text-gray-400 transition-colors hover:bg-gray-800 hover:text-white disabled:opacity-50",
                collapsed ? "justify-center gap-0" : "gap-2"
              )}
            >
              <LogOut size={16} aria-hidden />
              {!collapsed && (signingOut ? "Signing out…" : "Sign out")}
            </button>
          </>
        ) : null}
      </div>
    </aside>
  );
}
