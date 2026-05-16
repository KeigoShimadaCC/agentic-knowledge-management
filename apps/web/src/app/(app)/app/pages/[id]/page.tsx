import { notFound } from "next/navigation";
import { getServerApiUrl } from "@/lib/serverApiUrl";
import { PageView } from "@/components/pages/PageView";
import type { PageOut } from "@/types";

async function fetchPage(id: string): Promise<PageOut | null> {
  const apiUrl = getServerApiUrl();
  try {
    const res = await fetch(`${apiUrl}/api/v1/pages/${id}`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json() as Promise<PageOut>;
  } catch {
    return null;
  }
}

async function fetchObject(id: string) {
  const apiUrl = getServerApiUrl();
  try {
    const res = await fetch(`${apiUrl}/api/v1/objects/${id}`, { cache: "no-store" });
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
