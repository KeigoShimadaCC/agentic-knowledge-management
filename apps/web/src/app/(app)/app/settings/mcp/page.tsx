"use client";

import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import {
  deleteMcpConnection,
  listMcpConnections,
  testMcpConnection,
} from "@/lib/api";
import { CreateMcpConnectionModal } from "@/components/mcp/CreateMcpConnectionModal";
import { ListPage } from "@/components/lists/ListPage";
import type { McpConnectionOut, McpConnectionTestResult } from "@/types";

function formatDate(value: string | null): string {
  if (!value) return "Never";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function McpSettingsPage() {
  const [connections, setConnections] = useState<McpConnectionOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testingIds, setTestingIds] = useState<Set<string>>(new Set());
  const [testResults, setTestResults] = useState<Record<string, McpConnectionTestResult>>({});

  async function loadConnections() {
    setError(null);
    try {
      const items = await listMcpConnections();
      setConnections(items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load MCP connections");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadConnections();
  }, []);

  async function handleTest(connection: McpConnectionOut) {
    setTestingIds((ids) => new Set(ids).add(connection.id));
    try {
      const result = await testMcpConnection(connection.id);
      setTestResults((results) => ({ ...results, [connection.id]: result }));
      if (result.ok) {
        void loadConnections();
      }
    } catch (err) {
      setTestResults((results) => ({
        ...results,
        [connection.id]: {
          ok: false,
          tools: [],
          error: err instanceof Error ? err.message : "Connection test failed",
        },
      }));
    } finally {
      setTestingIds((ids) => {
        const next = new Set(ids);
        next.delete(connection.id);
        return next;
      });
    }
  }

  async function handleDelete(connection: McpConnectionOut) {
    if (!window.confirm(`Delete MCP connection "${connection.name}"?`)) return;
    await deleteMcpConnection(connection.id);
    await loadConnections();
  }

  return (
    <ListPage
      title="MCP"
      loading={loading}
      empty={!loading && connections.length === 0}
      emptyTitle="No MCP connections"
      emptyDescription="Add a stdio or SSE connection to use MCP tools as KnowledgeOS sources"
      actions={
        <button
          type="button"
          onClick={() => setIsModalOpen(true)}
          className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-white text-gray-950 transition-colors hover:bg-gray-200"
          aria-label="Add MCP connection"
        >
          <Plus size={18} />
        </button>
      }
    >
      {error && (
        <div className="rounded-md border border-red-900/60 bg-red-950/40 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      )}

      <div className="grid gap-3">
        {connections.map((connection) => {
          const result = testResults[connection.id];
          const toolCount = connection.capabilities?.length ?? 0;
          return (
            <article
              key={connection.id}
              className="rounded-lg border border-gray-800 bg-gray-900 p-4"
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0 space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="truncate text-base font-semibold text-white">
                      {connection.name}
                    </h2>
                    <span
                      className={
                        connection.transport === "stdio"
                          ? "rounded-full bg-blue-500/15 px-2 py-0.5 text-xs font-medium text-blue-200"
                          : "rounded-full bg-green-500/15 px-2 py-0.5 text-xs font-medium text-green-200"
                      }
                    >
                      {connection.transport}
                    </span>
                    <span className="rounded-full bg-gray-800 px-2 py-0.5 text-xs text-gray-300">
                      {connection.enabled ? "Enabled" : "Disabled"}
                    </span>
                  </div>
                  <div className="grid gap-1 text-sm text-gray-400">
                    <p>Last tested: {formatDate(connection.last_tested_at)}</p>
                    <p>{toolCount} tool{toolCount === 1 ? "" : "s"}</p>
                    {connection.last_error && (
                      <p className="text-red-300">Last error: {connection.last_error}</p>
                    )}
                    {result && (
                      <p className={result.ok ? "text-green-300" : "text-red-300"}>
                        {result.ok
                          ? `Test succeeded with ${result.tools.length} tool${
                              result.tools.length === 1 ? "" : "s"
                            }`
                          : result.error ?? "Connection test failed"}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex shrink-0 gap-2">
                  <button
                    type="button"
                    onClick={() => void handleTest(connection)}
                    disabled={testingIds.has(connection.id)}
                    className="rounded-md border border-gray-700 px-3 py-2 text-sm text-gray-200 hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {testingIds.has(connection.id) ? "Testing..." : "Test"}
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleDelete(connection)}
                    className="rounded-md border border-red-900/70 px-3 py-2 text-sm text-red-200 hover:bg-red-950/50"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </article>
          );
        })}
      </div>

      <CreateMcpConnectionModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onCreated={(connection) => setConnections((items) => [connection, ...items])}
      />
    </ListPage>
  );
}
