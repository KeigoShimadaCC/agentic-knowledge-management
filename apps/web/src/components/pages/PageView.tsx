"use client";

import { useCallback, useRef, useState } from "react";
import { useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import Typography from "@tiptap/extension-typography";
import Link from "@tiptap/extension-link";
import Image from "@tiptap/extension-image";
import { EditorContent } from "@tiptap/react";
import { EditorToolbar } from "@/components/editor/EditorToolbar";
import { PageTitle } from "./PageTitle";
import { useAutoSave } from "@/lib/hooks/useAutoSave";

interface PageViewProps {
  pageId: string;
  initialTitle: string;
  initialContent: Record<string, unknown>;
}

export function PageView({ pageId, initialTitle, initialContent }: PageViewProps) {
  const [title, setTitle] = useState(initialTitle);
  const [wordCount, setWordCount] = useState(0);
  const contentRef = useRef<Record<string, unknown>>(initialContent);
  const textRef = useRef<string>("");

  const saveData = {
    title,
    content_json: contentRef.current,
    content_text: textRef.current,
  };

  const { status } = useAutoSave(pageId, saveData);

  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({ placeholder: "Write something..." }),
      Typography,
      Link.configure({ openOnClick: false }),
      Image,
    ],
    content: Object.keys(initialContent).length > 0 ? initialContent : undefined,
    autofocus: true,
    editorProps: {
      attributes: {
        class: "outline-none min-h-[400px] leading-relaxed text-gray-100",
      },
    },
    onUpdate: ({ editor: ed }) => {
      contentRef.current = ed.getJSON() as Record<string, unknown>;
      textRef.current = ed.getText();
      setWordCount(ed.getText().split(/\s+/).filter(Boolean).length);
    },
  });

  const handleTitleChange = useCallback((newTitle: string) => {
    setTitle(newTitle);
  }, []);

  const saveStatusLabel = {
    idle: "",
    saving: "Saving...",
    saved: "Saved",
    error: "Error saving",
  }[status];

  return (
    <div className="flex flex-col h-full">
      <EditorToolbar editor={editor} />
      <div className="flex-1 overflow-y-auto p-8 max-w-3xl mx-auto w-full">
        <PageTitle initialTitle={initialTitle} onTitleChange={handleTitleChange} />
        <EditorContent editor={editor} />
      </div>
      <div className="flex items-center justify-between px-8 py-2 border-t border-gray-800 text-xs text-gray-500">
        <span>{wordCount} words</span>
        <span className={status === "error" ? "text-red-400" : ""}>{saveStatusLabel}</span>
      </div>
    </div>
  );
}
