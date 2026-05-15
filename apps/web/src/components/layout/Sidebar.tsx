"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  BookOpen,
  FileText,
  Files,
  Image,
  Inbox,
  LogOut,
  MessageSquareText,
  Trash2,
} from "lucide-react";
import { clsx } from "clsx";
import { useState } from "react";
import { PanelLeft } from "lucide-react";

import { logout } from "@/lib/api";
import { useAuth } from "@/lib/hooks/useAuth";
import { useSidebarState } from "@/lib/hooks/useSidebarState";
import { useShortcut } from "@/lib/hooks/useShortcut";

const navItems = [
  { href: "/app", label: "All Objects", icon: Files },
  { href: "/app/pages", label: "Pages", icon: FileText },
  { href: "/app/assets", label: "Assets", icon: Image },
  { href: "/app/sources", label: "Sources", icon: BookOpen },
  { href: "/app/chats", label: "Chats", icon: MessageSquareText },
  { href: "/app/inbox", label: "Inbox", icon: Inbox },
  { href: "/app/trash", label: "Trash", icon: Trash2 },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isLoading, mutate } = useAuth();
  const [signingOut, setSigningOut] = useState(false);
  const { collapsed, toggle } = useSidebarState();

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
      </nav>

      <div className="shrink-0 space-y-2 border-t border-gray-800 p-3">
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
