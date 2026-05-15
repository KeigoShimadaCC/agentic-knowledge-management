"use client";

import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { Pin } from "lucide-react";

import { CompletenessBadge } from "@/components/projects/CompletenessBadge";
import { cn } from "@/lib/cn";
import type { ProjectOut } from "@/types";

interface ProjectCardProps {
  project: ProjectOut;
  selected?: boolean;
  highlighted?: boolean;
  onSelect?: () => void;
  onMouseEnter?: () => void;
}

function periodLabel(project: ProjectOut): string {
  if (!project.period_start && !project.period_end) return "No period";
  return `${project.period_start ?? "Unknown"} - ${project.period_end ?? "Ongoing"}`;
}

export function ProjectCard({
  project,
  selected = false,
  highlighted = false,
  onSelect,
  onMouseEnter,
}: ProjectCardProps) {
  const roleLine =
    [project.role, project.organization].filter(Boolean).join(" @ ") || "No role";

  return (
    <article
      onMouseEnter={onMouseEnter}
      className={cn(
        "rounded-lg border bg-gray-900 p-4 transition-colors",
        highlighted ? "border-gray-600 bg-gray-800" : "border-gray-800 hover:border-gray-700"
      )}
    >
      <div className="flex items-start gap-3">
        {onSelect ? (
          <input
            type="checkbox"
            checked={selected}
            onChange={onSelect}
            className="mt-1 h-3.5 w-3.5 shrink-0 accent-indigo-500"
            aria-label={`Select ${project.title}`}
          />
        ) : null}
        <div className="min-w-0 flex-1">
          <Link
            href={`/app/projects/${project.id}`}
            className="line-clamp-2 text-sm font-semibold text-white hover:underline"
          >
            {project.is_pinned ? (
              <Pin size={13} className="mr-1 inline-block text-amber-400" aria-hidden />
            ) : null}
            {project.title}
          </Link>
          <p className="mt-1 truncate text-xs text-gray-500">{roleLine}</p>
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
        <CompletenessBadge project={project} />
        <span>{formatDistanceToNow(new Date(project.updated_at), { addSuffix: true })}</span>
      </div>
    </article>
  );
}
