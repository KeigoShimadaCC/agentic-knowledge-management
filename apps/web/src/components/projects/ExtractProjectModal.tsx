"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Search, Sparkles, X } from "lucide-react";

import { extractProject, hybridSearch } from "@/lib/api";
import { objectKindLabel } from "@/lib/objectRouting";
import { toast } from "@/components/ui/Toast";
import { ApiError, type SearchResult } from "@/types";

interface ExtractProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const KIND_FILTERS = [
  { label: "Pages", value: "page" },
  { label: "Sources", value: "source" },
  { label: "Chats", value: "chat" },
];

export function ExtractProjectModal({ isOpen, onClose }: ExtractProjectModalProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState("page");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [selected, setSelected] = useState<SearchResult | null>(null);
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [aiDisabled, setAiDisabled] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    const trimmed = query.trim();
    if (!trimmed) {
      setResults([]);
      return;
    }
    setLoading(true);
    const timeout = window.setTimeout(() => {
      hybridSearch(trimmed, { kind, limit: 12 })
        .then((response) => setResults(response.results))
        .catch((err) =>
          toast.error("Could not search objects", {
            description: err instanceof Error ? err.message : undefined,
          })
        )
        .finally(() => setLoading(false));
    }, 250);
    return () => window.clearTimeout(timeout);
  }, [isOpen, kind, query]);

  if (!isOpen) return null;

  async function handleCreate() {
    if (!selected) return;
    setCreating(true);
    setAiDisabled(false);
    try {
      const response = await extractProject({
        source_id: selected.id,
        create: true,
        period_hint:
          periodStart || periodEnd ? [periodStart || null, periodEnd || null] : undefined,
      });
      toast.success("Project created");
      onClose();
      if (response.project_id) router.push(`/app/projects/${response.project_id}`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 503) {
        setAiDisabled(true);
      } else {
        toast.error("Could not extract project", {
          description: err instanceof Error ? err.message : undefined,
        });
      }
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="w-full max-w-3xl rounded-lg border border-gray-800 bg-gray-950 shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-800 px-4 py-3">
          <h2 className="text-sm font-medium text-white">Extract project</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-gray-500 hover:bg-gray-800 hover:text-white"
            aria-label="Close"
          >
            <X size={16} />
          </button>
        </div>
        <div className="space-y-4 p-4">
          {aiDisabled && (
            <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
              AI is disabled. Set OPENAI_API_KEY to use this feature.
            </div>
          )}
          <label className="flex items-center gap-2 rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-300">
            <Search size={16} />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search source material"
              className="min-w-0 flex-1 bg-transparent text-gray-100 outline-none placeholder:text-gray-500"
            />
          </label>
          <div className="flex flex-wrap gap-2">
            {KIND_FILTERS.map((filter) => (
              <button
                key={filter.value}
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
          <div className="grid gap-3 md:grid-cols-2">
            <label className="text-sm text-gray-300">
              Start hint
              <input
                type="date"
                value={periodStart}
                onChange={(e) => setPeriodStart(e.target.value)}
                className="mt-1 h-9 w-full rounded-md border border-gray-700 bg-gray-900 px-3 text-sm text-white focus:border-gray-500 focus:outline-none"
              />
            </label>
            <label className="text-sm text-gray-300">
              End hint
              <input
                type="date"
                value={periodEnd}
                onChange={(e) => setPeriodEnd(e.target.value)}
                className="mt-1 h-9 w-full rounded-md border border-gray-700 bg-gray-900 px-3 text-sm text-white focus:border-gray-500 focus:outline-none"
              />
            </label>
          </div>
        </div>
        <div className="max-h-80 overflow-y-auto border-y border-gray-800">
          {loading ? (
            <div className="px-4 py-6 text-sm text-gray-400">Searching...</div>
          ) : query.trim() && results.length === 0 ? (
            <div className="px-4 py-6 text-sm text-gray-400">No objects found.</div>
          ) : !query.trim() ? (
            <div className="px-4 py-6 text-sm text-gray-400">Search pages, sources, or chats.</div>
          ) : (
            results.map((result) => (
              <button
                type="button"
                key={result.id}
                onClick={() => setSelected(result)}
                className={
                  selected?.id === result.id
                    ? "block w-full border-b border-gray-900 bg-gray-900 px-4 py-3 text-left"
                    : "block w-full border-b border-gray-900 px-4 py-3 text-left hover:bg-gray-900"
                }
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
        <div className="flex justify-end gap-2 px-4 py-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => void handleCreate()}
            disabled={!selected || creating}
            className="inline-flex items-center gap-2 rounded-md bg-white px-3 py-2 text-sm font-medium text-gray-950 disabled:opacity-60"
          >
            <Sparkles size={15} />
            {creating ? "Creating..." : "Create project from this"}
          </button>
        </div>
      </div>
    </div>
  );
}
