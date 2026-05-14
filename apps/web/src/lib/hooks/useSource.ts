"use client";

import useSWR from "swr";
import { getSource } from "@/lib/api";
import { useSourcePolling } from "./useSources";
import type { SourceOut } from "@/types";

export function useSource(id: string) {
  const { data, error, isLoading, mutate } = useSWR<SourceOut>(["source", id], () => getSource(id));
  const refreshInterval = useSourcePolling(data?.ingestion_status);
  return { source: data, error, isLoading, mutate, refreshInterval };
}
