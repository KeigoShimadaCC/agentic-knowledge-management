"use client";

import { useState } from "react";
import { aiTriage, createEdge, updateObject } from "@/lib/api";
import type { ObjectOut, TriageResponse } from "@/types";
import { toast } from "@/components/ui/Toast";

interface TriageModalProps {
  object: ObjectOut;
  onClose: () => void;
  onApplied: () => void;
}

export function TriageModal({ object, onClose, onApplied }: TriageModalProps) {
  const [triage, setTriage] = useState<TriageResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [title, setTitle] = useState(object.title);
  const [applying, setApplying] = useState(false);

  async function handleTriage() {
    setLoading(true);
    setError(null);
    try {
      const result = await aiTriage(object.id);
      setTriage(result);
      setSelectedTags(result.suggested_tags);
      if (result.suggested_title) setTitle(result.suggested_title);
    } catch (e) {
      setError(e instanceof Error ? e.message : "AI triage failed");
    } finally {
      setLoading(false);
    }
  }

  function toggleTag(tag: string) {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  }

  async function handleApply() {
    setApplying(true);
    try {
      await updateObject(object.id, {
        title,
        description: triage?.summary ?? undefined,
        tags: selectedTags,
      });
      toast.success("Organized");
      onApplied();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Apply failed");
    } finally {
      setApplying(false);
    }
  }

  return (
    <div data-testid="triage-modal" className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-lg rounded-lg border border-gray-700 bg-gray-900 shadow-xl">
        <div className="border-b border-gray-800 px-5 py-4">
          <h2 className="text-sm font-medium text-gray-100">
            Organize: {object.title}
          </h2>
          <p className="mt-0.5 text-xs text-gray-500">
            {object.kind} · created {new Date(object.created_at).toLocaleDateString()}
          </p>
        </div>

        <div className="max-h-[60vh] overflow-y-auto px-5 py-4 space-y-4">
          {!triage && !loading && (
            <button
              type="button"
              onClick={() => void handleTriage()}
              className="w-full rounded bg-blue-900 px-3 py-2 text-sm text-blue-100 hover:bg-blue-800"
            >
              Analyze with AI
            </button>
          )}
          {loading && (
            <p className="text-center text-sm text-gray-500">Analyzing…</p>
          )}
          {error && (
            <p className="text-sm text-red-400">{error}</p>
          )}

          {triage && (
            <>
              {/* Title */}
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-400">
                  Title
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full rounded border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-700"
                />
              </div>

              {/* Summary */}
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-400">
                  Description (AI summary)
                </label>
                <p className="rounded border border-gray-800 bg-gray-950 px-3 py-2 text-xs leading-relaxed text-gray-300">
                  {triage.summary}
                </p>
              </div>

              {/* Tags */}
              {triage.suggested_tags.length > 0 && (
                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-400">
                    Suggested Tags (click to toggle)
                  </label>
                  <div className="flex flex-wrap gap-1.5">
                    {triage.suggested_tags.map((tag) => (
                      <button
                        key={tag}
                        type="button"
                        onClick={() => toggleTag(tag)}
                        className={`rounded-full px-2.5 py-0.5 text-xs transition-colors ${
                          selectedTags.includes(tag)
                            ? "bg-blue-800 text-blue-100"
                            : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                        }`}
                      >
                        {tag}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-gray-800 px-5 py-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded px-3 py-1.5 text-sm text-gray-400 hover:text-gray-200"
          >
            Skip
          </button>
          {triage && (
            <button
              type="button"
              onClick={() => void handleApply()}
              disabled={applying}
              className="rounded bg-blue-700 px-4 py-1.5 text-sm text-white hover:bg-blue-600 disabled:opacity-50"
            >
              {applying ? "Applying…" : "Apply"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
