# PHASE-ENHANCE-04B — GitHub Wiki Enhancement

## 0. North Star

Upgrade the already-published KnowledgeOS GitHub Wiki from a structurally valid first pass into
the complete repo-grounded wiki requested by the original prompt.

The wiki should explain the repository to maintainers, contributors, operators, and AI coding
agents. It must document actual architecture, systems, runtime surfaces, API contracts, data
models, workflows, operational notes, and project context in enough detail that a new maintainer
or agent can safely work in the repository.

Published wiki URL:

`https://github.com/KeigoShimadaCC/agentic-knowledge-management/wiki`

## 1. Starting Point

Phase 04A created and published a flat 56-page GitHub Wiki. It satisfies the mechanical
requirements:

- Flat GitHub Wiki file naming.
- `_Sidebar.md` links every generated page.
- Every page has one H1.
- Computed counts are present.
- Wiki repo was pushed and the published URL returned HTTP 200.

However, it is not yet complete against the original requested depth. The follow-up work should
deepen the existing page set rather than replace the structure.

## 2. Source of Truth

Use this precedence when documenting behavior:

1. Current source code, configs, tests, and CI.
2. `PROGRESS.md`.
3. `docs/`.
4. `README.md`.
5. `project-phases/` for background and planned/future context.

Do not invent features. If something is planned but not implemented, label it planned/future.

## 3. Non-Breakage Contract

- Do not change application code.
- Do not rename the existing wiki pages unless a split is necessary for readability.
- Preserve the flat GitHub Wiki filename convention.
- Preserve the reader-intent grouping in `_Sidebar.md`.
- Keep `Home.md` and `overview.md` concise; deepen child/reference pages instead.
- Avoid generic advice that is not tied to real repo files, commands, behavior, or conventions.
- If the main repo is dirty, do not touch unrelated files. This phase should only need this plan
  file in the main repo plus wiki repo Markdown changes.

## 4. Target Wiki Areas

Deepen these existing wiki sections:

| Area | Main pages |
| --- | --- |
| API / interfaces | `api.md`, `api--rest.md`, `api--mcp-tools.md`, `api--frontend-client.md`, `api--ai.md` |
| Data / primitives | `primitives*.md`, `reference--data-models.md`, `reference--configuration.md` |
| Runtime surfaces | `apps*.md` |
| Systems / internals | `systems*.md` |
| Sources / integrations | `sources*.md` |
| Contribution workflow | `how-to-contribute*.md` |
| Operations/security/reference | `deployment.md`, `security.md`, `reference*.md` |
| Context | `background*.md`, `by-the-numbers.md`, `lore.md`, `fun-facts.md` |

If a page becomes too large, create additional child pages with the same flat naming pattern, for
example `api--objects.md` or `systems--mcp.md`, and update `_Sidebar.md`.

## 5. Content Requirements

### API / Interface Pages

For each public interface, document:

- Purpose.
- Auth and permission model.
- Arguments, query parameters, or request body.
- Response shape.
- Side effects.
- Error behavior.
- Example request/response where useful.
- Key source files.

Minimum required coverage:

- REST routers under `services/api/app/api/v1`.
- MCP tools in `services/mcp/kos_mcp/tools.py`.
- Frontend API functions in `apps/web/src/lib/api.ts`.
- AI prompt/client surfaces in `services/api/app/ai` and career/chat AI services.

### Data / Primitive Pages

Document exact schemas and persistence details:

- SQLAlchemy models and table names.
- Pydantic request/response schemas.
- Field semantics.
- Serialization aliases such as `metadata_` -> `metadata`.
- Literal/enum values, including object kinds, edge kinds, workspace pane kinds, statuses, and
  MCP tool names.
- UUID and content-addressing conventions.
- Indexes and constraints where represented in migrations or docs.
- Source file paths.

### Runtime / App Pages

For each app/runtime/server/CLI page, document:

- Purpose.
- Entry point.
- Install/run commands.
- Lifecycle.
- Logging/debugging hooks.
- Integration points.
- Key source files.
- Modification entry points.

Minimum required surfaces:

- Next.js web app.
- FastAPI API server.
- RQ worker.
- MCP server.
- Scripts: setup, backup, reindex, MCP smoke, test helper.

### Systems / Internals Pages

For each subsystem, document:

- Purpose.
- Public surface.
- Important algorithms.
- State transitions where applicable.
- Integration points.
- Failure modes.
- Key source files.
- Modification entry points.

Use Mermaid diagrams where useful for component flow, request lifecycle, state machines, indexing,
and data relationships.

### Sources / Integrations Pages

For each source or integration, document:

- Trust tier.
- Source URL/API or local source.
- Auth requirements.
- Cache/TTL behavior, or explicitly say none/not persisted.
- Parser/client behavior.
- Known quirks and failure modes.
- Relevant test fixtures.
- Untrusted data handling.

### Contribution / Operations / Security Pages

Deepen:

- Definition of done.
- Branching and PR flow.
- Testing layout, async patterns, fixtures, mocks, and CI mapping.
- Debug runbooks.
- Lint, format, typecheck, pre-commit status if absent, security scans if absent.
- Local/server/cloud deployment modes.
- Env vars, state, logs, health, multi-instance limitations, and releases.
- Trust boundaries, hardening, outbound access, secret handling, static analysis, and what is not
  defended.

## 6. Validation Checklist

Before committing the wiki repo:

- Every generated page has exactly one H1.
- `_Sidebar.md` links every generated page except itself.
- Every local wiki link targets an existing generated page and omits `.md`.
- No generated page is empty.
- Every page remains reachable from `_Sidebar.md` or from a linked section page.
- Exact counts in `by-the-numbers.md` are recomputed from the repository.
- Planned/future work is labeled planned/future.
- Run `git diff --check` in the wiki clone.
- Verify the published wiki URL returns HTTP 200 after push.

## 7. Suggested Implementation Order

1. Re-clone or refresh the wiki repo:

   ```bash
   git clone https://github.com/KeigoShimadaCC/agentic-knowledge-management.wiki.git /private/tmp/agentic-knowledge-management.wiki
   ```

   If the directory already exists, use `git fetch` and fast-forward it instead.

2. Recompute repo inventory and counts from tracked files.
3. Expand API/interface pages.
4. Expand data/primitives/reference pages.
5. Expand app/runtime and systems pages.
6. Expand sources/integrations pages.
7. Expand contribution, deployment, and security pages.
8. Validate structure, links, coverage, and whitespace.
9. Commit:

   ```bash
   git commit -m "docs(wiki): deepen KnowledgeOS wiki reference"
   ```

10. Push the wiki repo and verify the public URL.

## 8. Acceptance Criteria

- The wiki is meaningfully deeper than Phase 04A, not just structurally valid.
- `api--rest.md` and `api--mcp-tools.md` are usable references, not only endpoint/tool lists.
- `reference--data-models.md` and `primitives--*.md` contain exact schema and persistence
  details backed by source.
- Runtime and systems pages identify where maintainers should modify behavior.
- Sources/integrations pages explain trust and untrusted-content handling.
- Contribution and operations pages are specific enough for maintainers and AI agents to use.
- The final handoff includes the wiki URL, wiki commit hash, validation results, and changed page
  list.

