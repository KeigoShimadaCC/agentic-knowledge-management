"use client";

import { Search, LayoutGrid, LayoutList } from "lucide-react";
import { cn } from "@/lib/cn";

export type SortKey = "newest" | "oldest" | "title";
export type ViewMode = "list" | "grid";

interface ListToolbarProps {
  search: string;
  onSearch: (q: string) => void;
  sort: SortKey;
  onSort: (s: SortKey) => void;
  viewMode?: ViewMode;
  onViewMode?: (v: ViewMode) => void;
  searchPlaceholder?: string;
  className?: string;
}

export function ListToolbar({
  search,
  onSearch,
  sort,
  onSort,
  viewMode,
  onViewMode,
  searchPlaceholder = "Filter…",
  className,
}: ListToolbarProps) {
  return (
    <div className={cn("flex items-center gap-2 pb-4", className)}>
      <div className="relative flex-1">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" />
        <input
          type="text"
          value={search}
          onChange={(e) => onSearch(e.target.value)}
          placeholder={searchPlaceholder}
          className="h-8 w-full rounded-md border border-gray-700 bg-gray-900 pl-8 pr-3 text-sm text-gray-200 placeholder:text-gray-600 focus:border-gray-500 focus:outline-none"
        />
      </div>

      <select
        value={sort}
        onChange={(e) => onSort(e.target.value as SortKey)}
        className="h-8 rounded-md border border-gray-700 bg-gray-900 px-2 text-xs text-gray-400 focus:border-gray-500 focus:outline-none"
      >
        <option value="newest">Newest</option>
        <option value="oldest">Oldest</option>
        <option value="title">Title</option>
      </select>

      {onViewMode && (
        <div className="flex rounded-md border border-gray-700 overflow-hidden">
          <button
            type="button"
            onClick={() => onViewMode("list")}
            className={cn(
              "flex h-8 w-8 items-center justify-center text-xs transition-colors",
              viewMode === "list" ? "bg-gray-700 text-white" : "bg-gray-900 text-gray-500 hover:text-gray-300"
            )}
            aria-label="List view"
          >
            <LayoutList size={14} />
          </button>
          <button
            type="button"
            onClick={() => onViewMode("grid")}
            className={cn(
              "flex h-8 w-8 items-center justify-center text-xs transition-colors",
              viewMode === "grid" ? "bg-gray-700 text-white" : "bg-gray-900 text-gray-500 hover:text-gray-300"
            )}
            aria-label="Grid view"
          >
            <LayoutGrid size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
