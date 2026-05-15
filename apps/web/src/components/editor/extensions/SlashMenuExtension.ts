import { Extension } from "@tiptap/react";

export interface SlashMenuState {
  active: boolean;
  query: string;
  range: { from: number; to: number } | null;
}

declare global {
  interface Window {
    __kosSlashMenuState?: SlashMenuState;
    __kosSlashMenuListeners?: Set<(state: SlashMenuState) => void>;
  }
}

function emitSlashState(state: SlashMenuState) {
  if (typeof window === "undefined") return;
  window.__kosSlashMenuState = state;
  window.__kosSlashMenuListeners?.forEach((fn) => fn(state));
}

export function subscribeSlashMenu(fn: (state: SlashMenuState) => void) {
  if (typeof window === "undefined") return () => undefined;
  if (!window.__kosSlashMenuListeners) window.__kosSlashMenuListeners = new Set();
  window.__kosSlashMenuListeners.add(fn);
  return () => window.__kosSlashMenuListeners?.delete(fn);
}

export const SlashMenuExtension = Extension.create({
  name: "slashMenu",

  addKeyboardShortcuts() {
    return {
      "/": ({ editor }) => {
        const { state } = editor;
        const { from } = state.selection;
        const $pos = state.doc.resolve(from);
        const lineStart = $pos.start();
        const textBefore = state.doc.textBetween(lineStart, from, undefined, "\n");

        if (textBefore.trim() !== "") return false;

        const coords = editor.view.coordsAtPos(from);
        emitSlashState({ active: true, query: "", range: { from, to: from } });
        void coords;
        return false;
      },
      Escape: () => {
        const state = typeof window !== "undefined" ? window.__kosSlashMenuState : undefined;
        if (!state?.active) return false;
        emitSlashState({ active: false, query: "", range: null });
        return true;
      },
    };
  },
});
