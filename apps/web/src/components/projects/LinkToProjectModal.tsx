"use client";

import { useEffect, useState } from "react";
import { Search, X } from "lucide-react";

import { createEdge, hybridSearch } from "@/lib/api";
import { objectKindLabel } from "@/lib/objectRouting";
import { toast } from "@/components/ui/Toast";
import type { SearchResult } from "@/types";

interface LinkToProjectModalProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  onLinked: () => void;
}

const KIND_FILTERS = [
  { label: "All", value: "" },
  { label: "Pages", value: "page" },
  { label: "Sources", value: "source" },
  { label: "Chats", value: "chat" },
];

export function LinkToProjectModal({
  projectId,
  isOpen,
  onClose,
  onLinked,
}: LinkToProjectModalProps) {
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    const trimmed = query.trim();
    if (!trimmed) {
      setResults([]);
      return;
    }
    setLoading(true);
    const timeout = window.setTimeout(() => {
      hybridSearch(trimmed, { kind: kind || undefined, limit: 12 })
        .then((response) =>
          setResults(response.results.filter((result) => result.id !== projectId))
        )
        .catch((err) =>
          toast.error("Could not search objects", {
            description: err instanceof Error ? err.message : undefined,
          })
        )
        .finally(() => setLoading(false));
    }, 250);
    return () => window.clearTimeout(timeout);
  }, [isOpen, kind, projectId, query]);

  if (!isOpen) return null;

  async function linkObject(result: SearchResult) {
    try {
      await createEdge({
        source_id: result.id,
        target_id: projectId,
        kind: "belongs_to_project",
      });
      toast.success("Evidence linked");
      onLinked();
      onClose();
    } catch (err) {
      toast.error("Could not link evidence", {
        description: err instanceof Error ? err.message : undefined,
      });
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="w-full max-w-2xl rounded-lg border border-gray-800 bg-gray-950 shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-800 px-4 py-3">
          <h2 className="text-sm font-medium text-white">Link evidence</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-gray-500 hover:bg-gray-800 hover:text-white"
            aria-label="Close"
          >
            <X size={16} />
          </button>
        </div>
        <div className="space-y-3 p-4">
          <label className="flex items-center gap-2 rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-300">
            <Search size={16} />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search pages, sources, or chats"
              className="min-w-0 flex-1 bg-transparent text-gray-100 outline-none placeholder:text-gray-500"
            />
          </label>
          <div className="flex flex-wrap gap-2">
            {KIND_FILTERS.map((filter) => (
              <button
                key={filter.label}
                type="button"
                onClick={() => setKind(filter.value)}
                className={
                  kind === filter.value
                    ? "rounded-md border border-gray-500 bg-gray-700 px-3 py-1.5 text-xs text-white"
                    : "rounded-md border border-gray-800 px-3 py-1.5 text-xs text-gray-400 hover:border-gray-700 hover:text-gray-200"
                }
              >
                {filter.label}
              </button>
            ))}
          </div>
        </div>
        <div className="max-h-96 overflow-y-auto border-t border-gray-800">
          {loading ? (
            <div className="px-4 py-6 text-sm text-gray-400">Searching...</div>
          ) : query.trim() && results.length === 0 ? (
            <div className="px-4 py-6 text-sm text-gray-400">No objects found.</div>
          ) : !query.trim() ? (
            <div className="px-4 py-6 text-sm text-gray-400">Search for evidence.</div>
          ) : (
            results.map((result) => (
              <button
                type="button"
                key={result.id}
                onClick={() => void linkObject(result)}
                className="block w-full border-b border-gray-900 px-4 py-3 text-left hover:bg-gray-900"
              >
                <span className="flex items-center gap-2">
                  <span className="rounded border border-gray-700 px-1.5 py-0.5 text-[10px] uppercase text-gray-400">
                    {objectKindLabel(result.kind)}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-sm text-gray-100">
                    {result.title || "Untitled object"}
                  </span>
                </span>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
