# iPhone App Concept — AI Coder Project Spec

> **Use this file:** Give this entire document to any AI coder working on the KnowledgeOS iPhone app track.  
> **Scope:** This is the canonical mobile project specification. It combines product concept, mobile architecture, API contract, networking contract, repo placement, phase plan, and parallel execution rules.  
> **Audience:** AI coding agents such as Claude Code, Codex, Cursor agents, or similar tools.  
> **Status:** Living mobile specification. PHONE-00 through PHONE-05 are complete on `main`; PHONE-06 remains device-smoke pending; PHONE-07 is the hardening/contract-repair phase. Do not implement new phone work before reading the repo’s existing `CLAUDE.md`, `AGENTS.md`, `docs/AI-CODER-BRIEFING.md`, `docs/API.md`, `docs/SECURITY.md`, and `infra/docker-compose.yml`.

---

## 0. One-paragraph summary

Build a **thin native iPhone client** for KnowledgeOS. The iPhone app must live in the same repository under `apps/ios/`, talk to the existing FastAPI backend over `/api/v1`, and treat the Mac-hosted Docker stack as the backend appliance. The app is not a second backend, not a cloud sync service, not an App Store product, and not a direct database/filesystem client. It is a private, local-first mobile front-end for reading, searching, capturing, and later lightly editing KnowledgeOS content.

```text
iPhone app
  ⇄ FastAPI REST API on Mac
      ⇄ Postgres / Redis / Qdrant / Kùzu / local filesystem
```

---

## 1. Existing KnowledgeOS context the coder must understand

KnowledgeOS is a local-first personal AI knowledge operating system.

The current repo already has:

```text
agentic-knowledge-management/
  apps/
    web/              # Next.js app
  services/
    api/              # FastAPI backend
    worker/           # RQ worker
    mcp/              # MCP server
  infra/              # Docker Compose, Dockerfiles, env examples
  docs/               # architecture, API, security, MCP, etc.
  project-phases/     # canonical phase specs
```

Key architectural facts:

1. **Postgres + `~/KnowledgeOS/library/` are canonical.**
2. **Qdrant and Kùzu are rebuildable indexes/caches.**
3. **The iPhone app must only use the REST API.**
4. **The iPhone app must never access Postgres, Redis, Qdrant, Kùzu, or filesystem paths directly.**
5. **The current web frontend uses browser session cookies; the iPhone app needs a mobile-safe bearer-token flow.**
6. **All existing local-first, audit, redaction, and soft-delete invariants remain binding.**
7. **Mobile work must be phase-based under `project-phases/PHASE-PHONE-xx-...`.**

---

## 2. Core architectural decision

### 2.1 Use SwiftUI native iOS

Use **SwiftUI native iOS** for the first version.

| Option | Decision | Reason |
|---|---:|---|
| SwiftUI native | **Use** | Best fit for private iPhone app, simulator/device builds, Keychain, file/photo capture, share extension later, and Xcode/Swift agent workflows. |
| React Native / Expo | Do not use initially | Adds JS/native bridge and package complexity. Cookie/session behavior and native networking configuration are more annoying. |
| PWA/mobile web | Do not use as main path | Fast fallback, but weaker native capture, share sheet, offline, file/photo, and device integration. |

### 2.2 Keep iPhone app in the same repo

The iPhone app must live in the same repo for now.

```text
agentic-knowledge-management/
  apps/
    web/
    ios/
      project.yml              # XcodeGen source of truth
      KnowledgeOS/
        App/
        Core/
        Features/
        Resources/
      KnowledgeOSTests/
      KnowledgeOSUITests/
  services/
    api/
    worker/
    mcp/
  docs/
  project-phases/
    PHASE-PHONE-00-...
```

Reasons:

| Reason | Why it matters |
|---|---|
| API and app evolve together | The app depends directly on FastAPI endpoints, auth, search, assets, AI, chats, projects, and workspaces. |
| Agent workflow is easier | Claude Code/Codex can inspect backend, mobile code, docs, and phase specs together. |
| Phase files stay canonical | The repo already uses `project-phases/` as the implementation-control layer. |
| No App Store/external SDK pressure | This is a private local-first client, so independent release cadence is not yet needed. |
| Shared security model | Mobile networking, auth, and API contract belong next to `docs/API.md`, `docs/SECURITY.md`, and `infra/docker-compose.yml`. |

Only split into a separate repo later if:

- the iPhone app becomes a general client for many KnowledgeOS servers;
- the repo becomes too large/noisy for agents;
- mobile release cadence becomes independent;
- Android/desktop clients justify a dedicated client monorepo;
- only the iOS app should be open-sourced or distributed separately.

