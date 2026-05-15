/** @example <Tooltip content="Save document"><Button>Save</Button></Tooltip> */
"use client";
import * as React from "react";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { cn } from "@/lib/cn";

export const TooltipProvider = TooltipPrimitive.Provider;

export interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactNode;
  delayDuration?: number;
  side?: "top" | "right" | "bottom" | "left";
  className?: string;
}

export function Tooltip({ content, children, delayDuration = 600, side = "top", className }: TooltipProps) {
  return (
    <TooltipPrimitive.Root delayDuration={delayDuration}>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
          side={side}
          sideOffset={4}
          className={cn(
            "z-50 overflow-hidden rounded-md border border-zinc-800 bg-surface-1 px-3 py-1.5 text-xs text-fg shadow-md motion-safe:animate-in motion-safe:fade-in-0 motion-safe:zoom-in-95",
            className
          )}
        >
          {content}
          <TooltipPrimitive.Arrow className="fill-zinc-800" />
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  );
}
