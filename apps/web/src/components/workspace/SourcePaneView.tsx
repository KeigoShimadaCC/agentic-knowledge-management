"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { getSource } from "@/lib/api";
import type { SourceOut } from "@/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const EXCERPT_LENGTH = 800;

function Skeleton() {
  return (
    <div className="animate-pulse space-y-3 p-4">
      <div className="h-3 w-full rounded bg-gray-800" />
      <div className="h-3 w-4/5 rounded bg-gray-800" />
      <div className="h-3 w-3/5 rounded bg-gray-800" />
    </div>
  );
}

function Badge({ label, colorClass }: { label: string; colorClass: string }) {
  return (
    <span className={`rounded border px-1.5 py-0.5 text-[10px] uppercase ${colorClass}`}>
      {label}
    </span>
  );
}

export function SourcePaneView({ id }: { id: string }) {
  const [source, setSource] = useState<SourceOut | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setError(false);
    getSource(id)
      .then((data) => { if (active) setSource(data); })
      .catch(() => { if (active) setError(true); })
      .finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [id]);

  if (isLoading) return <Skeleton />;
  if (error || !source) {
    return <p className="p-4 text-sm text-red-400">Could not load source.</p>;
  }

  const excerpt = source.extracted_text
    ? source.extracted_text.slice(0, EXCERPT_LENGTH) +
      (source.extracted_text.length > EXCERPT_LENGTH ? "…" : "")
    : null;

  return (
    <div className="p-4 space-y-3">
      <div className="flex flex-wrap gap-2">
        <Badge label={source.source_type} colorClass="bg-green-950 text-green-300 border-green-800" />
        <Badge
          label={source.ingestion_status}
          colorClass={
            source.ingestion_status === "ready"
              ? "bg-emerald-950 text-emerald-300 border-emerald-800"
              : source.ingestion_status === "error"
                ? "bg-red-950 text-red-300 border-red-800"
                : "bg-gray-900 text-gray-400 border-gray-700"
          }
        />
      </div>
      {source.thumbnail_path && (
        <div className="relative h-32 w-full overflow-hidden rounded border border-gray-800">
          <Image
            src={`${BASE}/api/v1/sources/${id}/thumbnail`}
            alt="thumbnail"
            fill
            className="object-cover"
            unoptimized
          />
        </div>
      )}
      {excerpt ? (
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-gray-300">{excerpt}</p>
      ) : (
        <p className="text-sm text-gray-600">No extracted text yet.</p>
      )}
    </div>
  );
}
