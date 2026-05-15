"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Link2, Plus, X } from "lucide-react";
import { objectRoute, objectKindLabel } from "@/lib/objectRouting";
import { ObjectPaneViewer } from "./ObjectPaneViewer";
import { LinkPaneModal } from "./LinkPaneModal";
import { useWorkspaceLite, type PaneState } from "./WorkspaceLiteProvider";

function KindBadge({ kind }: { kind: string }) {
  const cls =
    kind === "page"
      ? "bg-blue-950 text-blue-300 border-blue-800"
      : kind === "source"
        ? "bg-green-950 text-green-300 border-green-800"
        : "bg-gray-900 text-gray-300 border-gray-700";
  return (
    <span className={`rounded border px-1.5 py-0.5 text-[10px] uppercase ${cls}`}>
      {objectKindLabel(kind)}
    </span>
  );
}

interface PaneContainerProps {
  pane: PaneState;
  isLast: boolean;
}

export function PaneContainer({ pane, isLast }: PaneContainerProps) {
  const router = useRouter();
  const { removePane, addPane, panes, setActivePaneId } = useWorkspaceLite();
  const canAddPane = panes.length < 4;
  const [linkModalOpen, setLinkModalOpen] = useState(false);

  const otherPanesWithObjects = panes.filter(
    (p) => p.id !== pane.id && p.objectId !== null
  );
  const canLink = pane.objectId !== null && otherPanesWithObjects.length > 0;

  return (
    <>
    <div
      className="flex h-full flex-col border-l border-gray-800 bg-gray-950"
      onClick={() => setActivePaneId(pane.id)}
    >
      <div className="flex shrink-0 items-center gap-2 border-b border-gray-800 px-3 py-2">
        {pane.objectKind && <KindBadge kind={pane.objectKind} />}
        <span className="min-w-0 flex-1 truncate text-sm font-medium text-gray-100">
          {pane.title || "New pane"}
        </span>
        {isLast && canAddPane && (
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); addPane(); }}
            title="Add pane"
            aria-label="Add pane"
            className="shrink-0 rounded p-1 text-gray-500 hover:bg-gray-800 hover:text-gray-200"
          >
            <Plus className="h-3.5 w-3.5" />
          </button>
        )}
        {canLink && (
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); setLinkModalOpen(true); }}
            title="Link to another pane"
            aria-label="Link to another pane"
            className="shrink-0 rounded p-1 text-gray-500 hover:bg-gray-800 hover:text-gray-200"
          >
            <Link2 className="h-3.5 w-3.5" />
          </button>
        )}
        {pane.objectId && pane.objectKind && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              router.push(objectRoute(pane.objectKind!, pane.objectId!));
            }}
            title="Open full page"
            className="shrink-0 rounded px-1.5 py-0.5 text-xs text-blue-400 hover:bg-gray-800 hover:text-blue-300"
          >
            Open
          </button>
        )}
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); removePane(pane.id); }}
          aria-label="Close pane"
          title="Close pane"
          className="shrink-0 rounded p-1 text-gray-500 hover:bg-gray-800 hover:text-gray-200"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {pane.objectId && pane.objectKind ? (
          <ObjectPaneViewer id={pane.objectId} kind={pane.objectKind} title={pane.title} />
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-2 p-8 text-center">
            <p className="text-sm text-gray-500">Empty pane</p>
            <p className="text-xs text-gray-600">
              Open an object to view it here.
            </p>
          </div>
        )}
      </div>
    </div>
    <LinkPaneModal
      sourcePaneId={pane.id}
      open={linkModalOpen}
      onClose={() => setLinkModalOpen(false)}
    />
    </>
  );
}