### 2.3 Use XcodeGen

Use `apps/ios/project.yml` as the source of truth.

Rules:

- Do not hand-edit generated `.xcodeproj` files.
- Prefer committing `project.yml`, source files, test files, and docs.
- If `.xcodeproj` is committed at all, regenerate it deterministically and do not edit it manually.
- Avoid multiple agents editing `project.yml` concurrently.

---

## 3. Product goal

### 3.1 MVP goal

The first useful iPhone app should let the user:

1. Connect to the local Mac-hosted KnowledgeOS backend.
2. Log in using mobile-safe auth.
3. Search the knowledge base.
4. Browse recent objects.
5. Read pages, sources, chats, and projects.
6. Ask grounded KB questions through the existing AI endpoint.
7. Capture quick text notes.
8. Upload files/photos as assets/sources.
9. Run in iOS Simulator and later on a physical iPhone without App Store release.

### 3.2 Non-goals for MVP

Do **not** implement these in the first mobile track:

- second backend;
- direct database access;
- direct filesystem access;
- cloud sync;
- multi-user mobile server administration;
- rich Tiptap editor parity;
- full offline-first sync;
- App Store release;
- Android;
- generic multi-server SaaS client;
- use of `MCP_INTERNAL_TOKEN` as phone auth;
- arbitrary shell/MCP execution from the phone.

---

## 4. Mobile security and auth contract

### 4.1 Current web auth is not enough

The existing web app uses browser-style session cookies. The native iPhone app should not depend on that as its primary session model.

The mobile app must use:

```http
Authorization: Bearer <opaque_mobile_token>
```

### 4.2 Required backend behavior

Add a mobile token/session layer.

Possible implementation options:

1. Extend existing `sessions` table with `client_type = "ios"` and device metadata.
2. Create a separate `mobile_sessions` table.

Either is acceptable if the security invariants below hold.

Required properties:

- token is opaque and high entropy;
- raw token is returned only once at login;
- only a SHA-256 or stronger hash is stored server-side;
- token can be revoked;
- token has last-used timestamp;
- token records optional device name;
- all auth failures are safe and non-enumerating;
- bearer auth does not weaken existing cookie auth;
- bearer auth goes through the same `get_current_user` ownership filters;
- no token is logged;
- no token is exposed in API responses after creation;
- no `MCP_INTERNAL_TOKEN` reuse.

### 4.3 Required endpoints

Add or confirm these endpoints:

```http
POST /api/v1/auth/mobile-login
POST /api/v1/auth/mobile-logout
GET  /api/v1/mobile/bootstrap
```

Suggested request/response contract:

```json
// POST /api/v1/auth/mobile-login
{
  "email": "you@example.com",
  "password": "correct horse battery staple",
  "device_name": "Keigo's iPhone"
}
```

```json
// 200
{
  "token": "opaque-mobile-token-returned-once",
  "user": {
    "id": "uuid",
    "email": "you@example.com",
    "display_name": "You"
  },
  "expires_at": "2026-06-16T00:00:00Z"
}
```

```json
// GET /api/v1/mobile/bootstrap
{
  "user": {
    "id": "uuid",
    "email": "you@example.com",
    "display_name": "You"
  },
  "capabilities": {
    "ai_enabled": true,
    "embeddings_enabled": true,
    "upload_enabled": true,
    "mobile_api_version": 1
  }
}
```

### 4.4 iOS-side auth storage

The iOS app must:

- store bearer token in Keychain;
- never store token in `UserDefaults`;
- redact token from logs;
- provide logout that deletes token locally and calls mobile logout;
- allow base URL reset without preserving stale auth state accidentally.

---

## 5. Mobile networking contract

### 5.1 Network modes

The iOS app must support these API base URL modes:

| Mode | Base URL | Use case |
|---|---|---|
| Simulator local | `http://127.0.0.1:8001` | Fast local development. |
| Same-Wi-Fi iPhone | `http://<mac-lan-ip>:8001` | Physical iPhone on same network. |
| Tailscale iPhone | `http://<mac-tailnet-name>:8001` or HTTPS later | Private remote-ish access. |

### 5.2 Docker exposure rule

Default Docker Compose binds services to loopback only. That is safe.

For physical iPhone access, create an explicit mobile override:

```yaml
# infra/docker-compose.mobile.yml
services:
  api:
    ports:
      - "0.0.0.0:8001:8000"
```

Strict rule:

- Only FastAPI may be exposed for mobile access.
- Do **not** expose Postgres, Redis, Qdrant, Qdrant gRPC, or web unless explicitly required.
- Keep database/cache/vector ports loopback-only.

