/** @example <Select label="Kind" options={[{value:"page",label:"Page"},{value:"source",label:"Source"}]} /> */
"use client";
import * as React from "react";
import { cn } from "@/lib/cn";

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  hint?: string;
  error?: string;
  options?: SelectOption[];
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, hint, error, id, options, children, ...props }, ref) => {
    const selectId = id ?? (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={selectId} className="text-sm font-medium text-fg">
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={selectId}
          className={cn(
            "flex h-9 w-full rounded-md border border-zinc-700 bg-surface-1 px-3 py-1 text-sm text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
            error && "border-danger focus-visible:ring-danger",
            className
          )}
          {...props}
        >
          {options
            ? options.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))
            : children}
        </select>
        {error ? (
          <p className="text-xs text-danger">{error}</p>
        ) : hint ? (
          <p className="text-xs text-fg-subtle">{hint}</p>
        ) : null}
      </div>
    );
  }
);
Select.displayName = "Select";
