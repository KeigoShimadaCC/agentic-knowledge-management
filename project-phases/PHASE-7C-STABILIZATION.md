  ￼  ￼  ￼

# PHASE-7C — Stabilization
> **Type:** Stabilization phase  
> **Status:** Planned  
> **Scope:** Wave 1 only — MCP read tooling, local Docker/dev ops, and web routing/navigation cleanup  
> **Primary goal:** Turn the current feature-rich repo into a coherent, runnable, agent-accessible local knowledge system before starting MCP write tools or additional product features.
---
## Context
The repo has already shipped most core product phases:
- Phase 2 — Sources & Rich Media
- Phase 3 — Search
- Phase 4 — Graph Lite
- Phase 5 — AI Assistant + Inbox/Triage
- Phase 6A/6B — Chat Import and structured summaries
- Phase 8A/8B — Workspace Lite and Workspaces backend foundation
However, the post-Phase-7A audit surfaced three high-priority stabilization needs:
1. **MCP read access is not fully closed out.**
   Phase 7A planned a local-only stdio MCP server with read-safe tools, internal-token auth, allowlisted tools, and no write/shell/file tools. This surface should be completed and verified before any MCP write tools are planned or implemented.
2. **The local Docker experience is not truly end-to-end.**
   The API can enqueue ingestion and reindex jobs, but the default Docker Compose stack must also run the RQ worker so uploads and indexing actually complete after `docker compose up -d`.
3. **The web app has visible navigation/routing inconsistencies.**
   Sidebar links and route files disagree in multiple places. Some links are broken. Routes for pages, sources, assets, chats, inbox, and trash should follow one convention.
Phase 7C bundles these three Wave 1 tracks into one coordinated stabilization phase.
---
## Non-goals
Do **not** implement these in Phase 7C:
- MCP write tools:
  - `create_page`
  - `update_page`
  - `create_edge`
  - `archive_object`
  - `ingest_url`
  - `ingest_file`
- Any destructive or hard-delete behavior
- New AI product features
- New graph engine work such as Kùzu
- Major search-ranking redesign
- Full E2E test suite expansion beyond smoke checks needed for this phase
- Large documentation rewrite beyond docs touched by the three Phase 7C tracks
Phase 7B MCP write tools should remain a separate future phase.
---
## Definition of Done
Phase 7C is complete when all of the following are true:
### MCP
- [ ] `services/mcp/` has a working local stdio MCP server.
- [ ] MCP is disabled by default with `MCP_ENABLED=false`.
- [ ] FastAPI accepts `X-KOS-Internal-Token` as an internal MCP auth path when configured.
- [ ] MCP tool allowlist is enforced at startup.
- [ ] No write tools are registered.
- [ ] No shell tools are registered.
- [ ] No arbitrary file tools are registered.
- [ ] `search_objects` works against the keyword search API.
- [ ] `hybrid_search` works against the hybrid search API and degrades gracefully if embeddings are disabled.
- [ ] `get_object` returns compact object metadata with no secrets.
- [ ] `get_page` returns title and readable content, omitting editor JSON by default.
- [ ] `get_source` returns metadata and truncated extracted text.
- [ ] `get_related_objects` works with depth capped at 2.
- [ ] `answer_from_kb` is either:
  - wired to `POST /api/v1/ai/answer` with graceful AI-disabled fallback, or
  - removed from the allowed MCP tool surface and clearly documented as unavailable.
- [ ] MCP unit tests pass.
- [ ] MCP config/security tests pass.
- [ ] `docs/MCP_TOOLS.md`, `docs/SECURITY.md`, and `docs/AGENT_GUIDE.md` reflect the actual MCP behavior.
### Local ops / Docker
- [ ] `infra/docker-compose.yml` starts an RQ worker service by default.
- [ ] `docker compose -f infra/docker-compose.yml up -d` is sufficient to run:
  - Postgres
  - Redis
  - Qdrant
  - API
  - Web
  - Worker
- [ ] Source ingestion jobs do not stay stuck in `pending` after a normal Docker startup.
- [ ] Reindex jobs can be processed by the worker.
- [ ] Worker uses the correct in-container service URLs:
  - `postgres:5432`
  - `redis:6379`
  - `qdrant:6333`
- [ ] Host-facing docs clearly state the published ports:
  - API: `127.0.0.1:8001`
  - Web: `127.0.0.1:3000`
  - Postgres: `127.0.0.1:5433`
  - Redis: `127.0.0.1:6379`
  - Qdrant HTTP: `127.0.0.1:6333`
  - Qdrant gRPC: `127.0.0.1:6334`
