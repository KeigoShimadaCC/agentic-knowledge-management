"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { formatDistanceToNow } from "date-fns";
import { Plus, Sparkles } from "lucide-react";

import { createProject, deleteProject } from "@/lib/api";
import { BulkActionBar } from "@/components/lists/BulkActionBar";
import { ListPage } from "@/components/lists/ListPage";
import { ListToolbar, type SortKey } from "@/components/lists/ListToolbar";
import { toast } from "@/components/ui/Toast";
import { useListKeyNav } from "@/lib/hooks/useListKeyNav";
import { useListSelection } from "@/lib/hooks/useListSelection";
import { useProjects } from "@/lib/hooks/useProjects";
import { cn } from "@/lib/cn";
import type { ProjectOut, ProjectStatus } from "@/types";

type ProjectSort = SortKey | "period-desc" | "period-asc";

const STATUS_FILTERS: Array<{ label: string; value: ProjectStatus | "" }> = [
  { label: "All", value: "" },
  { label: "Active", value: "active" },
  { label: "Completed", value: "completed" },
  { label: "Paused", value: "paused" },
  { label: "Archived", value: "archived" },
];

function sortProjects(projects: ProjectOut[], sort: ProjectSort): ProjectOut[] {
  const arr = [...projects];
  if (sort === "newest") {
    return arr.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
  }
  if (sort === "oldest") {
    return arr.sort((a, b) => new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime());
  }
  if (sort === "period-desc") {
    return arr.sort((a, b) => (b.period_start ?? "").localeCompare(a.period_start ?? ""));
  }
  if (sort === "period-asc") {
    return arr.sort((a, b) => (a.period_start ?? "").localeCompare(b.period_start ?? ""));
  }
  return arr.sort((a, b) => a.title.localeCompare(b.title));
}

function projectMatches(project: ProjectOut, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return [project.title, project.role, project.organization]
    .filter(Boolean)
    .some((value) => value!.toLowerCase().includes(q));
}

function projectMatchesSkills(project: ProjectOut, skillFilter: string): boolean {
  const needles = skillFilter
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
  if (needles.length === 0) return true;
  return needles.some((needle) => project.skills.some((skill) => skill.includes(needle)));
}

function completenessScore(project: ProjectOut): number {
  return [
    project.problem,
    project.actions,
    project.results,
    project.skills.length > 0,
    Object.keys(project.metrics ?? {}).length > 0,
  ].filter(Boolean).length;
}

function periodLabel(project: ProjectOut): string {
  if (!project.period_start && !project.period_end) return "No period";
  return `${project.period_start ?? "Unknown"} - ${project.period_end ?? "Ongoing"}`;
}

