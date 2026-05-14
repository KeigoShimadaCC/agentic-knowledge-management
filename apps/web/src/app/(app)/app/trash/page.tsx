"use client";

import { useState } from "react";
import useSWR from "swr";
import { RotateCcw } from "lucide-react";
import { listTrashObjects, restoreObject } from "@/lib/api";
import type { ObjectOut } from "@/types";

function KindBadge({ kind }: { kind: string }) {
  return (
    <span className="rounded bg-gray-800 px-1.5 py-0.5 text-xs text-gray-400 capitalize">
      {kind}
    </span>
  );
}

function TrashItem({
  object,
  onRestore,
}: {
  object: ObjectOut;
  onRestore: (id: string) => Promise<void>;
}) {
  const [restoring, setRestoring] = useState(false);

  async function handleRestore() {
    setRestoring(true);
    try {
      await onRestore(object.id);
    } finally {
      setRestoring(false);
    }
  }

  const deletedAt = object.deleted_at
    ? new Date(object.deleted_at).toLocaleDateString()
    : "unknown";

  return (
    <div className="flex items-center justify-between gap-4 rounded-lg border border-gray-800 bg-gray-900 px-4 py-3">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <KindBadge kind={object.kind} />
          <span className="truncate text-sm font-medium text-white">
            {object.title || "(untitled)"}
          </span>
        </div>
        <p className="mt-1 text-xs text-gray-500">Deleted {deletedAt}</p>
      </div>
      <button
        type="button"
        disabled={restoring}
        onClick={() => void handleRestore()}
        className="flex shrink-0 items-center gap-1.5 rounded-md bg-gray-700 px-3 py-1.5 text-xs text-white transition-colors hover:bg-gray-600 disabled:opacity-50"
      >
        <RotateCcw size={12} />
        {restoring ? "Restoring…" : "Restore"}
      </button>
    </div>
  );
}

export default function TrashPage() {
  const { data: objects, mutate, isLoading } = useSWR<ObjectOut[]>(
    "/api/v1/objects/trash",
    listTrashObjects,
    { revalidateOnFocus: false }
  );

  async function handleRestore(id: string) {
    await restoreObject(id);
    await mutate();
  }

  const items = objects ?? [];

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Trash</h1>
        <p className="mt-1 text-sm text-gray-500">
          Deleted items — restore to return them to your knowledge base.
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-14 animate-pulse rounded-lg border border-gray-800 bg-gray-900" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="py-16 text-center text-gray-500">
          <p className="text-lg">Trash is empty</p>
          <p className="mt-2 text-sm">Deleted items appear here and can be restored.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((obj) => (
            <TrashItem key={obj.id} object={obj} onRestore={handleRestore} />
          ))}
        </div>
      )}
    </div>
  );
}
