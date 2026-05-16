"use client";

import { useEffect, useRef, useState } from "react";
import { clsx } from "clsx";
import { callMcpTool, createSource, ingestFromMcp, listMcpConnections } from "@/lib/api";
import type { McpCallResponse, McpConnectionOut, SourceType } from "@/types";
import { toast } from "@/components/ui/Toast";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Tab = "url" | "file" | "mcp";

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

  // MCP tab state
  const [mcpConnections, setMcpConnections] = useState<McpConnectionOut[]>([]);
  const [mcpLoaded, setMcpLoaded] = useState(false);
  const [mcpLoading, setMcpLoading] = useState(false);
  const [selectedConnectionId, setSelectedConnectionId] = useState("");
  const [selectedTool, setSelectedTool] = useState("");
  const [toolArgs, setToolArgs] = useState<Record<string, string>>({});
  const [preview, setPreview] = useState<McpCallResponse | null>(null);
  const [mcpAction, setMcpAction] = useState<"preview" | "source" | "page" | null>(null);
  const didFetchMcp = useRef(false);

  useEffect(() => {
    if (!isOpen || tab !== "mcp" || mcpLoaded || didFetchMcp.current) return;
    didFetchMcp.current = true;
    setMcpLoading(true);
    listMcpConnections()
      .then((all) => {
        const available = all.filter((c) => c.enabled && c.capabilities != null);
        setMcpConnections(available);
        if (available.length > 0 && available[0]) setSelectedConnectionId(available[0].id);
        setMcpLoaded(true);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load MCP connections");
      })
      .finally(() => setMcpLoading(false));
  }, [isOpen, tab, mcpLoaded]);

  const selectedConnection = mcpConnections.find((c) => c.id === selectedConnectionId);
  const availableTools = selectedConnection?.capabilities ?? [];

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
          <div className="grid grid-cols-3 gap-2">
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
            <button
              type="button"
              onClick={() => setTab("mcp")}
              className={clsx(
                "rounded-md px-3 py-2 text-sm font-medium transition-colors",
                tab === "mcp" ? "bg-gray-700 text-white" : "text-gray-400 hover:bg-gray-800 hover:text-white"
              )}
            >
              From MCP
            </button>
          </div>
        </div>

        <div className="p-4">
          {tab === "mcp" ? (
            <div className="space-y-4">
              {mcpLoading && <p className="text-sm text-gray-400">Loading connections...</p>}
              {!mcpLoading && mcpConnections.length === 0 && (
                <p className="text-sm text-gray-400">
                  No enabled MCP connections with cached tools. Go to MCP settings to add and test
                  a connection.
                </p>
              )}
              {mcpConnections.length > 0 && (
                <>
                  <label className="block">
                    <span className="mb-1 block text-sm font-medium text-gray-300">Connection</span>
                    <select
                      value={selectedConnectionId}
                      onChange={(e) => {
                        setSelectedConnectionId(e.target.value);
                        setSelectedTool("");
                        setToolArgs({});
                        setPreview(null);
                      }}
                      className="w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-white outline-none focus:border-gray-500"
                    >
                      {mcpConnections.map((c) => (
                        <option key={c.id} value={c.id}>{c.name}</option>
                      ))}
                    </select>
                  </label>
                  {availableTools.length > 0 && (
                    <label className="block">
                      <span className="mb-1 block text-sm font-medium text-gray-300">Tool</span>
                      <select
                        value={selectedTool}
                        onChange={(e) => {
                          setSelectedTool(e.target.value);
                          setToolArgs({});
                          setPreview(null);
                        }}
                        className="w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-white outline-none focus:border-gray-500"
                      >
                        <option value="">Select a tool…</option>
                        {availableTools.map((t) => (
                          <option key={t.name} value={t.name}>{t.name}</option>
                        ))}
                      </select>
                    </label>
                  )}
                  {selectedTool && (
                    <div className="space-y-2">
                      <span className="block text-sm font-medium text-gray-300">Arguments</span>
                      {Object.entries(
                        (availableTools.find((t) => t.name === selectedTool)?.input_schema as
                          Record<string, { type?: string; description?: string }> | undefined) ?? {}
                      ).map(([key, schema]) => (
                        <label key={key} className="block">
                          <span className="mb-1 block text-xs text-gray-400">
                            {key}{schema?.description ? ` — ${schema.description}` : ""}
                          </span>
                          <input
                            type="text"
                            value={toolArgs[key] ?? ""}
                            onChange={(e) => setToolArgs((prev) => ({ ...prev, [key]: e.target.value }))}
                            className="w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-white outline-none focus:border-gray-500"
                          />
                        </label>
                      ))}
                      {Object.keys(
                        (availableTools.find((t) => t.name === selectedTool)?.input_schema as
                          Record<string, unknown> | undefined) ?? {}
                      ).length === 0 && (
                        <label className="block">
                          <span className="mb-1 block text-xs text-gray-400">Query</span>
                          <input
                            type="text"
                            value={toolArgs["query"] ?? ""}
                            onChange={(e) => setToolArgs({ query: e.target.value })}
                            className="w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-white outline-none focus:border-gray-500"
                            placeholder="Enter query or argument…"
                          />
                        </label>
                      )}
                    </div>
                  )}
                  {preview && (
                    <div>
                      <p className="mb-1 text-xs font-medium text-gray-400">Preview result:</p>
                      <pre className="max-h-40 overflow-auto rounded-md border border-gray-700 bg-gray-950 p-2 text-xs text-gray-300">
                        {JSON.stringify(preview.result, null, 2)}
                      </pre>
                    </div>
                  )}
                  {error && <p className="text-sm text-red-300">{error}</p>}
                  {selectedTool && (
                    <div className="flex gap-2">
                      <button
                        type="button"
                        disabled={mcpAction === "preview"}
                        onClick={async () => {
                          setError(null);
                          setMcpAction("preview");
                          try {
                            const res = await callMcpTool(selectedConnectionId, {
                              tool_name: selectedTool,
                              args: toolArgs,
                            });
                            setPreview(res);
                          } catch (err) {
                            setError(err instanceof Error ? err.message : "Preview failed");
                          } finally {
                            setMcpAction(null);
                          }
                        }}
                        className="flex-1 rounded-md border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 disabled:opacity-60"
                      >
                        {mcpAction === "preview" ? "Loading…" : "Preview"}
                      </button>
                      <button
                        type="button"
                        disabled={mcpAction !== null}
                        onClick={async () => {
                          setError(null);
                          setMcpAction("source");
                          try {
                            const res = await ingestFromMcp(selectedConnectionId, {
                              tool_name: selectedTool,
                              args: toolArgs,
                              target_kind: "source",
                            });
                            toast.success(`Ingest queued (job ${res.job_id.slice(0, 8)})`);
                            onCreated();
                            onClose();
                          } catch (err) {
                            setError(err instanceof Error ? err.message : "Ingest failed");
                            setMcpAction(null);
                          }
                        }}
                        className="flex-1 rounded-md bg-white px-3 py-2 text-sm font-medium text-gray-950 hover:bg-gray-200 disabled:opacity-60"
                      >
                        {mcpAction === "source" ? "Queuing…" : "Ingest as Source"}
                      </button>
                      <button
                        type="button"
                        disabled={mcpAction !== null}
                        onClick={async () => {
                          setError(null);
                          setMcpAction("page");
                          try {
                            const res = await ingestFromMcp(selectedConnectionId, {
                              tool_name: selectedTool,
                              args: toolArgs,
                              target_kind: "page",
                            });
                            toast.success(`Ingest queued (job ${res.job_id.slice(0, 8)})`);
                            onCreated();
                            onClose();
                          } catch (err) {
                            setError(err instanceof Error ? err.message : "Ingest failed");
                            setMcpAction(null);
                          }
                        }}
                        className="flex-1 rounded-md border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 disabled:opacity-60"
                      >
                        {mcpAction === "page" ? "Queuing…" : "Ingest as Page"}
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          ) : tab === "url" ? (
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