### 5.3 Network health check

The app and scripts should rely on:

```http
GET /api/v1/health
```

Add a helper script:

```text
scripts/mobile_network_check.sh
```

It should check:

- backend reachable from Mac;
- selected base URL health endpoint;
- whether mobile override is running;
- whether only the intended port is exposed;
- suggested base URLs for simulator/LAN/Tailscale.

### 5.4 iOS ATS / HTTP

The app will likely need App Transport Security configuration for local HTTP during development.

Rules:

- Keep ATS exceptions narrow.
- Do not globally disable ATS unless temporary and clearly documented.
- Prefer allowing only local/LAN/Tailscale development hosts.
- Later, if using HTTPS, remove broad HTTP exceptions.

---

## 6. iOS app architecture

### 6.1 Project structure

Create:

```text
apps/ios/
  project.yml
  README.md
  KnowledgeOS/
    App/
      KnowledgeOSApp.swift
      AppState.swift
      RootView.swift
    Core/
      API/
        APIClient.swift
        APIError.swift
        APIEndpoint.swift
        DTOs/
        MultipartUpload.swift
      Auth/
        AuthStore.swift
        LoginViewModel.swift
      Config/
        ServerConfig.swift
        EnvironmentConfig.swift
      Networking/
        NetworkMonitor.swift
      Security/
        KeychainStore.swift
      UI/
        LoadingView.swift
        ErrorView.swift
        EmptyStateView.swift
        ObjectKindBadge.swift
    Features/
      Connect/
      Home/
      Search/
      ObjectDetail/
      PageDetail/
      SourceDetail/
      ChatDetail/
      ProjectDetail/
      Capture/
      AI/
      Settings/
    Resources/
      Assets.xcassets
      Info.plist
  KnowledgeOSTests/
  KnowledgeOSUITests/
```

### 6.2 State management

Use SwiftUI with simple MVVM.

Recommended pattern:

```text
View
  -> ViewModel / ObservableObject or @Observable
    -> APIClient
      -> URLSession
```

Do not introduce heavy architecture frameworks unless necessary.

### 6.3 API client principles

`APIClient` must handle:

- base URL configuration;
- bearer token injection;
- `GET`, `POST`, `PATCH`, `PUT`, `DELETE`;
- JSON encoding/decoding;
- multipart upload;
- API error decoding;
- timeout handling;
- offline/unreachable errors;
- redacted request logging;
- mockability for unit tests.

Expected API error shape:

```json
{
  "detail": "Human-readable error message",
  "code": "machine_readable_code"
}
```

### 6.4 DTO rules

Create typed DTOs. Do not parse ad hoc dictionaries in views.

Minimum DTO groups:

```text
Core/API/DTOs/
  AuthDTO.swift
  ObjectDTO.swift
  PageDTO.swift
  SourceDTO.swift
  AssetDTO.swift
  ChatDTO.swift
  ProjectDTO.swift
  SearchDTO.swift
  AIDTO.swift
  WorkspaceDTO.swift
  PaginationDTO.swift
```

Rules:

- DTOs mirror `docs/API.md`.
- Date decoding must be centralized.
- Unknown fields should not crash the app unless semantically required.
- Views should consume domain/view models, not raw networking code.

### 6.5 UI principles

- Mobile-first, one-handed usability.
- Search is a first-class action.
- Reading should be fast and calm.
- Capture should be one tap from Home.
- AI actions should be explicit, never automatic.
- Show network and AI-disabled states clearly.
- Avoid desktop web parity; optimize for mobile tasks.

---

## 7. Backend API surface the app should consume

### 7.1 Required base

```text
Base URL: user-configured, e.g. http://127.0.0.1:8001
Prefix:   /api/v1
```

### 7.2 Health

```http
GET /api/v1/health
```

### 7.3 Auth

```http
POST /api/v1/auth/mobile-login
POST /api/v1/auth/mobile-logout
GET  /api/v1/auth/me
GET  /api/v1/mobile/bootstrap
```

### 7.4 Objects

```http
GET    /api/v1/objects
GET    /api/v1/objects/{id}
PATCH  /api/v1/objects/{id}
DELETE /api/v1/objects/{id}
POST   /api/v1/objects/{id}/restore
```

### 7.5 Pages

```http
POST  /api/v1/pages
GET   /api/v1/pages/{id}
PUT   /api/v1/pages/{id}
PATCH /api/v1/pages/{id}
```

### 7.6 Assets and sources

