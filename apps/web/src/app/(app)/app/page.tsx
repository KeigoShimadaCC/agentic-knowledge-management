"use client";

import { useObjects } from "@/lib/hooks/useObjects";
import { objectRoute } from "@/lib/objectRouting";
import { formatDistanceToNow } from "date-fns";
import Link from "next/link";

export default function AppPage() {
  const { objects, isLoading } = useObjects({ limit: 20 });

  if (isLoading) {
    return (
      <div className="p-8 text-gray-400">Loading...</div>
    );
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">All Objects</h1>
      </div>

      {objects.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <p className="text-lg mb-2">No objects yet</p>
          <p className="text-sm">Create a page or upload a file to get started</p>
        </div>
      ) : (
        <div className="space-y-2">
          {objects.map((obj) => (
            <Link
              key={obj.id}
              href={objectRoute(obj.kind, obj.id)}
              className="flex items-center gap-3 p-3 rounded-lg bg-gray-900 hover:bg-gray-800 border border-gray-800 transition-colors"
            >
              <span className="text-xs text-gray-500 uppercase font-mono w-12">{obj.kind}</span>
              <span className="flex-1 text-white text-sm font-medium truncate">
                {obj.title || "(untitled)"}
              </span>
              <span className="text-xs text-gray-500 shrink-0">
                {formatDistanceToNow(new Date(obj.updated_at), { addSuffix: true })}
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
