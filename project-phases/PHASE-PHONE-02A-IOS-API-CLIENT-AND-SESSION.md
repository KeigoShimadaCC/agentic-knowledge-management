# Phase PHONE-02A — iOS API Client & Session

**Status:** Complete
**Goal:** Typed `APIClient`, Keychain-backed bearer token storage, login/logout/bootstrap, full DTO set mirroring `docs/MOBILE_API_CONTRACT.md`.
**Wave:** 2 (parallel with 02B)
**Branch:** `phase-phone-02a-ios-api-client`
**Worktree:** `../kos-phone-02a`
**Depends on:** PHASE-PHONE-01A (auth contract), PHASE-PHONE-01C (scaffold)
**Blocks:** PHASE-PHONE-03A, 03B, 03C

## Scope

Only `apps/ios/KnowledgeOS/Core/**` and `apps/ios/KnowledgeOSTests/**`. Do **not** add feature UI yet (Wave 3 owns that). Do **not** modify `project.yml` structure beyond adding files.

## Files to create

```
Core/
  API/
    APIClient.swift          # base URL + bearer injection + URLSession wrapper
    APIError.swift           # decodes {detail, code}
    APIEndpoint.swift        # typed endpoint enum or struct
    MultipartUpload.swift    # boundary helper for /assets/upload
    DTOs/
      AuthDTO.swift          # MobileLoginRequest/Response, BootstrapResponse
      UserDTO.swift
      ObjectDTO.swift
      PageDTO.swift          # incl. Tiptap-JSON-as-AnyCodable
      SourceDTO.swift
      AssetDTO.swift
      ChatDTO.swift
      ProjectDTO.swift
      SearchDTO.swift        # hybrid search request/response
      AIDTO.swift            # answer/summarize/suggest-links request/response
      WorkspaceDTO.swift
      PaginationDTO.swift
      AnyCodable.swift       # for Tiptap blob and unknown JSON
  Auth/
    AuthStore.swift          # @Observable; current user, token state
    LoginViewModel.swift     # validates input, calls /mobile-login
  Security/
    KeychainStore.swift      # protocol + real impl + InMemory mock for tests
  Networking/
    NetworkMonitor.swift     # NWPathMonitor wrapper; reachable / unreachable
Features/
  Root/
    MainTabView.swift        # 5-tab shell — owns tab order so Wave 3 doesn't collide
    HomeTab.swift            # placeholder body, 03A replaces
    SearchTab.swift          # placeholder body, 03A replaces
    CaptureTab.swift         # placeholder body, 03B replaces
    AITab.swift              # placeholder body, 03C replaces
    SettingsTab.swift        # placeholder body, 03A replaces
  Auth/
    LoginView.swift          # minimal UI; needed so the auth flow is end-to-end testable
Tests:
  APIClientTests.swift       # URLProtocol mock; asserts request shape + bearer
  AuthStoreTests.swift       # uses KeychainStore mock
  DTOTests.swift             # decoder round-trips for each DTO against captured JSON
  ErrorDecodingTests.swift   # {detail, code} → APIError
```

## Tasks

1. Implement `APIClient` against `URLSession`. Supports GET/POST/PATCH/PUT/DELETE + multipart. Injects `Authorization: Bearer <token>` when AuthStore has one. Centralized JSON encoder/decoder with ISO8601 + fractional seconds. 30s timeout. Returns typed result or `APIError`.
2. `APIError` cases: `notAuthenticated`, `forbidden`, `notFound`, `validation(detail)`, `serverError`, `aiDisabled` (maps from backend `503`), `networkUnavailable`, `decodingFailed(Error)`.
3. `KeychainStore` protocol + real implementation backed by `kSecClassGenericPassword`. Token key: `os.knowledgeos.bearer`. **Never** writes token to `UserDefaults` or logs. Provide `InMemoryKeychain` for tests.
4. `AuthStore`:
   - On launch, attempts to read token from Keychain → calls `/mobile/bootstrap` → caches `User` + `Capabilities`.
   - `login(email, password, deviceName)` → POST `/auth/mobile-login` → Keychain → bootstrap.
   - `logout()` → POST `/auth/mobile-logout` → wipe Keychain.
   - Race-safe: subsequent 401 from any request triggers automatic logout.
5. `LoginView` + `LoginViewModel` minimum UI so the flow is testable end-to-end against the local backend.
6. Wire `LoginView` into `RootView` so the app shows Login when no token, Home placeholder when authed.
7. **Ship the TabView nav skeleton.** This is the contract that prevents Wave 3 merge conflicts. Create `Features/Root/MainTabView.swift` with five tabs in this order, each pointing to an empty placeholder view that 03A/03B/03C will replace:
   - `Home` (owned by 03A)
   - `Search` (owned by 03A)
   - `Capture` (owned by 03B)
   - `AI` (owned by 03C)
   - `Settings` (owned by 03A)
   Each placeholder is a single-file stub (e.g. `HomeTab.swift`) — Wave 3 owners replace the body only. Do **not** put logic in the placeholders. Tab order is fixed here so no Wave 3 phase needs to touch `MainTabView.swift`.
8. DTO set: every shape in `docs/MOBILE_API_CONTRACT.md`. Use captured JSON fixtures under `KnowledgeOSTests/Fixtures/` to make decoding tests stable.
9. Redacted request logging: `APIClient` logs path + method + status. **Never** logs the Authorization header or response body content.

## Definition of done

- All unit tests pass on `iPhone 16` simulator.
- Manual smoke against live local backend: login → bootstrap → logout succeeds.
- Token visible only inside Keychain (no occurrences in `os_log` / `print`).
- Changing base URL clears token automatically (security invariant).
- `PROGRESS.md` updated.

## Validation

```bash
# Backend up first
docker compose -f infra/docker-compose.yml up -d

# iOS unit tests
cd apps/ios
xcodegen generate
xcodebuild -project KnowledgeOS.xcodeproj -scheme KnowledgeOS \
  -destination 'platform=iOS Simulator,name=iPhone 16' test

# Manual smoke (operator)
# 1. Boot simulator. 2. Set base URL to http://127.0.0.1:8001.
# 3. Login with seeded user. 4. Confirm Home placeholder shows username.
```

## Out of scope

- Feature screens beyond Login + placeholder Home (Wave 3).
- Upload UX (Phase 03B will reuse `MultipartUpload`).
- AI UI (Phase 03C).
