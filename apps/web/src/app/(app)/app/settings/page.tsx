"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, ExternalLink, RotateCcw, Save, ServerCog, TestTube2 } from "lucide-react";

import {
  exportSettingsEnv,
  getSettings,
  patchSettingsSecrets,
  resetPromptOverride,
  testSettingsProvider,
  updateBackgroundAiSettings,
  updateAiFeatureSetting,
  updateMcpSettings,
  updatePromptOverride,
} from "@/lib/api";
import type { AiFeatureSettingOut, BackgroundAiSettings, McpSettingsSummary, PromptOut, SettingsResponse } from "@/types";

type TabKey = "providers" | "features" | "prompts" | "mcp" | "background" | "diagnostics";

const tabs: Array<{ key: TabKey; label: string }> = [
  { key: "providers", label: "AI Providers" },
  { key: "features", label: "Feature Models" },
  { key: "prompts", label: "Prompts" },
  { key: "mcp", label: "MCP" },
  { key: "background", label: "Background AI" },
  { key: "diagnostics", label: "Server/Diagnostics" },
];

function providerLabel(key: string) {
  return key === "openai_api_key" ? "OpenAI" : "Anthropic";
}

function StatusPill({ children, tone = "gray" }: { children: string; tone?: "gray" | "green" | "red" | "amber" }) {
  const cls =
    tone === "green"
      ? "bg-green-500/15 text-green-200"
      : tone === "red"
        ? "bg-red-500/15 text-red-200"
        : tone === "amber"
          ? "bg-amber-500/15 text-amber-200"
          : "bg-gray-800 text-gray-300";
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>{children}</span>;
}

function FeatureRow({
  feature,
  onSaved,
}: {
  feature: AiFeatureSettingOut;
  onSaved: (feature: AiFeatureSettingOut) => void;
}) {
  const [enabled, setEnabled] = useState(feature.enabled);
  const [provider, setProvider] = useState(feature.provider ?? feature.resolved_provider ?? "openai");
  const [model, setModel] = useState(feature.model ?? feature.resolved_model ?? "");
  const [temperature, setTemperature] = useState(String(feature.temperature ?? feature.resolved_temperature ?? 0.2));
  const [maxTokens, setMaxTokens] = useState(String(feature.max_tokens ?? feature.resolved_max_tokens ?? 2000));
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function save() {
    setSaving(true);
    setMessage(null);
    try {
      const saved = await updateAiFeatureSetting(feature.feature_key, {
        enabled,
        provider: provider as "openai" | "anthropic",
        model: model || null,
        temperature: Number(temperature),
        max_tokens: Number(maxTokens),
      });
      onSaved(saved);
      setMessage("Saved");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <article className="rounded-lg border border-gray-800 bg-gray-900 p-4">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold text-white">{feature.display_name}</h3>
            <StatusPill tone={feature.enabled ? "green" : "amber"}>
              {feature.enabled ? "Enabled" : "Disabled"}
            </StatusPill>
          </div>
          <p className="mt-1 text-xs text-gray-500">
            Resolved: {feature.resolved_provider ?? "none"} / {feature.resolved_model ?? "none"}
          </p>
          {feature.note && <p className="mt-1 text-xs text-amber-200">{feature.note}</p>}
        </div>
        <div className="grid flex-1 gap-3 sm:grid-cols-5">
          <label className="flex items-center gap-2 text-sm text-gray-300">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(event) => setEnabled(event.target.checked)}
              className="h-4 w-4 rounded border-gray-700 bg-gray-950"
            />
            On
          </label>
          <select
            value={provider}
            onChange={(event) => setProvider(event.target.value)}
            className="rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-gray-100"
          >
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
          </select>
          <input
            value={model}
            onChange={(event) => setModel(event.target.value)}
            className="rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-gray-100"
            placeholder="Model"
          />
          <input
            value={temperature}
            onChange={(event) => setTemperature(event.target.value)}
            className="rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-gray-100"
            inputMode="decimal"
            aria-label={`${feature.display_name} temperature`}
          />
          <input
            value={maxTokens}
            onChange={(event) => setMaxTokens(event.target.value)}
            className="rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-gray-100"
            inputMode="numeric"
            aria-label={`${feature.display_name} max tokens`}
          />
        </div>
        <button
          type="button"
          onClick={() => void save()}
          disabled={saving}
          className="inline-flex h-9 items-center gap-2 rounded-md bg-white px-3 text-sm font-medium text-gray-950 hover:bg-gray-200 disabled:opacity-60"
        >
          <Save size={16} />
          {saving ? "Saving" : "Save"}
        </button>
      </div>
      {message && <p className="mt-2 text-xs text-gray-400">{message}</p>}
    </article>
  );
}

