"use client";

import { FormEvent, useMemo, useState } from "react";
import { X } from "lucide-react";

import { createProject, updateProject } from "@/lib/api";
import { toast } from "@/components/ui/Toast";
import type { ProjectCreate, ProjectOut, ProjectStatus } from "@/types";

interface ProjectFormProps {
  mode: "create" | "edit";
  initialData?: ProjectOut;
  onSuccess: (project: ProjectOut) => void;
  onClose: () => void;
}

type MetricRow = { id: string; key: string; value: string };

const STATUSES: ProjectStatus[] = ["active", "paused", "completed", "archived"];

function rowsFromMetrics(metrics: ProjectOut["metrics"] | undefined): MetricRow[] {
  return Object.entries(metrics ?? {}).map(([key, value]) => ({
    id: crypto.randomUUID(),
    key,
    value: value === null ? "null" : String(value),
  }));
}

function parseMetricValue(raw: string): string | number | boolean | null {
  const value = raw.trim();
  if (value === "null") return null;
  if (value === "true") return true;
  if (value === "false") return false;
  if (value !== "" && Number.isFinite(Number(value))) return Number(value);
  return raw;
}

function addTagValue(current: string[], raw: string): string[] {
  const value = raw.trim().toLowerCase();
  if (!value || current.includes(value)) return current;
  return [...current, value].slice(0, 12);
}

