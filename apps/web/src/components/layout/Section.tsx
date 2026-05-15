/** @example <Section title="Recent pages"><Card /></Section> */
import * as React from "react";
import { cn } from "@/lib/cn";

export interface SectionProps extends React.HTMLAttributes<HTMLElement> {
  title?: string;
  description?: string;
  actions?: React.ReactNode;
}

export function Section({ title, description, actions, children, className, ...props }: SectionProps) {
  return (
    <section className={cn("flex flex-col gap-3", className)} {...props}>
      {(title || actions) && (
        <div className="flex items-center justify-between">
          <div>
            {title && <h2 className="text-sm font-semibold text-fg">{title}</h2>}
            {description && <p className="text-xs text-fg-muted">{description}</p>}
          </div>
          {actions && <div>{actions}</div>}
        </div>
      )}
      {children}
    </section>
  );
}
