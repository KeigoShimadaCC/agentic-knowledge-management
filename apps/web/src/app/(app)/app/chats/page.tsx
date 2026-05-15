"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { formatDistanceToNow } from "date-fns";
import { Plus, Upload } from "lucide-react";
import { clsx } from "clsx";
import { importChatContent, importChatFile } from "@/lib/api";
import { useChats } from "@/lib/hooks/useChats";
import { toast } from "@/components/ui/Toast";
import { ListPage } from "@/components/lists/ListPage";
import { ListToolbar, type SortKey } from "@/components/lists/ListToolbar";
import type { ChatOut, ChatProvider, ChatRawFormat } from "@/types";

const PROVIDERS: { label: string; value: ChatProvider }[] = [
  { label: "Auto", value: "auto" },
  { label: "ChatGPT", value: "chatgpt" },
  { label: "Claude", value: "claude" },
  { label: "Markdown", value: "markdown" },
  { label: "Plain Text", value: "plain_text" },
];

type ImportTab = "file" | "paste";

function chatExcerpt(chat: ChatOut): string {
  return chat.content_text.replace(/\s+/g, " ").trim().slice(0, 180);
}

function sortChats(chats: ChatOut[], sort: SortKey): ChatOut[] {
  const arr = [...chats];
  if (sort === "newest") return arr.sort((a, b) => new Date(b.imported_at).getTime() - new Date(a.imported_at).getTime());
  if (sort === "oldest") return arr.sort((a, b) => new Date(a.imported_at).getTime() - new Date(b.imported_at).getTime());
  return arr.sort((a, b) => (a.title ?? "").localeCompare(b.title ?? ""));
}

