"use client";

import useSWR from "swr";
import { getMe } from "@/lib/api";
import type { AuthResponse } from "@/types";
import { ApiError } from "@/types";

export function useAuth() {
  const { data, error, isLoading, mutate } = useSWR<AuthResponse, ApiError>(
    "/api/v1/auth/me",
    getMe,
    { revalidateOnFocus: false }
  );

  return {
    user: data?.user,
    isLoading,
    isAuthenticated: !!data?.user,
    error,
    mutate,
  };
}
