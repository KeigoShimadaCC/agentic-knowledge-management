"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { hybridSearch, keywordSearch, vectorSearch } from "@/lib/api";
import { ApiError } from "@/types";
import type { SearchMode, SearchResult } from "@/types";

interface UseSearchReturn {
  results: SearchResult[];
  isLoading: boolean;
  error: string | null;
  query: string;
  setQuery: (q: string) => void;
  mode: SearchMode;
  setMode: (m: SearchMode) => void;
}

export function useSearch(): UseSearchReturn {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<SearchMode>("hybrid");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const doSearch = useCallback(async (q: string, m: SearchMode) => {
    if (q.length < 2) {
      setResults([]);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const opts = { limit: 10 };
      let resp;
      if (m === "keyword") {
        resp = await keywordSearch(q, opts);
      } else if (m === "semantic") {
        resp = await vectorSearch(q, opts);
      } else {
        resp = await hybridSearch(q, opts);
      }
      setResults(resp.results);
    } catch (err) {
      if (err instanceof ApiError && err.status === 503) {
        try {
          const resp = await keywordSearch(q, { limit: 10 });
          setResults(resp.results);
        } catch {
          setError("Search unavailable");
          setResults([]);
        }
      } else {
        setError("Search failed");
        setResults([]);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      doSearch(query, mode);
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, mode, doSearch]);

  return { results, isLoading, error, query, setQuery, mode, setMode };
}
