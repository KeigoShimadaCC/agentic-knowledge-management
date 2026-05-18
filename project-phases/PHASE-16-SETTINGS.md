# PHASE-16 — Settings, AI Configuration, and Prompt Management

## Summary

Build backend-backed Settings for AI provider keys, per-feature model configuration, prompt overrides, MCP diagnostics, and server export. Runtime DB settings take effect immediately; allowlisted `.env` export provides restart durability when the host file is writable. Existing env/config defaults remain the fallback when no user setting exists.

## Tracks

- 16A: Create phase doc/worktree, update `PROGRESS.md`, and reconcile the existing multi-provider AI base.
- 16B: Backend settings foundation, encryption, `.env` export, schemas, services, router, and docs.
- 16C: Prompt registry plus AI call-site migration while preserving default outputs.
- 16D: Web Settings UI with API client/types, tabs/forms, prompt editor, and MCP relocation.
- 16E: iOS Settings parity with DTOs, API client/view model, SwiftUI screens, and identifiers.
- 16F: Final docs, progress, verification, and handoff.

## Backend Contract

New authenticated routes under `/api/v1/settings`:

- `GET /` returns redacted secret status, feature configs, prompt defaults/overrides, MCP summary, and env export status.
- `PATCH /secrets` saves or clears OpenAI/Anthropic keys; raw values are never returned.
- `POST /providers/{provider}/test` runs an explicit low-cost test call and records success/failure.
- `PATCH /ai-features/{feature_key}` updates provider/model/params for one feature.
- `PATCH /background-ai` updates per-user background AI enablement and task selection.
- `PATCH /mcp` updates per-user MCP web-search answer preferences.
- `PATCH /prompts/{prompt_key}` validates variables and saves an override.
- `POST /prompts/{prompt_key}/reset` removes the override.
- `POST /env/export` retries writing runtime settings to the configured `.env` path.

## Data Model

- `settings_secrets`: per-user encrypted values for `openai_api_key` and `anthropic_api_key`.
- `settings_provider_tests`: per-user provider test status, error, and timestamp without duplicating raw secrets.
- `ai_feature_settings`: per-user feature config keyed by feature.
- `settings_preferences`: per-user runtime preference payloads for background AI and MCP web-search settings.
- `prompt_overrides`: per-user prompt template overrides keyed by prompt.

## Prompt Registry

Registry covers summarize page/source, extract claims/tasks, suggest links, KB answer, KB+web answer, triage, inline complete/transform variants, extract project, resume bullets, and interview story. Each entry exposes key, display name, default template, variable names, and response contract notes.

## Test Plan

- Backend API tests for settings CRUD, redaction/encryption, `.env` allowlist export, prompt validation/reset, feature config fallback, provider disabled paths, and unauthorized access.
- AI integration tests proving key AI flows use prompt overrides and per-feature provider/model config.
- Web checks: typecheck, lint, and focused Settings UI coverage where practical.
- E2E smoke: Settings loads, prompt override save/reset works, feature config saves, and existing MCP page still works.
- iOS checks: DTO/view-model tests plus the `iPhone 16` build/test gate when the simulator environment is available.
