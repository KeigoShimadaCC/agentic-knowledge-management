"use client";

import * as React from "react";
import { Dialog, DialogContent } from "@/components/ui/Dialog";
import { SHORTCUTS, SHORTCUT_AREAS, type ShortcutArea } from "@/lib/shortcuts/registry";

interface ShortcutOverlayProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ShortcutOverlay({ open, onOpenChange }: ShortcutOverlayProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent title="Keyboard Shortcuts" size="lg">
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          {SHORTCUT_AREAS.map((area: ShortcutArea) => {
            const entries = SHORTCUTS.filter((s) => s.area === area);
            return (
              <section key={area} aria-labelledby={`shortcuts-area-${area}`}>
                <h3
                  id={`shortcuts-area-${area}`}
                  className="mb-2 text-xs font-semibold uppercase tracking-wider text-fg-subtle"
                >
                  {area}
                </h3>
                <ul className="space-y-1">
                  {entries.map((entry) => (
                    <li key={`${entry.area}-${entry.key}`} className="flex items-center justify-between gap-4">
                      <span className="text-sm text-fg-muted">{entry.description}</span>
                      <kbd className="shrink-0 rounded bg-surface-2 px-2 py-0.5 font-mono text-xs text-fg">
                        {entry.key}
                      </kbd>
                    </li>
                  ))}
                </ul>
              </section>
            );
          })}
        </div>
      </DialogContent>
    </Dialog>
  );
}
