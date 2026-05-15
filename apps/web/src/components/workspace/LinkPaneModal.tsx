"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { createEdge } from "@/lib/api";
import { useWorkspaceLite } from "./WorkspaceLiteProvider";

const EDGE_KINDS = [
  { value: "links_to", label: "Links to" },
  { value: "cites", label: "Cites" },
  { value: "mentions", label: "Mentions" },
  { value: "supports", label: "Supports" },
  { value: "contradicts", label: "Contradicts" },
  { value: "related_to", label: "Related to" },
];

interface LinkPaneModalProps {
  sourcePaneId: string;
  open: boolean;
  onClose: () => void;
}

export function LinkPaneModal({ sourcePaneId, open, onClose }: LinkPaneModalProps) {
  const { panes } = useWorkspaceLite();
  const [targetPaneId, setTargetPaneId] = useState<string>("");
  const [kind, setKind] = useState("links_to");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  if (!open) return null;

  const sourcePane = panes.find((p) => p.id === sourcePaneId);
  const targetPanes = panes.filter(
    (p) => p.id !== sourcePaneId && p.objectId !== null
  );

  async function handleLink() {
    const targetPane = panes.find((p) => p.id === targetPaneId);
    if (!sourcePane?.objectId || !targetPane?.objectId) return;
    setSaving(true);
    setError(null);
    try {
      await createEdge({
        source_id: sourcePane.objectId,
        target_id: targetPane.objectId,
        kind,
      });
      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        onClose();
      }, 1000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create link");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-sm rounded-xl border border-gray-800 bg-gray-900 p-6 shadow-2xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-100">Link to another pane</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-gray-500 hover:bg-gray-800 hover:text-gray-200"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {targetPanes.length === 0 ? (
          <p className="text-sm text-gray-500">No other panes with open objects. Open an object in another pane first.</p>
        ) : (
          <div className="space-y-3">
            <div>
              <p className="mb-1 text-xs text-gray-500">From</p>
              <p className="truncate rounded bg-gray-800 px-2 py-1.5 text-sm text-gray-300">
                {sourcePane?.title || sourcePane?.objectKind || "—"}
              </p>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-400">Edge type</label>
              <select
                value={kind}
                onChange={(e) => setKind(e.target.value)}
                className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 focus:border-blue-500 focus:outline-none"
              >
                {EDGE_KINDS.map((k) => (
                  <option key={k.value} value={k.value}>{k.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-400">Target pane</label>
              <select
                value={targetPaneId}
                onChange={(e) => setTargetPaneId(e.target.value)}
                className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 focus:border-blue-500 focus:outline-none"
              >
                <option value="">Select a pane…</option>
                {targetPanes.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.title || p.objectKind || p.id}
                  </option>
                ))}
              </select>
            </div>
            {error && <p className="text-xs text-red-400">{error}</p>}
            {success && <p className="text-xs text-green-400">Edge created!</p>}
          </div>
        )}

        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-3 py-1.5 text-sm text-gray-400 hover:bg-gray-800 hover:text-gray-200"
          >
            Cancel
          </button>
          {targetPanes.length > 0 && (
            <button
              type="button"
              disabled={!targetPaneId || !sourcePane?.objectId || saving}
              onClick={() => void handleLink()}
              className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
            >
              {saving ? "Linking…" : "Link"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
