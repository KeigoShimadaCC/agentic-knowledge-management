"use client";
import { ErrorState } from "@/components/ui/ErrorState";

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center p-8">
      <ErrorState error={error} onRetry={reset} />
    </div>
  );
}
