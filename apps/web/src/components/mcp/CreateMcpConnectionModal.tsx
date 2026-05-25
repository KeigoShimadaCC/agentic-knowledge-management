"use client";

import { useState } from "react";
import { createMcpConnection } from "@/lib/api";
import type { McpConnectionCreate, McpConnectionOut, McpTransport } from "@/types";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (conn: McpConnectionOut) => void;
}

interface KeyValueRow {
  id: string;
  key: string;
  value: string;
}

function rowsToRecord(rows: KeyValueRow[]): Record<string, string> {
  return rows.reduce<Record<string, string>>((acc, row) => {
    const key = row.key.trim();
    if (key) {
      acc[key] = row.value;
    }
    return acc;
  }, {});
}

function splitArgs(value: string): string[] {
  return value
    .split(",")
    .map((arg) => arg.trim())
    .filter(Boolean);
}

function createRow(): KeyValueRow {
  return { id: crypto.randomUUID(), key: "", value: "" };
}

export function CreateMcpConnectionModal({ isOpen, onClose, onCreated }: Props) {
  const [name, setName] = useState("");
  const [transport, setTransport] = useState<McpTransport>("stdio");
  const [command, setCommand] = useState("");
  const [args, setArgs] = useState("");
  const [url, setUrl] = useState("");
  const [envRows, setEnvRows] = useState<KeyValueRow[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  function resetForm() {
    setName("");
    setTransport("stdio");
    setCommand("");
    setArgs("");
    setUrl("");
    setEnvRows([]);
    setError(null);
  }

  function handleClose() {
    if (isSaving) return;
    resetForm();
    onClose();
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSaving(true);
    try {
      const data: McpConnectionCreate = {
        name: name.trim(),
        transport,
        env_vars: rowsToRecord(envRows),
        enabled: true,
      };
      if (transport === "stdio") {
        data.command = command.trim();
        data.args = splitArgs(args);
      } else {
        data.url = url.trim();
      }
      const created = await createMcpConnection(data);
      onCreated(created);
      resetForm();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create MCP connection");
    } finally {
      setIsSaving(false);
    }
  }

  function updateEnvRow(id: string, field: "key" | "value", value: string) {
    setEnvRows((rows) => rows.map((row) => (row.id === id ? { ...row, [field]: value } : row)));
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="max-h-[90vh] w-full max-w-lg overflow-hidden rounded-lg border border-gray-800 bg-gray-900 shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-800 p-4">
          <h2 className="text-lg font-semibold text-white">Add MCP Connection</h2>
          <button
            type="button"
            onClick={handleClose}
            className="rounded-md px-2 py-1 text-sm text-gray-400 hover:bg-gray-800 hover:text-white"
          >
            Close
          </button>
        </div>

        <form onSubmit={handleSubmit} className="max-h-[calc(90vh-65px)] space-y-4 overflow-y-auto p-4">
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-gray-300">Name</span>
            <input
              type="text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
              className="w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-white outline-none focus:border-gray-500"
              placeholder="Local notes MCP"
            />
          </label>

          <fieldset>
            <legend className="mb-2 block text-sm font-medium text-gray-300">Transport</legend>
            <div className="grid grid-cols-2 gap-2">
              {(["stdio", "sse", "http"] as const).map((value) => (
                <label
                  key={value}
                  className="flex cursor-pointer items-center gap-2 rounded-md border border-gray-800 bg-gray-950 px-3 py-2 text-sm text-gray-300"
                >
                  <input
                    type="radio"
                    value={value}
                    checked={transport === value}
                    onChange={() => setTransport(value)}
                    className="h-4 w-4"
                  />
                  {value}
                </label>
              ))}
            </div>
          </fieldset>

          {transport === "stdio" ? (
            <>
              <label className="block">
                <span className="mb-1 block text-sm font-medium text-gray-300">Command</span>
                <input
                  type="text"
                  value={command}
                  onChange={(event) => setCommand(event.target.value)}
                  required
                  className="w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-white outline-none focus:border-gray-500"
                  placeholder="uvx my-mcp-server"
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-sm font-medium text-gray-300">Args</span>
                <input
                  type="text"
                  value={args}
                  onChange={(event) => setArgs(event.target.value)}
                  className="w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-white outline-none focus:border-gray-500"
                  placeholder="--workspace, ~/KnowledgeOS"
                />
              </label>
            </>
          ) : (
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-gray-300">URL</span>
              <input
                type="url"
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                required
                className="w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-white outline-none focus:border-gray-500"
                placeholder="https://example.com/mcp"
              />
            </label>
          )}

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-300">Env Vars</span>
              <button
                type="button"
                onClick={() => setEnvRows((rows) => [...rows, createRow()])}
                className="rounded-md border border-gray-700 px-2 py-1 text-xs text-gray-300 hover:bg-gray-800 hover:text-white"
              >
                Add Env Var
              </button>
            </div>
            {envRows.map((row) => (
              <div key={row.id} className="grid grid-cols-[1fr_1fr_auto] gap-2">
                <input
                  type="text"
                  value={row.key}
                  onChange={(event) => updateEnvRow(row.id, "key", event.target.value)}
                  className="min-w-0 rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-white outline-none focus:border-gray-500"
                  placeholder="KEY"
                />
                <input
                  type="text"
                  value={row.value}
                  onChange={(event) => updateEnvRow(row.id, "value", event.target.value)}
                  className="min-w-0 rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-white outline-none focus:border-gray-500"
                  placeholder="value"
                />
                <button
                  type="button"
                  onClick={() => setEnvRows((rows) => rows.filter((item) => item.id !== row.id))}
                  className="rounded-md px-2 py-1 text-sm text-gray-400 hover:bg-gray-800 hover:text-red-300"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>

          {error && <p className="text-sm text-red-300">{error}</p>}

          <button
            type="submit"
            disabled={isSaving}
            className="w-full rounded-md bg-white px-3 py-2 text-sm font-medium text-gray-950 transition-colors hover:bg-gray-200 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSaving ? "Creating..." : "Create Connection"}
          </button>
        </form>
      </div>
    </div>
  );
}
