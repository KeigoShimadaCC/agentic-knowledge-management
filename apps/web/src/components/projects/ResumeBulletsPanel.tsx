"use client";

import { useState } from "react";
import { Copy, Sparkles, Trash2 } from "lucide-react";

import {
  deleteResumeBulletSet,
  generateResumeBullets,
  saveResumeBulletSet,
} from "@/lib/api";
import { toast } from "@/components/ui/Toast";
import { useResumeBulletSets } from "@/lib/hooks/useProjects";
import { useWorkspaceLite } from "@/components/workspace/WorkspaceLiteProvider";
import { ApiError, type GenerateResumeBulletsResponse, type ProjectOut } from "@/types";

interface ResumeBulletsPanelProps {
  projectId: string;
  project: ProjectOut;
}

function bulletSetToMarkdown(bullets: Array<{ text: string; confidence: string }>): string {
  return bullets.map((bullet) => `- ${bullet.text} [${bullet.confidence}]`).join("\n");
}

export function ResumeBulletsPanel({ projectId, project }: ResumeBulletsPanelProps) {
  const { bulletSets, mutate } = useResumeBulletSets(projectId);
  const { openSidePane } = useWorkspaceLite();
  const [targetRole, setTargetRole] = useState(project.role ?? "");
  const [emphasis, setEmphasis] = useState("");
  const [count, setCount] = useState(3);
  const [preview, setPreview] = useState<GenerateResumeBulletsResponse | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [aiDisabled, setAiDisabled] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  async function handleGenerate() {
    setIsGenerating(true);
    setAiDisabled(false);
    try {
      const result = await generateResumeBullets({
        project_id: projectId,
        target_role: targetRole || undefined,
        emphasis: emphasis || undefined,
        count,
      });
      setPreview(result);
    } catch (err) {
      if (err instanceof ApiError && err.status === 503) {
        setAiDisabled(true);
      } else {
        toast.error("Could not generate bullets", {
          description: err instanceof Error ? err.message : undefined,
        });
      }
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleSave() {
    if (!preview) return;
    try {
      await saveResumeBulletSet(projectId, {
        target_role: targetRole || undefined,
        emphasis: emphasis || undefined,
        count: preview.bullets.length,
        bullets: preview.bullets,
        agent_run_id: preview.agent_run_id,
      });
      await mutate();
      setPreview(null);
      toast.success("Bullet set saved");
    } catch (err) {
      toast.error("Could not save bullets", {
        description: err instanceof Error ? err.message : undefined,
      });
    }
  }

  async function handleDelete(id: string) {
    await deleteResumeBulletSet(id);
    await mutate();
    toast.success("Bullet set deleted");
  }

  return (
    <div className="space-y-5">
      {aiDisabled && (
        <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
          AI disabled. Set OPENAI_API_KEY or ANTHROPIC_API_KEY to use this feature.
        </div>
      )}

      <section className="rounded-lg border border-gray-800 bg-gray-900 p-4">
        <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto_auto]">
          <input
            value={targetRole}
            onChange={(e) => setTargetRole(e.target.value)}
            placeholder="Target role"
            className="h-9 rounded-md border border-gray-700 bg-gray-950 px-3 text-sm text-white placeholder:text-gray-600 focus:border-gray-500 focus:outline-none"
          />
          <input
            value={emphasis}
            onChange={(e) => setEmphasis(e.target.value)}
            placeholder="Emphasis"
            className="h-9 rounded-md border border-gray-700 bg-gray-950 px-3 text-sm text-white placeholder:text-gray-600 focus:border-gray-500 focus:outline-none"
          />
          <select
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
            className="h-9 rounded-md border border-gray-700 bg-gray-950 px-3 text-sm text-white focus:border-gray-500 focus:outline-none"
            aria-label="Bullet count"
          >
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => void handleGenerate()}
            disabled={isGenerating}
            className="inline-flex h-9 items-center justify-center gap-2 rounded-md bg-white px-3 text-sm font-medium text-gray-950 disabled:opacity-60"
          >
            <Sparkles size={15} />
            {isGenerating ? "Generating..." : "Generate"}
          </button>
        </div>
      </section>

      {preview && (
        <section className="rounded-lg border border-gray-700 bg-gray-900 p-4">
          <h2 className="text-sm font-semibold text-white">Preview</h2>
          <div className="mt-3 space-y-3">
            {preview.bullets.map((bullet, index) => (
              <article key={`${bullet.text}-${index}`} className="rounded-md border border-gray-800 p-3">
                <p className="text-sm text-gray-200">{bullet.text}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <span className="rounded border border-gray-700 px-2 py-0.5 text-xs text-gray-400">
                    {bullet.confidence}
                  </span>
                  {bullet.metrics_cited.map((metric) => (
                    <span key={metric} className="rounded border border-gray-700 px-2 py-0.5 text-xs text-gray-400">
                      {metric}
                    </span>
                  ))}
                  {bullet.evidence_object_ids.map((id) => (
                    <button
                      key={id}
                      type="button"
                      onClick={() => openSidePane({ id, kind: "page", title: id })}
                      className="rounded border border-gray-700 px-2 py-0.5 text-xs text-gray-400 hover:text-white"
                    >
                      evidence
                    </button>
                  ))}
                </div>
              </article>
            ))}
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setPreview(null)}
              className="rounded-md border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800"
            >
              Discard
            </button>
            <button
              type="button"
              onClick={() => void handleSave()}
              className="rounded-md bg-white px-3 py-2 text-sm font-medium text-gray-950"
            >
              Save
            </button>
          </div>
        </section>
      )}

      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-white">Saved sets</h2>
        {bulletSets.length === 0 ? (
          <div className="rounded-lg border border-gray-800 bg-gray-900 p-6 text-sm text-gray-500">
            No saved bullet sets.
          </div>
        ) : (
          bulletSets.map((set) => (
            <article key={set.id} className="rounded-lg border border-gray-800 bg-gray-900">
              <button
                type="button"
                onClick={() => setExpanded((current) => (current === set.id ? null : set.id))}
                className="flex w-full items-center justify-between gap-3 p-4 text-left"
              >
                <span className="min-w-0">
                  <span className="block text-sm font-medium text-white">
                    {set.target_role || "Untargeted"} · {set.count} bullets
                  </span>
                  <span className="block truncate text-xs text-gray-500">
                    {set.emphasis || "No emphasis"} · {new Date(set.created_at).toLocaleDateString()}
                  </span>
                </span>
              </button>
              {expanded === set.id && (
                <div className="space-y-3 border-t border-gray-800 p-4">
                  {set.bullets.map((bullet, index) => (
                    <p key={`${set.id}-${index}`} className="text-sm text-gray-300">
                      {bullet.text}
                    </p>
                  ))}
                  <div className="flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        void navigator.clipboard.writeText(bulletSetToMarkdown(set.bullets));
                        toast.success("Copied");
                      }}
                      className="inline-flex items-center gap-2 rounded-md border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800"
                    >
                      <Copy size={15} />
                      Copy Markdown
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleDelete(set.id)}
                      className="inline-flex items-center gap-2 rounded-md border border-red-500/40 px-3 py-2 text-sm text-red-300 hover:bg-red-500/10"
                    >
                      <Trash2 size={15} />
                      Delete
                    </button>
                  </div>
                </div>
              )}
            </article>
          ))
        )}
      </section>
    </div>
  );
}
