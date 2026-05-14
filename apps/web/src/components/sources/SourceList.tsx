"use client";

import type { SourceOut } from "@/types";
import { SourceCard } from "./SourceCard";

interface SourceListProps {
  sources: SourceOut[];
}

export function SourceList({ sources }: SourceListProps) {
  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
      {sources.map((source) => (
        <SourceCard key={source.id} source={source} />
      ))}
    </div>
  );
}
