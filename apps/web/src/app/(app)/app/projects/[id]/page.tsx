import { notFound } from "next/navigation";

import { ProjectView } from "@/components/projects/ProjectView";
import { getServerApiHeaders, getServerApiUrl } from "@/lib/serverApiUrl";
import type { ProjectOut } from "@/types";

async function fetchProject(id: string): Promise<ProjectOut | null> {
  const apiUrl = getServerApiUrl();
  try {
    const res = await fetch(`${apiUrl}/api/v1/projects/${id}`, {
      cache: "no-store",
      headers: getServerApiHeaders(),
    });
    if (res.status === 404) return null;
    if (!res.ok) return null;
    return res.json() as Promise<ProjectOut>;
  } catch {
    return null;
  }
}

export default async function ProjectDetailPage({ params }: { params: { id: string } }) {
  const project = await fetchProject(params.id);
  if (!project) notFound();
  return <ProjectView project={project} />;
}
