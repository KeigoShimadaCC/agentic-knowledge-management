"use client";

import { formatDistanceToNow } from "date-fns";
import Link from "next/link";
import { clsx } from "clsx";
import type { IngestionStatus, SourceOut, SourceType } from "@/types";

const sourceTypeLabels: Record<SourceType, string> = {
  pdf: "PDF",
  image: "IMG",
  video: "VID",
  audio: "AUD",
  youtube: "YT",
  web: "WEB",
  csv: "CSV",
  file: "FILE",
};

const statusClasses: Record<IngestionStatus, string> = {
  pending: "bg-gray-800 text-gray-300 border-gray-700",
  running: "bg-amber-950 text-amber-300 border-amber-800 animate-pulse",
  ready: "bg-green-950 text-green-300 border-green-800",
  error: "bg-red-950 text-red-300 border-red-800",
};

export function SourceTypeBadge({ sourceType }: { sourceType: SourceType }) {
  return (
    <span className="inline-flex h-9 w-11 shrink-0 items-center justify-center rounded-md bg-gray-800 text-[11px] font-semibold text-gray-200">
      {sourceTypeLabels[sourceType]}
    </span>
  );
}

export function SourceStatusBadge({ status }: { status: IngestionStatus }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium capitalize",
        statusClasses[status]
      )}
    >
      {status}
    </span>
  );
}

interface SourceCardProps {
  source: SourceOut;
}

export function SourceCard({ source }: SourceCardProps) {
  return (
    <Link
      href={`/app/sources/${source.id}`}
      className="flex items-start gap-3 rounded-lg border border-gray-800 bg-gray-900 p-3 transition-colors hover:border-gray-600 hover:bg-gray-800"
    >
      <SourceTypeBadge sourceType={source.source_type} />
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-3">
          <h2 className="truncate text-sm font-medium text-white">{source.title || "(untitled)"}</h2>
          <SourceStatusBadge status={source.ingestion_status} />
        </div>
        <p className="mt-1 text-xs text-gray-500">
          {formatDistanceToNow(new Date(source.created_at), { addSuffix: true })}
        </p>
      </div>
    </Link>
  );
}
