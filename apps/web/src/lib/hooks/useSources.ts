"use client";

import useSWR from "swr";
import { listSources } from "@/lib/api";
import type { IngestionStatus } from "@/types";

export function useSources(params?: { source_type?: string; ingestion_status?: string; q?: string }) {
  const { data, error, isLoading, mutate } = useSWR(
    ["sources", params],
    () => listSources(params),
    { refreshInterval: 0 }
  );
  return { sources: data ?? [], error, isLoading, mutate };
}

export function useSourcePolling(status: IngestionStatus | undefined) {
  return ["pending", "running"].includes(status ?? "") ? 3000 : 0;
}
