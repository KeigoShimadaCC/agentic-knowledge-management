/** @example <ErrorState error={new Error("Not found")} onRetry={refetch} /> */
import * as React from "react";
import { AlertCircle } from "lucide-react";
import { Button } from "./Button";
import { cn } from "@/lib/cn";

export interface ErrorStateProps extends React.HTMLAttributes<HTMLDivElement> {
  error: Error | string | null | undefined;
  onRetry?: () => void;
}

export function ErrorState({ error, onRetry, className, ...props }: ErrorStateProps) {
  const message = error instanceof Error ? error.message : (error ?? "Something went wrong");
  return (
    <div
      className={cn("flex flex-col items-center justify-center gap-3 py-16 text-center", className)}
      {...props}
    >
      <AlertCircle className="h-10 w-10 text-danger" />
      <p className="text-sm font-medium text-fg">Error</p>
      <p className="text-sm text-fg-muted max-w-xs">{message}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}
