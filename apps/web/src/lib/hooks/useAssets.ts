"use client";

import { useObjects } from "./useObjects";

export function useAssets() {
  return useObjects({ kind: "asset", limit: 100 });
}