function PromptEditor({
  prompt,
  onSaved,
}: {
  prompt: PromptOut;
  onSaved: (prompt: PromptOut) => void;
}) {
  const [template, setTemplate] = useState(prompt.effective_template);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    setTemplate(prompt.effective_template);
  }, [prompt.effective_template]);

  async function save() {
    setSaving(true);
    setMessage(null);
    try {
      const saved = await updatePromptOverride(prompt.key, template);
      onSaved(saved);
      setMessage("Saved");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function reset() {
    setSaving(true);
    setMessage(null);
    try {
      const saved = await resetPromptOverride(prompt.key);
      onSaved(saved);
      setTemplate(saved.effective_template);
      setMessage("Reset");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Reset failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <article className="rounded-lg border border-gray-800 bg-gray-900 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold text-white">{prompt.display_name}</h3>
            {prompt.has_override && <StatusPill tone="amber">Override</StatusPill>}
          </div>
          <p className="mt-1 text-xs text-gray-500">{prompt.response_contract}</p>
          <p className="mt-1 text-xs text-gray-500">
            Variables: {prompt.variables.length ? prompt.variables.map((v) => `{${v}}`).join(", ") : "none"}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => void reset()}
            disabled={saving || !prompt.has_override}
            className="inline-flex h-9 items-center gap-2 rounded-md border border-gray-700 px-3 text-sm text-gray-200 hover:bg-gray-800 disabled:opacity-50"
          >
            <RotateCcw size={16} />
            Reset
          </button>
          <button
            type="button"
            onClick={() => void save()}
            disabled={saving}
            className="inline-flex h-9 items-center gap-2 rounded-md bg-white px-3 text-sm font-medium text-gray-950 hover:bg-gray-200 disabled:opacity-60"
          >
            <Save size={16} />
            Save
          </button>
        </div>
      </div>
      <textarea
        value={template}
        onChange={(event) => setTemplate(event.target.value)}
        className="mt-3 min-h-44 w-full rounded-md border border-gray-700 bg-gray-950 p-3 font-mono text-sm text-gray-100"
        spellCheck={false}
      />
      {message && <p className="mt-2 text-xs text-gray-400">{message}</p>}
    </article>
  );
}

const backgroundTasks = [
  { key: "summarize", label: "Summarize" },
  { key: "extract_claims", label: "Extract claims" },
  { key: "suggest_links", label: "Suggest links" },
];

function BackgroundAiSection({
  value,
  onSaved,
}: {
  value: BackgroundAiSettings;
  onSaved: (value: BackgroundAiSettings) => void;
}) {
  const [enabled, setEnabled] = useState(value.enabled);
  const [tasks, setTasks] = useState<string[]>(value.tasks);
  const [message, setMessage] = useState<string | null>(null);

  async function save() {
    setMessage(null);
    try {
      const saved = await updateBackgroundAiSettings({ enabled, tasks });
      onSaved(saved);
      setMessage("Saved");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Save failed");
    }
  }

  return (
    <section className="rounded-lg border border-gray-800 bg-gray-900 p-4">
      <div className="flex items-center gap-2">
        <CheckCircle2 size={18} className="text-gray-400" />
        <h2 className="text-base font-semibold text-white">Background AI</h2>
      </div>
      <div className="mt-4 space-y-3">
        <label className="flex items-center gap-2 text-sm text-gray-300">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(event) => setEnabled(event.target.checked)}
            className="h-4 w-4 rounded border-gray-700 bg-gray-950"
          />
          Run AI automatically after page/source updates
        </label>
        <div className="flex flex-wrap gap-3">
          {backgroundTasks.map((task) => (
            <label key={task.key} className="flex items-center gap-2 text-sm text-gray-300">
              <input
                type="checkbox"
                checked={tasks.includes(task.key)}
                onChange={(event) =>
                  setTasks((prev) =>
                    event.target.checked
                      ? [...prev, task.key]
                      : prev.filter((item) => item !== task.key)
                  )
                }
                className="h-4 w-4 rounded border-gray-700 bg-gray-950"
              />
              {task.label}
            </label>
          ))}
        </div>
      </div>
      <div className="mt-4 flex items-center gap-3">
        <button
          type="button"
          onClick={() => void save()}
          className="inline-flex h-9 items-center gap-2 rounded-md bg-white px-3 text-sm font-medium text-gray-950 hover:bg-gray-200"
        >
          <Save size={16} />
          Save
        </button>
        {message && <p className="text-sm text-gray-400">{message}</p>}
      </div>
    </section>
  );
}

