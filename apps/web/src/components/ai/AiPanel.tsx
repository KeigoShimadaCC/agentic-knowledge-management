"use client";

import { useEffect, useState } from "react";
import {
  aiAnswer,
  aiExtractClaims,
  aiExtractTasks,
  aiSuggestLinks,
  aiSummarize,
  createEdge,
  enrichPage,
  getObject,
} from "@/lib/api";
import { formatDistanceToNow } from "date-fns";
import { toast } from "@/components/ui/Toast";
import type {
  AiAnswerResponse,
  EnrichPageResponse,
  ExtractResponse,
  LinkSuggestion,
  SuggestLinksResponse,
  SummarizeResponse,
  WebCitation,
} from "@/types";
import { useWorkspaceLite } from "@/components/workspace/WorkspaceLiteProvider";

interface AiPanelProps {
  objectId: string;
  onEdgeCreated?: () => void;
}

type AiScope = "all" | "pane" | "workspace";

type ActionState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "done"; data: T }
  | { status: "error"; message: string };

function useAiAction<T>() {
  const [state, setState] = useState<ActionState<T>>({ status: "idle" });

  async function run(fn: () => Promise<T>) {
    setState({ status: "loading" });
    try {
      const data = await fn();
      setState({ status: "done", data });
    } catch (e) {
      setState({ status: "error", message: e instanceof Error ? e.message : "Unknown error" });
    }
  }

  function reset() {
    setState({ status: "idle" });
  }

  return { state, run, reset };
}

