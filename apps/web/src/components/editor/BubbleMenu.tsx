/**
 * @example
 * // Used inside PageView when NEXT_PUBLIC_UX_EDITOR_V2=1
 * <EditorBubbleMenu editor={editor} />
 */
"use client";

import { useRef, useState } from "react";
import { BubbleMenu as TiptapBubbleMenu, type Editor } from "@tiptap/react";
import { Bold, Code, Italic, Link2, Loader2, Sparkles, Strikethrough } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/cn";
import { aiTransform } from "@/lib/api";

interface EditorBubbleMenuProps {
  editor: Editor;
  objectId?: string;
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

export function EditorBubbleMenu({ editor, objectId }: EditorBubbleMenuProps) {
  const [aiLoading, setAiLoading] = useState(false);
  const detailsRef = useRef<HTMLDetailsElement>(null);

  async function runTransform(instruction: "improve" | "concise" | "grammar" | "summarize") {
    if (detailsRef.current) detailsRef.current.open = false;
    const { from, to } = editor.state.selection;
    const selectedText = editor.state.doc.textBetween(from, to, "\n");
    if (!selectedText) return;
    setAiLoading(true);
    try {
      const { result } = await aiTransform(selectedText, instruction, objectId);
      editor.chain().focus().deleteRange({ from, to }).insertContentAt(from, result).run();
    } catch {
      toast.error("AI failed — try again");
    } finally {
      setAiLoading(false);
    }
  }

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
      {objectId && (
        <>
          <div className="mx-1 h-4 w-px bg-gray-700" />
          <details ref={detailsRef} className="relative">
            <summary
              className={cn(
                "flex h-7 cursor-pointer list-none items-center gap-1 rounded px-2 text-xs transition-colors",
                aiLoading
                  ? "text-gray-500"
                  : "text-gray-300 hover:bg-gray-700 hover:text-white"
              )}
            >
              {aiLoading ? (
                <Loader2 size={12} className="animate-spin" />
              ) : (
                <Sparkles size={12} />
              )}
              AI ▾
            </summary>
            <div className="absolute left-0 top-full z-50 mt-1 w-44 overflow-hidden rounded-lg border border-gray-700 bg-gray-900 shadow-xl">
              {(
                [
                  { label: "Improve", instruction: "improve" },
                  { label: "Make concise", instruction: "concise" },
                  { label: "Fix grammar", instruction: "grammar" },
                  { label: "Summarize selection", instruction: "summarize" },
                ] as const
              ).map(({ label, instruction }) => (
                <button
                  key={instruction}
                  type="button"
                  disabled={aiLoading}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    void runTransform(instruction);
                  }}
                  className="flex w-full items-center px-3 py-2 text-left text-xs text-gray-300 transition-colors hover:bg-gray-800 disabled:opacity-50"
                >
                  {label}
                </button>
              ))}
            </div>
          </details>
        </>
      )}
    </TiptapBubbleMenu>
  );
}