function ImportChatModal({
  isOpen,
  onClose,
  onImported,
}: {
  isOpen: boolean;
  onClose: () => void;
  onImported: (result: ChatOut[]) => void;
}) {
  const [tab, setTab] = useState<ImportTab>("file");
  const [provider, setProvider] = useState<ChatProvider>("auto");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [rawFormat, setRawFormat] = useState<ChatRawFormat>("txt");
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  async function submitPaste(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsImporting(true);
    try {
      const result = await importChatContent({ content, provider, title: title || undefined, raw_format: rawFormat });
      setContent("");
      setTitle("");
      onImported(result.imported);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to import transcript");
    } finally {
      setIsImporting(false);
    }
  }

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setError(null);
    setIsImporting(true);
    try {
      const result = await importChatFile({ file, provider, title: title || undefined });
      setTitle("");
      onImported(result.imported);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to import file");
    } finally {
      setIsImporting(false);
      event.target.value = "";
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="w-full max-w-2xl rounded-lg border border-gray-800 bg-gray-900 shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-800 p-4">
          <h2 className="text-lg font-semibold text-white">Import Chat</h2>
          <button type="button" onClick={onClose} className="rounded-md px-2 py-1 text-sm text-gray-400 hover:bg-gray-800 hover:text-white">Close</button>
        </div>
        <div className="grid grid-cols-2 gap-2 border-b border-gray-800 p-2">
          {(["file", "paste"] as ImportTab[]).map((value) => (
            <button key={value} type="button" onClick={() => setTab(value)}
              className={clsx("rounded-md px-3 py-2 text-sm font-medium transition-colors", tab === value ? "bg-gray-700 text-white" : "text-gray-400 hover:bg-gray-800 hover:text-white")}
            >
              {value === "file" ? "Upload File" : "Paste Transcript"}
            </button>
          ))}
        </div>
        <div className="space-y-4 p-4">
          <div className="grid gap-3 md:grid-cols-2">
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-gray-300">Provider</span>
              <select value={provider} onChange={(e) => setProvider(e.target.value as ChatProvider)}
                className="w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-white outline-none focus:border-gray-500">
                {PROVIDERS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-gray-300">Title</span>
              <input value={title} onChange={(e) => setTitle(e.target.value)}
                className="w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-white outline-none focus:border-gray-500" placeholder="Optional" />
            </label>
          </div>
          {tab === "paste" ? (
            <form onSubmit={submitPaste} className="space-y-4">
              <label className="block">
                <span className="mb-1 block text-sm font-medium text-gray-300">Format</span>
                <select value={rawFormat} onChange={(e) => setRawFormat(e.target.value as ChatRawFormat)}
                  className="w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-white outline-none focus:border-gray-500">
                  <option value="txt">Plain Text</option>
                  <option value="md">Markdown</option>
                  <option value="json">JSON</option>
                </select>
              </label>
              <textarea value={content} onChange={(e) => setContent(e.target.value)} required rows={12}
                className="w-full resize-y rounded-md border border-gray-700 bg-gray-950 px-3 py-2 font-mono text-sm text-white outline-none focus:border-gray-500" />
              {error && <p className="text-sm text-red-300">{error}</p>}
              <button type="submit" disabled={isImporting}
                className="w-full rounded-md bg-white px-3 py-2 text-sm font-medium text-gray-950 transition-colors hover:bg-gray-200 disabled:opacity-60">
                {isImporting ? "Importing..." : "Import Transcript"}
              </button>
            </form>
          ) : (
            <div className="space-y-4">
              <label className="flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-gray-700 bg-gray-950 px-4 py-10 text-center hover:border-gray-500">
                <Upload className="mb-3 h-6 w-6 text-gray-400" />
                <span className="text-sm font-medium text-white">Choose .json, .md, .markdown, or .txt</span>
                <input type="file" accept=".json,.md,.markdown,.txt,application/json,text/markdown,text/plain"
                  onChange={handleFileChange} disabled={isImporting} className="sr-only" />
              </label>
              {error && <p className="text-sm text-red-300">{error}</p>}
              {isImporting && <p className="text-sm text-gray-400">Importing...</p>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ChatsPage() {
  const router = useRouter();
  const { chats, isLoading, mutate } = useChats();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<SortKey>("newest");

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    const matched = q ? chats.filter((c) => (c.title ?? "").toLowerCase().includes(q)) : chats;
    return sortChats(matched, sort);
  }, [chats, search, sort]);

  function handleImported(imported: ChatOut[]) {
    void mutate();
    const count = imported.length;
    toast.success(count === 1 ? "Chat imported" : `${count} chats imported`);
    const onlyChat = imported[0];
    if (imported.length === 1 && onlyChat) {
      router.push(`/app/chats/${onlyChat.id}`);
    }
  }

  return (
    <ListPage
      title="Chats"
      loading={isLoading}
      empty={!isLoading && filtered.length === 0}
      emptyTitle={search ? "No chats match" : "No chats yet"}
      emptyDescription={search ? "Try a different search" : "Import a ChatGPT, Claude, Markdown, or text transcript"}
      actions={
        <button type="button" onClick={() => setIsModalOpen(true)}
          className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-white text-gray-950 transition-colors hover:bg-gray-200"
          aria-label="Import chat">
          <Plus size={18} />
        </button>
      }
      toolbar={
        <ListToolbar
          search={search}
          onSearch={setSearch}
          sort={sort}
          onSort={setSort}
          searchPlaceholder="Filter chats…"
        />
      }
    >
      <div className="space-y-2">
        {filtered.map((chat) => (
          <Link key={chat.id} href={`/app/chats/${chat.id}`}
            className="block rounded-lg border border-gray-800 bg-gray-900 p-4 transition-colors hover:border-gray-600 hover:bg-gray-800">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0 flex-1">
                <h2 className="truncate text-sm font-medium text-white">{chat.title || "(untitled)"}</h2>
                <p className="mt-2 line-clamp-2 text-xs text-gray-400">{chatExcerpt(chat)}</p>
              </div>
              <div className="shrink-0 text-right text-xs text-gray-500">
                <div className="uppercase text-violet-300">{chat.provider}</div>
                <div className="mt-1">{chat.turn_count} turns</div>
                <div className="mt-1">{formatDistanceToNow(new Date(chat.imported_at), { addSuffix: true })}</div>
              </div>
            </div>
          </Link>
        ))}
      </div>
      <ImportChatModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} onImported={handleImported} />
    </ListPage>
  );
}
