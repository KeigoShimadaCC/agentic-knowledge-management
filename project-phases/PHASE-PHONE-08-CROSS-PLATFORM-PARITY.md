# Phase PHONE-08 - Cross-Platform Parity & Propagation

**Status:** Draft
**Goal:** Prove the Mac-used web app and iPhone app share the same core knowledge workflows, then fix critical gaps needed for bidirectional propagation.
**Wave:** parity
**Branch:** `phase-phone-08-cross-platform-parity`
**Worktree:** `worktrees/kos-phone-08`
**Depends on:** PHONE-07 completed, or PHONE-07 explicitly accepted as the baseline
**Blocks:** future phone work that assumes Mac-created and iPhone-created knowledge behave identically

## Scope

PHONE-08 is a full parity build across:

- The Mac surface, meaning the existing Next.js web app in `apps/web`, not a native macOS app.
- The iPhone SwiftUI app in `apps/ios`.
- The shared FastAPI `/api/v1` resources.
- The current mobile non-goals in `docs/MOBILE_APP.md`.

The phase must audit first, then implement only the critical shared-workflow gaps discovered by that audit. The iPhone must continue to use the REST API only; do not add direct DB, Redis, Qdrant, Kuzu, or filesystem access.

## Starting Audit Seeds

Use these live-code entry points as the initial inventory, then expand with `rg` and route/API reads before editing:

- Mac routes: `apps/web/src/app/(app)/app/{page.tsx,pages,sources,assets,chats,projects,inbox,trash,settings/mcp}`.
- Mac API helpers: `apps/web/src/lib/api.ts` and feature hooks under `apps/web/src/lib/hooks`.
- iPhone endpoint registry: `apps/ios/KnowledgeOS/Core/API/APIEndpoint.swift`.
- iPhone DTOs: `apps/ios/KnowledgeOS/Core/API/DTOs/*.swift`.
- iPhone feature surfaces: `apps/ios/KnowledgeOS/Features/{Home,Search,ObjectDetail,PageDetail,SourceDetail,ChatDetail,ProjectDetail,Capture,AI,Sync,Root,Settings}`.
- iPhone accessibility registry: `apps/ios/KnowledgeOS/Core/UI/AccessibilityID.swift`.
- Backend routers: `services/api/app/api/v1/{objects,pages,assets,sources,chats,projects,search,ai,edges,workspaces}.py`.
- Existing E2E patterns: `tests/e2e/specs/01-auth.spec.ts` through `32-sai04-context7-mcp.spec.ts`.

## Parity Matrix

Create `docs/CROSS_PLATFORM_PARITY.md` before product edits. The matrix must be built from live code, not assumptions, and must compare:

- Mac routes and API helpers in `apps/web`.
- iPhone SwiftUI features, DTOs, and `APIEndpoint.swift`.
- Backend `/api/v1` resources.
- Intentional mobile non-goals from `docs/MOBILE_APP.md`.

Every row must use exactly one classification:

- `bidirectional-required` - core knowledge workflow that must work from both Mac and iPhone.
- `iphone-only` - phone capture, device/network/session behavior, simulator QA, and other phone-native workflows.
- `mac-only-by-design` - deep desktop/admin/developer surfaces that should not move to iPhone in PHONE-08.
- `critical-gap-fixed-in-phone-08` - shared workflow missing or broken on one side and owned by this phase.

The matrix must include current evidence columns for:

- Backend endpoint and method.
- Mac route/component/helper evidence.
- iPhone feature/DTO/endpoint evidence.
- Test coverage evidence.
- PHONE-08 action.

## Required Parity Baseline

Unless the matrix proves an item is intentionally out of scope, shared knowledge workflows must be `bidirectional-required`:

- Pages: create, read, search, edit-lite metadata/body, archive/trash/restore disclosure.
- Objects: list, detail, metadata edit, status/deleted/archive visibility where supported.
- Search: hybrid search for Mac-created and iPhone-created data.
- Sources and assets: upload/capture, read metadata, extracted text, thumbnails/downloads, ingestion status.
- Chats: read/import visibility, summary review where existing APIs already support it.
- Projects: list, open, update where existing APIs already support it.
- AI actions: answer, summarize, suggest links, and AI-disabled fallback.
- Graph: links/backlinks/related objects, including link creation/removal if existing APIs support the workflow.
- Workspaces: list/open/update where existing APIs and DTOs already support it.
- Offline/queued phone-originated states: Mac must render, search, edit, restore, and disclose status correctly after sync.

## Mac-Only By Design

Keep these Mac-only unless the parity matrix explicitly promotes one with evidence and a narrow implementation plan:

- MCP connection administration.
- Tutorial seed/reset and web onboarding controls.
- Deep Tiptap slash editing, rich formatting, editor-only AI complete/transform/enrich helpers.
- Career-memory generator and private release/signing controls.
- Lower-level developer/admin endpoints, including MCP internals and direct infrastructure controls.

