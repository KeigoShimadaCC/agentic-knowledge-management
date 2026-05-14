"use client";

import type { SearchResult } from "@/types";

const KIND_COLORS: Record<string, string> = {
  page: "bg-blue-900 text-blue-200",
  source: "bg-green-900 text-green-200",
  asset: "bg-gray-700 text-gray-300",
};

interface SearchResultCardProps {
  result: SearchResult;
  isSelected: boolean;
  onSelect: () => void;
}

export function SearchResultCard({ result, isSelected, onSelect }: SearchResultCardProps) {
  const kindColor = KIND_COLORS[result.kind] ?? "bg-gray-700 text-gray-300";
  const snippetHtml = result.snippet ?? "";

  return (
    <button
      onClick={onSelect}
      className={`w-full border-b border-gray-800 px-4 py-3 text-left transition-colors ${
        isSelected ? "bg-gray-800" : "hover:bg-gray-900"
      }`}
    >
      <div className="mb-1 flex items-center gap-2">
        <span className={`rounded px-2 py-0.5 text-xs font-medium ${kindColor}`}>
          {result.kind}
        </span>
        {result.source_type && (
          <span className="rounded bg-gray-700 px-2 py-0.5 text-xs text-gray-300">
            {result.source_type}
          </span>
        )}
        <span className="flex-1 truncate text-sm font-medium text-gray-100">{result.title}</span>
      </div>
      {snippetHtml && (
        <p
          className="line-clamp-2 text-xs text-gray-400 [&_mark]:rounded [&_mark]:bg-yellow-700 [&_mark]:text-yellow-100"
          dangerouslySetInnerHTML={{ __html: snippetHtml }}
        />
      )}
      {result.tags.length > 0 && (
        <div className="mt-1 flex gap-1">
          {result.tags.slice(0, 3).map((tag) => (
            <span key={tag} className="text-xs text-gray-500">
              #{tag}
            </span>
          ))}
        </div>
      )}
    </button>
  );
}