```http
POST /api/v1/assets/upload
POST /api/v1/assets/upload?create_source=true
GET  /api/v1/assets/{id}
GET  /api/v1/assets/{id}/download

POST   /api/v1/sources
GET    /api/v1/sources
GET    /api/v1/sources/{id}
PATCH  /api/v1/sources/{id}
DELETE /api/v1/sources/{id}
GET    /api/v1/sources/{id}/text
GET    /api/v1/sources/{id}/thumbnail
```

### 7.7 Search

```http
GET  /api/v1/search/keyword?q=...
POST /api/v1/search/vector
POST /api/v1/search/hybrid
```

Mobile MVP should primarily use:

```http
POST /api/v1/search/hybrid
```

because it degrades to keyword-only when embeddings are disabled.

### 7.8 Chats

```http
POST /api/v1/chats/import
GET  /api/v1/chats
GET  /api/v1/chats/{id}
GET  /api/v1/chats/{id}/raw
```

### 7.9 Projects / career memory

```http
GET   /api/v1/projects
GET   /api/v1/projects/{project_id}
POST  /api/v1/ai/extract-project
POST  /api/v1/ai/generate-resume-bullets
POST  /api/v1/ai/generate-interview-story
```

MVP read-only app only needs list/detail first.

### 7.10 AI

```http
POST /api/v1/ai/answer
POST /api/v1/ai/summarize
POST /api/v1/ai/suggest-links
POST /api/v1/ai/triage
```

Mobile rules:

- AI calls must be user-triggered.
- Show `503` AI-disabled state clearly.
- Show citations for grounded answers.
- Never silently send data to an AI provider without explicit action.

---

## 8. Phase plan

## Dependency map

```text
PHASE-PHONE-00
  ├─ PHASE-PHONE-01A  mobile backend auth/API
  ├─ PHASE-PHONE-01B  Mac/iPhone networking
  └─ PHASE-PHONE-01C  iOS app scaffold
        ├─ PHASE-PHONE-02A API client/session
        └─ PHASE-PHONE-02B simulator automation/QA
              ├─ PHASE-PHONE-03A read/search MVP
              ├─ PHASE-PHONE-03B capture/ingest MVP
              └─ PHASE-PHONE-03C mobile AI (depends on 03A surfaces)
                    ├─ PHASE-PHONE-04 edit-lite
                    ├─ PHASE-PHONE-05 offline/cache/queue
                    └─ PHASE-PHONE-06 device install/private release
PHASE-PHONE-07 hardens shipped mobile behavior and repairs contract drift.
```

---

### PHASE-PHONE-00-MOBILE-ARCHITECTURE-AND-CONTRACT

**Goal:** create the master mobile contract before implementation.

**Files to create/update:**

```text
project-phases/PHASE-PHONE-00-MOBILE-ARCHITECTURE-AND-CONTRACT.md
docs/MOBILE_APP.md
docs/MOBILE_API_CONTRACT.md
docs/MOBILE_NETWORKING.md
```

**Tasks:**

- Inspect `docs/API.md`, `docs/SECURITY.md`, `infra/docker-compose.yml`, frontend object routing, and existing phase specs.
- Confirm same-repo `apps/ios` decision.
- Confirm SwiftUI + XcodeGen.
- Define mobile auth contract.
- Define network profiles.
- Define MVP/non-goals.
- Define phase dependency graph.

**Definition of done:**

- Clear mobile architecture diagram.
- Endpoint map.
- Network modes.
- Auth decision.
- Phase plan committed.
- No implementation code unless needed for tiny doc validation.

---

### PHASE-PHONE-01A-MOBILE-BACKEND-AUTH-AND-API

**Goal:** make the backend safe for native mobile clients.

**Files likely touched:**

```text
services/api/app/core/deps.py
services/api/app/api/v1/auth.py
services/api/app/api/v1/router.py
services/api/app/models/
services/api/app/schemas/
services/api/app/services/
services/api/alembic/versions/
tests/api/
docs/API.md
docs/SECURITY.md
```

**Tasks:**

- Add mobile token/session storage.
- Add mobile login/logout/bootstrap endpoints.
- Add bearer token resolution in auth dependency.
- Preserve existing cookie auth.
- Add tests for success, invalid password, revoked token, missing token, other-user access, logout, bootstrap.
- Update API/security docs.

**Definition of done:**

- Backend tests pass.
- Existing browser auth still passes.
- Token is stored hashed.
- Token is returned only once.
- No token leaks in logs or responses.
- No `MCP_INTERNAL_TOKEN` use.

---

### PHASE-PHONE-01B-MAC-TO-IPHONE-NETWORKING

**Goal:** make the Mac backend reachable by simulator and physical iPhone safely.

**Files likely touched:**

