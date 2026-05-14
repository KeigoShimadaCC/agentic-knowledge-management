"use client";

import Link from "next/link";
import { useSource } from "@/lib/hooks/useSource";
import { SourceStatusBadge, SourceTypeBadge } from "@/components/sources/SourceCard";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isPreviewRows(value: unknown): value is unknown[][] {
  return Array.isArray(value) && value.every((row) => Array.isArray(row));
}

function CsvPreview({ previewData }: { previewData: Record<string, unknown> | null }) {
  const headers = previewData?.headers;
  if (!isStringArray(headers)) return null;

  const rowsValue = previewData?.rows;
  const rows = isPreviewRows(rowsValue) ? rowsValue : [];

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900">
      <div className="border-b border-gray-800 p-3">
        <h2 className="text-sm font-semibold text-white">CSV Preview</h2>
      </div>
      <div className="overflow-auto">
        <table className="w-full min-w-max text-left text-sm">
          <thead className="bg-gray-950 text-xs uppercase text-gray-500">
            <tr>
              {headers.map((header) => (
                <th key={header} className="border-b border-gray-800 px-3 py-2 font-medium">
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="text-gray-300">
            {rows.slice(0, 20).map((row, rowIndex) => (
              <tr key={rowIndex} className="border-b border-gray-800 last:border-0">
                {headers.map((header, cellIndex) => (
                  <td key={`${header}-${cellIndex}`} className="px-3 py-2">
                    {String(row[cellIndex] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function SourceDetailPage({ params }: { params: { id: string } }) {
  const { source, isLoading } = useSource(params.id);

  if (isLoading) {
    return <div className="p-8 text-gray-400">Loading...</div>;
  }

  if (!source) {
    return (
      <div className="p-8">
        <Link href="/sources" className="text-sm text-gray-400 hover:text-white">
          Back to Sources
        </Link>
        <div className="mt-8 text-gray-500">Source not found</div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <Link href="/sources" className="text-sm text-gray-400 hover:text-white">
        Back to Sources
      </Link>

      <div className="mt-6 mb-6 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="truncate text-2xl font-bold text-white">{source.title || "(untitled)"}</h1>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <SourceTypeBadge sourceType={source.source_type} />
            <SourceStatusBadge status={source.ingestion_status} />
          </div>
        </div>
      </div>

      <div className="space-y-6">
        {source.ingestion_status === "error" && source.error_message && (
          <div className="rounded-lg border border-red-800 bg-red-950 p-4 text-sm text-red-200">
            {source.error_message}
          </div>
        )}

        {source.thumbnail_path && (
          <div className="overflow-hidden rounded-lg border border-gray-800 bg-gray-900">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={`${BASE}/api/v1/sources/${params.id}/thumbnail`}
              alt={source.title}
              className="max-h-96 w-full object-contain"
            />
          </div>
        )}

        {source.source_type === "pdf" && source.page_count !== null && (
          <div className="rounded-lg border border-gray-800 bg-gray-900 p-4 text-sm text-gray-300">
            Page count: <span className="font-medium text-white">{source.page_count}</span>
          </div>
        )}

        <CsvPreview previewData={source.preview_data} />

        {source.extracted_text && (
          <div className="rounded-lg border border-gray-800 bg-gray-900">
            <div className="border-b border-gray-800 p-3">
              <h2 className="text-sm font-semibold text-white">Extracted Text</h2>
            </div>
            <pre className="max-h-96 overflow-auto whitespace-pre-wrap p-4 text-sm text-gray-300">
              {source.extracted_text}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
