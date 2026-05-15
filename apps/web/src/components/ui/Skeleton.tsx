/** @example <Skeleton className="h-4 w-32" /> */
import * as React from "react";
import { cn } from "@/lib/cn";

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("rounded-md bg-surface-2 motion-safe:animate-pulse", className)}
      {...props}
    />
  );
}