- [ ] `infra/.env.example` has exactly one `MCP_INTERNAL_TOKEN` entry.
- [ ] `MCP_API_BASE_URL` default matches the normal host-side Docker topology.
- [ ] README and relevant docs no longer contain misleading local port examples.
### Web routing / navigation
- [ ] Every Sidebar link points to a real route.
- [ ] Trash navigation is fixed by either:
  - building a minimal Trash view with restore, or
  - removing the Sidebar link until a view exists.
- [ ] Assets route mismatch is resolved.
- [ ] Routes are unified under one convention, preferably `/app/...`.
- [ ] `objectRoute()` returns correct routes for:
  - page
  - source
  - chat
  - asset
- [ ] Search result navigation works.
- [ ] Backlinks/related-object navigation works.
- [ ] Workspace Lite side-pane opening still works.
- [ ] `pnpm -F web typecheck` passes.
- [ ] `pnpm -F web build` passes.
---
## Recommended branch/worktree split
Run Phase 7C as three parallel branches or worktrees.
### Branch A — MCP
```text
phase7c-mcp-read-tools

Owns:

* services/mcp/**
* MCP-related API auth changes
* MCP config/env validation
* MCP tests
* docs/MCP_TOOLS.md
* MCP sections of docs/SECURITY.md
* MCP sections of docs/AGENT_GUIDE.md

Avoid touching:

* Web routes
* Docker Compose except env names needed for MCP
* Unrelated docs

Branch B — Local ops / Docker

phase7c-local-dev-infra

Owns:

* infra/docker-compose.yml
* Dockerfile changes needed for worker
* infra/.env.example
* README local setup sections
* Local port documentation
* Worker startup documentation

Avoid touching:

* MCP tool implementation
* Web route files
* Product UI

Branch C — Web routing / navigation

phase7c-web-routing-nav

Owns:

* apps/web/src/app/**
* apps/web/src/components/layout/Sidebar.tsx
* apps/web/src/lib/objectRouting.ts
* UI route references
* Route-related docs only if needed

Avoid touching:

* Backend API behavior unless a missing endpoint is truly required
* MCP
* Docker Compose

⸻

Workstream A — MCP read-tools completion

Goal

Complete the local-only read-safe MCP layer so external coding/research agents can inspect the knowledge base without receiving write permissions or filesystem/shell access.

Required behavior

The MCP server should expose only bounded, read-only tools. It should call the FastAPI backend rather than reading the database or local files directly.

Tools to implement or verify

Tool	Behavior	Write?	Notes
search_objects	Calls keyword search API	No	Must work without embeddings
hybrid_search	Calls hybrid search API	No	Graceful fallback if vector search unavailable
get_object	Gets compact object metadata	No	Must redact secrets
get_page	Gets page title/content text	No	Omit editor JSON by default
get_source	Gets source metadata/extracted text	No	Truncate long extracted text
get_related_objects	Calls graph/related endpoint	No	Depth capped at 2
answer_from_kb	Calls AI answer endpoint or is removed	No	Must handle missing AI key gracefully

Implementation tasks

A1 — Audit current MCP implementation

* Inspect:
    * services/mcp/kos_mcp/config.py
    * services/mcp/kos_mcp/client.py
    * services/mcp/kos_mcp/tools.py
    * services/mcp/tests/**
    * docs/MCP_TOOLS.md
* Confirm which tools are registered, which are stubs, and which are included in the default allowlist.
* Produce a short implementation note in the PR summary.

A2 — Enforce config invariants

* MCP must default to disabled.
* If MCP_ENABLED=true, require a non-empty internal token.
* Require allowlist entries to correspond to registered tools.
* Fail fast on unknown allowed tool names.
* Never silently expose extra tools.

A3 — Internal-token API auth

* Ensure FastAPI accepts X-KOS-Internal-Token only when:
    * the configured token is non-empty
    * the request token matches exactly
* Do not bypass ownership checks unless the app is explicitly single-user and this is documented.
* Do not log token values.

A4 — Implement/verify read tools

Each tool should:

* validate inputs
* call the API client
* return compact JSON
* redact secrets
* avoid leaking raw internal headers
* avoid returning huge payloads by default
* produce readable error payloads for expected failures

A5 — Decide answer_from_kb

Recommended approach:

* Wire answer_from_kb to POST /api/v1/ai/answer.
* Return:
    * answer
    * citations
    * context_count
    * agent_run_id
* If the backend returns AI-disabled / missing API key:
    * return a structured error such as:

{
  "error": "ai_disabled",
  "message": "AI answering is unavailable because no model API key is configured."
}

Alternative:

* Remove answer_from_kb from the default allowlist and tool registry.
* Document it as planned for a later phase.

Do not leave it as an advertised broken stub.

A6 — Tests

Add or verify tests for:

* MCP disabled by default
* MCP requires internal token when enabled
* unknown allowlist tool fails startup/config validation
* each read tool happy path with mocked API client
* API errors are returned cleanly
* answer_from_kb happy path or explicit unavailable behavior
* no write tools in list_tools
* no shell/file tools in list_tools
* secrets are redacted from tool responses

A7 — Docs

Update:

* docs/MCP_TOOLS.md
* docs/SECURITY.md
* docs/AGENT_GUIDE.md
* infra/.env.example if env behavior changes

Verification commands

uv run --project services/mcp pytest services/mcp/tests -v
uv run --project tests pytest tests/api -v
uv run --project services/mcp kos-mcp

Manual smoke:

1. Start local stack.
2. Enable MCP with a local token.
3. Run MCP server.
4. Call:
    * search_objects
    * hybrid_search
    * get_object
    * get_page
    * get_source
    * get_related_objects
    * answer_from_kb if enabled

Suggested commits

feat(mcp): complete read-only tool surface for local agents
feat(api): support internal-token auth for mcp calls
test(mcp): add config and read-tool coverage
docs(mcp): document read tools and security model

⸻

Workstream B — Local Docker/dev ops

Goal

A fresh clone should be able to run the full local system with one Docker Compose command. Source ingestion and reindex jobs must process without manual worker startup.

Implementation tasks

B1 — Add worker service to Docker Compose

Add a worker service to infra/docker-compose.yml.

Requirements:

* Uses the existing workspace packages.
* Runs the RQ worker for the kos-ingest queue.
* Shares the same library volume as the API.
* Depends on healthy Postgres, Redis, and Qdrant.
* Uses sync Postgres URL if the worker uses psycopg2.
* Uses in-container service hostnames.

Example shape:

worker:
  build:
    context: ..
    dockerfile: infra/Dockerfile.api
    target: development
  container_name: kos-worker
  restart: unless-stopped
  working_dir: /worker
  env_file: .env
  environment:
    DATABASE_URL: postgresql://${POSTGRES_USER:-kos}:${POSTGRES_PASSWORD:-kospass}@postgres:5432/${POSTGRES_DB:-knowledgeos}
    REDIS_URL: redis://redis:6379/0
    QDRANT_URL: http://qdrant:6333
    LIBRARY_ROOT: /library
    PYTHONPATH: /app:/worker
  volumes:
    - ../services/api:/app
    - ../services/worker:/worker
    - library-data:/library
  command:
    - sh
    - -c
    - "exec uv run rq worker kos-ingest --url $REDIS_URL"
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy
    qdrant:
      condition: service_healthy
  logging: *default-logging

Adjust to match the actual Dockerfile and workspace structure.

B2 — Verify worker package dependencies inside container

Confirm the worker container has:

* rq
* psycopg2-binary
* pypdf
* pillow
* httpx
* beautifulsoup4
* youtube-transcript-api
* qdrant-client
* embedding provider deps if needed

Do not rely on host-side Python packages.

B3 — Fix .env.example

* Collapse duplicate MCP sections.
* Ensure only one MCP_INTERNAL_TOKEN= entry exists.
* Set host-side MCP default to match Docker Compose:

MCP_API_BASE_URL=http://127.0.0.1:8001

Add comments:

# Host-side default: matches docker compose API publishing (127.0.0.1:8001 -> api:8000).
# If running kos-mcp inside the Docker network, use http://api:8000.
# If running the API natively on port 8000, use http://127.0.0.1:8000.

B4 — Add local ports cheat sheet

Update README with:

Service	Host	In-container
Web	127.0.0.1:3000	3000
API	127.0.0.1:8001	8000
Postgres	127.0.0.1:5433	5432
Redis	127.0.0.1:6379	6379
Qdrant HTTP	127.0.0.1:6333	6333
Qdrant gRPC	127.0.0.1:6334	6334

B5 — Fix docs with wrong host-side ports

Search and fix misleading examples:

grep -R "localhost:5432\|127.0.0.1:5432\|localhost:8000\|127.0.0.1:8000" README.md docs project-phases infra -n

Keep postgres:5432 only for Docker-internal URLs.

B6 — Smoke-test ingestion

Manual test:

1. docker compose -f infra/docker-compose.yml up -d --build
2. Create/login user.
3. Upload a small PDF or CSV as a Source.
4. Confirm source status transitions:
    * pending
    * running
    * success
5. Confirm worker logs show job execution.

B7 — Reindex smoke

If scripts/reindex.py exists, verify it can enqueue or execute reindex jobs against the Docker stack.

If it does not exist, do not build a large new system in this workstream. Add only minimal docs pointing to existing worker task entrypoints unless explicitly required.

Verification commands

docker compose -f infra/docker-compose.yml up -d --build
docker compose -f infra/docker-compose.yml ps
docker compose -f infra/docker-compose.yml logs worker
docker compose -f infra/docker-compose.yml logs api

Expected:

* kos-worker is running.
* Upload/reindex jobs are consumed.
* No job remains stuck in Redis under normal operation.

Suggested commits

infra(compose): add rq worker service for ingestion and reindex
infra(env): deduplicate mcp token and align api base url
docs(dev): document local docker port mapping
docs(ingestion): clarify worker-backed local ingestion flow

⸻

Workstream C — Web routing and navigation cleanup

Goal

Make the web route tree predictable and remove broken navigation from the primary UI.

Preferred routing convention

Use /app/... for authenticated application routes.

Recommended target:

Resource	Target URL
App dashboard / all objects	/app
Pages list	/app/pages
Page detail	/app/pages/[id]
Sources list	/app/sources
Source detail	/app/sources/[id]
Assets list	/app/assets
Chats list	/app/chats
Chat detail	/app/chats/[id]
Inbox	/app/inbox
Trash	/app/trash

Implementation tasks

C1 — Route inventory

Before moving files, inventory all current route references:

grep -R "\"/pages\|'/pages\|\"/sources\|'/sources\|\"/assets\|'/assets\|\"/inbox\|'/inbox\|\"/app/assets\|'/app/assets\|\"/app/trash\|'/app/trash" apps/web/src -n

Document findings in the PR summary.

C2 — Move route files

Move route files to the preferred /app/... convention.

Likely moves:

apps/web/src/app/(app)/pages/[id]/page.tsx
  -> apps/web/src/app/(app)/app/pages/[id]/page.tsx
apps/web/src/app/(app)/sources/page.tsx
  -> apps/web/src/app/(app)/app/sources/page.tsx
apps/web/src/app/(app)/sources/[id]/page.tsx
  -> apps/web/src/app/(app)/app/sources/[id]/page.tsx
apps/web/src/app/(app)/assets/page.tsx
  -> apps/web/src/app/(app)/app/assets/page.tsx
apps/web/src/app/(app)/inbox/page.tsx
  -> apps/web/src/app/(app)/app/inbox/page.tsx

Adjust based on actual current file tree.

C3 — Fix objectRoute

Update apps/web/src/lib/objectRouting.ts.

Expected behavior:

if (kind === "page") return `/app/pages/${id}`;
if (kind === "source") return `/app/sources/${id}`;
if (kind === "chat") return `/app/chats/${id}`;
if (kind === "asset") return "/app/assets";

If assets eventually get detail pages, add that later. Do not invent asset detail routing unless the app already supports it.

C4 — Fix Sidebar

Update apps/web/src/components/layout/Sidebar.tsx.

Expected links:

{ href: "/app", label: "All Objects", ... }
{ href: "/app/pages", label: "Pages", ... }
{ href: "/app/sources", label: "Sources", ... }
{ href: "/app/assets", label: "Assets", ... }
{ href: "/app/chats", label: "Chats", ... }
{ href: "/app/inbox", label: "Inbox", ... }
{ href: "/app/trash", label: "Trash", ... } // only if C5 builds it

C5 — Fix Trash

Recommended: build a minimal Trash view.

Requirements:

* Route: /app/trash
* Fetches deleted objects from existing trash endpoint.
* Renders:
    * title
    * kind
    * deleted date if available
    * restore button
* Restore button calls existing restore endpoint.
* No hard-delete button.
* Empty state when trash is empty.

If this is too large for the routing PR, remove the Trash sidebar link and leave a TODO.

Do not leave a broken Trash link.

C6 — Update route references

Update all hard-coded links in:

* search components
* graph panels
* backlinks/related panels
* Workspace Lite side-pane open actions
* page/source/chat cards
* tests or fixtures that reference frontend routes

C7 — Preserve Workspace Lite behavior

Workspace Lite from Phase 8A must still open objects in the side pane.

Check:

* search result “open in side pane”
* backlinks “open in side pane”
* related objects “open in side pane”
* direct object navigation

C8 — Compatibility redirects, optional

Because this is a local-first app, hard redirects are optional.

If simple, add redirect routes from old paths to new paths:

Old	New
/pages/[id]	/app/pages/[id]
/sources	/app/sources
/sources/[id]	/app/sources/[id]
/assets	/app/assets
/inbox	/app/inbox

If redirect implementation creates complexity, skip it and update all app-internal links only.

Verification commands

pnpm -F web typecheck
pnpm -F web build

Manual click test:

* Sidebar:
    * All Objects
    * Pages
    * Sources
    * Assets
    * Chats
    * Inbox
    * Trash, if present
* Open page detail.
* Open source detail.
* Open chat detail.
* Open search result.
* Open related/backlinked object.
* Open object in Workspace Lite side pane.

Suggested commits

refactor(web): unify authenticated routes under /app
fix(web): repair sidebar navigation links
feat(web): add minimal trash view with restore
fix(web): update object routing for pages sources chats assets

⸻

Merge strategy

Use stacked or parallel PRs, but merge in this order:

1. phase7c-local-dev-infra
2. phase7c-mcp-read-tools
3. phase7c-web-routing-nav

Reasoning:

* Local ops affects how MCP and web are manually tested.
* MCP can be tested more reliably once Docker/local stack is stable.
* Web routing is mostly frontend-only and can merge after infra/MCP without blocking them.

If route cleanup touches docs also edited by MCP/infra branches, resolve by keeping the route cleanup narrowly focused and doing final doc reconciliation in a later Wave 2 docs PR.

⸻

Required final validation

Before marking Phase 7C complete, run:

# Backend/API tests
uv run --project tests pytest tests/api -v
# MCP tests
uv run --project services/mcp pytest services/mcp/tests -v
# Web validation
pnpm -F web typecheck
pnpm -F web build
# Local stack
docker compose -f infra/docker-compose.yml up -d --build
docker compose -f infra/docker-compose.yml ps

Manual validation checklist:

* Fresh Docker stack starts.
* Worker container is running.
* Uploading a source completes ingestion.
* Search works.
* MCP search tool works.
* MCP object-fetch tool works.
* MCP does not expose writes.
* Sidebar has no broken links.
* Workspace Lite still opens objects in side pane.

⸻

Progress update template

When implementing this phase, update PROGRESS.md with a section like:

## Phase 7C — Wave 1 Stabilization 🚧 In Progress
**Goal:** Stabilize MCP read access, local Docker ingestion, and web routing/navigation before starting MCP write tools.
See [`project-phases/PHASE-7C-WAVE-1-STABILIZATION.md`](project-phases/PHASE-7C-WAVE-1-STABILIZATION.md).
- [ ] **Track A — MCP read tools:** local stdio server, internal-token auth, allowlist, read-only tool surface, tests, docs
- [ ] **Track B — Local ops:** Docker worker service, env defaults, local port docs, ingestion smoke
- [ ] **Track C — Web routing:** route convention cleanup, Sidebar fixes, Trash handling, Workspace Lite route validation

When complete:

## Phase 7C — Wave 1 Stabilization ✅ Complete
**Goal:** Stabilize MCP read access, local Docker ingestion, and web routing/navigation before starting MCP write tools.
- [x] **Track A — MCP read tools:** local stdio server, internal-token auth, allowlist, read-only tools, tests, docs
- [x] **Track B — Local ops:** Docker worker service, env defaults, local port docs, ingestion smoke
- [x] **Track C — Web routing:** unified `/app/...` routes, Sidebar fixes, Trash handling, Workspace Lite validation

⸻

Handoff prompt for coding agents

Use this prompt to delegate each workstream.

You are working in the agentic-knowledge-management repo.
Implement Phase 7C Wave 1 Stabilization for the assigned workstream only.
Read first:
- project-phases/PHASE-7C-WAVE-1-STABILIZATION.md
- PROGRESS.md
- CLAUDE.md
- AGENTS.md, if present
Your assigned workstream is: <A MCP | B Local Ops | C Web Routing>.
Rules:
- Stay inside your assigned workstream.
- Do not implement MCP write tools.
- Do not add shell/file MCP tools.
- Do not add hard-delete behavior.
- Prefer small, reviewable commits.
- Update docs only where directly affected by your changes.
- Add or update tests for changed behavior.
- Run the verification commands listed for your workstream.
- In your final message, report:
  1. Files changed
  2. Behavior changed
  3. Tests run
  4. Manual smoke checks performed
  5. Any remaining risks or follow-up tasks