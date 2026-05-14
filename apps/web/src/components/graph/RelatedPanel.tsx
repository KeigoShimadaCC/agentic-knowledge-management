"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Columns2 } from "lucide-react";
import { getObjectRelated } from "@/lib/api";
import { objectRoute } from "@/lib/objectRouting";
import { useWorkspaceLite } from "@/components/workspace/WorkspaceLiteProvider";
import type { RelatedObjectOut } from "@/types";

interface RelatedPanelProps {
  objectId: string;
}

function KindBadge({ kind }: { kind: string }) {
  const className =
    kind === "page"
      ? "bg-blue-950 text-blue-300 border-blue-800"
      : kind === "source"
        ? "bg-green-950 text-green-300 border-green-800"
        : kind === "chat"
          ? "bg-violet-950 text-violet-300 border-violet-800"
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

export function RelatedPanel({ objectId }: RelatedPanelProps) {
  const router = useRouter();
  const { openSidePane } = useWorkspaceLite();
  const [related, setRelated] = useState<RelatedObjectOut[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);

    getObjectRelated(objectId)
      .then((items) => {
        if (isMounted) setRelated(items);
      })
      .catch(() => {
        if (isMounted) setError("Could not load related objects.");
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
  if (related.length === 0) {
    return <div className="p-4 text-sm text-gray-500">No related objects yet.</div>;
  }

  return (
    <div className="divide-y divide-gray-900">
      {related.map((object) => (
        <div
          key={`${object.id}-${object.direction}-${object.edge_kind}`}
          className="flex items-stretch hover:bg-gray-900"
        >
          <button
            type="button"
            onClick={() => router.push(objectRoute(object.kind, object.id))}
            className="min-w-0 flex-1 px-3 py-3 text-left"
          >
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">{object.direction === "incoming" ? "←" : "→"}</span>
              <span className="min-w-0 flex-1 truncate text-sm text-gray-100">{object.title}</span>
            </div>
            <div className="mt-2 flex items-center gap-2">
              <KindBadge kind={object.kind} />
              <span className="truncate text-xs text-gray-500">{object.edge_kind}</span>
            </div>
          </button>
          <button
            type="button"
            title="Open in side pane"
            onClick={() => openSidePane({ id: object.id, kind: object.kind, title: object.title ?? "" })}
            className="shrink-0 px-2 text-gray-600 hover:text-gray-200"
          >
            <Columns2 className="h-3.5 w-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
}
