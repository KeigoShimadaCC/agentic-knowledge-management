"use client";

import { useMemo, useState } from "react";
import { Plus } from "lucide-react";
import { SourceList } from "@/components/sources/SourceList";
import { CreateSourceModal } from "@/components/sources/CreateSourceModal";
import { useSources } from "@/lib/hooks/useSources";
import { ListPage } from "@/components/lists/ListPage";
import { ListToolbar, type SortKey } from "@/components/lists/ListToolbar";
import type { SourceOut } from "@/types";

function sortSources(sources: SourceOut[], sort: SortKey): SourceOut[] {
  const arr = [...sources];
  if (sort === "newest") return arr.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  if (sort === "oldest") return arr.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
  return arr.sort((a, b) => (a.title ?? "").localeCompare(b.title ?? ""));
}

export default function SourcesPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const { sources, isLoading, mutate } = useSources();
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<SortKey>("newest");

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    const matched = q
      ? sources.filter((s) => (s.title ?? "").toLowerCase().includes(q) || (s.url ?? "").toLowerCase().includes(q))
      : sources;
    return sortSources(matched, sort);
  }, [sources, search, sort]);

  return (
    <>
    <ListPage
      title="Sources"
      loading={isLoading}
      empty={!isLoading && filtered.length === 0}
      emptyTitle={search ? "No sources match" : "No sources yet"}
      emptyDescription={search ? "Try a different search" : "Add a URL or upload a file to get started"}
      actions={
        <button
          type="button"
          onClick={() => setIsModalOpen(true)}
          className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-white text-gray-950 transition-colors hover:bg-gray-200"
          aria-label="Create source"
        >
          <Plus size={18} />
        </button>
      }
      toolbar={
        <ListToolbar
          search={search}
          onSearch={setSearch}
          sort={sort}
          onSort={setSort}
          searchPlaceholder="Filter sources…"
        />
      }
    >
      <SourceList sources={filtered} />
    </ListPage>
    <CreateSourceModal
      isOpen={isModalOpen}
      onClose={() => setIsModalOpen(false)}
      onCreated={() => void mutate()}
    />
    </>
  );
}
