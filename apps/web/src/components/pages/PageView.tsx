"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import Typography from "@tiptap/extension-typography";
import Link from "@tiptap/extension-link";
import Image from "@tiptap/extension-image";
import { EditorContent } from "@tiptap/react";
import { EditorToolbar } from "@/components/editor/EditorToolbar";
import { CitationExtension } from "@/components/editor/extensions/CitationExtension";
import { SourcePicker } from "@/components/editor/SourcePicker";
import { GraphPanel } from "@/components/graph/GraphPanel";
import { LinkToModal } from "@/components/graph/LinkToModal";
import { ObjectPicker } from "@/components/graph/ObjectPicker";
import { createEdge } from "@/lib/api";
import { PageTitle } from "./PageTitle";
import { useAutoSave } from "@/lib/hooks/useAutoSave";
import { SaveStatusChip } from "@/components/ui/SaveStatusChip";
import { toast } from "@/components/ui/Toast";
import { EditorBubbleMenu } from "@/components/editor/BubbleMenu";
import { SlashMenu } from "@/components/editor/SlashMenu";
import { SlashMenuExtension } from "@/components/editor/extensions/SlashMenuExtension";
import TaskList from "@tiptap/extension-task-list";
import TaskItem from "@tiptap/extension-task-item";
import { Table } from "@tiptap/extension-table";
import { TableRow } from "@tiptap/extension-table-row";
import { TableCell } from "@tiptap/extension-table-cell";
import { TableHeader } from "@tiptap/extension-table-header";
import HorizontalRule from "@tiptap/extension-horizontal-rule";

const useV2Editor = process.env.NEXT_PUBLIC_UX_EDITOR_V2 === "1";

type JsonValue = string | number | boolean | null | JsonObject | JsonValue[];
type JsonObject = { [key: string]: JsonValue };

function extractCitationSourceIds(node: JsonValue): string[] {
  if (!node || typeof node !== "object") return [];
  if (Array.isArray(node)) return node.flatMap((child) => extractCitationSourceIds(child));

  const attrs = node.attrs;
  const sourceId =
    node.type === "citation" &&
    attrs &&
    typeof attrs === "object" &&
    !Array.isArray(attrs) &&
    typeof attrs.sourceId === "string"
      ? attrs.sourceId
      : null;

  const childIds = Array.isArray(node.content) ? extractCitationSourceIds(node.content) : [];
  return sourceId ? [sourceId, ...childIds] : childIds;
}

interface PageViewProps {
  pageId: string;
  initialTitle: string;
  initialContent: Record<string, unknown>;
}

export function PageView({ pageId, initialTitle, initialContent }: PageViewProps) {
  const [title, setTitle] = useState(initialTitle);
  const [wordCount, setWordCount] = useState(0);
  const [isSourcePickerOpen, setIsSourcePickerOpen] = useState(false);
  const [isObjectPickerOpen, setIsObjectPickerOpen] = useState(false);
  const [linkTarget, setLinkTarget] = useState<{
    id: string;
    kind: string;
    title: string;
  } | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const contentRef = useRef<Record<string, unknown>>(initialContent);
  const textRef = useRef<string>("");

  const saveData = {
    title,
    content_json: contentRef.current,
    content_text: textRef.current,
  };

  const createCitationEdges = useCallback(async () => {
    if (!pageId) return;

    const sourceIds = Array.from(
      new Set(extractCitationSourceIds(contentRef.current as JsonObject))
    );
    await Promise.all(
      sourceIds.map(async (sourceId) => {
        try {
          await createEdge({ source_id: pageId, target_id: sourceId, kind: "cites" });
        } catch {
          // Citation edge writes should not block page auto-save.
        }
      })
    );
  }, [pageId]);

  const { status } = useAutoSave(pageId, saveData, 800, createCitationEdges);

  const prevStatusRef = useRef(status);
  useEffect(() => {
    if (status === "error" && prevStatusRef.current !== "error") {
      toast.error("Auto-save failed");
    }
    prevStatusRef.current = status;
  }, [status]);

  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({ placeholder: "Write something..." }),
      Typography,
      Link.configure({ openOnClick: false }),
      Image,
      CitationExtension,
      ...(useV2Editor
        ? [TaskList, TaskItem.configure({ nested: true }), Table.configure({ resizable: true }), TableRow, TableCell, TableHeader, HorizontalRule, SlashMenuExtension]
        : []),
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

  return (
    <div className="flex flex-col h-full">
      {useV2Editor && editor && <EditorBubbleMenu editor={editor} />}
      {useV2Editor && editor && <SlashMenu editor={editor} />}
      <EditorToolbar
        editor={editor}
        onCite={() => setIsSourcePickerOpen(true)}
        onLinkTo={() => setIsObjectPickerOpen(true)}
      />
      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 overflow-y-auto p-8 max-w-3xl mx-auto w-full">
          <PageTitle initialTitle={initialTitle} onTitleChange={handleTitleChange} />
          <EditorContent editor={editor} />
        </div>
        <div className="w-72 border-l border-gray-800 overflow-y-auto flex-shrink-0">
          <GraphPanel objectId={pageId} refreshKey={refreshKey} />
        </div>
      </div>
      <div className="flex items-center justify-between px-8 py-2 border-t border-gray-800 text-xs text-gray-500">
        <span>{wordCount} words</span>
        <SaveStatusChip status={status} />
      </div>
      <SourcePicker
        isOpen={isSourcePickerOpen}
        onClose={() => setIsSourcePickerOpen(false)}
        onSelect={(id, sourceTitle) => {
          editor?.chain().focus().insertCitation(id, sourceTitle).run();
        }}
      />
      <ObjectPicker
        isOpen={isObjectPickerOpen}
        onClose={() => setIsObjectPickerOpen(false)}
        excludeId={pageId}
        onSelect={(id, kind, objectTitle) => {
          setLinkTarget({ id, kind, title: objectTitle });
        }}
      />
      {linkTarget ? (
        <LinkToModal
          isOpen={Boolean(linkTarget)}
          onClose={() => setLinkTarget(null)}
          sourceId={pageId}
          targetId={linkTarget.id}
          targetKind={linkTarget.kind}
          targetTitle={linkTarget.title}
          sourceTitle={title}
          onLinked={() => setRefreshKey((current) => current + 1)}
        />
      ) : null}
    </div>
  );
}
