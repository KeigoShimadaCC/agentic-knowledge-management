"use client";

import Link from "next/link";

import { useProject } from "@/lib/hooks/useProjects";

function periodLabel(start?: string | null, end?: string | null): string {
  if (!start && !end) return "No period";
  return `${start ?? "Unknown"} - ${end ?? "Ongoing"}`;
}

export function ProjectPaneView({ id }: { id: string }) {
  const { project, isLoading, error } = useProject(id);

  if (isLoading) {
    return <div className="p-4 text-sm text-gray-400">Loading...</div>;
  }

  if (error || !project) {
    return <div className="p-4 text-sm text-red-300">Could not load project.</div>;
  }

  return (
    <div className="space-y-4 p-4">
      <div>
        <p className="text-xs uppercase text-gray-500">Project</p>
        <h2 className="mt-1 text-base font-semibold text-white">{project.title}</h2>
        <p className="mt-1 text-xs text-gray-500">
          {[project.role, project.organization].filter(Boolean).join(" @ ") || "No role"} ·{" "}
          {periodLabel(project.period_start, project.period_end)}
        </p>
      </div>
      <span className="inline-flex rounded-md border border-gray-700 px-2 py-1 text-xs capitalize text-gray-300">
        {project.status}
      </span>
      <div className="space-y-3 text-sm text-gray-300">
        {project.problem && (
          <section>
            <h3 className="text-xs font-medium uppercase text-gray-500">Problem</h3>
            <p className="mt-1 line-clamp-4 whitespace-pre-wrap">{project.problem}</p>
          </section>
        )}
        {project.actions && (
          <section>
            <h3 className="text-xs font-medium uppercase text-gray-500">Actions</h3>
            <p className="mt-1 line-clamp-4 whitespace-pre-wrap">{project.actions}</p>
          </section>
        )}
        {project.results && (
          <section>
            <h3 className="text-xs font-medium uppercase text-gray-500">Results</h3>
            <p className="mt-1 line-clamp-4 whitespace-pre-wrap">{project.results}</p>
          </section>
        )}
      </div>
      <Link
        href={`/app/projects/${project.id}`}
        className="inline-block text-xs text-blue-400 hover:text-blue-300"
      >
        Open full ↗
      </Link>
    </div>
  );
}
