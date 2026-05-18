import type { SettingsResponse } from "@/types";

export const sampleSettingsResponse: SettingsResponse = {
  secrets: [
    {
      key: "openai_api_key",
      configured: true,
      source: "env",
      redacted: "sk-t...stub",
      last_test_status: "success",
      last_test_error: null,
      last_tested_at: "2026-05-19T00:00:00Z",
    },
    {
      key: "anthropic_api_key",
      configured: false,
      source: "none",
      redacted: null,
      last_test_status: null,
      last_test_error: null,
      last_tested_at: null,
    },
  ],
  features: [
    {
      feature_key: "summarize",
      display_name: "Summarization",
      enabled: true,
      provider: "openai",
      model: null,
      temperature: 0.2,
      max_tokens: 2000,
      effort: null,
      resolved_provider: "openai",
      resolved_model: "gpt-4o-mini",
      resolved_temperature: 0.2,
      resolved_max_tokens: 2000,
      supports_effort: false,
      note: null,
    },
  ],
  prompts: [
    {
      key: "summarize.page",
      display_name: "Summarize Page",
      default_template: "Summarize the following content:\n\n{content}",
      effective_template: "Summarize the following content:\n\n{content}",
      override_template: null,
      has_override: false,
      variables: ["content"],
      response_contract: "Plain text summary, 3-5 sentences.",
      updated_at: null,
    },
  ],
  background_ai: {
    enabled: false,
    tasks: [],
  },
  mcp: {
    connection_count: 0,
    enabled_count: 0,
    web_search_threshold: 0.45,
    web_search_connection_name: null,
  },
  env_export: {
    available: false,
    path: null,
    last_warning: null,
    allowlisted_keys: ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"],
  },
};
