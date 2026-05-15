import Link from "next/link";
import { EmptyState } from "@/components/ui/EmptyState";

export default function AppNotFound() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center p-8">
      <EmptyState
        title="Page not found"
        description="The page you're looking for doesn't exist or has been moved."
        action={
          <Link href="/app" className="inline-flex h-9 items-center rounded-md bg-surface-2 px-4 text-sm font-medium text-fg hover:bg-surface-3 transition-colors">
            Go home
          </Link>
        }
      />
    </div>
  );
}
