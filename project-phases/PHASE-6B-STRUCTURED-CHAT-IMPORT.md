# Phase 6B — Structured Chat Import

## Audit

- Phase 6A Chat Import Lite is present: `chat` object kind, `chats` table, raw storage, parsers, chat API, chat UI, search/chunk integration, tests, and docs.
- Phase 5 is not complete in this repo. Present: `agent_runs`, OpenAI config fields, `object_revisions` migration, and `objects.ai_generated`. Missing: AI client/router, revision model/service, Claim/Task object support, AI UI/inbox.
- Phase 6B includes only the minimal Phase 5 prerequisites needed for structured chat import. It does not implement the full Phase 5 AI Assistant or Inbox/Triage scope.

## Goal

Turn imported chats into reusable structured knowledge. Users explicitly generate a structured summary, review it, apply it, and get durable extracted Claim/Task objects linked back to exact chat turns.

## Non-Goals

- No MCP work.
- No autonomous background AI processing.
- No full AI sidebar, Inbox/Triage, or KB Q&A from Phase 5.
- No concept/project object system, career memory, or Kuzu graph sync.
- No hard deletes and no silent AI writes.

## Definition of Done

- [ ] Minimal AI client, revision service, and Claim/Task generic object support exist.
- [ ] Chat structured summary fields exist and are migrated.
- [ ] Strict structured summary schema validates AI output and turn references.
- [ ] Preview endpoint generates and stores a reviewable structured summary.
- [ ] Apply endpoint persists summary, creates revisions, logs agent runs, creates/reuses Claim/Task objects, creates graph edges, and enqueues reindex.
- [ ] Chat detail UI supports generate, preview, apply, applied summary, extracted knowledge, linked objects, provenance, and disabled/error states.
- [ ] Keyword search finds applied structured summaries and extracted Claim/Task objects without API keys.
- [ ] Tests mock AI provider and cover auth, disabled AI, malformed AI JSON, preview, apply, idempotency, edges, turn refs, reindex, search, and cross-user isolation.
- [ ] Docs and `PROGRESS.md` are updated.
- [ ] Small commits are pushed after verified slices.

## Subtask Checklist

- [ ] Subtask 0 — Audit and Phase 6B plan
- [ ] Subtask 1 — Minimal AI/revision/claim-task prerequisites
- [ ] Subtask 2 — Structured summary data model
- [ ] Subtask 3 — Structured summary schema and prompt
- [ ] Subtask 4 — Structured summary preview API
- [ ] Subtask 5 — Apply structured summary and extracted objects
- [ ] Subtask 6 — Search/index integration
- [ ] Subtask 7 — Chat detail UI
- [ ] Subtask 8 — Tests and docs

## Data Model Plan

Add `chats.structured_summary`, `structured_summary_status`, `structured_summary_agent_run_id`, `structured_summary_updated_at`, and `structured_summary_hash`.

Use generic `objects.kind = "claim"` and `objects.kind = "task"` for extracted items. Store extraction data in object metadata instead of adding specialization tables in this phase.

Concepts and project-like entities stay inside `structured_summary` unless future object kinds already exist.

## Structured Summary Schema Plan

Validate strict JSON with `title`, `summary`, `date_range`, `topics`, `key_decisions`, `open_questions`, `action_items`, `claims`, `concepts`, `suggested_links`, and `warnings`.

Every decision, question, action item, claim, and concept must include valid `turn_refs` matching `parsed_turns.turn_index`.

## Prompt Plan

The prompt must instruct the AI to use only provided chat turns, avoid invented facts, preserve uncertainty, avoid trivial overextraction, include turn references, and return strict JSON only. If the chat is too large, truncate by a configured character limit and add a warning.

## API Plan

Add authenticated, user-scoped endpoints:

```http
POST /api/v1/chats/{id}/structured-summary
GET  /api/v1/chats/{id}/structured-summary
POST /api/v1/chats/{id}/structured-summary/apply
```

Preview calls AI, validates JSON, logs `agent_runs`, stores a preview, writes an object revision, and creates no extracted objects.

Apply validates the selected summary, logs `agent_runs`, writes the applied summary and revision, creates/reuses claims/tasks, creates graph edges, and reindexes touched objects.

## Object Extraction Plan

Claims:

- `kind="claim"`
- title from the claim text
- description = full claim
- metadata includes `claim_type`, `source_chat_id`, `turn_refs`, `confidence`, `agent_run_id`, `extraction_key`, `ai_generated`

Tasks:

- `kind="task"`
- title = task text
- description includes owner/due date when present
- metadata includes `owner`, `due_at`, `source_chat_id`, `turn_refs`, `confidence`, `agent_run_id`, `extraction_key`, `ai_generated`

Use `extraction_key = sha256(chat_id + item_type + normalized_text + turn_refs)` for idempotency.

## Graph Linking Plan

Use extracted object → chat with `kind="derives_from"` for Claim/Task provenance. Store `turn_refs`, `confidence`, `agent_run_id`, and `structured_summary_hash` in edge metadata.

Suggested links may be applied only to existing user-owned objects with valid edge kinds.

## Search / Indexing Plan

Chat chunk text includes transcript plus applied structured summary text. Generic Claim/Task objects are chunked from title, description, and metadata text. Applying a summary enqueues reindex for the chat and all created/reused extracted objects.

## UI Plan

Update `/app/chats/[id]` with a structured summary panel:

- Generate button when no summary exists.
- Preview view with Apply controls.
- Applied summary view with decisions, questions, tasks, claims, concepts, links, warnings, and provenance.
- Loading/error/AI-disabled states.
- Turn reference chips that scroll to turn cards.

## Tests

Backend tests:

- auth and cross-user isolation
- AI disabled error
- valid preview schema and persisted preview status
- malformed AI JSON repair/failure behavior
- apply stores summary and revision
- apply creates/reuses Claim/Task objects
- edges preserve turn refs
- reindex enqueue
- keyword search finds summary/claims/tasks
- repeated apply idempotency

Frontend validation:

- `pnpm -F @kos/web typecheck`
- `pnpm -F @kos/web build`

## Documentation Updates

Update `PROGRESS.md`, `README.md`, `docs/DATA_MODEL.md`, `docs/API.md`, `docs/INGESTION.md`, `docs/ARCHITECTURE.md`, `docs/AGENT_GUIDE.md`, `docs/SECURITY.md`, and `docs/REVISION_HISTORY.md`.

## Risks and Mitigations

- Phase 5 mismatch: implement only minimum prerequisites required for Phase 6B.
- Invalid AI JSON: strict validation and one repair retry.
- Overextraction: prompt caps and confidence filters.
- Duplicate objects: idempotent `extraction_key`.
- User data egress: only explicit user-triggered AI call.
- Large chats: character cap and warning.
- Project scope creep: keep projects as concepts/suggestions only.
- Graph direction drift: extracted object → chat with `derives_from`.

## Validation Commands

```bash
uv run ruff check services/api/app tests/api tests/unit
PYTHONPATH=services/api uv run pytest tests/api -q
PYTHONPATH=services/api uv run pytest tests/unit -q
cd services/api && uv run alembic upgrade head
PYTHONPATH=services/api:services/worker uv run python -c "from kos_worker.tasks import reindex_object, reindex_all_objects; print('worker imports ok')"
pnpm -F @kos/web typecheck
pnpm -F @kos/web build
```
