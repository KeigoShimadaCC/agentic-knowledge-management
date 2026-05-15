"use client";

import { cn } from "@/lib/cn";

const KINDS = [
  { value: "", label: "All" },
  { value: "page", label: "Pages" },
  { value: "asset", label: "Assets" },
  { value: "source", label: "Sources" },
  { value: "chat", label: "Chats" },
];

interface SearchFiltersProps {
  activeKind: string;
  onChange: (kind: string) => void;
  className?: string;
}

export function SearchFilters({ activeKind, onChange, className }: SearchFiltersProps) {
  return (
    <div className={cn("flex gap-1.5 px-3 py-2", className)}>
      {KINDS.map(({ value, label }) => (
        <button
          key={value}
          type="button"
          onClick={() => onChange(value)}
          className={cn(
            "rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors",
            activeKind === value
              ? "bg-brand text-brand-fg"
              : "bg-surface-2 text-fg-muted hover:bg-surface-3 hover:text-fg"
          )}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
