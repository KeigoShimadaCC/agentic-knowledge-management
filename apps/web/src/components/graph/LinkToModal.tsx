"use client";

import { useState } from "react";
import { createEdge } from "@/lib/api";

const EDGE_KINDS = ["links_to", "mentions", "supports", "contradicts", "related_to"] as const;
type EdgeKind = (typeof EDGE_KINDS)[number];

interface LinkToModalProps {
  isOpen: boolean;
  onClose: () => void;
  sourceId: string;
  targetId: string;
  targetKind: string;
  targetTitle: string;
  sourceTitle?: string;
  onLinked: () => void;
}

export function LinkToModal({
  isOpen,
  onClose,
  sourceId,
  targetId,
  targetKind,
  targetTitle,
  sourceTitle = "current page",
  onLinked,
}: LinkToModalProps) {
  const [selectedKind, setSelectedKind] = useState<EdgeKind>("links_to");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleCreateLink = async () => {
    setIsSaving(true);
    setError(null);

    try {
      await createEdge({ source_id: sourceId, target_id: targetId, kind: selectedKind });
      onLinked();
      onClose();
    } catch {
      setError("Could not create link.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-lg rounded border border-gray-700 bg-gray-950 shadow-xl">
        <div className="border-b border-gray-800 px-4 py-3">
          <h2 className="text-sm font-medium text-gray-100">Link object</h2>
          <p className="mt-1 truncate text-xs text-gray-500">
            Link {sourceTitle} -&gt; {targetTitle}
          </p>
        </div>
        <div className="space-y-4 p-4">
          <div>
            <div className="mb-2 text-xs font-medium uppercase text-gray-500">Edge kind</div>
            <div className="flex flex-wrap gap-2">
              {EDGE_KINDS.map((kind) => (
                <button
                  type="button"
                  key={kind}
                  onClick={() => setSelectedKind(kind)}
                  className={
                    selectedKind === kind
                      ? "rounded border border-blue-700 bg-blue-950 px-2.5 py-1 text-xs text-blue-200"
                      : "rounded border border-gray-700 bg-gray-900 px-2.5 py-1 text-xs text-gray-300 hover:bg-gray-800 hover:text-white"
                  }
                >
                  {kind}
                </button>
              ))}
            </div>
          </div>
          <div className="text-xs text-gray-500">Target kind: {targetKind}</div>
          {error ? <div className="text-sm text-red-400">{error}</div> : null}
        </div>
        <div className="flex items-center justify-end gap-2 border-t border-gray-800 px-4 py-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded border border-gray-700 px-3 py-1.5 text-sm text-gray-300 hover:bg-gray-800 hover:text-white"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleCreateLink}
            disabled={isSaving}
            className="rounded border border-blue-700 bg-blue-950 px-3 py-1.5 text-sm text-blue-200 hover:bg-blue-900 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSaving ? "Creating..." : "Create Link"}
          </button>
        </div>
      </div>
    </div>
  );
}