```text
infra/docker-compose.mobile.yml
scripts/mobile_network_check.sh
docs/MOBILE_NETWORKING.md
apps/ios/KnowledgeOS/Resources/Info.plist
```

**Tasks:**

- Add mobile Docker override exposing only API if needed.
- Add network check script.
- Document simulator, LAN, Tailscale profiles.
- Document ATS/HTTP behavior.
- Ensure no DB/cache/vector services are exposed in mobile override.
- Optionally add app config defaults for local/simulator.

**Definition of done:**

- `scripts/mobile_network_check.sh` exists and is executable.
- Only API is exposed in mobile profile.
- Docs include simulator, LAN, and Tailscale examples.
- ATS exception strategy is documented and narrow.

---

### PHASE-PHONE-01C-IOS-APP-SCAFFOLD

**Goal:** create a buildable SwiftUI iOS app.

**Files likely touched:**

```text
apps/ios/project.yml
apps/ios/README.md
apps/ios/KnowledgeOS/
apps/ios/KnowledgeOSTests/
apps/ios/KnowledgeOSUITests/
```

**Tasks:**

- Create SwiftUI app.
- Add XcodeGen `project.yml`.
- Add app entrypoint.
- Add basic app state.
- Add Connect screen.
- Add health-check screen.
- Add empty Home screen.
- Add test target.
- Add basic CI-compatible build/test command documentation.

**Definition of done:**

- `xcodegen generate` works.
- App builds in iOS Simulator.
- `xcodebuild test` works.
- Health check can call configurable base URL.
- No generated project manual edits.

---

### PHASE-PHONE-02A-IOS-API-CLIENT-AND-SESSION

**Goal:** implement typed API and session plumbing.

**Depends on:** PHONE-01A and PHONE-01C.

**Files likely touched:**

```text
apps/ios/KnowledgeOS/Core/API/
apps/ios/KnowledgeOS/Core/Auth/
apps/ios/KnowledgeOS/Core/Config/
apps/ios/KnowledgeOS/Core/Security/
apps/ios/KnowledgeOS/Core/Networking/
apps/ios/KnowledgeOSTests/
```

**Tasks:**

- Implement `APIClient`.
- Implement bearer token injection.
- Implement Keychain-backed `AuthStore`.
- Implement `ServerConfig`.
- Implement network monitor.
- Implement typed DTOs.
- Implement error decoding.
- Implement multipart helper.
- Add mock API tests.
- Add live smoke test pattern.

**Definition of done:**

- Login/logout works against mobile auth endpoint.
- Token persists securely.
- API client is unit-tested.
- Base URL can be changed.
- No token appears in logs.

---

### PHASE-PHONE-03A-READ-AND-SEARCH-MVP

**Goal:** make the mobile app useful for reading and searching.

**Depends on:** PHONE-02A.

**Files likely touched:**

```text
apps/ios/KnowledgeOS/Features/Home/
apps/ios/KnowledgeOS/Features/Search/
apps/ios/KnowledgeOS/Features/ObjectDetail/
apps/ios/KnowledgeOS/Features/PageDetail/
apps/ios/KnowledgeOS/Features/SourceDetail/
apps/ios/KnowledgeOS/Features/ChatDetail/
apps/ios/KnowledgeOS/Features/ProjectDetail/
apps/ios/KnowledgeOS/Features/Settings/
```

**Tasks:**

- Home screen with recent objects.
- Search screen using hybrid search.
- Object detail dispatcher by kind.
- Page reader.
- Source reader.
- Chat reader.
- Project reader.
- Settings screen.
- Loading, empty, and error states.

**Definition of done:**

- Login → search → open result works.
- Recent objects load.
- Page/source/chat/project detail views work.
- Search is usable on iPhone.
- Simulator smoke test exists or is updated.

---

### PHASE-PHONE-03B-CAPTURE-AND-INGEST-MVP

**Goal:** add iPhone-native capture.

**Depends on:** PHONE-02A.

**Files likely touched:**

```text
apps/ios/KnowledgeOS/Features/Capture/
apps/ios/KnowledgeOS/Core/API/MultipartUpload.swift
apps/ios/KnowledgeOS/Core/API/DTOs/AssetDTO.swift
apps/ios/KnowledgeOS/Core/API/DTOs/SourceDTO.swift
```

**Tasks:**

- Quick text note → `POST /api/v1/pages`.
- Clipboard import.
- File/photo upload → `POST /api/v1/assets/upload`.
- Optional `create_source=true`.
- Show ingestion status.
- Retry failed uploads.

**Definition of done:**

