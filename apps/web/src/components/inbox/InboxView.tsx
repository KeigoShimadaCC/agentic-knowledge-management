"use client";

import { useState } from "react";
import { useCallback } from "react";
import useSWR from "swr";
import { getInbox } from "@/lib/api";
import type { ObjectOut, PaginatedResponse } from "@/types";
import { TriageModal } from "./TriageModal";

const PAGE_SIZE = 20;

function kindBadge(kind: string) {
  const colors: Record<string, string> = {
    page: "bg-blue-900 text-blue-300",
    source: "bg-purple-900 text-purple-300",
    note: "bg-green-900 text-green-300",
    bookmark: "bg-yellow-900 text-yellow-300",
    claim: "bg-orange-900 text-orange-300",
    task: "bg-red-900 text-red-300",
    chat: "bg-gray-700 text-gray-300",
  };
  return colors[kind] ?? "bg-gray-800 text-gray-400";
}

export function InboxView() {
  const [offset, setOffset] = useState(0);
  const [triageTarget, setTriageTarget] = useState<ObjectOut | null>(null);

  const { data, mutate } = useSWR<PaginatedResponse<ObjectOut>>(
    ["inbox", offset],
    () => getInbox({ limit: PAGE_SIZE, offset }),
    { keepPreviousData: true }
  );

  const handleApplied = useCallback(() => {
    void mutate();
  }, [mutate]);

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-gray-100">Inbox</h1>
        <p className="mt-1 text-sm text-gray-500">
          {total > 0
            ? `${total} item${total !== 1 ? "s" : ""} need attention`
            : "All caught up!"}
          {total > 0 && " — objects without tags or description from the last 30 days"}
        </p>
      </div>

      {items.length === 0 && data && (
        <div className="rounded-lg border border-gray-800 bg-gray-900 px-6 py-12 text-center">
          <p className="text-gray-500">No unorganized items. Great job!</p>
        </div>
      )}

      <div className="space-y-3">
        {items.map((obj) => (
          <div
            key={obj.id}
            className="flex items-start justify-between gap-4 rounded-lg border border-gray-800 bg-gray-900 px-4 py-3"
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span
                  className={`rounded px-1.5 py-0.5 text-xs ${kindBadge(obj.kind)}`}
                >
                  {obj.kind}
                </span>
                <span className="truncate text-sm font-medium text-gray-100">
                  {obj.title}
                </span>
              </div>
              <p className="mt-0.5 text-xs text-gray-600">
                {new Date(obj.created_at).toLocaleDateString()}
              </p>
            </div>
            <button
              type="button"
              onClick={() => setTriageTarget(obj)}
              className="shrink-0 rounded bg-blue-900 px-2.5 py-1 text-xs text-blue-200 hover:bg-blue-800"
            >
              Triage with AI
            </button>
          </div>
        ))}
      </div>

      {total > PAGE_SIZE && (
        <div className="mt-6 flex items-center justify-center gap-4">
          <button
            type="button"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            className="rounded bg-gray-800 px-3 py-1.5 text-sm text-gray-300 hover:bg-gray-700 disabled:opacity-40"
          >
            Previous
          </button>
          <span className="text-sm text-gray-500">
            {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
          </span>
          <button
            type="button"
            disabled={offset + PAGE_SIZE >= total}
            onClick={() => setOffset(offset + PAGE_SIZE)}
            className="rounded bg-gray-800 px-3 py-1.5 text-sm text-gray-300 hover:bg-gray-700 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}

      {triageTarget && (
        <TriageModal
          object={triageTarget}
          onClose={() => setTriageTarget(null)}
          onApplied={handleApplied}
        />
      )}
    </div>
  );
}
