"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FileText, Files, Image, Trash2 } from "lucide-react";
import { clsx } from "clsx";

const navItems = [
  { href: "/app", label: "All Objects", icon: Files },
  { href: "/app/pages", label: "Pages", icon: FileText },
  { href: "/app/assets", label: "Assets", icon: Image },
  { href: "/app/trash", label: "Trash", icon: Trash2 },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-60 shrink-0 flex flex-col bg-gray-900 border-r border-gray-800 h-full">
      <div className="p-4 border-b border-gray-800">
        <span className="text-lg font-bold text-white tracking-tight">KnowledgeOS</span>
      </div>

      <nav className="flex-1 p-2 space-y-1 overflow-y-auto">
        {navItems.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={clsx(
              "flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors",
              pathname === href
                ? "bg-gray-700 text-white"
                : "text-gray-400 hover:text-white hover:bg-gray-800"
            )}
          >
            <Icon size={16} />
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
