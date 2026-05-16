/**
 * @example
 * // Used inside PageView when NEXT_PUBLIC_UX_EDITOR_V2=1
 * <SlashMenu editor={editor} />
 */
"use client";

import { useEffect, useRef, useState } from "react";
import type { Editor } from "@tiptap/react";
import {
  AlignLeft,
  CheckSquare,
  Code,
  Heading1,
  Heading2,
  Heading3,
  Minus,
  Quote,
  Sparkles,
  Table,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/cn";
import { aiComplete, aiTransform } from "@/lib/api";
import { applyAiAction } from "./AiSlashCommand";
import { subscribeSlashMenu, type SlashMenuState } from "./extensions/SlashMenuExtension";

type Command = {
  label: string;
  description: string;
  icon: LucideIcon;
  execute: (editor: Editor) => unknown;
};

const COMMANDS: Command[] = [
  {
    label: "Heading 1",
    description: "Large section heading",
    icon: Heading1,
    execute: (editor) => editor.chain().focus().toggleHeading({ level: 1 }).run(),
  },
  {
    label: "Heading 2",
    description: "Medium section heading",
    icon: Heading2,
    execute: (editor) => editor.chain().focus().toggleHeading({ level: 2 }).run(),
  },
  {
    label: "Heading 3",
    description: "Small section heading",
    icon: Heading3,
    execute: (editor) => editor.chain().focus().toggleHeading({ level: 3 }).run(),
  },
  {
    label: "Paragraph",
    description: "Plain text block",
    icon: AlignLeft,
    execute: (editor) => editor.chain().focus().setParagraph().run(),
  },
  {
    label: "Quote",
    description: "Blockquote",
    icon: Quote,
    execute: (editor) => editor.chain().focus().toggleBlockquote().run(),
  },
  {
    label: "Code block",
    description: "Monospace code block",
    icon: Code,
    execute: (editor) => editor.chain().focus().toggleCodeBlock().run(),
  },
  {
    label: "Task list",
    description: "Checkbox task list",
    icon: CheckSquare,
    execute: (editor) => editor.chain().focus().toggleTaskList().run(),
  },
  {
    label: "Divider",
    description: "Horizontal rule",
    icon: Minus,
    execute: (editor) => editor.chain().focus().setHorizontalRule().run(),
  },
  {
    label: "Table",
    description: "Insert a 3×3 table",
    icon: Table,
    execute: (editor) =>
      editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run(),
  },
];

interface SlashMenuProps {
  editor: Editor;
  objectId?: string;
}

export function SlashMenu({ editor, objectId }: SlashMenuProps) {
  const [menuState, setMenuState] = useState<SlashMenuState>({ active: false, query: "", range: null });
  const [selectedIdx, setSelectedIdx] = useState(0);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const unsub = subscribeSlashMenu(setMenuState);
    return () => { unsub(); };
  }, []);

  const aiCommands: Command[] = objectId
    ? [
        {
          label: "Continue writing",
          description: "Let AI complete your thought",
          icon: Sparkles,
          execute: (ed) => {
            const slashFrom = menuState.range?.from ?? ed.state.selection.from;
            const cursorPos = ed.state.selection.from;
            ed.chain().focus().deleteRange({ from: slashFrom, to: cursorPos }).run();
            const textBefore = ed.state.doc.textBetween(0, slashFrom, "\n", "\n");
            void applyAiAction(ed, "[AI writing…]", async () => {
              const { completion } = await aiComplete(textBefore, "continue", objectId);
              return completion;
            });
          },
        },
        {
          label: "Expand",
          description: "Expand the current paragraph with more detail",
          icon: Sparkles,
          execute: (ed) => {
            const slashFrom = menuState.range?.from ?? ed.state.selection.from;
            const cursorPos = ed.state.selection.from;
            ed.chain().focus().deleteRange({ from: slashFrom, to: cursorPos }).run();
            const textBefore = ed.state.doc.textBetween(0, slashFrom, "\n", "\n");
            void applyAiAction(ed, "[AI writing…]", async () => {
              const { completion } = await aiComplete(textBefore, "expand", objectId);
              return completion;
            });
          },
        },
        {
          label: "Improve writing",
          description: "Rewrite the current paragraph for clarity",
          icon: Sparkles,
          execute: (ed) => {
            const slashFrom = menuState.range?.from ?? ed.state.selection.from;
            const cursorPos = ed.state.selection.from;
            const { $anchor } = ed.state.selection;
            const paraStart = $anchor.start();
            const paraEnd = $anchor.end();
            const paraText = ed.state.doc.textBetween(paraStart, paraEnd, "\n");
            ed.chain().focus().deleteRange({ from: slashFrom, to: cursorPos }).run();
            ed.chain().focus().setTextSelection({ from: paraStart, to: paraEnd }).run();
            void applyAiAction(ed, "[AI writing…]", async () => {
              const { result } = await aiTransform(paraText, "improve", objectId);
              return result;
            });
          },
        },
        {
          label: "Make concise",
          description: "Shorten the current paragraph",
          icon: Sparkles,
          execute: (ed) => {
            const slashFrom = menuState.range?.from ?? ed.state.selection.from;
            const cursorPos = ed.state.selection.from;
            const { $anchor } = ed.state.selection;
            const paraStart = $anchor.start();
            const paraEnd = $anchor.end();
            const paraText = ed.state.doc.textBetween(paraStart, paraEnd, "\n");
            ed.chain().focus().deleteRange({ from: slashFrom, to: cursorPos }).run();
            ed.chain().focus().setTextSelection({ from: paraStart, to: paraEnd }).run();
            void applyAiAction(ed, "[AI writing…]", async () => {
              const { result } = await aiTransform(paraText, "concise", objectId);
              return result;
            });
          },
        },
        {
          label: "Fix grammar",
          description: "Correct spelling and grammar",
          icon: Sparkles,
          execute: (ed) => {
            const slashFrom = menuState.range?.from ?? ed.state.selection.from;
            const cursorPos = ed.state.selection.from;
            const { $anchor } = ed.state.selection;
            const paraStart = $anchor.start();
            const paraEnd = $anchor.end();
            const paraText = ed.state.doc.textBetween(paraStart, paraEnd, "\n");
            ed.chain().focus().deleteRange({ from: slashFrom, to: cursorPos }).run();
            ed.chain().focus().setTextSelection({ from: paraStart, to: paraEnd }).run();
            void applyAiAction(ed, "[AI writing…]", async () => {
              const { result } = await aiTransform(paraText, "grammar", objectId);
              return result;
            });
          },
        },
        {
          label: "Summarize selection",
          description: "Summarize this page in one paragraph",
          icon: Sparkles,
          execute: (ed) => {
            const slashFrom = menuState.range?.from ?? ed.state.selection.from;
            const cursorPos = ed.state.selection.from;
            ed.chain().focus().deleteRange({ from: slashFrom, to: cursorPos }).run();
            const fullText = ed.state.doc.textBetween(
              0,
              ed.state.doc.content.size,
              "\n",
              "\n",
            );
            void applyAiAction(ed, "[AI writing…]", async () => {
              const { result } = await aiTransform(fullText, "summarize", objectId);
              return result;
            });
          },
        },
      ]
    : [];

  const allCommands = [...COMMANDS, ...aiCommands];

  const filtered = allCommands.filter((c) =>
    !menuState.query || c.label.toLowerCase().includes(menuState.query.toLowerCase())
  );

  useEffect(() => {
    setSelectedIdx(0);
  }, [menuState.query]);

  useEffect(() => {
    if (!menuState.active) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIdx((i) => Math.min(i + 1, filtered.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIdx((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter") {
        e.preventDefault();
        filtered[selectedIdx]?.execute(editor);
        setMenuState({ active: false, query: "", range: null });
      }
    }
    document.addEventListener("keydown", onKey, true);
    return () => document.removeEventListener("keydown", onKey, true);
  }, [menuState.active, filtered, selectedIdx, editor]);

  if (!menuState.active || filtered.length === 0) return null;

  const { view } = editor;
  const domPos = menuState.range
    ? view.coordsAtPos(menuState.range.from)
    : null;

  const style = domPos
    ? { top: domPos.bottom + 4, left: domPos.left }
    : undefined;

  return (
    <div
      ref={menuRef}
      style={style}
      className="fixed z-50 w-64 overflow-hidden rounded-lg border border-gray-700 bg-gray-900 shadow-xl"
    >
      {filtered.map((cmd, i) => {
        const Icon = cmd.icon;
        return (
          <button
            key={cmd.label}
            type="button"
            onMouseDown={(e) => {
              e.preventDefault();
              cmd.execute(editor);
              setMenuState({ active: false, query: "", range: null });
            }}
            className={cn(
              "flex w-full items-center gap-3 px-3 py-2 text-left text-sm transition-colors",
              i === selectedIdx ? "bg-gray-800 text-white" : "text-gray-300 hover:bg-gray-800"
            )}
          >
            <Icon size={16} className="shrink-0 text-gray-400" />
            <div>
              <div className="font-medium">{cmd.label}</div>
              <div className="text-xs text-gray-500">{cmd.description}</div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
