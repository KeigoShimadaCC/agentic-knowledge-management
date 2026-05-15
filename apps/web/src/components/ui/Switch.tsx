/** @example <Switch label="Dark mode" checked={isDark} onCheckedChange={setDark} /> */
"use client";
import * as React from "react";
import * as SwitchPrimitive from "@radix-ui/react-switch";
import { cn } from "@/lib/cn";

export interface SwitchProps
  extends React.ComponentPropsWithoutRef<typeof SwitchPrimitive.Root> {
  label?: string;
}

export const Switch = React.forwardRef<
  React.ElementRef<typeof SwitchPrimitive.Root>,
  SwitchProps
>(({ className, label, id, ...props }, ref) => {
  const switchId = id ?? (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);
  return (
    <div className="flex items-center gap-2">
      <SwitchPrimitive.Root
        ref={ref}
        id={switchId}
        className={cn(
          "peer inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:bg-brand data-[state=unchecked]:bg-surface-3",
          className
        )}
        {...props}
      >
        <SwitchPrimitive.Thumb className="pointer-events-none block h-4 w-4 rounded-full bg-white shadow-lg ring-0 transition-transform duration-fast data-[state=checked]:translate-x-4 data-[state=unchecked]:translate-x-0" />
      </SwitchPrimitive.Root>
      {label && (
        <label htmlFor={switchId} className="text-sm text-fg cursor-pointer">
          {label}
        </label>
      )}
    </div>
  );
});
Switch.displayName = "Switch";
