# Cross-Platform Parity Matrix

> Phase PHONE-08 audit artifact. Built from live code on 2026-05-18; finalized 2026-05-19 after PHONE-08 implementation.

## Classification Key

- `bidirectional-required` - core knowledge workflow that must work from both Mac web and iPhone.
- `iphone-only` - phone-native workflow.
- `mac-only-by-design` - desktop/admin/developer workflow intentionally not promoted to iPhone in PHONE-08.
- `critical-gap-fixed-in-phone-08` - shared workflow gap closed in PHONE-08 (may remain Mac-only for a sub-feature).

## Test Coverage (PHONE-08)

| Area | Evidence |
|---|---|
| Pages/objects/trash/graph/projects/workspaces | `tests/e2e/specs/33-cross-platform-parity.spec.ts` (tests 1–2) |
| Assets/sources, chats, AI summarize/answer | `tests/e2e/specs/33-cross-platform-parity.spec.ts` (test 3) |
| iPhone endpoints/DTOs | `apps/ios/KnowledgeOSTests/APIClientTests.swift`, `DTOTests.swift` |
| Live mobile flow | `apps/ios/KnowledgeOSTests/LiveBackendSmokeTests.swift` (self-seeded search) |
| Edit-lite round-trip | `apps/ios/KnowledgeOSTests/EditLiteLiveSmokeTests.swift` |
| Simulator QA screenshots | `scripts/mobile_qa_phone08.sh` → `.tmp/mobile-qa/phone-08/` |

## Matrix

