"use client";

import { useEffect, useState } from "react";
import { Search, X } from "lucide-react";
import { keywordSearch } from "@/lib/api";
import type { SearchResult } from "@/types";

interface ObjectPickerProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (id: string, kind: string, title: string) => void;
  excludeId?: string;
}

function KindBadge({ kind }: { kind: string }) {
  const className =
    kind === "page"
      ? "bg-blue-950 text-blue-300 border-blue-800"
      : kind === "source"
        ? "bg-green-950 text-green-300 border-green-800"
        : "bg-gray-900 text-gray-300 border-gray-700";

  return (
    <span className={`rounded border px-1.5 py-0.5 text-[10px] uppercase ${className}`}>
      {kind}
    </span>
  );
}

export function ObjectPicker({ isOpen, onClose, onSelect, excludeId }: ObjectPickerProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!isOpen) return;

    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      setResults([]);
      setIsLoading(false);
      setError(null);
      return;
    }

    let isMounted = true;
    setIsLoading(true);
    setError(null);

    const timeout = window.setTimeout(() => {
      keywordSearch(trimmedQuery, { limit: 10 })
        .then((response) => {
          if (!isMounted) return;
          setResults(response.results.filter((result) => result.id !== excludeId));
        })
        .catch(() => {
          if (isMounted) setError("Could not search objects.");
        })
        .finally(() => {
          if (isMounted) setIsLoading(false);
        });
    }, 300);

    return () => {
      isMounted = false;
      window.clearTimeout(timeout);
    };
  }, [excludeId, isOpen, query]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-lg rounded border border-gray-700 bg-gray-950 shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-800 px-4 py-3">
          <h2 className="text-sm font-medium text-gray-100">Select object</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-gray-400 hover:bg-gray-800 hover:text-white"
            title="Close"
          >
            <X size={16} />
          </button>
        </div>
        <div className="p-4">
          <label className="flex items-center gap-2 rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-300">
            <Search size={16} />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search objects"
              className="min-w-0 flex-1 bg-transparent text-gray-100 outline-none placeholder:text-gray-500"
            />
          </label>
        </div>
        <div className="max-h-80 overflow-y-auto border-t border-gray-800">
          {isLoading ? (
            <div className="px-4 py-6 text-sm text-gray-400">Searching objects...</div>
          ) : error ? (
            <div className="px-4 py-6 text-sm text-red-400">{error}</div>
          ) : !query.trim() ? (
            <div className="px-4 py-6 text-sm text-gray-400">Search for an object.</div>
          ) : results.length === 0 ? (
            <div className="px-4 py-6 text-sm text-gray-400">No objects found.</div>
          ) : (
            results.map((result) => (
              <button
                type="button"
                key={result.id}
                onClick={() => {
                  onSelect(result.id, result.kind, result.title);
                  onClose();
                }}
                className="block w-full border-b border-gray-900 px-4 py-3 text-left hover:bg-gray-900"
              >
                <span className="flex items-center gap-2">
                  <KindBadge kind={result.kind} />
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
