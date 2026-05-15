"use client";

import { cn } from "@/lib/cn";

export interface BulkAction {
  label: string;
  onClick: () => void;
  variant?: "default" | "danger";
  loading?: boolean;
}

interface BulkActionBarProps {
  count: number;
  actions: BulkAction[];
  onClear: () => void;
  className?: string;
}

export function BulkActionBar({ count, actions, onClear, className }: BulkActionBarProps) {
  if (count === 0) return null;

  return (
    <div
      className={cn(
        "fixed bottom-6 left-1/2 z-40 flex -translate-x-1/2 items-center gap-3 rounded-xl border border-gray-600 bg-gray-900 px-4 py-2.5 shadow-xl",
        className
      )}
    >
      <span className="text-sm font-medium text-gray-200">
        {count} selected
      </span>
      <div className="h-4 w-px bg-gray-700" />
      {actions.map((action) => (
        <button
          key={action.label}
          type="button"
          onClick={action.onClick}
          disabled={action.loading}
          className={cn(
            "rounded-md px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-50",
            action.variant === "danger"
              ? "bg-danger/20 text-danger hover:bg-danger/30"
              : "bg-gray-700 text-gray-200 hover:bg-gray-600"
          )}
        >
          {action.loading ? "…" : action.label}
        </button>
      ))}
      <button
        type="button"
        onClick={onClear}
        className="ml-1 text-xs text-gray-500 hover:text-gray-300"
        aria-label="Clear selection"
      >
        ✕
      </button>
    </div>
  );
}
