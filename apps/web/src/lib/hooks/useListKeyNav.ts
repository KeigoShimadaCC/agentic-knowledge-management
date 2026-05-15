"use client";

import { useCallback, useEffect, useState } from "react";

interface UseListKeyNavOptions {
  count: number;
  onOpen?: (idx: number) => void;
  onOpenInPane?: (idx: number) => void;
  onDelete?: (idx: number) => void;
  enabled?: boolean;
}

export function useListKeyNav({
  count,
  onOpen,
  onOpenInPane,
  onDelete,
  enabled = true,
}: UseListKeyNavOptions) {
  const [highlightIdx, setHighlightIdx] = useState(-1);

  const reset = useCallback(() => setHighlightIdx(-1), []);

  useEffect(() => {
    if (!enabled || count === 0) return;

    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement;
      const inInput =
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable;
      if (inInput) return;

      switch (e.key) {
        case "j":
        case "ArrowDown":
          e.preventDefault();
          setHighlightIdx((i) => Math.min(i + 1, count - 1));
          break;
        case "k":
        case "ArrowUp":
          e.preventDefault();
          setHighlightIdx((i) => Math.max(i - 1, 0));
          break;
        case "Enter":
          if (highlightIdx >= 0) {
            e.preventDefault();
            onOpen?.(highlightIdx);
          }
          break;
        case "o":
          if (highlightIdx >= 0) {
            e.preventDefault();
            onOpenInPane?.(highlightIdx);
          }
          break;
        case "Backspace":
        case "Delete":
          if (highlightIdx >= 0) {
            e.preventDefault();
            onDelete?.(highlightIdx);
          }
          break;
        case "Escape":
          setHighlightIdx(-1);
          break;
      }
    }

    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [enabled, count, highlightIdx, onOpen, onOpenInPane, onDelete]);

  return { highlightIdx, setHighlightIdx, reset };
}
