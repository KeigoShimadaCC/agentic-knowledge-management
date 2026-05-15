"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";
import { RotateCcw } from "lucide-react";
import { listTrashObjects, restoreObject } from "@/lib/api";
import type { ObjectOut } from "@/types";
import { toast } from "@/components/ui/Toast";
import { ListPage } from "@/components/lists/ListPage";
import { ListToolbar, type SortKey } from "@/components/lists/ListToolbar";
import { BulkActionBar } from "@/components/lists/BulkActionBar";
import { useListSelection } from "@/lib/hooks/useListSelection";
import { cn } from "@/lib/cn";

function sortObjects(objects: ObjectOut[], sort: SortKey): ObjectOut[] {
  const arr = [...objects];
  if (sort === "newest") return arr.sort((a, b) => new Date(b.deleted_at ?? b.updated_at).getTime() - new Date(a.deleted_at ?? a.updated_at).getTime());
  if (sort === "oldest") return arr.sort((a, b) => new Date(a.deleted_at ?? a.updated_at).getTime() - new Date(b.deleted_at ?? b.updated_at).getTime());
  return arr.sort((a, b) => (a.title ?? "").localeCompare(b.title ?? ""));
}

export default function TrashPage() {
  const { data: objects, mutate, isLoading } = useSWR<ObjectOut[]>(
    "/api/v1/objects/trash",
    listTrashObjects,
    { revalidateOnFocus: false }
  );
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<SortKey>("newest");
  const [bulkRestoring, setBulkRestoring] = useState(false);
  const selection = useListSelection();

  const items = useMemo(() => objects ?? [], [objects]);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    const matched = q ? items.filter((o) => (o.title ?? "").toLowerCase().includes(q)) : items;
    return sortObjects(matched, sort);
  }, [items, search, sort]);

  async function handleRestore(id: string) {
    const item = items.find((o) => o.id === id);
    await restoreObject(id);
    await mutate();
    toast.success(`"${item?.title || "Item"}" restored`);
  }

  async function handleBulkRestore() {
    setBulkRestoring(true);
    const ids = Array.from(selection.selected);
    const chunks: string[][] = [];
    for (let i = 0; i < ids.length; i += 4) chunks.push(ids.slice(i, i + 4));
    for (const chunk of chunks) {
      await Promise.allSettled(chunk.map((id) => restoreObject(id)));
    }
    await mutate();
    selection.clear();
    setBulkRestoring(false);
    toast.success(`${ids.length} item${ids.length !== 1 ? "s" : ""} restored`);
  }

  return (
    <>
      <ListPage
        title="Trash"
        description="Deleted items — restore to return them to your knowledge base."
        loading={isLoading}
        empty={!isLoading && filtered.length === 0}
        emptyTitle={search ? "No results" : "Trash is empty"}
        emptyDescription={search ? "Try a different search" : "Deleted items appear here and can be restored."}
        toolbar={
          <ListToolbar
            search={search}
            onSearch={setSearch}
            sort={sort}
            onSort={setSort}
            searchPlaceholder="Filter trash…"
          />
        }
      >
        <div className="space-y-2">
          {filtered.map((obj) => (
            <div
              key={obj.id}
              className={cn(
                "flex items-center justify-between gap-4 rounded-lg border border-gray-800 px-4 py-3",
                selection.has(obj.id) ? "border-gray-600 bg-gray-800" : "bg-gray-900"
              )}
            >
              <div className="flex min-w-0 flex-1 items-center gap-3">
                <input
                  type="checkbox"
                  checked={selection.has(obj.id)}
                  onChange={() => selection.toggle(obj.id)}
                  className="h-3.5 w-3.5 shrink-0 accent-indigo-500"
                  aria-label={`Select ${obj.title ?? "item"}`}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="rounded bg-gray-800 px-1.5 py-0.5 text-xs capitalize text-gray-400">{obj.kind}</span>
                    <span className="truncate text-sm font-medium text-white">{obj.title || "(untitled)"}</span>
                  </div>
                  <p className="mt-1 text-xs text-gray-500">
                    Deleted {obj.deleted_at ? new Date(obj.deleted_at).toLocaleDateString() : "unknown"}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => void handleRestore(obj.id)}
                className="flex shrink-0 items-center gap-1.5 rounded-md bg-gray-700 px-3 py-1.5 text-xs text-white transition-colors hover:bg-gray-600"
              >
                <RotateCcw size={12} />
                Restore
              </button>
            </div>
          ))}
        </div>
      </ListPage>

      <BulkActionBar
        count={selection.size}
        onClear={selection.clear}
        actions={[
          {
            label: "Restore all",
            loading: bulkRestoring,
            onClick: () => void handleBulkRestore(),
          },
        ]}
      />
    </>
  );
}
