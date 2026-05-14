"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { formatDistanceToNow } from "date-fns";
import { Pin, Plus } from "lucide-react";

import { createPage } from "@/lib/api";
import { useObjects } from "@/lib/hooks/useObjects";
import { objectRoute } from "@/lib/objectRouting";
import { ApiError } from "@/types";

export default function PagesListPage() {
  const router = useRouter();
  const { objects, isLoading, mutate } = useObjects({ kind: "page", limit: 100 });
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleNewPage() {
    setError(null);
    setCreating(true);
    try {
      const res = await createPage("Untitled page");
      await mutate();
      router.push(`/pages/${res.object.id}`);
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else if (err instanceof Error) setError(err.message);
      else setError("Could not create page");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Pages</h1>
        <button
          type="button"
          onClick={() => void handleNewPage()}
          disabled={creating}
          className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-white text-gray-950 transition-colors hover:bg-gray-200 disabled:cursor-not-allowed disabled:opacity-60"
          aria-label="New page"
        >
          <Plus size={18} />
        </button>
      </div>

      {error && (
        <p className="mb-4 rounded-lg border border-red-900 bg-red-950/40 px-3 py-2 text-sm text-red-300">
          {error}
        </p>
      )}

      {isLoading ? (
        <div className="text-gray-400">Loading...</div>
      ) : objects.length === 0 ? (
        <div className="py-16 text-center text-gray-500">
          <p className="text-lg mb-2">No pages yet</p>
          <p className="text-sm">Use + to create a page or browse All Objects.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {objects.map((obj) => (
            <Link
              key={obj.id}
              href={objectRoute(obj.kind, obj.id)}
              className="flex items-center gap-3 rounded-lg border border-gray-800 bg-gray-900 p-3 transition-colors hover:bg-gray-800"
            >
              <span className="flex min-w-0 flex-1 items-center gap-2">
                {obj.is_pinned ? (
                  <Pin size={14} className="shrink-0 text-amber-400" aria-hidden />
                ) : null}
                <span className="truncate text-sm font-medium text-white">
                  {obj.title || "(untitled)"}
                </span>
              </span>
              <span className="shrink-0 text-xs text-gray-500">
                {formatDistanceToNow(new Date(obj.updated_at), { addSuffix: true })}
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
