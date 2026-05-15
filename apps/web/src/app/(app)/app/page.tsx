"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { deleteObject } from "@/lib/api";
import { useObjects } from "@/lib/hooks/useObjects";
import { useWorkspaceLite } from "@/components/workspace/WorkspaceLiteProvider";
import { objectRoute } from "@/lib/objectRouting";
import { toast } from "@/components/ui/Toast";
import { ListPage } from "@/components/lists/ListPage";
import { ListToolbar, type SortKey } from "@/components/lists/ListToolbar";
import { BulkActionBar } from "@/components/lists/BulkActionBar";
import { useListSelection } from "@/lib/hooks/useListSelection";
import { useListKeyNav } from "@/lib/hooks/useListKeyNav";
import type { ObjectOut } from "@/types";
import { cn } from "@/lib/cn";

function sortObjects(objects: ObjectOut[], sort: SortKey): ObjectOut[] {
  const arr = [...objects];
  if (sort === "newest") return arr.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
  if (sort === "oldest") return arr.sort((a, b) => new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime());
  return arr.sort((a, b) => (a.title ?? "").localeCompare(b.title ?? ""));
}

export default function AppPage() {
  const router = useRouter();
  const { openSidePane } = useWorkspaceLite();
  const { objects, isLoading, mutate } = useObjects({ limit: 100 });
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<SortKey>("newest");
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const selection = useListSelection();

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    const matched = q ? objects.filter((o) => (o.title ?? "").toLowerCase().includes(q) || o.kind.includes(q)) : objects;
    return sortObjects(matched, sort);
  }, [objects, search, sort]);

  async function softDelete(id: string, title: string) {
    await deleteObject(id);
    await mutate();
    toast.success(`"${title || "Item"}" moved to trash`);
  }

  const nav = useListKeyNav({
    count: filtered.length,
    onOpen: (i) => { const obj = filtered[i]; if (obj) router.push(objectRoute(obj.kind, obj.id)); },
    onOpenInPane: (i) => { const obj = filtered[i]; if (obj) openSidePane(obj); },
    onDelete: (i) => { const obj = filtered[i]; if (obj) void softDelete(obj.id, obj.title ?? ""); },
  });

  async function handleBulkDelete() {
    setBulkDeleting(true);
    const ids = Array.from(selection.selected);
    const chunks: string[][] = [];
    for (let i = 0; i < ids.length; i += 4) chunks.push(ids.slice(i, i + 4));
    for (const chunk of chunks) {
      await Promise.allSettled(chunk.map((id) => deleteObject(id)));
    }
    await mutate();
    selection.clear();
    setBulkDeleting(false);
    toast.success(`${ids.length} item${ids.length !== 1 ? "s" : ""} moved to trash`);
  }

  return (
    <>
      <ListPage
        title="All Objects"
        loading={isLoading}
        empty={!isLoading && filtered.length === 0}
        emptyTitle={search ? "No results" : "No objects yet"}
        emptyDescription={search ? "Try a different search" : "Create a page or upload a file to get started"}
        toolbar={
          <ListToolbar
            search={search}
            onSearch={setSearch}
            sort={sort}
            onSort={setSort}
            searchPlaceholder="Filter objects…"
          />
        }
      >
        <div className="space-y-1">
          {filtered.map((obj, i) => (
            <div
              key={obj.id}
              className={cn(
                "flex items-center gap-3 rounded-lg border border-gray-800 px-3 py-2.5 transition-colors",
                nav.highlightIdx === i ? "border-gray-600 bg-gray-800" : "bg-gray-900 hover:bg-gray-800"
              )}
              onMouseEnter={() => nav.setHighlightIdx(i)}
            >
              <input
                type="checkbox"
                checked={selection.has(obj.id)}
                onChange={() => selection.toggle(obj.id)}
                className="h-3.5 w-3.5 shrink-0 accent-indigo-500"
                aria-label={`Select ${obj.title ?? "item"}`}
              />
              <span className="w-14 shrink-0 font-mono text-xs uppercase text-gray-500">{obj.kind}</span>
              <Link
                href={objectRoute(obj.kind, obj.id)}
                className="min-w-0 flex-1 truncate text-sm font-medium text-white hover:underline"
              >
                {obj.title || "(untitled)"}
              </Link>
              <span className="shrink-0 text-xs text-gray-500">
                {formatDistanceToNow(new Date(obj.updated_at), { addSuffix: true })}
              </span>
            </div>
          ))}
        </div>
      </ListPage>

      <BulkActionBar
        count={selection.size}
        onClear={selection.clear}
        actions={[
          {
            label: "Delete",
            variant: "danger",
            loading: bulkDeleting,
            onClick: () => void handleBulkDelete(),
          },
        ]}
      />
    </>
  );
}