export default function ProjectsPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<ProjectSort>("period-desc");
  const [statusFilter, setStatusFilter] = useState<ProjectStatus | "">("");
  const [skillFilter, setSkillFilter] = useState("");
  const [creating, setCreating] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const selection = useListSelection();

  const { projects, isLoading, error, mutate } = useProjects({
    status: statusFilter || undefined,
    limit: 100,
  });

  const filtered = useMemo(() => {
    const matched = projects.filter(
      (project) => projectMatches(project, search) && projectMatchesSkills(project, skillFilter)
    );
    return sortProjects(matched, sort);
  }, [projects, search, skillFilter, sort]);

  async function handleCreate() {
    if (!title.trim()) {
      toast.error("Title is required");
      return;
    }
    setCreating(true);
    try {
      const project = await createProject({ title: title.trim() });
      await mutate();
      setCreateOpen(false);
      setTitle("");
      router.push(`/app/projects/${project.id}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not create project";
      toast.error("Could not create project", { description: message });
    } finally {
      setCreating(false);
    }
  }

  async function handleBulkDelete() {
    setBulkDeleting(true);
    const ids = Array.from(selection.selected);
    const chunks: string[][] = [];
    for (let i = 0; i < ids.length; i += 4) chunks.push(ids.slice(i, i + 4));
    for (const chunk of chunks) {
      await Promise.allSettled(chunk.map((id) => deleteProject(id)));
    }
    await mutate();
    selection.clear();
    setBulkDeleting(false);
    toast.success(`${ids.length} project${ids.length === 1 ? "" : "s"} moved to trash`);
  }

  const nav = useListKeyNav({
    count: filtered.length,
    onOpen: (i) => {
      const project = filtered[i];
      if (project) router.push(`/app/projects/${project.id}`);
    },
    onDelete: (i) => {
      const project = filtered[i];
      if (project) void deleteProject(project.id).then(() => mutate());
    },
  });

  return (
    <>
      <ListPage
        title="Projects"
        description="Career memory dashboard"
        loading={isLoading}
        error={error}
        onRetry={() => void mutate()}
        empty={!isLoading && filtered.length === 0}
        emptyTitle={search || skillFilter ? "No projects match" : "No projects yet"}
        emptyDescription={
          search || skillFilter
            ? "Try a different title, role, organization, or skill."
            : "Create a project record from your work history."
        }
        actions={
          <>
            <button
              type="button"
              onClick={() => toast.message("Project extraction will be available from this page.")}
              className="inline-flex h-9 items-center gap-2 rounded-md border border-gray-700 px-3 text-sm text-gray-200 transition-colors hover:bg-gray-800"
            >
              <Sparkles size={16} />
              Extract
            </button>
            <button
              type="button"
              onClick={() => setCreateOpen(true)}
              className="inline-flex h-9 items-center gap-2 rounded-md bg-white px-3 text-sm font-medium text-gray-950 transition-colors hover:bg-gray-200"
            >
              <Plus size={16} />
              New project
            </button>
          </>
        }
        toolbar={
          <div className="space-y-3">
            <ListToolbar
              search={search}
              onSearch={setSearch}
              sort={sort === "period-desc" || sort === "period-asc" ? "newest" : sort}
              onSort={(next) => setSort(next)}
              searchPlaceholder="Filter by title, role, or organization..."
            />
            <div className="flex flex-wrap items-center gap-2">
              {STATUS_FILTERS.map((filter) => (
                <button
                  key={filter.label}
                  type="button"
                  onClick={() => setStatusFilter(filter.value)}
                  className={cn(
                    "rounded-md border px-3 py-1.5 text-xs transition-colors",
                    statusFilter === filter.value
                      ? "border-gray-500 bg-gray-700 text-white"
                      : "border-gray-800 text-gray-400 hover:border-gray-700 hover:text-gray-200"
                  )}
                >
                  {filter.label}
                </button>
              ))}
              <input
                value={skillFilter}
                onChange={(e) => setSkillFilter(e.target.value)}
                placeholder="Skill filter"
                aria-label="Skill filter"
                className="h-8 min-w-48 rounded-md border border-gray-700 bg-gray-900 px-3 text-xs text-gray-200 placeholder:text-gray-600 focus:border-gray-500 focus:outline-none"
              />
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value as ProjectSort)}
                aria-label="Project sort order"
                className="h-8 rounded-md border border-gray-700 bg-gray-900 px-2 text-xs text-gray-400 focus:border-gray-500 focus:outline-none"
              >
                <option value="period-desc">Period newest</option>
                <option value="period-asc">Period oldest</option>
                <option value="newest">Updated newest</option>
                <option value="oldest">Updated oldest</option>
                <option value="title">Title</option>
              </select>
            </div>
          </div>
        }
      >
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((project, i) => {
            const score = completenessScore(project);
            return (
              <article
                key={project.id}
                onMouseEnter={() => nav.setHighlightIdx(i)}
                className={cn(
                  "rounded-lg border bg-gray-900 p-4 transition-colors",
                  nav.highlightIdx === i
                    ? "border-gray-600 bg-gray-800"
                    : "border-gray-800 hover:border-gray-700"
                )}
              >
                <div className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={selection.has(project.id)}
                    onChange={() => selection.toggle(project.id)}
                    className="mt-1 h-3.5 w-3.5 shrink-0 accent-indigo-500"
                    aria-label={`Select ${project.title}`}
                  />
                  <div className="min-w-0 flex-1">
                    <Link
                      href={`/app/projects/${project.id}`}
                      className="line-clamp-2 text-sm font-semibold text-white hover:underline"
                    >
                      {project.title}
                    </Link>
                    <p className="mt-1 truncate text-xs text-gray-500">
                      {[project.role, project.organization].filter(Boolean).join(" @ ") ||
                        "No role"}
                    </p>
                    <p className="mt-1 text-xs text-gray-600">{periodLabel(project)}</p>
                  </div>
                  <span className="rounded-md border border-gray-700 px-2 py-1 text-xs capitalize text-gray-300">
                    {project.status}
                  </span>
                </div>
                <div className="mt-4 flex flex-wrap gap-1.5">
                  {project.skills.slice(0, 5).map((skill) => (
                    <span
                      key={skill}
                      className="rounded border border-gray-800 px-2 py-0.5 text-xs text-gray-400"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
                <div className="mt-4 flex items-center justify-between text-xs text-gray-500">
                  <span
                    className={cn(
                      "rounded-md px-2 py-1",
                      score < 2 && "bg-red-500/15 text-red-300",
                      score >= 2 && score < 4 && "bg-amber-500/15 text-amber-300",
                      score >= 4 && "bg-emerald-500/15 text-emerald-300"
                    )}
                  >
                    {score}/5 complete
                  </span>
                  <span>{formatDistanceToNow(new Date(project.updated_at), { addSuffix: true })}</span>
                </div>
              </article>
            );
          })}
        </div>
      </ListPage>

      {createOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md rounded-lg border border-gray-800 bg-gray-950 p-5 shadow-xl">
            <h2 className="text-base font-semibold text-white">New project</h2>
            <label className="mt-4 block text-sm text-gray-300">
              Title
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="mt-1 h-9 w-full rounded-md border border-gray-700 bg-gray-900 px-3 text-sm text-white focus:border-gray-500 focus:outline-none"
                autoFocus
              />
            </label>
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setCreateOpen(false)}
                className="rounded-md border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => void handleCreate()}
                disabled={creating}
                className="rounded-md bg-white px-3 py-2 text-sm font-medium text-gray-950 disabled:opacity-60"
              >
                {creating ? "Saving..." : "Save"}
              </button>
            </div>
          </div>
        </div>
      )}

      <BulkActionBar
        count={selection.size}
        onClear={selection.clear}
        actions={[
          {
            label: "Delete",
            variant: "danger",
            loading: bulkDeleting,
            onClick: () => void handleBulkDelete(),
          },
        ]}
      />
    </>
  );
}
