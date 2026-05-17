"use client";
import { useEffect } from "react";

type ShortcutOptions = {
  /** If true, the shortcut fires even when an input/textarea/contenteditable is focused. Default: false. */
  allowInInputs?: boolean;
};

/** Registers a keyboard shortcut at the document level. */
export function useShortcut(
  key: string,
  handler: (e: KeyboardEvent) => void,
  deps: React.DependencyList = [],
  options: ShortcutOptions = {}
) {
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (!options.allowInInputs) {
        const target = e.target as HTMLElement;
        if (
          target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable
        ) {
          return;
        }
      }
      if (e.key !== key) return;
      handler(e);
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}
