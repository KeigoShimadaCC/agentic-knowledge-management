"use client";
import { useEffect, useState } from "react";

const STORAGE_KEY = "kos:sidebar:collapsed";

/** localStorage-backed sidebar collapse state. Defaults to expanded (false). */
export function useSidebarState() {
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === "1") setCollapsed(true);
    } catch {
      // localStorage unavailable (SSR or private browsing)
    }
  }, []);

  function toggle() {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        if (next) localStorage.setItem(STORAGE_KEY, "1");
        else localStorage.removeItem(STORAGE_KEY);
      } catch {
        // ignore
      }
      return next;
    });
  }

  return { collapsed, toggle };
}
