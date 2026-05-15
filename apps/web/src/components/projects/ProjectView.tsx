"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Archive, Copy, Download, Edit, FileDown, Trash2 } from "lucide-react";

import { archiveObject, deleteProject, updateObject } from "@/lib/api";
import { EvidencePanel } from "@/components/projects/EvidencePanel";
import { ProjectForm } from "@/components/projects/ProjectForm";
import { ResumeBulletsPanel } from "@/components/projects/ResumeBulletsPanel";
import { toast } from "@/components/ui/Toast";
import { cn } from "@/lib/cn";
import type { ProjectOut } from "@/types";

type Tab = "overview" | "evidence" | "bullets" | "stories";

const TABS: Array<{ id: Tab; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "evidence", label: "Evidence" },
  { id: "bullets", label: "Resume Bullets" },
  { id: "stories", label: "Interview Stories" },
];

function periodLabel(project: ProjectOut): string {
  if (!project.period_start && !project.period_end) return "No period";
  return `${project.period_start ?? "Unknown"} - ${project.period_end ?? "Ongoing"}`;
}

function simpleProjectText(project: ProjectOut): string {
  return [
    `# ${project.title}`,
    project.role || project.organization
      ? `Role: ${[project.role, project.organization].filter(Boolean).join(" @ ")}`
      : "",
    `Period: ${periodLabel(project)}`,
    project.description ?? "",
    project.problem ? `Problem: ${project.problem}` : "",
    project.actions ? `Actions: ${project.actions}` : "",
    project.results ? `Results: ${project.results}` : "",
  ]
    .filter(Boolean)
    .join("\n\n");
}

export function ProjectView({ project: initialProject }: { project: ProjectOut }) {
  const router = useRouter();
  const [project, setProject] = useState(initialProject);
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);

  async function handlePin() {
    setBusy(true);
    try {
      const obj = await updateObject(project.id, { is_pinned: !project.is_pinned });
      setProject((current) => ({ ...current, is_pinned: obj.is_pinned }));
    } catch (err) {
      toast.error("Could not update project", {
        description: err instanceof Error ? err.message : undefined,
      });
    } finally {
      setBusy(false);
    }
  }

  async function handleArchive() {
    setBusy(true);
    try {
      const obj = await archiveObject(project.id);
      setProject((current) => ({ ...current, is_archived: obj.is_archived }));
      toast.success("Project archived");
    } catch (err) {
      toast.error("Could not archive project", {
        description: err instanceof Error ? err.message : undefined,
      });
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    setBusy(true);
    try {
      await deleteProject(project.id);
      toast.success("Project moved to trash");
      router.push("/app/projects");
      router.refresh();
    } catch (err) {
      toast.error("Could not delete project", {
        description: err instanceof Error ? err.message : undefined,
      });
      setBusy(false);
    }
  }

  async function copyText() {
    await navigator.clipboard.writeText(simpleProjectText(project));
    toast.success("Copied");
  }

  return (
    <div className="min-h-full pb-20">
      <header className="border-b border-gray-800 px-8 py-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-bold text-white">{project.title}</h1>
              <span className="rounded-md border border-gray-700 px-2 py-1 text-xs capitalize text-gray-300">
                {project.status}
              </span>
              <span className="rounded-md border border-gray-700 px-2 py-1 text-xs text-gray-400">
                {project.confidence}
              </span>
            </div>
            <p className="mt-2 text-sm text-gray-500">
              {[project.role, project.organization].filter(Boolean).join(" @ ") || "No role"} ·{" "}
              {periodLabel(project)}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setEditing(true)}
              className="inline-flex items-center gap-2 rounded-md border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800"
            >
              <Edit size={15} />
              Edit
            </button>
            <button
              type="button"
              onClick={() => void handlePin()}
              disabled={busy}
              className="rounded-md border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 disabled:opacity-60"
            >
              {project.is_pinned ? "Unpin" : "Pin"}
            </button>
            <button
              type="button"
              onClick={() => void handleArchive()}
              disabled={busy || project.is_archived}
              className="inline-flex items-center gap-2 rounded-md border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 disabled:opacity-60"
            >
              <Archive size={15} />
              Archive
            </button>
            <button
              type="button"
              onClick={() => void handleDelete()}
              disabled={busy}
              className="inline-flex items-center gap-2 rounded-md border border-red-500/40 px-3 py-2 text-sm text-red-300 hover:bg-red-500/10 disabled:opacity-60"
            >
              <Trash2 size={15} />
              Delete
            </button>
          </div>
        </div>
        <nav className="mt-6 flex flex-wrap gap-2">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "rounded-md border px-3 py-1.5 text-sm transition-colors",
                activeTab === tab.id
                  ? "border-gray-500 bg-gray-700 text-white"
                  : "border-gray-800 text-gray-400 hover:border-gray-700 hover:text-gray-200"
              )}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="px-8 py-6">
        {activeTab === "overview" && <Overview project={project} />}
        {activeTab === "evidence" && <EvidencePanel projectId={project.id} />}
        {activeTab === "bullets" && <ResumeBulletsPanel projectId={project.id} project={project} />}
        {activeTab === "stories" && <PanelPlaceholder title="Interview Stories" />}
      </main>

      <div className="fixed bottom-0 left-60 right-0 z-30 border-t border-gray-800 bg-gray-950/95 px-8 py-3 backdrop-blur">
        <div className="flex flex-wrap justify-end gap-2">
          <button
            type="button"
            onClick={() => toast.message("Markdown export is not ready yet.")}
            className="inline-flex items-center gap-2 rounded-md border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800"
          >
            <Download size={15} />
            Download Markdown
          </button>
          <button
            type="button"
            onClick={() => toast.message("PDF export is not ready yet.")}
            className="inline-flex items-center gap-2 rounded-md border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800"
          >
            <FileDown size={15} />
            Download PDF
          </button>
          <button
            type="button"
            onClick={() => void copyText()}
            className="inline-flex items-center gap-2 rounded-md border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800"
          >
            <Copy size={15} />
            Copy text
          </button>
        </div>
      </div>

      {editing && (
        <ProjectForm
          mode="edit"
          initialData={project}
          onClose={() => setEditing(false)}
          onSuccess={(saved) => setProject(saved)}
        />
      )}
    </div>
  );
}