- Create note from iPhone.
- Upload file/photo.
- See source ingestion status.
- Failed upload can be retried.
- No direct filesystem/backend bypass.

---

### PHASE-PHONE-04-EDIT-LITE

**Goal:** add safe lightweight edits.

**Depends on:** PHONE-03A.

**Tasks:**

- Edit title.
- Edit tags.
- Edit simple plain-text page body.
- Convert plain text to simple Tiptap JSON paragraphs.
- Preserve existing content on cancel.
- Handle conflicts if backend supports versioning.
- Avoid rich editor scope creep.

**Definition of done:**

- Title/tags/body edits work.
- Page content remains valid Tiptap JSON.
- Conflict/error states are clear.
- No full rich editor attempted.

---

### PHASE-PHONE-03C-MOBILE-AI

**Goal:** expose high-value AI operations on mobile.

**Depends on:** PHONE-02A and PHONE-03A. Coordinates with PHONE-03A detail surfaces.

**Tasks:**

- KB Q&A using `/api/v1/ai/answer`.
- Summarize current object.
- Suggest links for current object.
- Show citations and warnings.
- Show AI-disabled state.
- Avoid automatic AI calls.

**Definition of done:**

- User can ask grounded KB questions.
- Citations display.
- AI disabled state is clear.
- No silent external calls.

---

### PHASE-PHONE-05-OFFLINE-CACHE-AND-QUEUE

**Goal:** make the app tolerable when backend is unreachable.

**Depends on:** PHONE-03A and PHONE-03B.

**Tasks:**

- Cache recent objects.
- Cache recent search results.
- Cache recently opened details.
- Queue unsent quick notes.
- Retry sync when backend returns.
- Show sync status.

**Definition of done:**

- Read cached recent content offline.
- Draft quick note offline.
- Sync queue is visible.
- No destructive auto-resolution.

---

### PHASE-PHONE-02B-SIMULATOR-AUTOMATION-AND-QA

**Goal:** give AI coders eyes and hands inside the iOS Simulator.

**Can begin after:** PHONE-01C.

**Tasks:**

- Add accessibility identifiers.
- Add simulator smoke scripts.
- Add MCP setup docs for `ios-simulator-mcp`.
- Optionally add `mobile-mcp` docs.
- Add reusable QA prompts.
- Save screenshots under `.tmp/mobile-qa/`.

**Definition of done:**

- Agent can build, install, launch, screenshot, inspect, and interact with app.
- QA docs exist.
- Tool versions are pinned or constrained.
- Dangerous/unneeded MCP tools are filtered where possible.

---

### PHASE-PHONE-06-DEVICE-INSTALL-AND-PRIVATE-RELEASE

**Goal:** run on physical iPhone without App Store release.

**Depends on:** simulator MVP. This phase remains device-smoke pending until the physical iPhone flow succeeds.

**Tasks:**

- Configure bundle ID.
- Configure signing.
- Document direct install from Xcode.
- Confirm physical iPhone can connect to Mac backend.
- Document reinstall/recovery process.
- Optionally document TestFlight later.

**Definition of done:**

- App runs on physical iPhone.
- Login/search/open object works against selected network profile.
- Private release checklist exists.
- Recovery checklist exists.

---

## 9. Parallel execution plan

Parallelize by **contract boundary**, not by feature screens first.

### Wave 0 — do first, mostly alone

```text
PHASE-PHONE-00-MOBILE-ARCHITECTURE-AND-CONTRACT
```

This should be done first and merged quickly.

Do not let multiple coders edit the same contract files at once.

---

### Wave 1 — safe to run in parallel after Phase 00

```text
Track A: PHASE-PHONE-01A-MOBILE-BACKEND-AUTH-AND-API
Track B: PHASE-PHONE-01C-IOS-APP-SCAFFOLD
Track C: PHASE-PHONE-01B-MAC-TO-IPHONE-NETWORKING
```

Rationale:

- Backend auth can evolve independently from iOS scaffold.
- iOS scaffold can use only health check/stubs.
- Networking docs/override can proceed independently if it does not change auth.

---

### Wave 1.5 — start after iOS scaffold builds

```text
Track D: PHASE-PHONE-02B-SIMULATOR-AUTOMATION-AND-QA
```

This can run while API client is being built.

---

### Wave 2 — after backend auth and iOS scaffold

```text
Track E: PHASE-PHONE-02A-IOS-API-CLIENT-AND-SESSION
```

This should wait for the mobile auth contract and the SwiftUI scaffold.

---

### Wave 3 — feature parallelization after API client

