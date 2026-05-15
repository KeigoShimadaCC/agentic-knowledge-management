"use client";

import { useMemo, useState } from "react";
import { useCallback } from "react";
import useSWR from "swr";
import { getInbox, aiTriage, updateObject } from "@/lib/api";
import type { ObjectOut, PaginatedResponse } from "@/types";
import { TriageModal } from "./TriageModal";
import { toast } from "@/components/ui/Toast";
import { ListPage } from "@/components/lists/ListPage";
import { BulkActionBar } from "@/components/lists/BulkActionBar";
import { useListSelection } from "@/lib/hooks/useListSelection";
import { cn } from "@/lib/cn";

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
  const [bulkTriaging, setBulkTriaging] = useState(false);
  const selection = useListSelection();

  const { data, mutate, isLoading } = useSWR<PaginatedResponse<ObjectOut>>(
    ["inbox", offset],
    () => getInbox({ limit: PAGE_SIZE, offset }),
    { keepPreviousData: true }
  );

  const handleApplied = useCallback(() => {
    void mutate();
  }, [mutate]);

  const items = useMemo(() => data?.items ?? [], [data]);
  const total = data?.total ?? 0;

  async function handleBulkTriage() {
    setBulkTriaging(true);
    const ids = Array.from(selection.selected);
    let succeeded = 0;
    let failed = 0;

    const chunks: string[][] = [];
    for (let i = 0; i < ids.length; i += 4) chunks.push(ids.slice(i, i + 4));

    for (const chunk of chunks) {
      const results = await Promise.allSettled(
        chunk.map(async (id) => {
          const suggestion = await aiTriage(id);
          await updateObject(id, {
            ...(suggestion.suggested_tags.length > 0 && { tags: suggestion.suggested_tags }),
            ...(suggestion.suggested_title && { title: suggestion.suggested_title }),
          });
        })
      );
      for (const r of results) {
        if (r.status === "fulfilled") succeeded++;
        else failed++;
      }
    }

    await mutate();
    selection.clear();
    setBulkTriaging(false);

    if (failed === 0) {
      toast.success(`${succeeded} item${succeeded !== 1 ? "s" : ""} auto-triaged`);
    } else {
      toast.error(`${succeeded} succeeded, ${failed} failed`);
    }
  }

  return (
    <>
      <ListPage
        title="Inbox"
        description={
          total > 0
            ? `${total} item${total !== 1 ? "s" : ""} need attention — objects without tags or description from the last 30 days`
            : undefined
        }
        loading={isLoading}
        empty={items.length === 0 && !!data}
        emptyTitle="All caught up!"
        emptyDescription="No unorganized items."
        skeletonRows={5}
      >
        <div className="space-y-3">
          {items.map((obj) => (
            <div
              key={obj.id}
              className={cn(
                "flex items-start justify-between gap-4 rounded-lg border bg-gray-900 px-4 py-3 transition-colors",
                selection.has(obj.id) ? "border-brand/50 bg-brand/5" : "border-gray-800"
              )}
            >
              <label className="flex min-w-0 flex-1 cursor-pointer items-start gap-3">
                <input
                  type="checkbox"
                  className="mt-0.5 rounded border-gray-600 bg-gray-800 accent-indigo-500"
                  checked={selection.has(obj.id)}
                  onChange={() => selection.toggle(obj.id)}
                  aria-label={`Select ${obj.title ?? obj.id}`}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className={`rounded px-1.5 py-0.5 text-xs ${kindBadge(obj.kind)}`}>
                      {obj.kind}
                    </span>
                    <span className="truncate text-sm font-medium text-gray-100">{obj.title}</span>
                  </div>
                  <p className="mt-0.5 text-xs text-gray-600">
                    {new Date(obj.created_at).toLocaleDateString()}
                  </p>
                </div>
              </label>
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
      </ListPage>

      <BulkActionBar
        count={selection.size}
        onClear={selection.clear}
        actions={[
          {
            label: "Auto-triage selected",
            onClick: () => void handleBulkTriage(),
            loading: bulkTriaging,
          },
        ]}
      />

      {triageTarget && (
        <TriageModal
          object={triageTarget}
          onClose={() => setTriageTarget(null)}
          onApplied={handleApplied}
        />
      )}
    </>
  );
}
