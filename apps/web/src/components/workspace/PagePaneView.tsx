"use client";

import { useEffect, useState, useCallback } from "react";
import { getPage, createEdge } from "@/lib/api";
import type { PageOut } from "@/types";
import { useCrossPaneDragTarget, type DragPayload } from "@/hooks/useCrossPane";

function Skeleton() {
  return (
    <div className="animate-pulse space-y-3 p-4">
      <div className="h-3 w-full rounded bg-gray-800" />
      <div className="h-3 w-4/5 rounded bg-gray-800" />
      <div className="h-3 w-3/5 rounded bg-gray-800" />
    </div>
  );
}

interface DroppedQuote {
  text: string;
  attribution: string;
}

export function PagePaneView({ id, objectTitle }: { id: string; objectTitle?: string }) {
  const [page, setPage] = useState<PageOut | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);
  const [quotes, setQuotes] = useState<DroppedQuote[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setError(false);
    getPage(id)
      .then((data) => { if (active) setPage(data); })
      .catch(() => { if (active) setError(true); })
      .finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [id]);

  const handleQuoteDrop = useCallback(
    (payload: DragPayload) => {
      setQuotes((prev) => [...prev, { text: payload.text, attribution: payload.sourceTitle }]);
      setIsDragOver(false);
      // Create a cites edge from this page to the source
      createEdge({ source_id: id, target_id: payload.sourceObjectId, kind: "cites" }).catch(() => {});
    },
    [id]
  );

  const dropProps = useCrossPaneDragTarget(handleQuoteDrop);

  if (isLoading) return <Skeleton />;
  if (error || !page) {
    return <p className="p-4 text-sm text-red-400">Could not load page.</p>;
  }

  const paragraphs = (page.content_text ?? "").split(/\n\n+/).filter(Boolean);

  return (
    <div
      {...dropProps}
      onDragEnter={() => setIsDragOver(true)}
      onDragLeave={() => setIsDragOver(false)}
      className={`p-4 ${isDragOver ? "ring-2 ring-inset ring-blue-500 bg-blue-950/10" : ""}`}
    >
      <p className="mb-3 text-xs text-gray-500">{page.word_count} words</p>
      {quotes.length > 0 && (
        <div className="mb-4 space-y-2">
          <p className="text-[10px] uppercase text-gray-600">Dropped quotes</p>
          {quotes.map((q, i) => (
            <blockquote key={i} className="rounded border-l-2 border-blue-600 bg-gray-900 px-3 py-2">
              <p className="text-sm text-gray-300">&ldquo;{q.text}&rdquo;</p>
              <footer className="mt-1 text-xs text-gray-500">— {q.attribution}</footer>
            </blockquote>
          ))}
        </div>
      )}
      <div className="space-y-3 text-sm leading-relaxed text-gray-300">
        {paragraphs.length > 0 ? (
          paragraphs.map((para, i) => (
            <p key={i} className="whitespace-pre-wrap">
              {para}
            </p>
          ))
        ) : (
          <p className="text-gray-600">No content yet.</p>
        )}
      </div>
      {isDragOver && (
        <div className="mt-4 rounded border border-dashed border-blue-500 p-4 text-center text-xs text-blue-400">
          Drop to add quote
        </div>
      )}
    </div>
  );
}
