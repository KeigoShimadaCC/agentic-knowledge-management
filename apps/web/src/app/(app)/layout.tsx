import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";

async function getCurrentUser() {
  const apiUrl = process.env.API_URL ?? "http://localhost:8000";
  const cookieStore = cookies();
  const sessionCookie = cookieStore.get("kos_session");

  if (!sessionCookie) return null;

  try {
    const res = await fetch(`${apiUrl}/api/v1/auth/me`, {
      headers: {
        Cookie: `kos_session=${sessionCookie.value}`,
      },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const user = await getCurrentUser();
  if (!user) redirect("/login");

  return <AppShell>{children}</AppShell>;
}