function McpSettingsSection({
  value,
  onSaved,
}: {
  value: McpSettingsSummary;
  onSaved: (value: McpSettingsSummary) => void;
}) {
  const [threshold, setThreshold] = useState(String(value.web_search_threshold));
  const [connectionName, setConnectionName] = useState(value.web_search_connection_name ?? "");
  const [message, setMessage] = useState<string | null>(null);

  async function save() {
    setMessage(null);
    try {
      const saved = await updateMcpSettings({
        web_search_threshold: Number(threshold),
        web_search_connection_name: connectionName || null,
      });
      onSaved(saved);
      setMessage("Saved");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Save failed");
    }
  }

  return (
    <section className="rounded-lg border border-gray-800 bg-gray-900 p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-white">MCP</h2>
          <p className="mt-1 text-sm text-gray-400">
            {value.enabled_count} enabled / {value.connection_count} total
          </p>
        </div>
        <Link
          href="/app/settings/mcp"
          className="inline-flex h-9 items-center gap-2 rounded-md bg-white px-3 text-sm font-medium text-gray-950 hover:bg-gray-200"
        >
          <ExternalLink size={16} />
          MCP Connections
        </Link>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <label className="grid gap-1 text-sm text-gray-300">
          Web-search threshold
          <input
            value={threshold}
            onChange={(event) => setThreshold(event.target.value)}
            className="rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-gray-100"
            inputMode="decimal"
          />
        </label>
        <label className="grid gap-1 text-sm text-gray-300">
          Preferred web-search connection
          <input
            value={connectionName}
            onChange={(event) => setConnectionName(event.target.value)}
            className="rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-gray-100"
            placeholder="Any matching connection"
          />
        </label>
      </div>
      <div className="mt-4 flex items-center gap-3">
        <button
          type="button"
          onClick={() => void save()}
          className="inline-flex h-9 items-center gap-2 rounded-md border border-gray-700 px-3 text-sm text-gray-200 hover:bg-gray-800"
        >
          <Save size={16} />
          Save
        </button>
        {message && <p className="text-sm text-gray-400">{message}</p>}
      </div>
    </section>
  );
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>("providers");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openAiKey, setOpenAiKey] = useState("");
  const [anthropicKey, setAnthropicKey] = useState("");
  const [savingSecrets, setSavingSecrets] = useState(false);
  const [secretMessage, setSecretMessage] = useState<string | null>(null);

  useEffect(() => {
    getSettings()
      .then(setSettings)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load settings"))
      .finally(() => setLoading(false));
  }, []);

  const promptGroups = useMemo(() => {
    const prompts = settings?.prompts ?? [];
    return {
      core: prompts.filter((p) => !p.key.startsWith("inline.") && !p.key.startsWith("career.")),
      inline: prompts.filter((p) => p.key.startsWith("inline.")),
      career: prompts.filter((p) => p.key.startsWith("career.")),
    };
  }, [settings?.prompts]);

  function replaceFeature(feature: AiFeatureSettingOut) {
    setSettings((prev) =>
      prev
        ? { ...prev, features: prev.features.map((item) => (item.feature_key === feature.feature_key ? feature : item)) }
        : prev
    );
  }

  function replacePrompt(prompt: PromptOut) {
    setSettings((prev) =>
      prev ? { ...prev, prompts: prev.prompts.map((item) => (item.key === prompt.key ? prompt : item)) } : prev
    );
  }

  function replaceBackgroundAi(background_ai: BackgroundAiSettings) {
    setSettings((prev) => (prev ? { ...prev, background_ai } : prev));
  }

  function replaceMcp(mcp: McpSettingsSummary) {
    setSettings((prev) => (prev ? { ...prev, mcp } : prev));
  }

  async function saveSecrets() {
    setSavingSecrets(true);
    setSecretMessage(null);
    try {
      const next = await patchSettingsSecrets({
        openai_api_key: openAiKey || null,
        anthropic_api_key: anthropicKey || null,
        export_env: true,
      });
      setSettings(next);
      setOpenAiKey("");
      setAnthropicKey("");
      setSecretMessage(next.env_export.last_warning ?? "Saved");
    } catch (err) {
      setSecretMessage(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSavingSecrets(false);
    }
  }

  async function clearSecret(key: "openai_api_key" | "anthropic_api_key") {
    const next = await patchSettingsSecrets({
      clear_openai_api_key: key === "openai_api_key",
      clear_anthropic_api_key: key === "anthropic_api_key",
      export_env: true,
    });
    setSettings(next);
  }

  async function testProvider(provider: "openai" | "anthropic") {
    const result = await testSettingsProvider(provider);
    setSecretMessage(result.ok ? `${provider} test succeeded` : result.error ?? `${provider} test failed`);
    const next = await getSettings();
    setSettings(next);
  }

  async function retryExport() {
    const next = await exportSettingsEnv();
    setSettings(next);
    setSecretMessage(next.env_export.last_warning ?? "Exported");
  }

  if (loading) {
    return <div className="p-6 text-sm text-gray-400">Loading settings...</div>;
  }
  if (error || !settings) {
    return <div className="p-6 text-sm text-red-300">{error ?? "Settings unavailable"}</div>;
  }

  return (
    <main className="min-h-full bg-gray-950 text-gray-100">
      <div className="border-b border-gray-800 px-6 py-5">
        <h1 className="text-2xl font-semibold text-white">Settings</h1>
        <div className="mt-4 flex flex-wrap gap-2" role="tablist" aria-label="Settings sections">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className={`rounded-md px-3 py-2 text-sm transition-colors ${
                activeTab === tab.key
                  ? "bg-white text-gray-950"
                  : "border border-gray-800 text-gray-300 hover:bg-gray-900"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-4 p-6">
        {activeTab === "providers" && (
          <section className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              {settings.secrets.map((secret) => {
                const provider = secret.key === "openai_api_key" ? "openai" : "anthropic";
                return (
                  <article key={secret.key} className="rounded-lg border border-gray-800 bg-gray-900 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h2 className="text-base font-semibold text-white">{providerLabel(secret.key)}</h2>
                        <p className="mt-1 text-sm text-gray-400">{secret.redacted ?? "Not configured"}</p>
                      </div>
                      <StatusPill tone={secret.configured ? "green" : "amber"}>{secret.source}</StatusPill>
                    </div>
                    {secret.last_test_error && <p className="mt-3 text-sm text-red-300">{secret.last_test_error}</p>}
                    <div className="mt-4 flex gap-2">
                      <button
                        type="button"
                        onClick={() => void testProvider(provider)}
                        className="inline-flex h-9 items-center gap-2 rounded-md border border-gray-700 px-3 text-sm text-gray-200 hover:bg-gray-800"
                      >
                        <TestTube2 size={16} />
                        Test
                      </button>
                      <button
                        type="button"
                        onClick={() => void clearSecret(secret.key)}
                        className="h-9 rounded-md border border-red-900/70 px-3 text-sm text-red-200 hover:bg-red-950/50"
                      >
                        Clear
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
            <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
              <div className="grid gap-3 md:grid-cols-2">
                <input
                  value={openAiKey}
                  onChange={(event) => setOpenAiKey(event.target.value)}
                  className="rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-gray-100"
                  placeholder="OpenAI API key"
                  type="password"
                />
                <input
                  value={anthropicKey}
                  onChange={(event) => setAnthropicKey(event.target.value)}
                  className="rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-gray-100"
                  placeholder="Anthropic API key"
                  type="password"
                />
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={() => void saveSecrets()}
                  disabled={savingSecrets}
                  className="inline-flex h-9 items-center gap-2 rounded-md bg-white px-3 text-sm font-medium text-gray-950 hover:bg-gray-200 disabled:opacity-60"
                >
                  <Save size={16} />
                  Save Keys
                </button>
                {secretMessage && <p className="text-sm text-gray-400">{secretMessage}</p>}
              </div>
            </div>
          </section>
        )}

        {activeTab === "features" && (
          <section className="space-y-3">
            {settings.features.map((feature) => (
              <FeatureRow key={feature.feature_key} feature={feature} onSaved={replaceFeature} />
            ))}
          </section>
        )}

        {activeTab === "prompts" && (
          <section className="space-y-6">
            {[promptGroups.core, promptGroups.inline, promptGroups.career].map((group, index) => (
              <div key={index} className="space-y-3">
                {group.map((prompt) => (
                  <PromptEditor key={prompt.key} prompt={prompt} onSaved={replacePrompt} />
                ))}
              </div>
            ))}
          </section>
        )}

        {activeTab === "mcp" && (
          <McpSettingsSection value={settings.mcp} onSaved={replaceMcp} />
        )}

        {activeTab === "background" && (
          <BackgroundAiSection value={settings.background_ai} onSaved={replaceBackgroundAi} />
        )}

        {activeTab === "diagnostics" && (
          <section className="rounded-lg border border-gray-800 bg-gray-900 p-4">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <ServerCog size={18} className="text-gray-400" />
                  <h2 className="text-base font-semibold text-white">Environment Export</h2>
                </div>
                <p className="mt-2 text-sm text-gray-400">
                  {settings.env_export.available ? settings.env_export.path : "No export path configured"}
                </p>
                {settings.env_export.last_warning && (
                  <p className="mt-2 text-sm text-amber-200">{settings.env_export.last_warning}</p>
                )}
              </div>
              <button
                type="button"
                onClick={() => void retryExport()}
                className="inline-flex h-9 items-center gap-2 rounded-md border border-gray-700 px-3 text-sm text-gray-200 hover:bg-gray-800"
              >
                <Save size={16} />
                Export
              </button>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {settings.env_export.allowlisted_keys.map((key) => (
                <StatusPill key={key}>{key}</StatusPill>
              ))}
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
