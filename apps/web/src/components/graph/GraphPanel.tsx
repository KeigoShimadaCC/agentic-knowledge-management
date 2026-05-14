"use client";

import { useState } from "react";
import { BacklinksPanel } from "./BacklinksPanel";
import { RelatedPanel } from "./RelatedPanel";

interface GraphPanelProps {
  objectId: string;
  refreshKey: number;
}

type GraphTab = "backlinks" | "related";

export function GraphPanel({ objectId, refreshKey }: GraphPanelProps) {
  const [activeTab, setActiveTab] = useState<GraphTab>("backlinks");

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-gray-800 p-3">
        <div className="text-xs font-medium uppercase text-gray-500">Graph</div>
        <div className="mt-3 grid grid-cols-2 rounded border border-gray-800 bg-gray-950 p-0.5">
          <button
            type="button"
            onClick={() => setActiveTab("backlinks")}
            className={
              activeTab === "backlinks"
                ? "rounded bg-gray-800 px-2 py-1 text-xs text-gray-100"
                : "rounded px-2 py-1 text-xs text-gray-500 hover:text-gray-100"
            }
          >
            Backlinks
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("related")}
            className={
              activeTab === "related"
                ? "rounded bg-gray-800 px-2 py-1 text-xs text-gray-100"
                : "rounded px-2 py-1 text-xs text-gray-500 hover:text-gray-100"
            }
          >
            Related
          </button>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {activeTab === "backlinks" ? (
          <BacklinksPanel key={`backlinks-${refreshKey}`} objectId={objectId} />
        ) : (
          <RelatedPanel key={`related-${refreshKey}`} objectId={objectId} />
        )}
      </div>
    </div>
  );
}
