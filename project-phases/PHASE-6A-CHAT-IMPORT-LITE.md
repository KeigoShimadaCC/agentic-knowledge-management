# Phase 6A — Chat Import Lite

## Goal

Implement first-class, searchable chat imports without AI. Users can upload or paste ChatGPT, Claude, Markdown, and plain-text transcripts; KnowledgeOS stores raw content under `LIBRARY_ROOT/chats`, renders parsed turns in the browser, and makes chat content available through the existing search and reindex pipeline.

## Scope

- Add `objects.kind = "chat"` with a `chats` specialization table.
- Parse ChatGPT `conversations.json` batch exports into one chat object per conversation.
- Parse Markdown/plain transcripts with common speaker labels, with graceful fallback to one `unknown` turn.
- Store raw chat files and import metadata under `library/chats/{provider}/...`.
- Add authenticated `/api/v1/chats` import/list/detail/raw/delete/restore/reindex endpoints.
- Add keyword search and chunking support for `chat.content_text`.
- Add `/app/chats` and `/app/chats/[id]` UI routes.
- Route search and graph object navigation for `kind=chat`.

## Non-Goals

- No LLM summarization or extraction.
- No claims/tasks/concepts/projects generation.
- No MCP chat import tools.
- No hard-delete of raw imported files.
- No Kuzu graph sync changes.

## Subtasks

- [x] Subtask 0 — Audit + Phase 6A plan artifact
- [x] Subtask 1 — Chat data model and migration
- [x] Subtask 2 — Chat parser and raw storage services
- [x] Subtask 3 — Chat API endpoints
- [x] Subtask 4 — Search/indexing integration
- [x] Subtask 5 — Chat UI
- [x] Subtask 6 — Search/graph routing polish
- [x] Subtask 7 — Tests, docs, progress, final validation

## Storage Contract

All chat files stay under `settings.library_root / "chats"`. Database rows store relative paths only. Delete operations soft-delete the base object and never remove raw files.

Single imports use:

```text
chats/{provider}/{chat_object_id}/raw.{json|md|txt}
chats/{provider}/{chat_object_id}/metadata.json
```

ChatGPT batch imports additionally store the exact uploaded export once at:

```text
chats/chatgpt/imports/{batch_uuid}/raw.json
```

## Validation

Phase 6A coverage includes parser unit tests, chat API import/CRUD/raw/restore tests, chunking tests, keyword search tests, deleted-object search exclusion, and cross-user 404 access checks.
