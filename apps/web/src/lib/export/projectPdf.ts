import { jsPDF } from "jspdf";

import { projectToMarkdown } from "@/lib/export/projectMarkdown";
import type { InterviewStoryOut, ProjectOut, ResumeBulletSetOut } from "@/types";

function filename(title: string): string {
  return `${title.trim().replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "") || "project"}.pdf`;
}

export function projectToPdf(
  project: ProjectOut,
  bulletSets: ResumeBulletSetOut[],
  stories: InterviewStoryOut[]
): void {
  const markdown = projectToMarkdown(project, bulletSets, stories);
  const doc = new jsPDF({ unit: "pt", format: "letter" });
  const margin = 48;
  const maxWidth = 612 - margin * 2;
  const lineHeight = 14;
  let y = margin;

  doc.setFont("courier", "normal");
  doc.setFontSize(10);

  for (const rawLine of markdown.split("\n")) {
    const wrapped = doc.splitTextToSize(rawLine || " ", maxWidth) as string[];
    for (const line of wrapped) {
      if (y > 744) {
        doc.addPage();
        y = margin;
      }
      doc.text(line, margin, y);
      y += lineHeight;
    }
  }

  doc.save(filename(project.title));
}
