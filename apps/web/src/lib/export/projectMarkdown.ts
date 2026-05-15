import type { InterviewStoryOut, ProjectOut, ResumeBulletSetOut } from "@/types";

function valueOrDash(value: string | null | undefined): string {
  return value?.trim() || "-";
}

function period(project: ProjectOut): string {
  if (!project.period_start && !project.period_end) return "-";
  return `${project.period_start ?? "Unknown"} - ${project.period_end ?? "Ongoing"}`;
}

export function projectToMarkdown(
  project: ProjectOut,
  bulletSets: ResumeBulletSetOut[],
  stories: InterviewStoryOut[]
): string {
  const lines: string[] = [
    `# ${project.title}`,
    "",
    `**Role:** ${valueOrDash(project.role)} @ ${valueOrDash(project.organization)}  **Period:** ${period(project)}  **Status:** ${project.status}`,
    "",
  ];

  if (project.description) lines.push(project.description, "");

  lines.push("## Problem", valueOrDash(project.problem), "");
  lines.push("## Actions", valueOrDash(project.actions), "");
  lines.push("## Results", valueOrDash(project.results), "");

  lines.push("## Metrics", "| Key | Value |", "|---|---|");
  const metrics = Object.entries(project.metrics ?? {});
  if (metrics.length === 0) lines.push("| - | - |");
  for (const [key, value] of metrics) lines.push(`| ${key} | ${String(value)} |`);
  lines.push("");

  lines.push("## Skills", project.skills.length ? project.skills.join(", ") : "-", "");

  lines.push("## Resume Bullets");
  if (bulletSets.length === 0) {
    lines.push("-");
  } else {
    for (const set of bulletSets) {
      lines.push(`### ${valueOrDash(set.target_role)} (${new Date(set.created_at).toLocaleDateString()})`);
      for (const bullet of set.bullets) {
        lines.push(`- ${bullet.text} [${bullet.confidence}]`);
      }
      lines.push("");
    }
  }

  lines.push("## Interview Stories");
  if (stories.length === 0) {
    lines.push("-");
  } else {
    for (const story of stories) {
      lines.push(
        `### ${story.question_type} - ${valueOrDash(story.target_role)} (${new Date(story.created_at).toLocaleDateString()})`,
        `**Situation:** ${story.story.situation}`,
        "",
        `**Task:** ${story.story.task}`,
        "",
        `**Action:** ${story.story.action}`,
        "",
        `**Result:** ${story.story.result}`,
        ""
      );
    }
  }

  return `${lines.join("\n").trim()}\n`;
}
