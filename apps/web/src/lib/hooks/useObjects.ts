"use client";

import useSWR from "swr";
import { listObjects, type ListObjectsParams } from "@/lib/api";
import type { ObjectOut, PaginatedResponse } from "@/types";

export function useObjects(params: ListObjectsParams = {}) {
  const key = ["/api/v1/objects", params] as const;
  const { data, error, isLoading, mutate } = useSWR<PaginatedResponse<ObjectOut>>(
    key,
    () => listObjects(params),
    { revalidateOnFocus: false }
  );

  return {
    objects: data?.items ?? [],
    total: data?.total ?? 0,
    isLoading,
    error,
    mutate,
  };
}
