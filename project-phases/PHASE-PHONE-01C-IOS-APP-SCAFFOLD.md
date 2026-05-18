# Phase PHONE-01C — iOS App Scaffold

**Status:** Complete
**Goal:** Create a buildable SwiftUI iOS project at `apps/ios/` using XcodeGen. App boots, hits a configurable base URL, and shows a Connect + health-check screen.
**Wave:** 1 (parallel with 01A, 01B)
**Branch:** `phase-phone-01c-ios-scaffold`
**Worktree:** `worktrees/kos-phone-01c`
**Depends on:** PHASE-PHONE-00
**Blocks:** PHASE-PHONE-02A, 02B

## Scope

Only `apps/ios/` and supporting `docs/`/`PROGRESS.md`. Do **not** touch `services/`, `infra/`, or `scripts/`. Do **not** add network code beyond the health check stub.

## Files to create

```
apps/ios/
  project.yml                       # XcodeGen spec — source of truth
  README.md                         # how to run, prereqs (xcodegen, Xcode 16+)
  KnowledgeOS/
    App/
      KnowledgeOSApp.swift          # @main App, RootView injection
      AppState.swift                # ObservableObject; baseURL, loadingState
      RootView.swift                # NavigationStack, top-level switch
    Core/
      Config/
        ServerConfig.swift          # base URL persistence (UserDefaults for URL only)
        EnvironmentConfig.swift     # static build/runtime flags (simulator vs device, debug)
      UI/
        LoadingView.swift
        ErrorView.swift
        EmptyStateView.swift
        ObjectKindBadge.swift       # kind badge used by Wave 3 screens; ship empty/styled stub here
    Features/
      Connect/
        ConnectView.swift           # base URL input + Test Connection
        ConnectViewModel.swift
      Home/
        HomePlaceholderView.swift   # post-connect landing; "API client coming in 02A"
    Resources/
      Assets.xcassets/              # AppIcon placeholder + AccentColor
      Info.plist                    # ATS exceptions for 127.0.0.1, 10.0.0.0/8, *.ts.net
  KnowledgeOSTests/
    AppStateTests.swift             # smoke
    ServerConfigTests.swift
  KnowledgeOSUITests/
    BootSmokeTests.swift            # launches app, asserts Connect screen visible
```

## Tasks

1. Write `apps/ios/project.yml`. Targets: `KnowledgeOS` (iOS app), `KnowledgeOSTests`, `KnowledgeOSUITests`. iOS deployment target 17.0. Swift 5.10+. No external SPM dependencies in this phase.
2. Implement the scaffold files above. Health check uses raw `URLSession`; calls `GET <baseURL>/api/v1/health` and shows PASS/FAIL.
3. `ServerConfig` persists base URL only (no credentials yet). Default `http://127.0.0.1:8001` on Simulator.
4. ATS plist: narrow `NSExceptionDomains` for local development. Document removal path in `apps/ios/README.md`.
5. `apps/ios/README.md` documents:
   - Prereqs: Xcode 16+, `brew install xcodegen`.
   - `cd apps/ios && xcodegen generate`.
   - `xcodebuild -project KnowledgeOS.xcodeproj -scheme KnowledgeOS -destination 'platform=iOS Simulator,name=iPhone 16' build test`.
   - DO NOT hand-edit the generated `.xcodeproj`.
6. Add `.gitignore` rules for `*.xcodeproj`, `.build/`, `DerivedData/`, `*.xcuserstate` under `apps/ios/` (or extend repo root `.gitignore`).
7. Decision: commit the generated `.xcodeproj`? **No** — keep `project.yml` as sole source, regenerate locally and in CI.

## Definition of done

- `xcodegen generate` produces a project that builds clean on a fresh checkout.
- `xcodebuild -project KnowledgeOS.xcodeproj -scheme KnowledgeOS -destination 'platform=iOS Simulator,name=iPhone 16' build` succeeds.
- `xcodebuild -project KnowledgeOS.xcodeproj -scheme KnowledgeOS -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:KnowledgeOSTests test` runs `BootSmokeTests` and passes.
- Connect screen accepts a URL, hits `/api/v1/health`, shows result.
- No raw `.xcodeproj` committed.
- `PROGRESS.md` updated.

## Validation

```bash
cd apps/ios
xcodegen generate
xcodebuild -project KnowledgeOS.xcodeproj -scheme KnowledgeOS \
  -destination 'platform=iOS Simulator,name=iPhone 16' clean build test
```

## Out of scope

- Bearer auth, login UI (PHASE-PHONE-02A).
- DTOs, typed API client (PHASE-PHONE-02A).
- Any feature screens beyond Connect + placeholder Home (Wave 3).
- Simulator MCP automation (PHASE-PHONE-02B).
