# Revision History Design

## Why This Matters Before Agent Writes

KnowledgeOS will eventually let AI agents (via MCP write tools or the AI assistant) directly modify pages and objects. Without a revision history, an agent that overwrites a page with incorrect content leaves no way to inspect what changed or undo the damage.

**Revision history is a prerequisite for enabling MCP write tools (`update_page`, `archive_object`, etc.).**

The `agent_runs` table already records that an agent performed an action. `object_revisions` records what the state of each affected object was before and after. Together they form a complete audit trail.

This system is planned for implementation in Phase 5 (AI Assistant) or Phase 7 (MCP Server) — whichever arrives first. Phase 3 (Search) and Phase 4 (Graph Lite) do not require it.

---

## Planned Table: `object_revisions`

```sql
CREATE TABLE object_revisions (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  object_id       uuid NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
  agent_run_id    uuid NULL REFERENCES agent_runs(id) ON DELETE SET NULL,
  change_type     text NOT NULL,      -- 'create' | 'update' | 'soft_delete' | 'restore'
  before_json     jsonb NULL,         -- snapshot of affected row(s) before change
  after_json      jsonb NULL,         -- snapshot of affected row(s) after change
  changed_by      text NOT NULL,      -- 'user:<user_id>' or 'agent:<agent_name>'
  change_summary  text NULL,          -- human-readable description of what changed
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_object_revisions_object_id ON object_revisions (object_id);
CREATE INDEX idx_object_revisions_user_id   ON object_revisions (user_id);
CREATE INDEX idx_object_revisions_agent_run ON object_revisions (agent_run_id)
  WHERE agent_run_id IS NOT NULL;
```

---

## Scope of `before_json` / `after_json`

A revision captures the complete state of the affected specialization row plus the base `objects` row at the time of change. For a page update:

```json
{
  "object": {"id": "...", "title": "...", "tags": [], "metadata": {}, "updated_at": "..."},
  "page": {"content_json": {...}, "content_text": "...", "word_count": 123, "version": 5}
}
```

For a source soft-delete:

```json
{
  "object": {"id": "...", "title": "...", "deleted_at": null},
  "source": {"ingestion_status": "ready", "extracted_text": "..."}
}
```

`before_json` is `null` for `create` events. `after_json` is `null` for hard-delete events (which we don't currently support — soft-delete only).

---

## Relation to `agent_runs`

Every MCP write tool call creates one `agent_runs` row. That row records:
- Which agent called which tool
- The tool's input and output
- Whether it succeeded or errored

For each object modified by the tool call, a corresponding `object_revisions` row is created and linked via `agent_run_id`. This means a single `agent_runs` row may have many `object_revisions` rows (e.g., if a tool archives 10 objects at once).

User-initiated edits (from the browser editor) also create `object_revisions` rows, but with `agent_run_id = null` and `changed_by = "user:<user_id>"`. This keeps the revision log complete regardless of whether a human or agent made the change.

---

## Rollback Strategy

Rolling back a page to a previous revision:

1. Read the target `object_revisions` row for the desired state.
2. Extract `before_json.page` and `before_json.object`.
3. Write those values back to the `pages` and `objects` rows via the API.
4. Create a new `object_revisions` row with `change_type = "restore"`, `before_json` = current state, `after_json` = restored state, `change_summary = "Restored to revision <id>"`.

Rollback is itself an audited write — it does not delete the revision that is being undone.

---

## Soft-Delete Interaction

When an object is soft-deleted (`deleted_at` set), its revision history is preserved. The `object_id` FK uses `ON DELETE CASCADE` — if we ever hard-delete an object (which we currently never do), the revisions would cascade-delete too. This is intentional: hard deletes are reserved for GDPR-style erasure, which should also erase revision history.

Restored objects (clearing `deleted_at`) produce a `"restore"` revision row that links back to the soft-delete row.

---

## Implementation Notes

When implementing, consider:

1. **Write the revision inside the same DB transaction as the object change.** If the transaction rolls back, the revision row rolls back too. No orphaned revisions.
2. **Do not snapshot binary content.** `before_json.page.content_json` is fine for structured Tiptap JSON. Never put file paths or asset binaries into revision JSON.
3. **Keep `before_json` compact.** Exclude `created_at` from the diff payload (it never changes). Include `updated_at`, `version`, and all user-visible fields.
4. **Index for fast history lookup.** The `object_id` index is the most important — users will view history for a specific object.
5. **Rate-limit revision writes.** The 800ms Tiptap auto-save creates a new `object_revisions` row on every save if not throttled. Consider: write revision only if `updated_at` gap > 30s, or only when the agent (not user auto-save) triggers the change.

---

## Future: Revision Viewer UI

Phase 8 (Multi-Pane Workspaces) is a good candidate for a first revision viewer: a timeline panel that shows when a page was edited, by whom (user vs. which agent), and lets you restore a previous version with one click. This pairs well with the audit/accountability requirements of MCP write tools.
