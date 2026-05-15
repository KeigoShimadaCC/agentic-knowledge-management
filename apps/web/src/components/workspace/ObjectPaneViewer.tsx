"use client";

import { objectKindLabel, objectRoute } from "@/lib/objectRouting";
import { PagePaneView } from "./PagePaneView";
import { SourcePaneView } from "./SourcePaneView";
import { ProjectPaneView } from "@/components/projects/ProjectPaneView";

interface ObjectPaneViewerProps {
  id: string;
  kind: string;
  title: string;
}

export function ObjectPaneViewer({ id, kind, title }: ObjectPaneViewerProps) {
  if (kind === "page") return <PagePaneView id={id} objectTitle={title} />;
  if (kind === "source") return <SourcePaneView id={id} title={title} />;
  if (kind === "project") return <ProjectPaneView id={id} />;

  return (
    <div className="p-4">
      <p className="mb-2 text-xs text-gray-500">{objectKindLabel(kind)}</p>
      <p className="text-sm text-gray-300">{title}</p>
      <a
        href={objectRoute(kind, id)}
        className="mt-3 inline-block text-xs text-blue-400 hover:text-blue-300"
      >
        Open full page →
      </a>
    </div>
  );
}
