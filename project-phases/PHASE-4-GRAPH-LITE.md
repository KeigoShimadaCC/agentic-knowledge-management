# KnowledgeOS — Phase 4 Graph Lite Plan

## Phase 3 Audit

Phase 3 is not complete in the current repo state.

- Complete: chunk schema readiness, chunking service, embedding provider abstraction, Qdrant client setup.
- In progress: reindex worker wiring exists in the worktree but is not finalized, tested, or committed.
- Not present: keyword/vector/hybrid search endpoints, search router, Cmd+K search UI, and search API tests.

Phase 4 must therefore avoid touching Phase 3 search/indexing surfaces while Phase 3 is still in progress.

## Goal

Build Graph Lite on top of canonical Postgres `edges`, backend first.

Phase 4A implements the stable graph API foundation:

- edge kind taxonomy,
- edge validation and idempotent create,
- object-centered edge/backlink/related endpoints,
- simple Postgres traversal up to depth 2,
- tests and documentation.

Graph UI, reusable object picker, typed link modal, right-panel backlinks, and `POST /api/v1/search/graph` are deferred until Phase 3 search endpoints and UI are stable.

## Non-Goals

- No Kuzu integration.
- No visual graph canvas.
- No AI link suggestion.
- No MCP tools.
- No graph embeddings.
- No changes to Qdrant, chunks, reindex worker, or Phase 3 search routes.

## Definition of Done

- Edge kinds are validated by code-level constants, not a DB enum.
- Existing data remains valid, including `link`, `related`, `citation`, `cites`, and `derives_from`.
- Creating the same `(source_id, target_id, kind)` is idempotent.
- Soft-deleted duplicate edges are restored instead of duplicated.
- Both source and target objects must belong to the current user.
- Deleted objects are excluded by default.
- Object graph APIs exist:
  - `GET /api/v1/objects/{id}/edges`
  - `GET /api/v1/objects/{id}/backlinks`
  - `GET /api/v1/objects/{id}/related`
- Backend tests cover validation, ownership, deleted objects, backlinks, related, and depth behavior.
- Docs and `PROGRESS.md` describe Graph Lite accurately.

## Edge Taxonomy

Canonical edge kinds:

- `links_to`
- `cites`
- `derives_from`
- `mentions`
- `supports`
- `contradicts`
- `related_to`
- `summarizes`
- `belongs_to_project`
- `evidence_for`
- `created_from`

Legacy accepted kinds:

- `link` — conceptual alias for `links_to`
- `related` — conceptual alias for `related_to`
- `citation` — legacy citation kind; prefer `cites`
- `embed`
- `child`
- `tag`

Do not rewrite legacy edge rows automatically.

## API Plan

Keep existing endpoints backward-compatible:

- `POST /api/v1/edges`
- `GET /api/v1/edges`
- `DELETE /api/v1/edges/{id}`

Extend graph APIs:

- `GET /api/v1/objects/{id}/edges?direction=incoming|outgoing|both&kind=&include_deleted=`
- `GET /api/v1/objects/{id}/backlinks?kind=`
- `GET /api/v1/objects/{id}/related?depth=1|2&edge_types=&direction=both&limit=`

Object-centered responses include object summaries, edge direction relative to the requested object, edge kind, weight, metadata, timestamps, and traversal distance where applicable.

## Subtasks

### Subtask 0 — Plan artifact

Create this file and update `PROGRESS.md`.

Commit: `docs: add Phase 4 Graph Lite plan`

### Subtask 1 — Edge taxonomy and validation

Add code-level edge kind constants and use them in schemas/services.

Commit: `feat(api): define graph edge kind taxonomy`

### Subtask 2 — Harden edge API

Validate ownership, kind, deleted object exclusion, metadata, weight, idempotency, and soft-delete restoration in the service layer.

Commit: `feat(api): harden edge API for graph lite`

### Subtask 3 — Object graph endpoints

Add object-centered edges, backlinks, and related endpoints using Postgres queries over `edges`.

Commit: `feat(api): add backlinks and related object endpoints`

### Subtask 4 — Tests and docs

Add graph API tests and update API/data model/architecture/agent docs.

Commit: `test: add graph lite API coverage`
Commit: `docs: document graph lite APIs and edge taxonomy`

## Validation

Run:

```bash
cd tests && PYTHONPATH=../services/api uv run pytest api/ -v
cd services/api && uv run ruff check .
pnpm -F @kos/web typecheck
```

Frontend build is required only when Phase 4B UI work starts.

## Risks and Mitigations

- Phase 3 conflict: keep Phase 4A away from search router, Qdrant, chunks, reindex, and Cmd+K UI.
- Edge kind drift: use code constants and documentation; avoid DB enum migration.
- Cross-user graph leakage: validate both source and target ownership in service functions.
- Deleted object leakage: exclude deleted objects by default.
- Premature graph infra: defer Kuzu until Postgres traversal is insufficient.

## Phase 4B Roadmap

After Phase 3 search UI stabilizes:

- reusable `ObjectPicker`,
- typed link creation UI,
- backlinks and related panels,
- citation UX cleanup,
- optional `POST /api/v1/search/graph` in the Phase 3 search router.
