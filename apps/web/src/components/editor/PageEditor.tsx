"use client";

import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import Typography from "@tiptap/extension-typography";
import Link from "@tiptap/extension-link";
import Image from "@tiptap/extension-image";

interface PageEditorProps {
  initialContent: Record<string, unknown>;
  onUpdate: (json: Record<string, unknown>, text: string) => void;
}

export function PageEditor({ initialContent, onUpdate }: PageEditorProps) {
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
        class: "outline-none min-h-[300px] leading-relaxed text-gray-100",
      },
    },
    onUpdate: ({ editor: ed }) => {
      onUpdate(ed.getJSON() as Record<string, unknown>, ed.getText());
    },
  });

  return <EditorContent editor={editor} />;
}
