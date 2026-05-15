import { cn } from "@/lib/cn";
import type { ProjectOut } from "@/types";

export function projectCompletenessScore(project: ProjectOut): number {
  return [
    project.problem,
    project.actions,
    project.results,
    project.skills.length > 0,
    Object.keys(project.metrics ?? {}).length > 0,
  ].filter(Boolean).length;
}

export function CompletenessBadge({ project }: { project: ProjectOut }) {
  const score = projectCompletenessScore(project);

  return (
    <span
      className={cn(
        "rounded-md px-2 py-1 text-xs",
        score < 2 && "bg-red-500/15 text-red-300",
        score >= 2 && score < 4 && "bg-amber-500/15 text-amber-300",
        score >= 4 && "bg-emerald-500/15 text-emerald-300"
      )}
    >
      {score}/5
    </span>
  );
}
