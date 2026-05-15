"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ExternalLink, PanelRightOpen, Plus, Unlink } from "lucide-react";

import { deleteEdge, getObjectBacklinks } from "@/lib/api";
import { objectKindLabel, objectRoute } from "@/lib/objectRouting";
import { LinkToProjectModal } from "@/components/projects/LinkToProjectModal";
import { toast } from "@/components/ui/Toast";
import { useWorkspaceLite } from "@/components/workspace/WorkspaceLiteProvider";
import type { EdgeWithObjectsOut } from "@/types";

type EvidenceObject = { id: string; kind: string; title: string };

function evidenceFromEdge(edge: EdgeWithObjectsOut): EvidenceObject | null {
  return edge.source ?? edge.source_object ?? null;
}

function groupLabel(kind: string): string {
  if (kind === "page") return "Pages";
  if (kind === "source") return "Sources";
  if (kind === "chat") return "Chats";
  if (kind === "claim") return "Claims";
  return "Other";
}

export function EvidencePanel({ projectId }: { projectId: string }) {
  const [edges, setEdges] = useState<EdgeWithObjectsOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [linkOpen, setLinkOpen] = useState(false);
  const { openSidePane } = useWorkspaceLite();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const rows = await getObjectBacklinks(projectId);
      setEdges(rows.filter((edge) => edge.kind === "belongs_to_project"));
    } catch (err) {
      toast.error("Could not load evidence", {
        description: err instanceof Error ? err.message : undefined,
      });
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  const grouped = useMemo(() => {
    const groups = new Map<string, Array<{ edge: EdgeWithObjectsOut; object: EvidenceObject }>>();
    for (const edge of edges) {
      const object = evidenceFromEdge(edge);
      if (!object) continue;
      const label = groupLabel(object.kind);
      groups.set(label, [...(groups.get(label) ?? []), { edge, object }]);
    }
    return Array.from(groups.entries());
  }, [edges]);

  async function unlink(edgeId: string) {
    try {
      await deleteEdge(edgeId);
      await load();
      toast.success("Evidence unlinked");
    } catch (err) {
      toast.error("Could not unlink evidence", {
        description: err instanceof Error ? err.message : undefined,
      });
    }
  }

  if (loading) {
    return <div className="rounded-lg border border-gray-800 bg-gray-900 p-6 text-sm text-gray-400">Loading...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-white">Evidence</h2>
        <button
          type="button"
          onClick={() => setLinkOpen(true)}
          className="inline-flex items-center gap-2 rounded-md border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800"
        >
          <Plus size={15} />
          Link evidence
        </button>
      </div>

      {grouped.length === 0 ? (
        <div className="rounded-lg border border-gray-800 bg-gray-900 p-6 text-sm text-gray-500">
          No evidence linked yet. Link pages, sources, or chats to this project.
        </div>
      ) : (
        grouped.map(([label, items]) => (
          <section key={label}>
            <h3 className="mb-2 text-xs font-medium uppercase text-gray-500">{label}</h3>
            <div className="grid gap-2 md:grid-cols-2">
              {items.map(({ edge, object }) => (
                <article key={edge.id} className="rounded-lg border border-gray-800 bg-gray-900 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <Link
                        href={objectRoute(object.kind, object.id)}
                        className="line-clamp-2 text-sm font-medium text-white hover:underline"
                      >
                        {object.title || "Untitled object"}
                      </Link>
                      <span className="mt-2 inline-flex rounded border border-gray-700 px-2 py-0.5 text-xs text-gray-400">
                        {objectKindLabel(object.kind)}
                      </span>
                    </div>
                    <div className="flex shrink-0 gap-1">
                      <button
                        type="button"
                        onClick={() => openSidePane(object)}
                        className="rounded p-1.5 text-gray-400 hover:bg-gray-800 hover:text-white"
                        aria-label="Open in pane"
                      >
                        <PanelRightOpen size={15} />
                      </button>
                      <Link
                        href={objectRoute(object.kind, object.id)}
                        className="rounded p-1.5 text-gray-400 hover:bg-gray-800 hover:text-white"
                        aria-label="Open"
                      >
                        <ExternalLink size={15} />
                      </Link>
                      <button
                        type="button"
                        onClick={() => void unlink(edge.id)}
                        className="rounded p-1.5 text-gray-400 hover:bg-gray-800 hover:text-red-300"
                        aria-label="Unlink"
                      >
                        <Unlink size={15} />
                      </button>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </section>
        ))
      )}

      <LinkToProjectModal
        projectId={projectId}
        isOpen={linkOpen}
        onClose={() => setLinkOpen(false)}
        onLinked={() => void load()}
      />
    </div>
  );
}