function Overview({ project }: { project: ProjectOut }) {
  return (
    <div className="space-y-6">
      {project.description && <p className="max-w-3xl text-sm text-gray-300">{project.description}</p>}
      <section className="grid gap-4 lg:grid-cols-3">
        {[
          ["Problem", project.problem],
          ["Actions", project.actions],
          ["Results", project.results],
        ].map(([label, value]) => (
          <div key={label} className="rounded-lg border border-gray-800 bg-gray-900 p-4">
            <h2 className="text-sm font-semibold text-white">{label}</h2>
            <p className="mt-2 whitespace-pre-wrap text-sm text-gray-400">{value || "Not recorded"}</p>
          </div>
        ))}
      </section>
      <section className="grid gap-4 lg:grid-cols-2">
        <div>
          <h2 className="text-sm font-semibold text-white">Metrics</h2>
          <div className="mt-2 overflow-hidden rounded-lg border border-gray-800">
            {Object.entries(project.metrics ?? {}).length === 0 ? (
              <p className="bg-gray-900 p-3 text-sm text-gray-500">No metrics</p>
            ) : (
              <table className="w-full text-left text-sm">
                <tbody>
                  {Object.entries(project.metrics).map(([key, value]) => (
                    <tr key={key} className="border-t border-gray-800 first:border-t-0">
                      <th className="bg-gray-900 px-3 py-2 font-medium text-gray-300">{key}</th>
                      <td className="px-3 py-2 text-gray-400">{String(value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
        <div>
          <h2 className="text-sm font-semibold text-white">Skills</h2>
          <div className="mt-2 flex flex-wrap gap-2">
            {project.skills.length === 0 ? (
              <span className="text-sm text-gray-500">No skills</span>
            ) : (
              project.skills.map((skill) => (
                <span
                  key={skill}
                  className="rounded border border-gray-800 px-2 py-1 text-xs text-gray-300"
                >
                  {skill}
                </span>
              ))
            )}
          </div>
          <h2 className="mt-5 text-sm font-semibold text-white">Tags</h2>
          <div className="mt-2 flex flex-wrap gap-2">
            {project.tags.length === 0 ? (
              <span className="text-sm text-gray-500">No tags</span>
            ) : (
              project.tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded border border-gray-800 px-2 py-1 text-xs text-gray-300"
                >
                  {tag}
                </span>
              ))
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

function PanelPlaceholder({ title }: { title: string }) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 p-6">
      <h2 className="text-sm font-semibold text-white">{title}</h2>
    </div>
  );
}
