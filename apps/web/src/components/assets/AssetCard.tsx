"use client";

import { FileText, Film, Music, Table, File } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import type { ObjectOut } from "@/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function humanSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function FileIcon({ contentType }: { contentType: string }) {
  if (contentType.startsWith("video/")) return <Film size={32} className="text-purple-400" />;
  if (contentType.startsWith("audio/")) return <Music size={32} className="text-green-400" />;
  if (contentType === "text/csv" || contentType.includes("spreadsheet"))
    return <Table size={32} className="text-emerald-400" />;
  if (contentType === "application/pdf" || contentType.startsWith("text/"))
    return <FileText size={32} className="text-orange-400" />;
  return <File size={32} className="text-gray-400" />;
}

interface AssetCardProps {
  object: ObjectOut;
  contentType: string;
  sizeBytes: number;
  assetId: string;
  onClick: () => void;
}

export function AssetCard({ object, contentType, sizeBytes, assetId, onClick }: AssetCardProps) {
  const isImage = contentType.startsWith("image/");

  return (
    <button
      onClick={onClick}
      className="flex flex-col bg-gray-900 border border-gray-800 rounded-lg overflow-hidden hover:border-gray-600 transition-colors text-left w-full"
    >
      <div className="aspect-square bg-gray-800 flex items-center justify-center overflow-hidden">
        {isImage ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={`${BASE}/api/v1/assets/${assetId}/download`}
            alt={object.title}
            className="w-full h-full object-cover"
          />
        ) : (
          <FileIcon contentType={contentType} />
        )}
      </div>
      <div className="p-2">
        <p className="text-xs text-white font-medium truncate">{object.title}</p>
        <p className="text-xs text-gray-500">
          {humanSize(sizeBytes)} · {formatDistanceToNow(new Date(object.updated_at), { addSuffix: true })}
        </p>
      </div>
    </button>
  );
}
