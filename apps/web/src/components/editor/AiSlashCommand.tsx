"use client";

import type { Editor } from "@tiptap/react";
import { toast } from "sonner";

export async function applyAiAction(
  editor: Editor,
  placeholder: string,
  action: () => Promise<string>,
): Promise<void> {
  const { from, to } = editor.state.selection;
  if (from < to) {
    editor.chain().focus().deleteRange({ from, to }).run();
  }
  editor.chain().focus().insertContentAt(from, placeholder).run();
  const placeholderTo = from + placeholder.length;
  try {
    const result = await action();
    editor
      .chain()
      .focus()
      .deleteRange({ from, to: placeholderTo })
      .insertContentAt(from, result)
      .run();
  } catch {
    editor.chain().focus().deleteRange({ from, to: placeholderTo }).run();
    toast.error("AI failed — try again");
  }
}