```text
Track F: PHASE-PHONE-03A-READ-AND-SEARCH-MVP
Track G: PHASE-PHONE-03B-CAPTURE-AND-INGEST-MVP
Track H: PHASE-PHONE-03C-MOBILE-AI
```

Rules:

- PHONE-03A owns read/search UI.
- PHONE-03B owns capture/upload UI.
- PHONE-03C owns AI UI and AI DTOs.
- Shared DTO/API client changes should follow PHONE-02A patterns.

---

### Wave 4 — intentionally wait

```text
PHASE-PHONE-04-EDIT-LITE
PHASE-PHONE-05-OFFLINE-CACHE-AND-QUEUE
PHASE-PHONE-06-DEVICE-INSTALL-AND-PRIVATE-RELEASE
```

Reasons:

- Edit-lite touches detail/page rendering and should wait for read UI stability.
- Offline cache cross-cuts API client, state, queueing, error handling, and capture.
- Device install is only useful after simulator MVP works.

---

## 10. What not to parallelize

| Do not parallelize | Reason |
|---|---|
| Mobile auth implementation by multiple coders | High risk of weakening auth or duplicating session models. |
| API client core and feature screens before DTOs stabilize | Causes broken assumptions and merge conflicts. |
| Edit-lite and read/detail UI | Both touch page detail and content rendering. |
| Offline cache and API client | Cache changes cross-cut request lifecycle, state, and errors. |
| Multiple coders editing `project.yml` | XcodeGen spec conflicts still matter. |
| Multiple coders editing `docs/API.md` and `docs/SECURITY.md` | Assign one doc owner. |
| Multiple coders editing `AppState` or `RootView` | High conflict zone. |
| Backend networking exposure and security hardening without coordination | Easy to accidentally expose wrong ports/services. |

---

## 11. Worktree and branch plan

Use isolated worktrees.

### Initial worktrees

```bash
git worktree add ../kos-phone-00 -b phase-phone-00-mobile-contract
git worktree add ../kos-phone-01 -b phase-phone-01-mobile-auth
git worktree add ../kos-phone-02 -b phase-phone-02-networking
git worktree add ../kos-phone-03 -b phase-phone-03-ios-scaffold
git worktree add ../kos-phone-10 -b phase-phone-10-simulator-qa
```

### Later worktrees

```bash
git worktree add ../kos-phone-04 -b phase-phone-04-ios-api-client
git worktree add ../kos-phone-05 -b phase-phone-05-read-search
git worktree add ../kos-phone-06 -b phase-phone-06-capture-ingest
git worktree add ../kos-phone-08 -b phase-phone-08-mobile-ai
```

### Before starting any work

Run:

```bash
git fetch
git status
git worktree list
```

Then inspect active diffs:

```bash
git diff --name-only main...HEAD
```

If another worktree touches your target files, stop and narrow scope.

---

## 12. AI coder operating rules

Every AI coder must follow these rules.

### 12.1 Before editing

1. Read this file end-to-end.
2. Read `CLAUDE.md`.
3. Read `AGENTS.md`.
4. Read `docs/AI-CODER-BRIEFING.md`.
5. Read the target `project-phases/PHASE-PHONE-xx-...` file.
6. Inspect relevant existing code.
7. Produce a short plan before edits.
8. Identify likely conflict files.

### 12.2 During implementation

- Stay inside the assigned phase.
- Do not modify unrelated files.
- Do not weaken auth.
- Do not expose non-API services to LAN.
- Do not reuse `MCP_INTERNAL_TOKEN` for the phone app.
- Do not hand-edit generated Xcode project files.
- Do not add cloud dependencies.
- Do not add arbitrary shell/MCP execution.
- Keep all DTOs typed.
- Keep tokens out of logs.
- Update docs when behavior changes.
- Add tests for every backend/API change.
- Add iOS unit tests for client/session logic.

### 12.3 Before final response / PR

Run relevant checks.

Backend:

```bash
cd tests
uv run pytest api/ unit/ -q
```

iOS:

```bash
cd apps/ios
xcodegen generate
xcodebuild \
  -project KnowledgeOS.xcodeproj \
  -scheme KnowledgeOS \
  -destination 'platform=iOS Simulator,name=iPhone 16' \
  test
```

Docker/mobile networking:

```bash
docker compose -f infra/docker-compose.yml up -d
curl http://127.0.0.1:8001/api/v1/health
bash scripts/mobile_network_check.sh
```

If a command cannot be run, state exactly why.

---

## 13. Testing strategy

### 13.1 Backend tests

Required for:

- mobile login/logout;
- bearer auth;
- revoked/expired token;
- bootstrap;
- access control;
- existing cookie auth regression;
- mobile networking override if testable.

