"use client";
import * as React from "react";
import { cn } from "@/lib/cn";

export type SaveStatus = "idle" | "saved" | "saving" | "unsaved" | "error";

interface SaveStatusChipProps {
  status: SaveStatus;
  className?: string;
}

export function SaveStatusChip({ status, className }: SaveStatusChipProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-xs",
        status === "saved" && "text-fg-subtle",
        status === "saving" && "text-fg-muted",
        status === "unsaved" && "text-warning",
        status === "error" && "text-danger",
        className
      )}
    >
      {status === "saving" && (
        <span className="h-3 w-3 animate-spin rounded-full border border-current border-t-transparent" />
      )}
      {status === "idle" && null}
      {status === "saved" && "Saved"}
      {status === "saving" && "Saving…"}
      {status === "unsaved" && "Unsaved changes"}
      {status === "error" && "Save failed"}
    </span>
  );
}