export function AiPanel({ objectId, onEdgeCreated }: AiPanelProps) {
  const [aiProcessedAt, setAiProcessedAt] = useState<string | null>(null);

  useEffect(() => {
    if (!objectId) return;
    getObject(objectId)
      .then((obj) => {
        const ts = obj.metadata?.ai_processed_at;
        if (typeof ts === "string") setAiProcessedAt(ts);
      })
      .catch(() => {});
  }, [objectId]);

  const summarize = useAiAction<SummarizeResponse>();
  const claims = useAiAction<ExtractResponse>();
  const tasks = useAiAction<ExtractResponse>();
  const links = useAiAction<SuggestLinksResponse>();
  const answer = useAiAction<AiAnswerResponse>();
  const enrich = useAiAction<EnrichPageResponse>();
  const [question, setQuestion] = useState("");
  const [useWebSearch, setUseWebSearch] = useState(false);
  const [enrichQuery, setEnrichQuery] = useState("");
  const [creatingEdge, setCreatingEdge] = useState<string | null>(null);
  const [aiScope, setAiScope] = useState<AiScope>("all");
  const { panes } = useWorkspaceLite();

  function getScopeObjectIds(): string[] | undefined {
    if (aiScope === "all") return undefined;
    if (aiScope === "pane") return objectId ? [objectId] : undefined;
    // workspace = all panes with objectId
    const ids = panes.flatMap((p) => (p.objectId ? [p.objectId] : []));
    return ids.length > 0 ? ids : undefined;
  }

  async function handleCreateLink(suggestion: LinkSuggestion) {
    setCreatingEdge(suggestion.target_id);
    try {
      await createEdge({
        source_id: objectId,
        target_id: suggestion.target_id,
        kind: "related_to",
      });
      onEdgeCreated?.();
    } catch (err) {
      toast.error("Couldn't create link", {
        description: err instanceof Error ? err.message : undefined,
      });
    } finally {
      setCreatingEdge(null);
    }
  }

  return (
    <div data-testid="ai-panel" className="space-y-4 p-3">
      {aiProcessedAt && (
        <p className="text-[10px] text-gray-600">
          Auto-processed {formatDistanceToNow(new Date(aiProcessedAt), { addSuffix: true })}
        </p>
      )}
      {/* Summarize */}
      <section>
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-gray-400">Summarize</span>
          {summarize.state.status === "done" && (
            <button
              type="button"
              onClick={() => { summarize.reset(); summarize.run(() => aiSummarize(objectId, true)); }}
              className="text-xs text-gray-500 hover:text-gray-300"
            >
              Re-run
            </button>
          )}
        </div>
        {summarize.state.status === "idle" && (
          <button
            type="button"
            onClick={() => summarize.run(() => aiSummarize(objectId))}
            className="mt-1 w-full rounded bg-gray-800 px-2 py-1.5 text-xs text-gray-300 hover:bg-gray-700"
          >
            Summarize
          </button>
        )}
        {summarize.state.status === "loading" && (
          <p className="mt-1 text-xs text-gray-500">Summarizing…</p>
        )}
        {summarize.state.status === "done" && (
          <p className="mt-1 text-xs leading-relaxed text-gray-300">
            {summarize.state.data.summary}
          </p>
        )}
        {summarize.state.status === "error" && (
          <p className="mt-1 text-xs text-red-400">{summarize.state.message}</p>
        )}
      </section>

      {/* Extract Claims */}
      <section>
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-gray-400">Extract Claims</span>
        </div>
        {claims.state.status === "idle" && (
          <button
            type="button"
            onClick={() => claims.run(() => aiExtractClaims(objectId))}
            className="mt-1 w-full rounded bg-gray-800 px-2 py-1.5 text-xs text-gray-300 hover:bg-gray-700"
          >
            Extract Claims
          </button>
        )}
        {claims.state.status === "loading" && (
          <p className="mt-1 text-xs text-gray-500">Extracting…</p>
        )}
        {claims.state.status === "done" && (
          <div className="mt-1">
            {claims.state.data.items.length === 0 ? (
              <p className="text-xs text-gray-500">No claims found.</p>
            ) : (
              <ul className="space-y-0.5">
                {claims.state.data.items.map((item) => (
                  <li key={item.id} className="truncate text-xs text-gray-300">
                    · {item.title}
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-0.5 text-xs text-gray-600">
              {claims.state.data.items.length} claim{claims.state.data.items.length !== 1 ? "s" : ""} created
            </p>
          </div>
        )}
        {claims.state.status === "error" && (
          <p className="mt-1 text-xs text-red-400">{claims.state.message}</p>
        )}
      </section>

      {/* Extract Tasks */}
      <section>
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-gray-400">Extract Tasks</span>
        </div>
        {tasks.state.status === "idle" && (
          <button
            type="button"
            onClick={() => tasks.run(() => aiExtractTasks(objectId))}
            className="mt-1 w-full rounded bg-gray-800 px-2 py-1.5 text-xs text-gray-300 hover:bg-gray-700"
          >
            Extract Tasks
          </button>
        )}
        {tasks.state.status === "loading" && (
          <p className="mt-1 text-xs text-gray-500">Extracting…</p>
        )}
        {tasks.state.status === "done" && (
          <div className="mt-1">
            {tasks.state.data.items.length === 0 ? (
              <p className="text-xs text-gray-500">No tasks found.</p>
            ) : (
              <ul className="space-y-0.5">
                {tasks.state.data.items.map((item) => (
                  <li key={item.id} className="truncate text-xs text-gray-300">
                    · {item.title}
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-0.5 text-xs text-gray-600">
              {tasks.state.data.items.length} task{tasks.state.data.items.length !== 1 ? "s" : ""} created
            </p>
          </div>
        )}
        {tasks.state.status === "error" && (
          <p className="mt-1 text-xs text-red-400">{tasks.state.message}</p>
        )}
      </section>

      {/* Suggest Links */}
      <section>
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-gray-400">Suggest Links</span>
          {links.state.status === "done" && (
            <button
              type="button"
              onClick={() => links.run(() => aiSuggestLinks(objectId))}
              className="text-xs text-gray-500 hover:text-gray-300"
            >
              Re-run
            </button>
          )}
        </div>
        {links.state.status === "idle" && (
          <button
            type="button"
            onClick={() => links.run(() => aiSuggestLinks(objectId))}
            className="mt-1 w-full rounded bg-gray-800 px-2 py-1.5 text-xs text-gray-300 hover:bg-gray-700"
          >
            Suggest Links
          </button>
        )}
        {links.state.status === "loading" && (
          <p className="mt-1 text-xs text-gray-500">Searching…</p>
        )}
        {links.state.status === "done" && (
          <div className="mt-1 space-y-2">
            {links.state.data.suggestions.length === 0 ? (
              <p className="text-xs text-gray-500">No suggestions found.</p>
            ) : (
              links.state.data.suggestions.map((s) => (
                <div key={s.target_id} className="rounded border border-gray-800 p-2">
                  <div className="flex items-center justify-between gap-1">
                    <span className="truncate text-xs font-medium text-gray-200">
                      {s.target_title}
                    </span>
                    <button
                      type="button"
                      disabled={creatingEdge === s.target_id}
                      onClick={() => handleCreateLink(s)}
                      className="shrink-0 rounded bg-blue-900 px-1.5 py-0.5 text-xs text-blue-200 hover:bg-blue-800 disabled:opacity-50"
                    >
                      {creatingEdge === s.target_id ? "…" : "Link"}
                    </button>
                  </div>
                  <p className="mt-0.5 text-xs text-gray-500 line-clamp-2">{s.reason}</p>
                </div>
              ))
            )}
          </div>
        )}
        {links.state.status === "error" && (
          <p className="mt-1 text-xs text-red-400">{links.state.message}</p>
        )}
      </section>

      {/* Ask KB */}
      <section>
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-gray-400">Ask KB</span>
          {panes.length > 1 && (
            <select
              value={aiScope}
              onChange={(e) => setAiScope(e.target.value as AiScope)}
              className="rounded border border-gray-700 bg-gray-900 px-1 py-0.5 text-[10px] text-gray-400 focus:outline-none"
            >
              <option value="all">All knowledge</option>
              <option value="pane">This object</option>
              <option value="workspace">Open panes</option>
            </select>
          )}
        </div>
        <div className="mt-1 flex gap-1">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && question.trim()) {
                answer.run(() =>
                  aiAnswer(question.trim(), undefined, getScopeObjectIds(), useWebSearch)
                );
              }
            }}
            placeholder="Ask a question…"
            className="min-w-0 flex-1 rounded border border-gray-700 bg-gray-900 px-2 py-1 text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-700"
          />
          <button
            type="button"
            disabled={!question.trim() || answer.state.status === "loading"}
            onClick={() =>
              answer.run(() =>
                aiAnswer(question.trim(), undefined, getScopeObjectIds(), useWebSearch)
              )
            }
            className="shrink-0 rounded bg-gray-800 px-2 py-1 text-xs text-gray-300 hover:bg-gray-700 disabled:opacity-50"
          >
            Ask
          </button>
        </div>
        <label className="mt-2 flex cursor-pointer items-center gap-2 text-xs text-gray-400">
          <input
            type="checkbox"
            checked={useWebSearch}
            onChange={(e) => setUseWebSearch(e.target.checked)}
            className="rounded border-gray-600"
          />
          Search web if KB has no match
        </label>
        {answer.state.status === "loading" && (
          <p className="mt-1 text-xs text-gray-500">Thinking…</p>
        )}
        {answer.state.status === "done" && (
          <div className="mt-2">
            <p className="text-xs leading-relaxed text-gray-300">
              {answer.state.data.answer}
            </p>
            {answer.state.data.citations.length > 0 && (
              <div className="mt-1 space-y-0.5">
                <p className="text-xs text-gray-600">Sources:</p>
                {answer.state.data.citations.map((c) => (
                  <p key={c.object_id} className="truncate text-xs text-gray-500">
                    · {c.title}
                  </p>
                ))}
              </div>
            )}
            {answer.state.data.web_citations.length > 0 && (
              <div className="mt-2 space-y-1">
                <p className="text-xs text-gray-600">Web sources:</p>
                {answer.state.data.web_citations.map((citation: WebCitation) => (
                  <div key={citation.url} className="rounded border border-gray-800 p-2">
                    <a
                      href={citation.url}
                      target="_blank"
                      rel="noreferrer"
                      className="block truncate text-xs font-medium text-blue-300 hover:text-blue-200"
                    >
                      {citation.title}
                    </a>
                    {citation.snippet && (
                      <p className="mt-0.5 line-clamp-2 text-xs text-gray-500">
                        {citation.snippet}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
            {answer.state.data.warning === "web_search_unavailable" && (
              <p className="mt-2 rounded border border-yellow-900/60 bg-yellow-950/40 px-2 py-1 text-xs text-yellow-300">
                Web search is unavailable.
              </p>
            )}
          </div>
        )}
        {answer.state.status === "error" && (
          <p className="mt-1 text-xs text-red-400">{answer.state.message}</p>
        )}
      </section>

      {objectId && (
        <section>
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400">Enrich with Docs</span>
          </div>
          <div className="mt-1 flex gap-1">
            <input
              type="text"
              value={enrichQuery}
              onChange={(e) => setEnrichQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && enrichQuery.trim()) {
                  enrich.run(() => enrichPage(objectId, enrichQuery.trim()));
                }
              }}
              placeholder="Library or topic…"
              className="min-w-0 flex-1 rounded border border-gray-700 bg-gray-900 px-2 py-1 text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-700"
            />
            <button
              type="button"
              disabled={!enrichQuery.trim() || enrich.state.status === "loading"}
              onClick={() => enrich.run(() => enrichPage(objectId, enrichQuery.trim()))}
              className="shrink-0 rounded bg-gray-800 px-2 py-1 text-xs text-gray-300 hover:bg-gray-700 disabled:opacity-50"
            >
              Fetch & Link Docs
            </button>
          </div>
          {enrich.state.status === "loading" && (
            <p className="mt-1 text-xs text-gray-500">Fetching docs…</p>
          )}
          {enrich.state.status === "done" && (
            <p className="mt-1 text-xs text-gray-400">
              Linked {enrich.state.data.sources_created.length} source
              {enrich.state.data.sources_created.length !== 1 ? "s" : ""}.
            </p>
          )}
          {enrich.state.status === "error" && (
            <p className="mt-1 text-xs text-red-400">{enrich.state.message}</p>
          )}
        </section>
      )}
    </div>
  );
}
