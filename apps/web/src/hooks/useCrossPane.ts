"use client";

import { useCallback } from "react";

export interface DragPayload {
  text: string;
  sourceObjectId: string;
  sourceKind: string;
  sourceTitle: string;
}

const MIME = "application/kos-text";

export function useCrossPaneDragSource() {
  const onDragStart = useCallback(
    (e: React.DragEvent, payload: DragPayload) => {
      e.dataTransfer.setData(MIME, JSON.stringify(payload));
      e.dataTransfer.effectAllowed = "copy";
    },
    []
  );
  return { onDragStart };
}

export function useCrossPaneDragTarget(
  onDrop: (payload: DragPayload) => void
) {
  const handleDragOver = useCallback((e: React.DragEvent) => {
    if (e.dataTransfer.types.includes(MIME)) {
      e.preventDefault();
      e.dataTransfer.dropEffect = "copy";
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      const raw = e.dataTransfer.getData(MIME);
      if (!raw) return;
      e.preventDefault();
      try {
        const payload = JSON.parse(raw) as DragPayload;
        onDrop(payload);
      } catch {
        // malformed payload — ignore
      }
    },
    [onDrop]
  );

  return { onDragOver: handleDragOver, onDrop: handleDrop };
}
