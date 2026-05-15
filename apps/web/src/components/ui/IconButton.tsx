/** @example <IconButton aria-label="Close panel"><X /></IconButton> */
"use client";
import * as React from "react";
import { Button, type ButtonProps } from "./Button";
import { cn } from "@/lib/cn";

export interface IconButtonProps extends Omit<ButtonProps, "leftIcon" | "rightIcon"> {
  "aria-label": string;
}

export const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ className, size = "md", variant = "ghost", children, ...props }, ref) => (
    <Button
      ref={ref}
      variant={variant}
      size={size}
      className={cn(
        size === "sm" && "h-7 w-7 p-0",
        size === "md" && "h-9 w-9 p-0",
        size === "lg" && "h-11 w-11 p-0",
        className
      )}
      {...props}
    >
      {children}
    </Button>
  )
);
IconButton.displayName = "IconButton";