### 13.2 iOS unit tests

Required for:

- API request construction;
- bearer token injection;
- Keychain store behavior with test double;
- error decoding;
- date decoding;
- pagination decoding;
- search DTO decoding;
- AI-disabled error state mapping.

### 13.3 iOS UI/smoke tests

Required for:

- connect screen;
- login flow;
- search flow;
- open object detail;
- quick note capture;
- upload/capture flow later;
- AI question flow later.

### 13.4 Simulator MCP QA

For features with UI, run or document:

- screenshot before/after;
- accessibility tree inspection;
- tap/type/swipe flow;
- failed state flow.

Screenshots should go to:

```text
.tmp/mobile-qa/
```

Do not commit temporary screenshots unless explicitly requested.

---

## 14. Pull request checklist

Each PR must include:

```text
## Scope
- Phase:
- Files changed:
- What this PR does:
- What this PR intentionally does not do:

## Validation
- Backend tests:
- iOS tests:
- Simulator run:
- Network check:
- Manual smoke:

## Security
- Token handling checked:
- No secrets logged:
- No non-API services exposed:
- No MCP_INTERNAL_TOKEN reuse:
- ATS/networking implications:

## Docs
- docs/API.md updated if needed:
- docs/SECURITY.md updated if needed:
- docs/MOBILE_*.md updated if needed:
- project phase file updated:

## Screenshots / QA
- Simulator screenshot path or note:
```

---

## 15. File ownership guidance by phase

| Phase | Primary files | Avoid touching |
|---|---|---|
| 00 | `docs/MOBILE_*`, `project-phases/PHASE-PHONE-00-*` | Implementation code |
| 01 | `services/api`, `tests/api`, API/security docs | `apps/ios` except generated API examples |
| 02 | `infra`, `scripts`, networking docs | Auth implementation |
| 03 | `apps/ios/project.yml`, app scaffold | Backend auth |
| 04 | `apps/ios/Core/API`, `Core/Auth`, DTOs | Feature-heavy screens |
| 05 | Read/search features | Auth backend, networking infra |
| 06 | Capture/upload features | Read/search core routing unless needed |
| 07 | Edit-lite detail/editor files | Offline cache |
| 08 | AI feature UI/DTOs | Backend AI internals unless bugfix |
| 09 | Cache/queue layer | Auth model |
| 10 | QA docs/scripts/accessibility IDs | Product behavior changes |
| 11 | signing/device docs | Core API/auth |

---

## 16. Final target state

The desired end state after the phone track:

```text
agentic-knowledge-management/
  apps/
    web/
    ios/
      project.yml
      KnowledgeOS/
      KnowledgeOSTests/
      KnowledgeOSUITests/
  services/
    api/
      app/
        api/v1/auth.py            # includes mobile login/logout
        api/v1/mobile.py          # bootstrap/capabilities if separated
  infra/
    docker-compose.yml
    docker-compose.mobile.yml
  scripts/
    mobile_network_check.sh
  docs/
    MOBILE_APP.md
    MOBILE_API_CONTRACT.md
    MOBILE_NETWORKING.md
    MOBILE_QA.md
  project-phases/
    PHASE-PHONE-00-MOBILE-ARCHITECTURE-AND-CONTRACT.md
    PHASE-PHONE-01A-MOBILE-BACKEND-AUTH-AND-API.md
    PHASE-PHONE-01B-MAC-TO-IPHONE-NETWORKING.md
    PHASE-PHONE-01C-IOS-APP-SCAFFOLD.md
    PHASE-PHONE-02A-IOS-API-CLIENT-AND-SESSION.md
    PHASE-PHONE-02B-SIMULATOR-AUTOMATION-AND-QA.md
    PHASE-PHONE-03A-READ-AND-SEARCH-MVP.md
    PHASE-PHONE-03B-CAPTURE-AND-INGEST-MVP.md
    PHASE-PHONE-03C-MOBILE-AI.md
    PHASE-PHONE-04-EDIT-LITE.md
    PHASE-PHONE-05-OFFLINE-CACHE-AND-QUEUE.md
    PHASE-PHONE-06-DEVICE-INSTALL-AND-PRIVATE-RELEASE.md
    PHASE-PHONE-07-MOBILE-HARDENING-AND-CONTRACT-REPAIR.md
```

The iPhone app should feel like a lightweight native remote control and capture surface for the local KnowledgeOS appliance:

- search and read from anywhere;
- capture into the local knowledge base;
- ask grounded questions;
- upload useful artifacts;
- remain private/local-first;
- keep backend data canonical on the Mac;
- stay agent-friendly for future implementation.
