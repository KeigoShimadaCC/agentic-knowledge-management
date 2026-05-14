"use client";

import useSWR from "swr";
import { getPage } from "@/lib/api";
import type { PageOut } from "@/types";

export function usePage(id: string) {
  const { data, error, isLoading, mutate } = useSWR<PageOut>(
    `/api/v1/pages/${id}`,
    () => getPage(id),
    { revalidateOnFocus: false }
  );

  return { page: data, isLoading, error, mutate };
}
