"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Sparkles } from "lucide-react";

import { deleteProject } from "@/lib/api";
import { BulkActionBar } from "@/components/lists/BulkActionBar";
import { ListPage } from "@/components/lists/ListPage";
import { ListToolbar, type SortKey } from "@/components/lists/ListToolbar";
import { ProjectForm } from "@/components/projects/ProjectForm";
import { ProjectCard } from "@/components/projects/ProjectCard";
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

export default function ProjectsPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<ProjectSort>("period-desc");
  const [statusFilter, setStatusFilter] = useState<ProjectStatus | "">("");
  const [skillFilter, setSkillFilter] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
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
          {filtered.map((project, i) => (
            <ProjectCard
              key={project.id}
              project={project}
              selected={selection.has(project.id)}
              highlighted={nav.highlightIdx === i}
              onSelect={() => selection.toggle(project.id)}
              onMouseEnter={() => nav.setHighlightIdx(i)}
            />
          ))}
        </div>
      </ListPage>

      {createOpen && (
        <ProjectForm
          mode="create"
          onClose={() => setCreateOpen(false)}
          onSuccess={(project) => {
            void mutate();
            router.push(`/app/projects/${project.id}`);
          }}
        />
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
