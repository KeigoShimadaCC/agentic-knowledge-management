"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { clsx } from "clsx";
import { getRawChatUrl } from "@/lib/api";
import { useChat } from "@/lib/hooks/useChats";

const ROLE_CLASSES: Record<string, string> = {
  user: "border-blue-900 bg-blue-950/40 text-blue-100",
  assistant: "border-green-900 bg-green-950/35 text-green-100",
  system: "border-amber-900 bg-amber-950/35 text-amber-100",
  tool: "border-cyan-900 bg-cyan-950/35 text-cyan-100",
  unknown: "border-gray-800 bg-gray-900 text-gray-200",
};

export default function ChatDetailPage({ params }: { params: { id: string } }) {
  const { chat, isLoading } = useChat(params.id);
  const [showRaw, setShowRaw] = useState(false);
  const [raw, setRaw] = useState("");

  useEffect(() => {
    if (!showRaw || raw) return;
    fetch(getRawChatUrl(params.id), { credentials: "include" })
      .then((res) => {
        if (!res.ok) throw new Error(res.statusText);
        return res.text();
      })
      .then(setRaw)
      .catch(() => setRaw("Could not load raw transcript."));
  }, [params.id, raw, showRaw]);

  if (isLoading) {
    return <div className="p-8 text-gray-400">Loading...</div>;
  }

  if (!chat) {
    return (
      <div className="p-8">
        <Link href="/app/chats" className="text-sm text-gray-400 hover:text-white">
          Back to Chats
        </Link>
        <div className="mt-8 text-gray-500">Chat not found</div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <Link href="/app/chats" className="text-sm text-gray-400 hover:text-white">
        Back to Chats
      </Link>

      <div className="mt-6 mb-6 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="truncate text-2xl font-bold text-white">{chat.title || "(untitled)"}</h1>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-gray-400">
            <span className="rounded border border-violet-900 bg-violet-950 px-2 py-1 uppercase text-violet-200">
              {chat.provider}
            </span>
            <span>{chat.turn_count} turns</span>
            <span>{chat.raw_format.toUpperCase()}</span>
            {chat.source_filename && <span>{chat.source_filename}</span>}
          </div>
        </div>
        <button
          type="button"
          onClick={() => setShowRaw((value) => !value)}
          className="rounded-md border border-gray-700 px-3 py-2 text-sm text-gray-200 hover:bg-gray-800"
        >
          {showRaw ? "Hide Raw" : "Show Raw"}
        </button>
      </div>

      {showRaw && (
        <pre className="mb-6 max-h-96 overflow-auto rounded-lg border border-gray-800 bg-gray-950 p-4 text-sm text-gray-300">
          {raw || "Loading raw transcript..."}
        </pre>
      )}

      <div className="space-y-3">
        {chat.parsed_turns.map((turn) => (
          <article
            key={turn.turn_index}
            className={clsx(
              "rounded-lg border p-4",
              ROLE_CLASSES[turn.role] ?? ROLE_CLASSES.unknown
            )}
          >
            <div className="mb-2 flex items-center justify-between gap-3 text-xs uppercase tracking-wide text-gray-400">
              <span>{turn.author || turn.role}</span>
              {turn.created_at && <span>{new Date(turn.created_at).toLocaleString()}</span>}
            </div>
            <div className="whitespace-pre-wrap text-sm leading-6">{turn.content}</div>
          </article>
        ))}
      </div>
    </div>
  );
}
