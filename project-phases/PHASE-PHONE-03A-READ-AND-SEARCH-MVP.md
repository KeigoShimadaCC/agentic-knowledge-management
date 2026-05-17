# Phase PHONE-03A — Read & Search MVP

**Status:** Planned
**Goal:** Make the app actually useful: search the KB, browse recent objects, read pages/sources/chats/projects.
**Wave:** 3 (parallel with 03B, 03C)
**Branch:** `phase-phone-03a-read-search`
**Worktree:** `../kos-phone-03a`
**Depends on:** PHASE-PHONE-02A
**Blocks:** PHASE-PHONE-04, 05 (page detail must be stable)

## Scope

Only `apps/ios/KnowledgeOS/Features/{Home,Search,ObjectDetail,PageDetail,SourceDetail,ChatDetail,ProjectDetail,Settings}/**` and read-only ViewModels. Do **not** modify `Core/API/` shapes; if a DTO is missing, add it in `Core/API/DTOs/` with a one-line justification.

**Nav contract:** 02A ships `Features/Root/MainTabView.swift` and the five tab placeholders (`HomeTab`, `SearchTab`, `CaptureTab`, `AITab`, `SettingsTab`). This phase replaces the **body** of `HomeTab.swift`, `SearchTab.swift`, and `SettingsTab.swift` only. Do **not** modify `MainTabView.swift` (tab order is frozen). Do **not** touch `CaptureTab.swift` (03B) or `AITab.swift` (03C).

## Endpoints consumed

- `GET /api/v1/objects` (recent, paginated)
- `GET /api/v1/objects/{id}`
- `GET /api/v1/pages/{id}`
- `GET /api/v1/sources/{id}`, `GET /api/v1/sources/{id}/text`, `GET /api/v1/sources/{id}/thumbnail`
- `GET /api/v1/chats/{id}`
- `GET /api/v1/projects/{project_id}`
- `POST /api/v1/search/hybrid` (preferred — degrades to keyword)

## Tasks

1. **Home**: paginated list of recent objects. Pull-to-refresh. Tap → ObjectDetail dispatcher.
2. **Search**: search field with debounce; hybrid search; result list with kind badges; tap → ObjectDetail dispatcher. Use `kos.search.input` ax id from 02B.
3. **ObjectDetail**: dispatches to PageDetail / SourceDetail / ChatDetail / ProjectDetail based on `kind`.
4. **PageDetail**: renders Tiptap JSON as read-only. MVP supports paragraph, heading 1–3, bullet/ordered lists, blockquote, code block, link. Skip tables/embeds in MVP — show "unsupported block" placeholder.
5. **SourceDetail**: shows extracted text; thumbnail if available; download button (links to `/sources/{id}/download` via Safari).
6. **ChatDetail**: renders chat turns; preserves role/content.
7. **ProjectDetail**: header + linked objects list.
8. **Settings**: shows logged-in user, base URL, logout, "About" with mobile_api_version from bootstrap.
9. Loading / empty / error states for every screen (reuse `LoadingView`, `EmptyStateView`, `ErrorView` from 01C).
10. UI tests (`KnowledgeOSUITests/`): smoke flow login → search → open first result.

## Coordination point with 03C

Each detail view renders an `AIActionsBar(object:)` placeholder component. 03A ships an empty stub of that component; 03C replaces the stub body. Do **not** modify `AIActionsBar.swift` content beyond the empty stub.

## Definition of done

- All seven feature screens build and navigate.
- Search returns results from real local backend.
- Each detail view renders without crashing across at least one fixture per kind.
- UI smoke test passes on `iPhone 16` simulator.
- Accessibility IDs follow 02B convention.
- `PROGRESS.md` updated.

## Validation

```bash
docker compose -f infra/docker-compose.yml up -d
cd apps/ios
xcodebuild -project KnowledgeOS.xcodeproj -scheme KnowledgeOS \
  -destination 'platform=iOS Simulator,name=iPhone 16' test
# Manual: login → search "test" → open result. Screenshot via 02B helper.
```

## Out of scope

- Edits (PHASE-PHONE-04).
- Capture (PHASE-PHONE-03B).
- AI features (PHASE-PHONE-03C).
- Offline (PHASE-PHONE-05).
