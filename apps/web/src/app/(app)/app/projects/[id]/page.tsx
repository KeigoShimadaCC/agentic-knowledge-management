import { cookies } from "next/headers";
import { notFound } from "next/navigation";

import { ProjectView } from "@/components/projects/ProjectView";
import type { ProjectOut } from "@/types";

async function fetchProject(id: string): Promise<ProjectOut | null> {
  const apiUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const cookieStore = cookies();
  const sessionCookie = cookieStore.get("kos_session");
  if (!sessionCookie) return null;

  try {
    const res = await fetch(`${apiUrl}/api/v1/projects/${id}`, {
      headers: { Cookie: `kos_session=${sessionCookie.value}` },
      cache: "no-store",
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
