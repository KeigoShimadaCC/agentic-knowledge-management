"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getObjectBacklinks } from "@/lib/api";
import { objectRoute } from "@/lib/objectRouting";
import type { EdgeWithObjectsOut } from "@/types";

interface BacklinksPanelProps {
  objectId: string;
}

function KindBadge({ kind }: { kind: string }) {
  const className =
    kind === "page"
      ? "bg-blue-950 text-blue-300 border-blue-800"
      : kind === "source"
        ? "bg-green-950 text-green-300 border-green-800"
        : "bg-gray-900 text-gray-300 border-gray-700";

  return (
    <span className={`rounded border px-1.5 py-0.5 text-[10px] uppercase ${className}`}>
      {kind}
    </span>
  );
}

function SkeletonRows() {
  return (
    <div className="space-y-2 p-3">
      {[0, 1, 2].map((index) => (
        <div key={index} className="rounded border border-gray-800 p-3">
          <div className="h-3 w-2/3 rounded bg-gray-800" />
          <div className="mt-2 h-2 w-1/3 rounded bg-gray-900" />
        </div>
      ))}
    </div>
  );
}

export function BacklinksPanel({ objectId }: BacklinksPanelProps) {
  const router = useRouter();
  const [backlinks, setBacklinks] = useState<EdgeWithObjectsOut[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);

    getObjectBacklinks(objectId)
      .then((items) => {
        if (isMounted) setBacklinks(items);
      })
      .catch(() => {
        if (isMounted) setError("Could not load backlinks.");
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [objectId]);

  if (isLoading) return <SkeletonRows />;
  if (error) return <div className="p-4 text-sm text-red-400">{error}</div>;
  if (backlinks.length === 0) {
    return <div className="p-4 text-sm text-gray-500">No backlinks yet.</div>;
  }

  return (
    <div className="divide-y divide-gray-900">
      {backlinks.map((edge) => {
        const source = edge.source_object;
        if (!source) return null;

        return (
          <button
            type="button"
            key={edge.id}
            onClick={() => router.push(objectRoute(source.kind, source.id))}
            className="block w-full px-3 py-3 text-left hover:bg-gray-900"
          >
            <div className="truncate text-sm text-gray-100">{source.title}</div>
            <div className="mt-2 flex items-center gap-2">
              <KindBadge kind={source.kind} />
              <span className="truncate text-xs text-gray-500">{edge.kind}</span>
            </div>
          </button>
        );
      })}
    </div>
  );
}
