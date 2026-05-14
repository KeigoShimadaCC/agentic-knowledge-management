"use client";

import { useEffect, useMemo, useState } from "react";
import { Search, X } from "lucide-react";
import { listSources } from "@/lib/api";
import type { SourceOut } from "@/types";

interface SourcePickerProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (id: string, title: string) => void;
}

export function SourcePicker({ isOpen, onClose, onSelect }: SourcePickerProps) {
  const [sources, setSources] = useState<SourceOut[]>([]);
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;
    setIsLoading(true);
    setError(null);

    listSources()
      .then((items) => {
        if (isMounted) setSources(items);
      })
      .catch(() => {
        if (isMounted) setError("Could not load sources.");
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen]);

  const filteredSources = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) return sources;

    return sources.filter((source) => {
      const haystack = [
        source.title,
        source.description ?? "",
        source.source_type,
        source.url ?? "",
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(normalizedQuery);
    });
  }, [query, sources]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-lg rounded border border-gray-700 bg-gray-950 shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-800 px-4 py-3">
          <h2 className="text-sm font-medium text-gray-100">Select source</h2>
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
              placeholder="Search sources"
              className="min-w-0 flex-1 bg-transparent text-gray-100 outline-none placeholder:text-gray-500"
            />
          </label>
        </div>
        <div className="max-h-80 overflow-y-auto border-t border-gray-800">
          {isLoading ? (
            <div className="px-4 py-6 text-sm text-gray-400">Loading sources...</div>
          ) : error ? (
            <div className="px-4 py-6 text-sm text-red-400">{error}</div>
          ) : filteredSources.length === 0 ? (
            <div className="px-4 py-6 text-sm text-gray-400">No sources found.</div>
          ) : (
            filteredSources.map((source) => {
              const title = source.title || source.url || "Untitled source";
              return (
                <button
                  type="button"
                  key={source.id}
                  onClick={() => {
                    onSelect(source.id, title);
                    onClose();
                  }}
                  className="block w-full border-b border-gray-900 px-4 py-3 text-left hover:bg-gray-900"
                >
                  <span className="block truncate text-sm text-gray-100">{title}</span>
                  <span className="mt-1 block truncate text-xs text-gray-500">
                    {source.source_type}
                    {source.url ? ` · ${source.url}` : ""}
                  </span>
                </button>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
