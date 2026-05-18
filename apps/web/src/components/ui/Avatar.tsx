/** @example <Avatar name="Demo User" size="md" /> */
import * as React from "react";
import { cn } from "@/lib/cn";

const sizeMap = {
  sm: "h-6 w-6 text-xs",
  md: "h-8 w-8 text-sm",
  lg: "h-10 w-10 text-base",
} as const;

export interface AvatarProps extends React.HTMLAttributes<HTMLSpanElement> {
  name?: string;
  size?: "sm" | "md" | "lg";
}

export function Avatar({ name, size = "md", className, ...props }: AvatarProps) {
  const initials = name
    ? name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .slice(0, 2)
        .toUpperCase()
    : "?";
  return (
    <span
      className={cn(
        "inline-flex items-center justify-center rounded-full bg-brand font-medium text-brand-fg select-none",
        sizeMap[size],
        className
      )}
      aria-label={name}
      {...props}
    >
      {initials}
    </span>
  );
}
