"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { SourceList } from "@/components/sources/SourceList";
import { CreateSourceModal } from "@/components/sources/CreateSourceModal";
import { useSources } from "@/lib/hooks/useSources";

export default function SourcesPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const { sources, isLoading, mutate } = useSources();

  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Sources</h1>
        <button
          type="button"
          onClick={() => setIsModalOpen(true)}
          className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-white text-gray-950 transition-colors hover:bg-gray-200"
          aria-label="Create source"
        >
          <Plus size={18} />
        </button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <div
              key={index}
              className="h-20 animate-pulse rounded-lg border border-gray-800 bg-gray-900"
            />
          ))}
        </div>
      ) : sources.length === 0 ? (
        <div className="py-16 text-center text-gray-500">
          <p className="text-lg">No sources yet</p>
          <p className="mt-2 text-sm">Add a URL or upload a file to get started</p>
        </div>
      ) : (
        <SourceList sources={sources} />
      )}

      <CreateSourceModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onCreated={() => {
          void mutate();
        }}
      />
    </div>
  );
}
