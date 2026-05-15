/** @example <PageHeader title="Pages" description="All your pages" actions={<Button>New</Button>} /> */
import * as React from "react";
import { cn } from "@/lib/cn";

export interface PageHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  breadcrumbs?: React.ReactNode;
}

export function PageHeader({ title, description, actions, breadcrumbs, className, ...props }: PageHeaderProps) {
  return (
    <div className={cn("flex flex-col gap-1 pb-4", className)} {...props}>
      {breadcrumbs && <div className="text-xs text-fg-subtle">{breadcrumbs}</div>}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-fg">{title}</h1>
          {description && <p className="text-sm text-fg-muted mt-0.5">{description}</p>}
        </div>
        {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
      </div>
    </div>
  );
}
