"use client";

import { useState } from "react";
import { useObjects } from "@/lib/hooks/useObjects";
import { AssetUploader } from "@/components/assets/AssetUploader";
import { AssetGrid } from "@/components/assets/AssetGrid";
import { ListPage } from "@/components/lists/ListPage";
import { ListToolbar, type SortKey, type ViewMode } from "@/components/lists/ListToolbar";
import { useMemo } from "react";
import type { ObjectOut } from "@/types";

function sortObjects(objects: ObjectOut[], sort: SortKey): ObjectOut[] {
  const arr = [...objects];
  if (sort === "newest") return arr.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
  if (sort === "oldest") return arr.sort((a, b) => new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime());
  return arr.sort((a, b) => (a.title ?? "").localeCompare(b.title ?? ""));
}

export default function AssetsPage() {
  const { objects, mutate } = useObjects({ kind: "asset", limit: 100 });
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<SortKey>("newest");
  const [viewMode, setViewMode] = useState<ViewMode>("grid");

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    const matched = q ? objects.filter((o) => (o.title ?? "").toLowerCase().includes(q)) : objects;
    return sortObjects(matched, sort);
  }, [objects, search, sort]);

  // TODO(asset-metadata): asset metadata (content_type, size_bytes) requires separate /api/v1/assets/{id} fetches.
  // Deferred to a future phase — using placeholder values for now.
  const assetData = filtered.map((obj) => ({
    object: obj,
    contentType: "application/octet-stream",
    sizeBytes: 0,
  }));

  return (
    <ListPage
      title="Assets"
      empty={filtered.length === 0 && !search}
      emptyTitle="No assets yet"
      emptyDescription="Drop files below to upload your first asset"
      emptyAction={<AssetUploader onUploadComplete={() => void mutate()} />}
      toolbar={
        <ListToolbar
          search={search}
          onSearch={setSearch}
          sort={sort}
          onSort={setSort}
          viewMode={viewMode}
          onViewMode={setViewMode}
          searchPlaceholder="Filter assets…"
        />
      }
    >
      <div className="mb-6">
        <AssetUploader onUploadComplete={() => void mutate()} />
      </div>
      {filtered.length > 0 && (
        viewMode === "grid"
          ? <AssetGrid assets={assetData} />
          : (
            <div className="space-y-1">
              {filtered.map((obj) => (
                <div key={obj.id} className="flex items-center gap-3 rounded-lg border border-gray-800 bg-gray-900 px-3 py-2.5">
                  <span className="min-w-0 flex-1 truncate text-sm text-white">{obj.title || "(untitled)"}</span>
                  <span className="text-xs text-gray-500">{new Date(obj.updated_at).toLocaleDateString()}</span>
                </div>
              ))}
            </div>
          )
      )}
    </ListPage>
  );
}
