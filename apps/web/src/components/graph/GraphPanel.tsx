"use client";

import { useState } from "react";
import { AiPanel } from "@/components/ai/AiPanel";
import { BacklinksPanel } from "./BacklinksPanel";
import { RelatedPanel } from "./RelatedPanel";

interface GraphPanelProps {
  objectId: string;
  refreshKey: number;
}

type GraphTab = "backlinks" | "related" | "ai";

export function GraphPanel({ objectId, refreshKey }: GraphPanelProps) {
  const [activeTab, setActiveTab] = useState<GraphTab>("backlinks");
  const [edgeRefreshKey, setEdgeRefreshKey] = useState(0);

  return (
    <div data-testid="graph-panel" className="flex h-full flex-col">
      <div className="border-b border-gray-800 p-3">
        <div className="text-xs font-medium uppercase text-gray-500">Graph</div>
        <div className="mt-3 grid grid-cols-3 rounded border border-gray-800 bg-gray-950 p-0.5">
          {(["backlinks", "related", "ai"] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              data-testid={`graph-tab-${tab}`}
              onClick={() => setActiveTab(tab)}
              className={
                activeTab === tab
                  ? "rounded bg-gray-800 px-2 py-1 text-xs text-gray-100"
                  : "rounded px-2 py-1 text-xs text-gray-500 hover:text-gray-100"
              }
            >
              {tab === "ai" ? "AI" : tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {activeTab === "backlinks" ? (
          <BacklinksPanel key={`backlinks-${refreshKey}`} objectId={objectId} />
        ) : activeTab === "related" ? (
          <RelatedPanel key={`related-${refreshKey}`} objectId={objectId} />
        ) : (
          <AiPanel
            key={`ai-${objectId}`}
            objectId={objectId}
            onEdgeCreated={() => setEdgeRefreshKey((k) => k + 1)}
          />
        )}
      </div>
    </div>
  );
}