## Implementation Tasks

1. Create the worktree from current `main`, verify it is clean, and record `git status --short --branch` plus `git worktree list` in the kickoff notes.
2. Boot and prove iPhone 16 simulator availability before product edits. If CoreSimulator is unavailable, PHONE-08 is blocked, not complete.
3. Build `docs/CROSS_PLATFORM_PARITY.md` from live code and classify every feature.
4. Add shared cross-platform fixtures using unique titles/tags so Mac and iPhone checks assert the same records without relying on ambient data.
5. Implement missing iPhone critical workflows in priority order: object lifecycle, source/asset lifecycle, project lifecycle, chat read/import/summary review, graph link management, workspace access, and AI action coverage.
6. Add Mac-side fixes only when phone-originated data fails to render, search, edit, restore, or disclose status correctly in the web app.
7. Add bidirectional tests: Mac creates/edits then iPhone reads/searches/edits; iPhone captures/uploads/edits then Mac reads/searches/edits.
8. Extend iOS Swift DTOs, API endpoints, feature views, view models, tests, and `kos.*` accessibility identifiers as needed.
9. Finalize `docs/CROSS_PLATFORM_PARITY.md`, this phase doc's completion checklist, and `PROGRESS.md`.

## Files Expected To Change

This is an audit-driven phase, so the exact file list must come from the matrix. Expected areas:

- `docs/CROSS_PLATFORM_PARITY.md`
- `PROGRESS.md`
- `apps/ios/KnowledgeOS/Core/API/**`
- `apps/ios/KnowledgeOS/Core/UI/AccessibilityID.swift`
- `apps/ios/KnowledgeOS/Features/**`
- `apps/ios/KnowledgeOSTests/**`
- `apps/web/src/**` only for Mac-side propagation/status fixes
- `tests/e2e/fixtures/**`
- `tests/e2e/specs/33-cross-platform-parity.spec.ts`

Do not add a database migration unless a verified critical parity gap cannot be handled through existing APIs. If a schema redesign is required, record it as a follow-up phase instead of silently expanding PHONE-08.

## Validation

Required commands for completion:

```bash
git status --short --branch
git worktree list

pnpm typecheck
pnpm lint
pnpm -F @kos/web test:run
pnpm --dir tests/e2e test specs/33-cross-platform-parity.spec.ts

cd apps/ios && xcodegen generate
cd apps/ios && xcodebuild -project KnowledgeOS.xcodeproj -scheme KnowledgeOS -destination 'platform=iOS Simulator,name=iPhone 16' build
cd apps/ios && xcodebuild -project KnowledgeOS.xcodeproj -scheme KnowledgeOS -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:KnowledgeOSTests test

cd tests && PYTHONPATH=../services/api uv run pytest unit/test_phone_phase_docs.py -q
bash scripts/mobile_network_check.sh
bash scripts/mobile_simulator_boot.sh
```

Simulator MCP acceptance:

- Use `ios-simulator` MCP after boot.
- Capture screenshots under `.tmp/mobile-qa/phone-08/` for login, home, search, detail, capture/upload, edit, AI, and settings.
- `ui_describe_all` must show expected `kos.*` identifiers for the exercised flows.
- If CoreSimulator is unavailable, PHONE-08 is blocked, not complete.

Physical iPhone validation is a manual non-blocking note. The hard completion gate for PHONE-08 is iPhone 16 simulator validation.

## Definition Of Done

- `docs/CROSS_PLATFORM_PARITY.md` exists and classifies every audited feature.
- All `critical-gap-fixed-in-phone-08` rows in the matrix are implemented or explicitly moved to a follow-up with a reason.
- Mac-created pages, objects, sources/assets, chats, projects, graph links, workspaces, and AI-action results are visible and usable from iPhone where classified as bidirectional.
- iPhone-created/captured/edited data renders, searches, edits, restores, and discloses status correctly in the Mac web app.
- `tests/e2e/specs/33-cross-platform-parity.spec.ts` proves bidirectional propagation with unique fixtures.
- iOS unit/live smoke coverage covers new DTOs, endpoints, view models, and error/fallback states.
- Required `kos.*` accessibility identifiers exist for every exercised simulator flow.
- `PROGRESS.md` reflects the phase state, validation results, blocked items, and repo state.
- iPhone 16 simulator build, test, MCP UI describe, and screenshot acceptance all pass.

## Out Of Scope

- Native macOS app.
- New cloud sync backend.
- App Store release.
- Rich Tiptap editor parity on iPhone.
- MCP connection administration on iPhone.
- Direct phone access to the database, filesystem, worker queues, Redis, Qdrant, or Kuzu.