| Feature | Backend endpoint/method | Mac evidence | iPhone evidence | Classification | PHONE-08 action |
|---|---|---|---|---|---|
| Health and connection | `GET /api/v1/health` | login/auth flow uses API base health indirectly | `APIEndpoint.health`, `ConnectView`, `kos.connect.*` | `iphone-only` | Keep as phone setup surface. |
| Web session auth | `POST /api/v1/auth/login`, `/logout`, `/me` | `login`, `getMe`; auth routes | Not used directly | `mac-only-by-design` | Keep web cookie auth on Mac. |
| Mobile bearer auth | `POST /api/v1/auth/mobile-login`, `GET /mobile/bootstrap` | Not a Mac app workflow | `APIEndpoint.mobileLogin`, `AuthStore`, `SettingsTab` | `iphone-only` | Keep separate from MCP/internal token. |
| Recent object list | `GET /api/v1/objects` | `listObjects`, list routes | `HomeTab`, `HomeViewModel`, `CachedReadAPI` | `bidirectional-required` | Covered; E2E + live smoke. |
| Object detail | `GET /api/v1/objects/{id}` | `getObject`, detail routes | `ObjectDetailView`, `ReadAPI` | `bidirectional-required` | Covered; E2E + live smoke. |
| Object metadata edit | `PATCH /api/v1/objects/{id}` | `updateObject` | `EditMetadataSheet`, `EditAPI` | `bidirectional-required` | Covered; `EditLiteLiveSmokeTests`. |
| Object archive/delete/restore/trash | `DELETE`, `POST .../archive`, `GET /objects/trash`, `POST .../restore` | `/app/trash`, trash helpers | `ObjectLifecycleAPI`, `TrashView`, `TrashViewModel`, `kos.trash.*` | `bidirectional-required` | **Fixed in PHONE-08.** E2E trash/restore. |
| Page create/read/edit-lite | `POST/GET/PUT /pages` | Tiptap editor, `PageView` | `CaptureAPI`, `PageDetailView`, `EditBodySheet` | `bidirectional-required` | Covered; E2E + edit-lite smoke. |
| Page rich editing and slash AI | `POST /ai/complete`, `/transform`, `/enrich-page` | `PageEditor`, slash AI | Not present | `mac-only-by-design` | Unchanged. |
| Asset upload | `POST /assets/upload?create_source=true` | `AssetUploader`, `/app/assets` | `CaptureAPI`, `CaptureRootView`, queue | `bidirectional-required` | Covered; E2E test 3 (API upload → Mac source). |
| Asset metadata/download | `GET /assets/{id}`, `/download` | asset grid | `assetMeta`, `assetDownload`, `SourceDetailView` | `bidirectional-required` | Covered on iPhone read path. |
| Source read/status/lifecycle | `GET/PATCH/DELETE /sources`, restore | source routes | `SourceDetailView`; delete via object lifecycle | `bidirectional-required` | **Fixed in PHONE-08** for lifecycle via objects; source PATCH UI deferred. |
| Hybrid search | `POST /search/hybrid` | `hybridSearch`, `SearchModal` | `SearchTab`, `SearchViewModel` | `bidirectional-required` | Covered; `LiveBackendSmokeTests` self-seeds. |
| Keyword/vector search | `GET /search/keyword`, `POST /search/vector` | web helpers | Not on iPhone by design | `mac-only-by-design` | Unchanged. |
| Chat list/read/import | `/chats/import`, `GET /chats`, `GET /chats/{id}` | `/app/chats`, import UI | `ChatListView`, `ChatDetailView`, `kos.chat.*` | `bidirectional-required` | **Fixed in PHONE-08** for list/read; Mac-only import UI. E2E test 3. |
| Chat structured summary | `POST/GET .../structured-summary` | Mac apply UI | `ChatSummaryAPI`, review-only `ChatDetailView` | `bidirectional-required` | Review on iPhone; apply Mac-only. |
| AI answer/summarize | `POST /ai/answer`, `/summarize` | `AiPanel` | `AskKBView`, `SummarizeSheet`, `AIActionsBar` | `bidirectional-required` | Covered; E2E test 3 (API + disabled fallback). |
| AI suggest links | `POST /ai/suggest-links` | `AiPanel` + edge create | `SuggestLinksSheet` + `GraphAPI` edge create | `bidirectional-required` | **Fixed in PHONE-08.** |
| AI extract/inbox/triage | extract-claims, inbox, triage | Mac panels | Not present | `mac-only-by-design` | Unchanged. |
| Projects list/update | `GET/PATCH /projects` | `/app/projects` | `ProjectListView`, `ProjectDetailView`, edit sheet | `bidirectional-required` | **Fixed in PHONE-08.** E2E test 2. |
| Career project AI | career endpoints | Mac panels | Not present | `mac-only-by-design` | Unchanged. |
| Graph edges/backlinks | `GET/POST/DELETE /edges`, backlinks | `GraphPanel`, `LinkToModal` | `GraphLinksSection`, `GraphAPI`, `kos.graph.*` | `bidirectional-required` | **Fixed in PHONE-08.** E2E backlinks. |
| Persisted workspaces | `POST/GET/PATCH /workspaces` | `WorkspaceNameModal` | `WorkspaceListView`, `WorkspaceAPI`, `kos.workspace.*` | `bidirectional-required` | **Fixed in PHONE-08.** E2E test 2. |
| Offline cache / capture queue | client-side | N/A | `CacheStore`, `QueueDrainer` | `iphone-only` | Unit tests; Mac sees synced writes. |
| MCP admin, tutorial, signing | various | Mac settings | Not on iPhone | `mac-only-by-design` | Unchanged. |

## PHONE-08 Critical Gap Queue (final)

| # | Gap | Status |
|---|---|---|
| 1 | Object lifecycle on iPhone | **Fixed in PHONE-08** |
| 2 | Workspaces on iPhone | **Fixed in PHONE-08** |
| 3 | Graph link management on iPhone | **Fixed in PHONE-08** |
| 4 | Project list/update on iPhone | **Fixed in PHONE-08** |
| 5 | Chat list + summary review on iPhone | **Fixed in PHONE-08** |
| 6 | AI suggest-links → edge create on iPhone | **Fixed in PHONE-08** |

**Follow-up (not PHONE-08):** iPhone source PATCH UI; chat import on iPhone; chat summary apply on iPhone; physical-device smoke (PHONE-06).

No database schema change was required. Any future schema need should become a follow-up phase.
