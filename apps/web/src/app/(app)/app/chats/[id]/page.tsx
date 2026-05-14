"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { clsx } from "clsx";
import {
  applyStructuredChatSummary,
  generateStructuredChatSummary,
  getRawChatUrl,
} from "@/lib/api";
import { useChat } from "@/lib/hooks/useChats";
import type { ObjectOut, StructuredChatSummary, StructuredTurnItem } from "@/types";

const ROLE_CLASSES: Record<string, string> = {
  user: "border-blue-900 bg-blue-950/40 text-blue-100",
  assistant: "border-green-900 bg-green-950/35 text-green-100",
  system: "border-amber-900 bg-amber-950/35 text-amber-100",
  tool: "border-cyan-900 bg-cyan-950/35 text-cyan-100",
  unknown: "border-gray-800 bg-gray-900 text-gray-200",
};

export default function ChatDetailPage({ params }: { params: { id: string } }) {
  const { chat, isLoading, mutate } = useChat(params.id);
  const [showRaw, setShowRaw] = useState(false);
  const [raw, setRaw] = useState("");
  const [preview, setPreview] = useState<StructuredChatSummary | null>(null);
  const [linkedObjects, setLinkedObjects] = useState<ObjectOut[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [error, setError] = useState("");

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

  const summary = preview ?? chat.structured_summary;
  const canApply = Boolean(preview || chat.structured_summary_status === "previewed");

  async function handleGenerate() {
    setError("");
    setIsGenerating(true);
    try {
      const result = await generateStructuredChatSummary(params.id);
      setPreview(result.structured_summary);
      await mutate();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleApply() {
    setError("");
    setIsApplying(true);
    try {
      const result = await applyStructuredChatSummary(params.id, preview ?? undefined);
      setPreview(null);
      setLinkedObjects([...result.created_objects, ...result.reused_objects]);
      await mutate(result.chat, { revalidate: false });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setIsApplying(false);
    }
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

      <section className="mb-6 rounded-lg border border-gray-800 bg-gray-950 p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-white">Structured Summary</h2>
            <p className="mt-1 text-sm text-gray-400">
              Status: {chat.structured_summary_status}
              {chat.structured_summary_agent_run_id
                ? ` · Agent run ${chat.structured_summary_agent_run_id}`
                : ""}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleGenerate}
              disabled={isGenerating || isApplying}
              className="rounded-md border border-blue-800 px-3 py-2 text-sm text-blue-100 hover:bg-blue-950 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isGenerating ? "Generating..." : "Generate"}
            </button>
            <button
              type="button"
              onClick={handleApply}
              disabled={!canApply || isGenerating || isApplying}
              className="rounded-md border border-green-800 px-3 py-2 text-sm text-green-100 hover:bg-green-950 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isApplying ? "Applying..." : "Apply"}
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-4 rounded-md border border-red-900 bg-red-950/40 px-3 py-2 text-sm text-red-200">
            {error === "ai_disabled"
              ? "AI is disabled. Add an OpenAI API key before generating summaries."
              : error}
          </div>
        )}

        {summary ? (
          <StructuredSummaryView summary={summary} isPreview={Boolean(preview)} />
        ) : (
          <div className="mt-5 text-sm text-gray-500">
            Generate a structured summary to extract decisions, questions, tasks, claims, and
            concepts from this chat.
          </div>
        )}

        {linkedObjects.length > 0 && (
          <div className="mt-5 border-t border-gray-800 pt-4">
            <h3 className="text-sm font-semibold uppercase text-gray-400">Linked Objects</h3>
            <div className="mt-3 grid gap-2">
              {linkedObjects.map((object) => (
                <Link
                  key={object.id}
                  href="/app"
                  className="rounded-md border border-gray-800 px-3 py-2 text-sm text-gray-200 hover:bg-gray-900"
                >
                  <span className="mr-2 uppercase text-gray-500">{object.kind}</span>
                  {object.title}
                </Link>
              ))}
            </div>
          </div>
        )}
      </section>

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

function StructuredSummaryView({
  summary,
  isPreview,
}: {
  summary: StructuredChatSummary;
  isPreview: boolean;
}) {
  return (
    <div className="mt-5 space-y-5">
      {isPreview && (
        <div className="rounded-md border border-amber-900 bg-amber-950/30 px-3 py-2 text-sm text-amber-100">
          Preview only. Apply to store extracted objects and graph links.
        </div>
      )}
      <div>
        <h3 className="text-base font-semibold text-white">{summary.title}</h3>
        <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-gray-300">{summary.summary}</p>
        {summary.topics.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {summary.topics.map((topic) => (
              <span key={topic} className="rounded border border-gray-700 px-2 py-1 text-xs text-gray-300">
                {topic}
              </span>
            ))}
          </div>
        )}
      </div>
      <SummarySection title="Key Decisions" items={summary.key_decisions} textKey="decision" />
      <SummarySection title="Open Questions" items={summary.open_questions} textKey="question" />
      <SummarySection title="Action Items" items={summary.action_items} textKey="task" />
      <SummarySection title="Claims" items={summary.claims} textKey="claim" />
      <SummarySection title="Concepts" items={summary.concepts} textKey="name" />
      {summary.warnings.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold uppercase text-gray-400">Warnings</h3>
          <ul className="mt-2 space-y-1 text-sm text-amber-100">
            {summary.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function SummarySection<T extends StructuredTurnItem & Record<string, unknown>>({
  title,
  items,
  textKey,
}: {
  title: string;
  items: T[];
  textKey: keyof T;
}) {
  if (items.length === 0) return null;
  return (
    <div>
      <h3 className="text-sm font-semibold uppercase text-gray-400">{title}</h3>
      <div className="mt-2 grid gap-2">
        {items.map((item, index) => (
          <div key={`${title}-${index}`} className="rounded-md border border-gray-800 p-3">
            <div className="text-sm text-gray-200">{String(item[textKey])}</div>
            <div className="mt-2 text-xs text-gray-500">
              Turns {item.turn_refs.join(", ") || "none"} · {item.confidence}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function errorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  return "Request failed";
}
