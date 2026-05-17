# Phase PHONE-04 — Edit-Lite

**Status:** Planned
**Goal:** Safe lightweight edits on iPhone without recreating Tiptap.
**Wave:** 4
**Branch:** `phase-phone-04-edit-lite`
**Worktree:** `../kos-phone-04`
**Depends on:** PHASE-PHONE-03A (PageDetail must be stable)
**Blocks:** none

## Scope

Only `apps/ios/KnowledgeOS/Features/PageDetail/Edit*.swift` and `Features/ObjectDetail/EditMetadata*.swift`. Do **not** add a rich editor. Do **not** modify read views beyond adding an "Edit" entry point.

## Endpoints consumed

- `PATCH /api/v1/objects/{id}` (title, tags)
- `PUT   /api/v1/pages/{id}` (body)

## Tasks

1. **Edit title** sheet on ObjectDetail.
2. **Edit tags** chip editor.
3. **Edit body** plain-text editor. On save, wrap each non-empty line into a Tiptap paragraph node. Preserve unmodified blocks if a `version` field is present (server may add it; otherwise full body replace).
4. **Cancel preserves original** — no destructive auto-save.
5. **Conflict handling** if backend returns 409 — show a "page changed elsewhere" sheet with "discard" / "keep mine" choices; don't silently merge.
6. UI test: edit title, save, reopen, assert new title.

## Definition of done

- Title/tags/body edits succeed and persist.
- Page body remains valid Tiptap JSON after edits.
- Conflict path is reachable and clear.
- No formatting toolbar added (scope guard).
- `PROGRESS.md` updated.

## Out of scope

- Rich text editor.
- Image insertion.
- Real-time collaboration.
