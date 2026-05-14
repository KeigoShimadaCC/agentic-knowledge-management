import { cookies } from "next/headers";
import { notFound } from "next/navigation";
import { PageView } from "@/components/pages/PageView";
import type { PageOut } from "@/types";

async function fetchPage(id: string): Promise<PageOut | null> {
  const apiUrl = process.env.API_URL ?? "http://localhost:8000";
  const cookieStore = cookies();
  const sessionCookie = cookieStore.get("kos_session");
  if (!sessionCookie) return null;

  try {
    const res = await fetch(`${apiUrl}/api/v1/pages/${id}`, {
      headers: { Cookie: `kos_session=${sessionCookie.value}` },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json() as Promise<PageOut>;
  } catch {
    return null;
  }
}

async function fetchObject(id: string) {
  const apiUrl = process.env.API_URL ?? "http://localhost:8000";
  const cookieStore = cookies();
  const sessionCookie = cookieStore.get("kos_session");
  if (!sessionCookie) return null;

  try {
    const res = await fetch(`${apiUrl}/api/v1/objects/${id}`, {
      headers: { Cookie: `kos_session=${sessionCookie.value}` },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function PageEditorPage({
  params,
}: {
  params: { id: string };
}) {
  const [page, obj] = await Promise.all([fetchPage(params.id), fetchObject(params.id)]);

  if (!page || !obj) notFound();

  return (
    <PageView
      pageId={params.id}
      initialTitle={(obj as { title: string }).title}
      initialContent={page.content_json}
    />
  );
}
