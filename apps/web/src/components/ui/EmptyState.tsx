/**
 * @example
 * <EmptyState
 *   icon={<FileText />}
 *   title="No pages yet"
 *   description="Create your first page to get started"
 *   action={<Button>New page</Button>}
 * />
 */
import * as React from "react";
import { cn } from "@/lib/cn";

export interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({ icon, title, description, action, className, ...props }: EmptyStateProps) {
  return (
    <div
      className={cn("flex flex-col items-center justify-center gap-3 py-16 text-center", className)}
      {...props}
    >
      {icon && <div className="text-fg-subtle [&>svg]:h-10 [&>svg]:w-10">{icon}</div>}
      <p className="text-sm font-medium text-fg">{title}</p>
      {description && <p className="text-sm text-fg-muted max-w-xs">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
