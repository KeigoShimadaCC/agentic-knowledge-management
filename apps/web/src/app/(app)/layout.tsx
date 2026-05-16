import { AppShell } from "@/components/layout/AppShell";
import { TutorialProvider } from "@/components/tutorial/TutorialProvider";
import { WorkspaceLiteProvider } from "@/components/workspace/WorkspaceLiteProvider";
import { ErrorBoundary } from "@/components/layout/ErrorBoundary";
import { Toaster } from "@/components/ui/Toast";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <WorkspaceLiteProvider>
      <TutorialProvider>
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
      </TutorialProvider>
    </WorkspaceLiteProvider>
  );
}
