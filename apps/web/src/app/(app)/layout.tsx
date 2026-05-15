import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { WorkspaceLiteProvider } from "@/components/workspace/WorkspaceLiteProvider";
import { ErrorBoundary } from "@/components/layout/ErrorBoundary";
import { Toaster } from "@/components/ui/Toast";

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

  return (
    <WorkspaceLiteProvider>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-brand focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-brand-fg focus:outline-none"
      >
        Skip to content
      </a>
      <ErrorBoundary>
        <AppShell>{children}</AppShell>
      </ErrorBoundary>
      <Toaster position="bottom-right" richColors />
    </WorkspaceLiteProvider>
  );
}
