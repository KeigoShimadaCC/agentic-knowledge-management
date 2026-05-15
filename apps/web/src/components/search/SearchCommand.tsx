/**
 * @example
 * <SearchCommand isOpen={open} onClose={() => setOpen(false)} />
 */
"use client";

import { useEffect, useRef, useState } from "react";
import { Command } from "cmdk";
import { useRouter } from "next/navigation";
import { BookOpen, type LucideProps, FileText, Files, Image, MessageSquareText, Search } from "lucide-react";
import { cn } from "@/lib/cn";
import { useSearch } from "@/lib/hooks/useSearch";
import { objectRoute } from "@/lib/objectRouting";
import { useWorkspaceLite } from "@/components/workspace/WorkspaceLiteProvider";
import { SearchFilters } from "./SearchFilters";
import { addRecentSearch, getRecentSearches } from "./RecentSearches";

type LucideIcon = React.ForwardRefExoticComponent<Omit<LucideProps, "ref"> & React.RefAttributes<SVGSVGElement>>;

const KIND_ICONS: Record<string, LucideIcon> = {
  page: FileText,
  asset: Image,
  source: BookOpen,
  chat: MessageSquareText,
};

function KindIcon({ kind, size, className }: { kind: string; size?: number; className?: string }) {
  const Icon = KIND_ICONS[kind] ?? Files;
  return <Icon size={size} className={className} />;
}

interface SearchCommandProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SearchCommand({ isOpen, onClose }: SearchCommandProps) {
  const router = useRouter();
  const { openSidePane } = useWorkspaceLite();
  const { results, isLoading, query, setQuery } = useSearch();
  const [kindFilter, setKindFilter] = useState("");
  const [recents, setRecents] = useState<string[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setRecents(getRecentSearches());
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const filtered = kindFilter
    ? results.filter((r) => r.kind === kindFilter)
    : results;

  function navigateTo(kind: string, id: string) {
    if (query.trim()) addRecentSearch(query.trim());
    onClose();
    router.push(objectRoute(kind, id));
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center px-4 pt-16">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative w-full max-w-xl overflow-hidden rounded-xl border border-gray-700 bg-gray-950 shadow-2xl">
        <Command shouldFilter={false} className="flex flex-col">
          <div className="flex items-center gap-3 border-b border-gray-800 px-4 py-3">
            <Search size={16} className="shrink-0 text-gray-400" />
            <Command.Input
              ref={inputRef}
              value={query}
              onValueChange={setQuery}
              placeholder="Search knowledge base…"
              className="flex-1 bg-transparent text-sm text-gray-100 outline-none placeholder:text-gray-500"
            />
            {isLoading && (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-gray-400 border-t-transparent" />
            )}
            <kbd className="rounded bg-gray-800 px-1.5 py-0.5 text-xs text-gray-500">Esc</kbd>
          </div>

          <SearchFilters activeKind={kindFilter} onChange={setKindFilter} />

          <Command.List className="max-h-80 overflow-y-auto">
            {!query && recents.length > 0 && (
              <Command.Group heading="Recent searches" className="px-2 py-1">
                {recents.map((q) => (
                  <Command.Item
                    key={q}
                    value={q}
                    onSelect={() => setQuery(q)}
                    className={cn(
                      "flex cursor-pointer items-center gap-2 rounded-md px-3 py-2 text-sm text-gray-400",
                      "aria-selected:bg-gray-800 aria-selected:text-white"
                    )}
                  >
                    <Search size={12} className="shrink-0" />
                    {q}
                  </Command.Item>
                ))}
              </Command.Group>
            )}

            {query.length >= 2 && filtered.length === 0 && !isLoading && (
              <Command.Empty className="px-4 py-6 text-center text-sm text-gray-500">
                No results found
              </Command.Empty>
            )}

            {filtered.length > 0 && (
              <Command.Group heading="Results" className="px-2 py-1">
                {filtered.map((result) => (
                  <Command.Item
                    key={result.id}
                    value={result.id}
                    onSelect={() => navigateTo(result.kind, result.id)}
                    className={cn(
                      "flex cursor-pointer items-center gap-2.5 rounded-md px-3 py-2 text-sm",
                      "aria-selected:bg-gray-800"
                    )}
                  >
                    <KindIcon kind={result.kind} size={14} className="shrink-0 text-gray-400" />
                    <span className="min-w-0 flex-1 truncate text-gray-100">{result.title}</span>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        openSidePane(result);
                        onClose();
                      }}
                      className="shrink-0 rounded px-1.5 py-0.5 text-xs text-gray-500 hover:bg-gray-700 hover:text-gray-200"
                    >
                      Side pane
                    </button>
                    <span className="shrink-0 text-xs capitalize text-gray-600">{result.kind}</span>
                  </Command.Item>
                ))}
              </Command.Group>
            )}

            {!query && recents.length === 0 && (
              <p className="px-4 py-6 text-center text-xs text-gray-600">
                Type at least 2 characters to search
              </p>
            )}
          </Command.List>

          <div className="flex items-center justify-between border-t border-gray-800 px-4 py-2 text-xs text-gray-600">
            <span>{filtered.length > 0 ? `${filtered.length} result${filtered.length !== 1 ? "s" : ""}` : ""}</span>
            <span>↑↓ navigate · Enter open</span>
          </div>
        </Command>
      </div>
    </div>
  );
}
