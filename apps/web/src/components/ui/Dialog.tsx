/**
 * @example
 * <Dialog open={open} onOpenChange={setOpen}>
 *   <DialogContent title="Confirm" size="sm">Are you sure?</DialogContent>
 * </Dialog>
 */
"use client";
import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "@/lib/cn";

export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.Close;

const sizeClasses = {
  sm: "max-w-sm",
  md: "max-w-lg",
  lg: "max-w-2xl",
} as const;

export interface DialogContentProps
  extends React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content> {
  title?: string;
  description?: string;
  size?: "sm" | "md" | "lg";
  hideClose?: boolean;
}

export const DialogContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  DialogContentProps
>(({ className, title, description, size = "md", hideClose, children, ...props }, ref) => (
  <DialogPrimitive.Portal>
    <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/60 motion-safe:animate-in motion-safe:fade-in-0" />
    <DialogPrimitive.Content
      ref={ref}
      className={cn(
        "fixed left-[50%] top-[50%] z-50 translate-x-[-50%] translate-y-[-50%] w-full rounded-lg border border-zinc-800 bg-surface-1 p-6 shadow-xl motion-safe:animate-in motion-safe:fade-in-0 motion-safe:zoom-in-95",
        sizeClasses[size],
        className
      )}
      {...props}
    >
      {(title || !hideClose) && (
        <div className="flex items-start justify-between mb-4">
          {title && (
            <DialogPrimitive.Title className="text-lg font-semibold text-fg">
              {title}
            </DialogPrimitive.Title>
          )}
          {!hideClose && (
            <DialogPrimitive.Close className="ml-auto rounded-sm opacity-70 hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring">
              <X className="h-4 w-4 text-fg" />
              <span className="sr-only">Close</span>
            </DialogPrimitive.Close>
          )}
        </div>
      )}
      {description && (
        <DialogPrimitive.Description className="text-sm text-fg-muted mb-4">
          {description}
        </DialogPrimitive.Description>
      )}
      {children}
    </DialogPrimitive.Content>
  </DialogPrimitive.Portal>
));
DialogContent.displayName = "DialogContent";
