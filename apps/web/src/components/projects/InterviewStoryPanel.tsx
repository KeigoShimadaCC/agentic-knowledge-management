"use client";

import { useState } from "react";
import { Copy, Sparkles, Trash2 } from "lucide-react";

import {
  deleteInterviewStory,
  generateInterviewStory,
  saveInterviewStory,
} from "@/lib/api";
import { toast } from "@/components/ui/Toast";
import { useInterviewStories } from "@/lib/hooks/useProjects";
import { ApiError, type GenerateInterviewStoryResponse, type ProjectOut } from "@/types";

interface InterviewStoryPanelProps {
  projectId: string;
  project: ProjectOut;
}

type QuestionType = "behavioral" | "technical" | "leadership";
type Filter = "all" | QuestionType;

const QUESTION_TYPES: QuestionType[] = ["behavioral", "technical", "leadership"];
const FILTERS: Filter[] = ["all", ...QUESTION_TYPES];

function storyToMarkdown(story: {
  situation: string;
  task: string;
  action: string;
  result: string;
}): string {
  return [
    `**Situation:** ${story.situation}`,
    `**Task:** ${story.task}`,
    `**Action:** ${story.action}`,
    `**Result:** ${story.result}`,
  ].join("\n\n");
}

export function InterviewStoryPanel({ projectId, project }: InterviewStoryPanelProps) {
  const [questionType, setQuestionType] = useState<QuestionType>("behavioral");
  const [targetRole, setTargetRole] = useState(project.role ?? "");
  const [maxWords, setMaxWords] = useState(400);
  const [filter, setFilter] = useState<Filter>("all");
  const [preview, setPreview] = useState<GenerateInterviewStoryResponse | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [aiDisabled, setAiDisabled] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const { stories, mutate } = useInterviewStories(
    projectId,
    filter === "all" ? undefined : filter
  );

  async function handleGenerate() {
    setIsGenerating(true);
    setAiDisabled(false);
    try {
      const result = await generateInterviewStory({
        project_id: projectId,
        question_type: questionType,
        target_role: targetRole || undefined,
        max_words: maxWords,
      });
      setPreview(result);
    } catch (err) {
      if (err instanceof ApiError && err.status === 503) {
        setAiDisabled(true);
      } else {
        toast.error("Could not generate story", {
          description: err instanceof Error ? err.message : undefined,
        });
      }
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleSave() {
    if (!preview) return;
    try {
      await saveInterviewStory(projectId, {
        question_type: questionType,
        target_role: targetRole || undefined,
        max_words: maxWords,
        word_count: preview.word_count,
        story: preview.story,
        agent_run_id: preview.agent_run_id,
      });
      await mutate();
      setPreview(null);
      toast.success("Story saved");
    } catch (err) {
      toast.error("Could not save story", {
        description: err instanceof Error ? err.message : undefined,
      });
    }
  }

  async function handleDelete(id: string) {
    await deleteInterviewStory(id);
    await mutate();
    toast.success("Story deleted");
  }

  return (
    <div className="space-y-5">
      {aiDisabled && (
        <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
          AI disabled. Set OPENAI_API_KEY or ANTHROPIC_API_KEY to use this feature.
        </div>
      )}

      <section className="rounded-lg border border-gray-800 bg-gray-900 p-4">
        <div className="grid gap-3 md:grid-cols-[auto_1fr_auto_auto]">
          <select
            value={questionType}
            onChange={(e) => setQuestionType(e.target.value as QuestionType)}
            className="h-9 rounded-md border border-gray-700 bg-gray-950 px-3 text-sm text-white focus:border-gray-500 focus:outline-none"
            aria-label="Question type"
          >
            {QUESTION_TYPES.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
          <input
            value={targetRole}
            onChange={(e) => setTargetRole(e.target.value)}
            placeholder="Target role"
            className="h-9 rounded-md border border-gray-700 bg-gray-950 px-3 text-sm text-white placeholder:text-gray-600 focus:border-gray-500 focus:outline-none"
          />
          <input
            type="number"
            min={100}
            max={800}
            value={maxWords}
            onChange={(e) => setMaxWords(Number(e.target.value))}
            className="h-9 w-28 rounded-md border border-gray-700 bg-gray-950 px-3 text-sm text-white focus:border-gray-500 focus:outline-none"
            aria-label="Max words"
          />
          <button
            type="button"
            onClick={() => void handleGenerate()}
            disabled={isGenerating}
            className="inline-flex h-9 items-center justify-center gap-2 rounded-md bg-white px-3 text-sm font-medium text-gray-950 disabled:opacity-60"
          >
            <Sparkles size={15} />
            {isGenerating ? "Generating..." : "Generate"}
          </button>
        </div>
      </section>

      {preview && (
        <section className="rounded-lg border border-gray-700 bg-gray-900 p-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">Preview</h2>
            <span className="text-xs text-gray-500">{preview.word_count} words</span>
          </div>
          <StoryBlocks story={preview.story} />
          <div className="mt-4 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setPreview(null)}
              className="rounded-md border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800"
            >
              Discard
            </button>
            <button
              type="button"
              onClick={() => void handleSave()}
              className="rounded-md bg-white px-3 py-2 text-sm font-medium text-gray-950"
            >
              Save
            </button>
          </div>
        </section>
      )}

      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-semibold text-white">Saved stories</h2>
          <div className="flex flex-wrap gap-2">
            {FILTERS.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setFilter(item)}
                className={
                  filter === item
                    ? "rounded-md border border-gray-500 bg-gray-700 px-3 py-1.5 text-xs capitalize text-white"
                    : "rounded-md border border-gray-800 px-3 py-1.5 text-xs capitalize text-gray-400 hover:border-gray-700 hover:text-gray-200"
                }
              >
                {item}
              </button>
            ))}
          </div>
        </div>
        {stories.length === 0 ? (
          <div className="rounded-lg border border-gray-800 bg-gray-900 p-6 text-sm text-gray-500">
            No saved stories.
          </div>
        ) : (
          stories.map((story) => (
            <article key={story.id} className="rounded-lg border border-gray-800 bg-gray-900">
              <button
                type="button"
                onClick={() => setExpanded((current) => (current === story.id ? null : story.id))}
                className="flex w-full items-center justify-between gap-3 p-4 text-left"
              >
                <span className="min-w-0">
                  <span className="block text-sm font-medium capitalize text-white">
                    {story.question_type} · {story.target_role || "Untargeted"}
                  </span>
                  <span className="block truncate text-xs text-gray-500">
                    {story.word_count} words · {new Date(story.created_at).toLocaleDateString()}
                  </span>
                </span>
              </button>
              {expanded === story.id && (
                <div className="border-t border-gray-800 p-4">
                  <StoryBlocks story={story.story} />
                  <div className="mt-4 flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        void navigator.clipboard.writeText(storyToMarkdown(story.story));
                        toast.success("Copied");
                      }}
                      className="inline-flex items-center gap-2 rounded-md border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800"
                    >
                      <Copy size={15} />
                      Copy Markdown
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleDelete(story.id)}
                      className="inline-flex items-center gap-2 rounded-md border border-red-500/40 px-3 py-2 text-sm text-red-300 hover:bg-red-500/10"
                    >
                      <Trash2 size={15} />
                      Delete
                    </button>
                  </div>
                </div>
              )}
            </article>
          ))
        )}
      </section>
    </div>
  );
}

function StoryBlocks({
  story,
}: {
  story: { situation: string; task: string; action: string; result: string };
}) {
  return (
    <div className="mt-3 grid gap-3 md:grid-cols-2">
      {[
        ["Situation", story.situation],
        ["Task", story.task],
        ["Action", story.action],
        ["Result", story.result],
      ].map(([label, value]) => (
        <div key={label} className="rounded-md border border-gray-800 p-3">
          <h3 className="text-xs font-medium uppercase text-gray-500">{label}</h3>
          <p className="mt-2 whitespace-pre-wrap text-sm text-gray-300">{value}</p>
        </div>
      ))}
    </div>
  );
}
