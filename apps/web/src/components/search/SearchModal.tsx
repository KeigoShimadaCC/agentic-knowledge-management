"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useSearch } from "@/lib/hooks/useSearch";
import type { SearchMode } from "@/types";
import { objectRoute } from "@/lib/objectRouting";
import { SearchResultCard } from "./SearchResultCard";

const MODES: { label: string; value: SearchMode }[] = [
  { label: "Keyword", value: "keyword" },
  { label: "Semantic", value: "semantic" },
  { label: "Hybrid", value: "hybrid" },
];

interface SearchModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SearchModal({ isOpen, onClose }: SearchModalProps) {
  const router = useRouter();
  const { results, isLoading, error, query, setQuery, mode, setMode } = useSearch();
  const [selectedIdx, setSelectedIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setSelectedIdx(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  useEffect(() => {
    setSelectedIdx(0);
  }, [results]);

  useEffect(() => {
    if (!isOpen) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIdx((i) => Math.min(i + 1, results.length - 1));
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIdx((i) => Math.max(i - 1, 0));
      }
      if (e.key === "Enter" && results[selectedIdx]) {
        onClose();
        router.push(objectRoute(results[selectedIdx].kind, results[selectedIdx].id));
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [isOpen, results, selectedIdx, onClose, router]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center px-4 pt-20">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative w-full max-w-xl overflow-hidden rounded-xl border border-gray-700 bg-gray-950 shadow-2xl">
        <div className="flex border-b border-gray-800">
          {MODES.map(({ label, value }) => (
            <button
              key={value}
              onClick={() => setMode(value)}
              className={`flex-1 py-2 text-xs font-medium transition-colors ${
                mode === value
                  ? "border-b-2 border-blue-500 text-white"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3 border-b border-gray-800 px-4 py-3">
          <svg
            className="h-4 w-4 shrink-0 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search knowledge base..."
            className="flex-1 bg-transparent text-sm text-gray-100 outline-none placeholder:text-gray-500"
          />
          {isLoading && (
            <svg className="h-4 w-4 shrink-0 animate-spin text-gray-400" fill="none" viewBox="0 0 24 24">
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
          )}
          <kbd className="rounded bg-gray-800 px-1.5 py-0.5 text-xs text-gray-500">Esc</kbd>
        </div>
        <div className="max-h-80 overflow-y-auto">
          {error && <p className="px-4 py-3 text-sm text-red-400">{error}</p>}
          {!isLoading && !error && query.length >= 2 && results.length === 0 && (
            <p className="px-4 py-6 text-center text-sm text-gray-500">No results found</p>
          )}
          {!error &&
            results.map((result, idx) => (
              <SearchResultCard
                key={result.id}
                result={result}
                isSelected={idx === selectedIdx}
                onSelect={() => {
                  onClose();
                  router.push(objectRoute(result.kind, result.id));
                }}
              />
            ))}
          {!query && (
            <p className="px-4 py-6 text-center text-xs text-gray-600">
              Type at least 2 characters to search
            </p>
          )}
        </div>
        {results.length > 0 && (
          <div className="flex justify-between border-t border-gray-800 px-4 py-2 text-xs text-gray-600">
            <span>
              {results.length} result{results.length !== 1 ? "s" : ""}
            </span>
            <span>↑↓ navigate · Enter open</span>
          </div>
        )}
      </div>
    </div>
  );
}
