# PHASE-ENHANCE-04 — GitHub Wiki

## 0. North Star

Create and publish a complete GitHub Wiki for KnowledgeOS at:

`https://github.com/KeigoShimadaCC/agentic-knowledge-management/wiki`

The wiki should explain the repository to maintainers, contributors, operators, and AI coding
agents. It must be grounded in the live repository, not a shallow README rewrite.

## 1. Source of Truth

Use this precedence when documenting behavior:

1. Current source code, configs, tests, and CI.
2. `PROGRESS.md`.
3. `docs/`.
4. `README.md`.
5. `project-phases/` for background and planned/future context.

Do not invent features. If something is planned but not implemented, label it planned/future.

## 2. Delivery Target

- Generate a flat GitHub Wiki Markdown page set.
- Clone the wiki repo:

  ```bash
  git clone https://github.com/KeigoShimadaCC/agentic-knowledge-management.wiki.git /private/tmp/agentic-knowledge-management.wiki
  ```

- Treat the generated page set as canonical.
- Replace stale top-level wiki Markdown pages.
- Commit and push the wiki repo.
- Do not modify the main application repo except this phase document.

## 3. Page Set

Create these wiki files:

- Core: `Home.md`, `_Sidebar.md`
- Overview: `overview.md`, `overview--architecture.md`, `overview--getting-started.md`,
  `overview--glossary.md`
- Context: `by-the-numbers.md`, `lore.md`, `fun-facts.md`, `background.md`,
  `background--design-decisions.md`
- Apps / Runtime: `apps.md`, `apps--web.md`, `apps--api.md`, `apps--worker.md`,
  `apps--mcp.md`, `apps--scripts.md`
- Systems: `systems.md`, `systems--auth-and-sessions.md`, `systems--object-model.md`,
  `systems--sources-and-ingestion.md`, `systems--search-and-indexing.md`,
  `systems--graph.md`, `systems--ai-workflows.md`, `systems--chat-import.md`,
  `systems--workspaces.md`, `systems--career-memory.md`, `systems--audit-and-revisions.md`,
  `systems--frontend-ux.md`
- Sources / Integrations: `sources.md`, `sources--ingestion-extractors.md`,
  `sources--external-services.md`, `sources--fixtures-and-evals.md`
- Primitives / Data: `primitives.md`, `primitives--kosobject.md`, `primitives--edges.md`,
  `primitives--chunks.md`, `primitives--career-artifacts.md`,
  `primitives--sessions-and-audit.md`
- Interfaces: `api.md`, `api--rest.md`, `api--mcp-tools.md`, `api--frontend-client.md`,
  `api--ai.md`
- Contribution: `how-to-contribute.md`, `how-to-contribute--development-workflow.md`,
  `how-to-contribute--testing.md`, `how-to-contribute--debugging.md`,
  `how-to-contribute--patterns-and-conventions.md`, `how-to-contribute--tooling.md`
- Operations / Reference: `deployment.md`, `security.md`, `reference.md`,
  `reference--configuration.md`, `reference--data-models.md`,
  `reference--dependencies.md`

## 4. Sidebar Contract

`_Sidebar.md` must link to every generated page and group pages by reader intent in this order:

1. Overview
2. By the numbers
3. Lore
4. Fun facts
5. How to contribute
6. Apps / Runtime surfaces
7. Systems / Internals
8. Sources / Integrations
9. Primitives / Data types
10. API / Interface reference
11. Deployment
12. Security
13. Background
14. Reference

Use GitHub Wiki links without `.md`, for example `[Architecture](overview--architecture)`.

## 5. Content Requirements

- Every page must have exactly one H1.
- Prefer tables for inventories, configs, schemas, commands, and module maps.
- Use Mermaid diagrams for architecture, request lifecycle, ingestion, and indexing flows where
  useful.
- Use real commands, env vars, routes, table names, models, tool names, and file paths.
- Mark fetched, uploaded, or user-provided content as untrusted where relevant.
- Include agent-facing rules from `CLAUDE.md`, `AGENTS.md`, `docs/MCP_TOOLS.md`,
  `docs/SECURITY.md`, and `docs/AI-CODER-BRIEFING.md` where they affect development.
- Distinguish committed implementation from future plans such as Phase 11/12 work or Kuzu.

## 6. Systems To Cover

The wiki must document:

- Next.js app routes under `/app`, auth routes, app shell, editor, workspaces, projects, sources,
  chats, assets, trash, inbox, and search.
- FastAPI routers under `/api/v1`.
- Worker runtime `kos_worker`, RQ queue `kos-ingest`, ingestion extractors, and reindex jobs.
- MCP package `kos-mcp`, read tools, gated write tools, career tools, internal token auth,
  redaction, rate limits, file safety, and URL safety.
- Data tables and models: `users`, `sessions`, `objects`, `pages`, `assets`, `sources`, `edges`,
  `chunks`, `ingestion_jobs`, `agent_runs`, `object_revisions`, `chats`, `projects`,
  `workspaces`, `resume_bullet_sets`, and `interview_story_records`.
- Config defaults from `services/api/app/config.py`, `services/mcp/kos_mcp/config.py`,
  `infra/.env.example`, and `infra/docker-compose.yml`.
- Security boundaries: local-first storage, `LIBRARY_ROOT`, `kos_session`,
  `X-KOS-Internal-Token`, soft deletes, audit/revision rules, SSRF defenses, secret redaction,
  and AI-disabled behavior.

## 7. Validation

Before committing the wiki repo:

- Verify every generated page has exactly one H1.
- Verify `_Sidebar.md` links to every generated page except `_Sidebar.md`.
- Verify all local wiki links target generated pages and omit `.md`.
- Verify there are no empty pages.
- Run `git diff --check` in the wiki clone.
- Commit with:

  ```bash
  git commit -m "docs(wiki): publish KnowledgeOS project wiki"
  ```

- Push the wiki repo and verify the published wiki URL resolves.

No application test suite is required because this phase publishes only the separate GitHub Wiki.

## 8. Definition of Done

- The wiki repo contains the canonical generated page set.
- The wiki has a complete `_Sidebar.md` and every page is reachable.
- The wiki is pushed to GitHub.
- Final handoff includes the wiki URL, wiki commit hash, and generated page manifest.

