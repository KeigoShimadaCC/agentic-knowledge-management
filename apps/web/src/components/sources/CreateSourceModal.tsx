"use client";

import { useState } from "react";
import { clsx } from "clsx";
import { createSource } from "@/lib/api";
import type { SourceType } from "@/types";
import { toast } from "@/components/ui/Toast";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Tab = "url" | "file";

interface CreateSourceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: () => void;
}

export function CreateSourceModal({ isOpen, onClose, onCreated }: CreateSourceModalProps) {
  const [tab, setTab] = useState<Tab>("url");
  const [url, setUrl] = useState("");
  const [sourceType, setSourceType] = useState<Extract<SourceType, "youtube" | "web">>("web");
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  async function handleUrlSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsCreating(true);
    try {
      await createSource({ source_type: sourceType, url });
      setUrl("");
      toast.success("Source created");
      onCreated();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create source");
    } finally {
      setIsCreating(false);
    }
  }

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setError(null);
    setIsCreating(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${BASE}/api/v1/assets/upload?create_source=true`, {
        method: "POST",
        credentials: "include",
        body: formData,
      });
      if (!res.ok) {
        const fallback = { detail: res.statusText };
        const body = (await res.json().catch(() => fallback)) as { detail?: string };
        throw new Error(body.detail ?? res.statusText);
      }
      toast.success("File uploaded");
      onCreated();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload file");
    } finally {
      setIsCreating(false);
      event.target.value = "";
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="w-full max-w-md rounded-lg border border-gray-800 bg-gray-900 shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-800 p-4">
          <h2 className="text-lg font-semibold text-white">Create Source</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-2 py-1 text-sm text-gray-400 hover:bg-gray-800 hover:text-white"
          >
            Close
          </button>
        </div>

        <div className="border-b border-gray-800 p-2">
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setTab("url")}
              className={clsx(
                "rounded-md px-3 py-2 text-sm font-medium transition-colors",
                tab === "url" ? "bg-gray-700 text-white" : "text-gray-400 hover:bg-gray-800 hover:text-white"
              )}
            >
              Paste URL
            </button>
            <button
              type="button"
              onClick={() => setTab("file")}
              className={clsx(
                "rounded-md px-3 py-2 text-sm font-medium transition-colors",
                tab === "file" ? "bg-gray-700 text-white" : "text-gray-400 hover:bg-gray-800 hover:text-white"
              )}
            >
              Upload File
            </button>
          </div>
        </div>

        <div className="p-4">
          {tab === "url" ? (
            <form onSubmit={handleUrlSubmit} className="space-y-4">
              <label className="block">
                <span className="mb-1 block text-sm font-medium text-gray-300">URL</span>
                <input
                  type="url"
                  value={url}
                  onChange={(event) => setUrl(event.target.value)}
                  required
                  className="w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-white outline-none focus:border-gray-500"
                  placeholder="https://example.com"
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-sm font-medium text-gray-300">Type</span>
                <select
                  value={sourceType}
                  onChange={(event) =>
                    setSourceType(event.target.value === "youtube" ? "youtube" : "web")
                  }
                  className="w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-white outline-none focus:border-gray-500"
                >
                  <option value="web">Web</option>
                  <option value="youtube">YouTube</option>
                </select>
              </label>
              {error && <p className="text-sm text-red-300">{error}</p>}
              <button
                type="submit"
                disabled={isCreating}
                className="w-full rounded-md bg-white px-3 py-2 text-sm font-medium text-gray-950 transition-colors hover:bg-gray-200 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isCreating ? "Creating..." : "Create Source"}
              </button>
            </form>
          ) : (
            <div className="space-y-4">
              <label className="block">
                <span className="mb-1 block text-sm font-medium text-gray-300">File</span>
                <input
                  type="file"
                  onChange={handleFileChange}
                  disabled={isCreating}
                  className="w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-gray-300 file:mr-3 file:rounded-md file:border-0 file:bg-gray-800 file:px-3 file:py-1.5 file:text-sm file:text-white hover:file:bg-gray-700 disabled:cursor-not-allowed disabled:opacity-60"
                />
              </label>
              {error && <p className="text-sm text-red-300">{error}</p>}
              {isCreating && <p className="text-sm text-gray-400">Uploading...</p>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
