/**
 * @example
 * // Used inside PageView when NEXT_PUBLIC_UX_EDITOR_V2=1
 * <EditorBubbleMenu editor={editor} />
 */
"use client";

import { BubbleMenu as TiptapBubbleMenu, type Editor } from "@tiptap/react";
import { Bold, Code, Italic, Link2, Strikethrough } from "lucide-react";
import { cn } from "@/lib/cn";

interface EditorBubbleMenuProps {
  editor: Editor;
}

function ToolbarButton({
  onClick,
  active,
  title,
  children,
}: {
  onClick: () => void;
  active?: boolean;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onMouseDown={(e) => {
        e.preventDefault();
        onClick();
      }}
      title={title}
      aria-label={title}
      className={cn(
        "flex h-7 w-7 items-center justify-center rounded text-sm transition-colors",
        active ? "bg-gray-600 text-white" : "text-gray-300 hover:bg-gray-700 hover:text-white"
      )}
    >
      {children}
    </button>
  );
}

export function EditorBubbleMenu({ editor }: EditorBubbleMenuProps) {
  return (
    <TiptapBubbleMenu
      editor={editor}
      tippyOptions={{ duration: 100, placement: "top-start" }}
      className="flex items-center gap-0.5 rounded-lg border border-gray-600 bg-gray-900 p-1 shadow-xl"
    >
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleBold().run()}
        active={editor.isActive("bold")}
        title="Bold (⌘B)"
      >
        <Bold size={14} />
      </ToolbarButton>
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleItalic().run()}
        active={editor.isActive("italic")}
        title="Italic (⌘I)"
      >
        <Italic size={14} />
      </ToolbarButton>
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleStrike().run()}
        active={editor.isActive("strike")}
        title="Strikethrough"
      >
        <Strikethrough size={14} />
      </ToolbarButton>
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleCode().run()}
        active={editor.isActive("code")}
        title="Inline code"
      >
        <Code size={14} />
      </ToolbarButton>
      <div className="mx-1 h-4 w-px bg-gray-700" />
      <ToolbarButton
        onClick={() => {
          const url = window.prompt("URL", editor.getAttributes("link").href ?? "");
          if (url === null) return;
          if (url === "") {
            editor.chain().focus().unsetLink().run();
          } else {
            editor.chain().focus().setLink({ href: url }).run();
          }
        }}
        active={editor.isActive("link")}
        title="Link (⌘K)"
      >
        <Link2 size={14} />
      </ToolbarButton>
    </TiptapBubbleMenu>
  );
}
