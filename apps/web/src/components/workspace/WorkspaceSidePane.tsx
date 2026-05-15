"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { X } from "lucide-react";
import { useWorkspaceLite } from "./WorkspaceLiteProvider";
import { ObjectPaneViewer } from "./ObjectPaneViewer";
import { objectRoute, objectKindLabel } from "@/lib/objectRouting";

function KindBadge({ kind }: { kind: string }) {
  const className =
    kind === "page"
      ? "bg-blue-950 text-blue-300 border-blue-800"
      : kind === "source"
        ? "bg-green-950 text-green-300 border-green-800"
        : "bg-gray-900 text-gray-300 border-gray-700";
  return (
    <span className={`rounded border px-1.5 py-0.5 text-[10px] uppercase ${className}`}>
      {objectKindLabel(kind)}
    </span>
  );
}

export function WorkspaceSidePane() {
  const { sidePaneObject, closeSidePane } = useWorkspaceLite();
  const router = useRouter();

  useEffect(() => {
    if (!sidePaneObject) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") closeSidePane();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [sidePaneObject, closeSidePane]);

  if (!sidePaneObject) return null;

  const { id, kind, title } = sidePaneObject;

  return (
    <aside data-testid="side-pane" className="hidden md:flex w-96 shrink-0 flex-col border-l border-gray-800 bg-gray-950 transition-all duration-200">
      <div className="flex items-center gap-2 border-b border-gray-800 px-3 py-2">
        <KindBadge kind={kind} />
        <span className="min-w-0 flex-1 truncate text-sm font-medium text-gray-100">{title}</span>
        <button
          type="button"
          onClick={() => {
            closeSidePane();
            router.push(objectRoute(kind, id));
          }}
          title="Open full page"
          className="shrink-0 rounded px-1.5 py-0.5 text-xs text-blue-400 hover:bg-gray-800 hover:text-blue-300"
        >
          Open
        </button>
        <button
          type="button"
          onClick={closeSidePane}
          title="Close side pane (Esc)"
          className="shrink-0 rounded p-1 text-gray-500 hover:bg-gray-800 hover:text-gray-200"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">
        <ObjectPaneViewer id={id} kind={kind} title={title} />
      </div>
    </aside>
  );
}