export function ProjectForm({ mode, initialData, onSuccess, onClose }: ProjectFormProps) {
  const [title, setTitle] = useState(initialData?.title ?? "");
  const [description, setDescription] = useState(initialData?.description ?? "");
  const [periodStart, setPeriodStart] = useState(initialData?.period_start ?? "");
  const [periodEnd, setPeriodEnd] = useState(initialData?.period_end ?? "");
  const [role, setRole] = useState(initialData?.role ?? "");
  const [organization, setOrganization] = useState(initialData?.organization ?? "");
  const [problem, setProblem] = useState(initialData?.problem ?? "");
  const [actions, setActions] = useState(initialData?.actions ?? "");
  const [results, setResults] = useState(initialData?.results ?? "");
  const [status, setStatus] = useState<ProjectStatus>(initialData?.status ?? "active");
  const [skills, setSkills] = useState<string[]>(initialData?.skills ?? []);
  const [skillInput, setSkillInput] = useState("");
  const [tags, setTags] = useState<string[]>(initialData?.tags ?? []);
  const [tagInput, setTagInput] = useState("");
  const [metrics, setMetrics] = useState<MetricRow[]>(() => rowsFromMetrics(initialData?.metrics));
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const heading = mode === "create" ? "New project" : "Edit project";
  const canSubmit = !saving;

  const metricObject = useMemo(() => {
    const out: ProjectCreate["metrics"] = {};
    for (const row of metrics) {
      const key = row.key.trim();
      if (key) out[key] = parseMetricValue(row.value);
    }
    return out;
  }, [metrics]);

  function addSkill(raw: string) {
    setSkills((current) => addTagValue(current, raw));
    setSkillInput("");
  }

  function addTag(raw: string) {
    const value = raw.trim();
    if (!value || tags.includes(value)) return;
    setTags((current) => [...current, value]);
    setTagInput("");
  }

  function validate(): boolean {
    if (!title.trim()) {
      setError("Title is required");
      return false;
    }
    if (periodStart && periodEnd && periodEnd < periodStart) {
      setError("End date must be after start date");
      return false;
    }
    const duplicateMetric = metrics
      .map((row) => row.key.trim())
      .filter(Boolean)
      .some((key, index, keys) => keys.indexOf(key) !== index);
    if (duplicateMetric) {
      setError("Metric keys must be unique");
      return false;
    }
    return true;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!validate()) return;
    setSaving(true);
    const payload: ProjectCreate = {
      title: title.trim(),
      description: description.trim() || undefined,
      period_start: periodStart || undefined,
      period_end: periodEnd || undefined,
      role: role.trim() || undefined,
      organization: organization.trim() || undefined,
      problem: problem.trim() || undefined,
      actions: actions.trim() || undefined,
      results: results.trim() || undefined,
      metrics: metricObject,
      skills,
      status,
      tags,
    };
    try {
      const saved =
        mode === "create"
          ? await createProject(payload)
          : await updateProject(initialData!.id, payload);
      toast.success(mode === "create" ? "Project created" : "Project updated");
      onSuccess(saved);
      onClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not save project";
      setError(message);
      toast.error("Could not save project", { description: message });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/70 p-4 md:py-10">
      <form
        onSubmit={(event) => void handleSubmit(event)}
        className="w-full max-w-3xl rounded-lg border border-gray-800 bg-gray-950 p-5 shadow-xl"
      >
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-base font-semibold text-white">{heading}</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-gray-500 hover:bg-gray-800 hover:text-white"
            aria-label="Close"
          >
            <X size={16} />
          </button>
        </div>

        {error && (
          <div className="mt-4 rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">
            {error}
          </div>
        )}

        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <label className="md:col-span-2 text-sm text-gray-300">
            Title
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="mt-1 h-9 w-full rounded-md border border-gray-700 bg-gray-900 px-3 text-sm text-white focus:border-gray-500 focus:outline-none"
            />
          </label>
          <label className="text-sm text-gray-300">
            Role
            <input
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="mt-1 h-9 w-full rounded-md border border-gray-700 bg-gray-900 px-3 text-sm text-white focus:border-gray-500 focus:outline-none"
            />
          </label>
          <label className="text-sm text-gray-300">
            Organization
            <input
              value={organization}
              onChange={(e) => setOrganization(e.target.value)}
              className="mt-1 h-9 w-full rounded-md border border-gray-700 bg-gray-900 px-3 text-sm text-white focus:border-gray-500 focus:outline-none"
            />
          </label>
          <label className="text-sm text-gray-300">
            Start date
            <input
              type="date"
              value={periodStart}
              onChange={(e) => setPeriodStart(e.target.value)}
              className="mt-1 h-9 w-full rounded-md border border-gray-700 bg-gray-900 px-3 text-sm text-white focus:border-gray-500 focus:outline-none"
            />
          </label>
          <label className="text-sm text-gray-300">
            End date
            <input
              type="date"
              value={periodEnd}
              onChange={(e) => setPeriodEnd(e.target.value)}
              className="mt-1 h-9 w-full rounded-md border border-gray-700 bg-gray-900 px-3 text-sm text-white focus:border-gray-500 focus:outline-none"
            />
          </label>
          <label className="text-sm text-gray-300">
            Status
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as ProjectStatus)}
              className="mt-1 h-9 w-full rounded-md border border-gray-700 bg-gray-900 px-3 text-sm text-white focus:border-gray-500 focus:outline-none"
            >
              {STATUSES.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label className="md:col-span-2 text-sm text-gray-300">
            Description
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white focus:border-gray-500 focus:outline-none"
            />
          </label>
          {[
            ["Problem", problem, setProblem],
            ["Actions", actions, setActions],
            ["Results", results, setResults],
          ].map(([label, value, setter]) => (
            <label key={label as string} className="md:col-span-2 text-sm text-gray-300">
              {label as string}
              <textarea
                value={value as string}
                onChange={(e) => (setter as (value: string) => void)(e.target.value)}
                rows={3}
                className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white focus:border-gray-500 focus:outline-none"
              />
            </label>
          ))}
        </div>

        <div className="mt-5 grid gap-5 md:grid-cols-2">
          <section>
            <h3 className="text-sm font-medium text-gray-200">Skills</h3>
            <div className="mt-2 flex flex-wrap gap-2">
              {skills.map((skill) => (
                <button
                  key={skill}
                  type="button"
                  onClick={() => setSkills((current) => current.filter((item) => item !== skill))}
                  className="rounded border border-gray-700 px-2 py-1 text-xs text-gray-300"
                >
                  {skill} x
                </button>
              ))}
            </div>
            <input
              value={skillInput}
              onChange={(e) => setSkillInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addSkill(skillInput);
                }
              }}
              placeholder="Type and press Enter"
              className="mt-2 h-9 w-full rounded-md border border-gray-700 bg-gray-900 px-3 text-sm text-white placeholder:text-gray-600 focus:border-gray-500 focus:outline-none"
            />
          </section>

          <section>
            <h3 className="text-sm font-medium text-gray-200">Tags</h3>
            <div className="mt-2 flex flex-wrap gap-2">
              {tags.map((tag) => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => setTags((current) => current.filter((item) => item !== tag))}
                  className="rounded border border-gray-700 px-2 py-1 text-xs text-gray-300"
                >
                  {tag} x
                </button>
              ))}
            </div>
            <input
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addTag(tagInput);
                }
              }}
              placeholder="Type and press Enter"
              className="mt-2 h-9 w-full rounded-md border border-gray-700 bg-gray-900 px-3 text-sm text-white placeholder:text-gray-600 focus:border-gray-500 focus:outline-none"
            />
          </section>
        </div>

        <section className="mt-5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-200">Metrics</h3>
            <button
              type="button"
              onClick={() =>
                setMetrics((current) => [
                  ...current,
                  { id: crypto.randomUUID(), key: "", value: "" },
                ])
              }
              className="rounded-md border border-gray-700 px-2 py-1 text-xs text-gray-300 hover:bg-gray-800"
            >
              Add metric
            </button>
          </div>
          <div className="mt-2 space-y-2">
            {metrics.map((row) => (
              <div key={row.id} className="grid gap-2 md:grid-cols-[1fr_1fr_auto]">
                <input
                  value={row.key}
                  onChange={(e) =>
                    setMetrics((current) =>
                      current.map((item) =>
                        item.id === row.id ? { ...item, key: e.target.value } : item
                      )
                    )
                  }
                  placeholder="Metric"
                  className="h-9 rounded-md border border-gray-700 bg-gray-900 px-3 text-sm text-white placeholder:text-gray-600 focus:border-gray-500 focus:outline-none"
                />
                <input
                  value={row.value}
                  onChange={(e) =>
                    setMetrics((current) =>
                      current.map((item) =>
                        item.id === row.id ? { ...item, value: e.target.value } : item
                      )
                    )
                  }
                  placeholder="string / number / bool"
                  className="h-9 rounded-md border border-gray-700 bg-gray-900 px-3 text-sm text-white placeholder:text-gray-600 focus:border-gray-500 focus:outline-none"
                />
                <button
                  type="button"
                  onClick={() =>
                    setMetrics((current) => current.filter((item) => item.id !== row.id))
                  }
                  className="h-9 rounded-md border border-gray-700 px-3 text-sm text-gray-300 hover:bg-gray-800"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        </section>

        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!canSubmit}
            className="rounded-md bg-white px-3 py-2 text-sm font-medium text-gray-950 disabled:opacity-60"
          >
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </form>
    </div>
  );
}
