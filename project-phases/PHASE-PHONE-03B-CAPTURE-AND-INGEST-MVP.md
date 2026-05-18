# Phase PHONE-03B — Capture & Ingest MVP

**Status:** Complete
**Goal:** Exploit what the iPhone is good at — quick capture of text and photos into the KB.
**Wave:** 3 (parallel with 03A, 03C)
**Branch:** `phase-phone-03b-capture-ingest`
**Worktree:** `worktrees/kos-phone-03b`
**Depends on:** PHASE-PHONE-02A
**Blocks:** PHASE-PHONE-05 (offline queue extends this)

## Scope

Only `apps/ios/KnowledgeOS/Features/Capture/**` and the **body** of `Features/Root/CaptureTab.swift` (placeholder shipped by 02A). May extend `Core/API/MultipartUpload.swift` if missing pieces are needed. Do **not** modify read screens (03A owns those). Do **not** modify `MainTabView.swift` (tab order is frozen by 02A).

## Endpoints consumed

- `POST /api/v1/pages` (quick note)
- `POST /api/v1/assets/upload` and `POST /api/v1/assets/upload?create_source=true`
- `GET  /api/v1/sources/{id}` (poll ingestion status post-upload)

## Tasks

1. **Capture entry point** in the Capture tab body owned by this phase. Home remains owned by PHONE-03A; shared navigation stays in `MainTabView.swift`. Accessibility id `kos.capture.entry`.
2. **Quick text note** screen: title + body text fields. `POST /api/v1/pages` with Tiptap JSON wrapping the plain text in paragraphs. Show success toast + link to new page.
3. **Clipboard import**: button to paste clipboard contents into the note body.
4. **Photo/file upload**: `PhotosPicker` (iOS 17+) for images; `fileImporter` for documents. Upload via `MultipartUpload`. Default `create_source=true`. Show progress per file.
5. **Ingestion status**: after upload, navigate to a status view that polls `GET /api/v1/sources/{id}` every 2s until status is `ready` or `failed` (max 60s, then keep a manual refresh button).
6. **Retry** failed uploads from a small in-memory queue (full persistent queue is PHASE-PHONE-05's job).
7. **No silent retries** to external services; no direct filesystem writes; no compose of `Authorization` outside the existing `APIClient`.

## Definition of done

- Create note from iPhone → page is created and visible in web UI.
- Upload photo → asset row + source row appears; source eventually ingests.
- Failed upload (kill the backend mid-flight) is retryable from UI.
- No new network code outside `APIClient` / `MultipartUpload`.
- `PROGRESS.md` updated.

## Validation

```bash
docker compose -f infra/docker-compose.yml up -d
cd apps/ios
xcodebuild -project KnowledgeOS.xcodeproj -scheme KnowledgeOS \
  -destination 'platform=iOS Simulator,name=iPhone 16' \
  -only-testing:KnowledgeOSTests test
# Manual: simulator drag a JPEG to Files; capture flow; assert ingestion succeeds.
```

## Out of scope

- Share Extension (later phase).
- Persistent offline queue (PHASE-PHONE-05).
- Editing existing pages (PHASE-PHONE-04).
