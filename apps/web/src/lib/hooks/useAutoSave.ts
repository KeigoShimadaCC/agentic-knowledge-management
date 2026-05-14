"use client";

import { useEffect, useRef, useState } from "react";
import { updatePage } from "@/lib/api";

type SaveStatus = "idle" | "saving" | "saved" | "error";

export function useAutoSave(
  id: string,
  data: { title?: string; content_json?: Record<string, unknown>; content_text?: string },
  delayMs = 800
) {
  const [status, setStatus] = useState<SaveStatus>("idle");
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dataRef = useRef(data);
  dataRef.current = data;

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);

    timerRef.current = setTimeout(async () => {
      setStatus("saving");
      try {
        await updatePage(id, dataRef.current);
        setStatus("saved");
      } catch {
        setStatus("error");
      }
    }, delayMs);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, delayMs, JSON.stringify(data)]);

  return { status };
}
