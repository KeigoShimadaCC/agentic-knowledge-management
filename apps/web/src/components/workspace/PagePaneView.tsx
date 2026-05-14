"use client";

import { useEffect, useState } from "react";
import { getPage } from "@/lib/api";
import type { PageOut } from "@/types";

function Skeleton() {
  return (
    <div className="animate-pulse space-y-3 p-4">
      <div className="h-3 w-full rounded bg-gray-800" />
      <div className="h-3 w-4/5 rounded bg-gray-800" />
      <div className="h-3 w-3/5 rounded bg-gray-800" />
    </div>
  );
}

export function PagePaneView({ id }: { id: string }) {
  const [page, setPage] = useState<PageOut | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);

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

  if (isLoading) return <Skeleton />;
  if (error || !page) {
    return <p className="p-4 text-sm text-red-400">Could not load page.</p>;
  }

  const paragraphs = (page.content_text ?? "").split(/\n\n+/).filter(Boolean);

  return (
    <div className="p-4">
      <p className="mb-3 text-xs text-gray-500">{page.word_count} words</p>
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
    </div>
  );
}
