"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { useWorkspaceLite } from "./WorkspaceLiteProvider";

interface WorkspaceNameModalProps {
  open: boolean;
  onClose: () => void;
}

export function WorkspaceNameModal({ open, onClose }: WorkspaceNameModalProps) {
  const { saveWorkspace } = useWorkspaceLite();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  async function handleSave() {
    if (!name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await saveWorkspace(name.trim(), description.trim() || undefined);
      setName("");
      setDescription("");
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save workspace");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-sm rounded-xl border border-gray-800 bg-gray-900 p-6 shadow-2xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-100">Save Workspace</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-gray-500 hover:bg-gray-800 hover:text-gray-200"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-400">
              Name <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") void handleSave(); }}
              placeholder="My research session"
              autoFocus
              className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 placeholder-gray-600 focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-400">
              Description <span className="text-gray-600">(optional)</span>
            </label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What are you researching?"
              className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 placeholder-gray-600 focus:border-blue-500 focus:outline-none"
            />
          </div>
          {error && <p className="text-xs text-red-400">{error}</p>}
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-3 py-1.5 text-sm text-gray-400 hover:bg-gray-800 hover:text-gray-200"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={!name.trim() || saving}
            onClick={() => void handleSave()}
            className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
