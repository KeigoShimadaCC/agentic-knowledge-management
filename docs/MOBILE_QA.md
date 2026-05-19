# Mobile QA — iOS Simulator Automation

Operator guide for AI coders validating the KnowledgeOS iPhone app in the iOS Simulator. Complements [`MOBILE_APP.md`](MOBILE_APP.md), [`MOBILE_NETWORKING.md`](MOBILE_NETWORKING.md), and [`apps/ios/README.md`](../apps/ios/README.md).

---

## Prerequisites

| Requirement | Purpose |
|---|---|
| macOS with Xcode 16+ | Build, Simulator, `xcrun simctl` |
| XcodeGen (`brew install xcodegen`) | Regenerate `KnowledgeOS.xcodeproj` from `project.yml` |
| Node.js 18+ | Run `ios-simulator-mcp` via `npx` |
| [Facebook IDB](https://fbidb.io/docs/installation) | Required by `ios-simulator-mcp` for UI describe/tap/type/swipe |
| iPhone 16 Simulator runtime | Default device profile (`SIMULATOR_NAME`) |
| Docker stack (optional) | Login/search/capture QA needs `GET /api/v1/health` reachable — see networking below |

**Networking:** Run `bash scripts/mobile_network_check.sh` before flows that hit the API. Simulator default base URL: `http://127.0.0.1:8001`.

**Missing simulator:** If `iPhone 16` is not listed:

```bash
xcrun simctl create "iPhone 16" "com.apple.CoreSimulator.SimDeviceType.iPhone-16" \
  "com.apple.CoreSimulator.SimRuntime.iOS-18-0"
```

Adjust the runtime identifier to match `xcrun simctl list runtimes`.

---

## Helper scripts (repo)

From the repository root:

```bash
# Boot simulator, build, install, and launch KnowledgeOS
bash scripts/mobile_simulator_boot.sh

# Screenshot the booted simulator → .tmp/mobile-qa/<timestamp>.png
bash scripts/mobile_simulator_screenshot.sh

# PHONE-08 parity flows → .tmp/mobile-qa/phone-08/<timestamp>/*.png
bash scripts/mobile_qa_phone08.sh
```

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `SIMULATOR_NAME` | `iPhone 16` | Simulator device name |
| `SCHEME` | `KnowledgeOS` | Xcode scheme |
| `BUNDLE_ID` | `com.knowledgeos.ios` | App bundle identifier |

---

## Screenshot conventions

- **Path pattern:** `.tmp/mobile-qa/<phase>/<step>-<YYYYMMDD-HHMMSS>.png`
  - Example: `.tmp/mobile-qa/phone-03a/login-01-20260517-143022.png`
- **Never commit** screenshots — `.gitignore` ignores `.tmp/mobile-qa/*` except `.gitkeep`.
- **Script default:** `mobile_simulator_screenshot.sh` writes `.tmp/mobile-qa/<timestamp>.png` at repo root.
- **MCP default dir:** Set `IOS_SIMULATOR_MCP_DEFAULT_OUTPUT_DIR` to the repo's `.tmp/mobile-qa` absolute path so agent screenshots land in the same tree.

---

## ios-simulator-mcp (recommended)

MCP server for iOS Simulator UI automation. **Pin version `>=1.3.3`** — earlier versions had a command-injection vulnerability (CVE-2025-52573) fixed in v1.3.3.

### Install (Cursor)

Edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "ios-simulator": {
      "command": "npx",
      "args": ["-y", "ios-simulator-mcp@>=1.3.3"],
      "env": {
        "IOS_SIMULATOR_MCP_FILTERED_TOOLS": "record_video,stop_recording,open_simulator,get_booted_sim_id",
        "IOS_SIMULATOR_MCP_DEFAULT_OUTPUT_DIR": "/absolute/path/to/agentic-knowledge-management/.tmp/mobile-qa"
      }
    }
  }
}
```

Replace the output directory with your checkout path.

### Install (Claude Code)

```bash
claude mcp add ios-simulator npx ios-simulator-mcp@>=1.3.3
```

Configure filtered tools and output dir in Claude's MCP config if supported.

### Allowed tools for agents

Only use these tools unless explicitly expanding scope:

| Tool | Use |
|---|---|
| `ui_describe_all` | Full accessibility tree (JSON) |
| `ui_find_element` | Find element by `kos.*` identifier or label |
| `ui_tap` | Tap coordinates or resolved element |
| `ui_type` | Keyboard input |
| `ui_swipe` | Scroll / navigate |
| `screenshot` | Save PNG to disk |
| `ui_view` | Inline screenshot in MCP response |
| `install_app` | Install `.app` bundle |
| `launch_app` | Launch `com.knowledgeos.ios` |

**Filter out** via `IOS_SIMULATOR_MCP_FILTERED_TOOLS`: `record_video`, `stop_recording`, `open_simulator`, `get_booted_sim_id` (redundant with repo boot script).

### Finding elements by accessibility ID

Use `ui_find_element` with exact match on the identifier string:

```json
{
  "search": ["kos.connect.urlField"],
  "matchMode": "exact"
}
```

Swift constants live in `apps/ios/KnowledgeOS/Core/UI/AccessibilityID.swift` (`enum Kos`).

---

## XCTest tab selection (iOS 26)

On iOS 26 simulators, `XCUIApplication.tabBars.buttons[...]` often reports hit point `{-1,-1}`, and off-screen `TabView` children remain in the accessibility tree. UI tests should **not rely on tapping the tab bar** or on visibility of identifiers from inactive tabs.

| Launch argument / env | Purpose |
|---|---|
| `-ui-testing-reset` | Clear Keychain + cache; use on first login in a test class |
| `-ui-testing-skip-reset` | Preserve session; pair with a prior login in the same XCTest run |
| `KOS_UI_TAB` / `-KOS_UI_TAB=<tab>` | `home`, `search`, `capture`, `ai`, or `settings` — selects tab on launch (env + launch argument) |
| `-ui-testing-single-tab` | UITest relaunch only: render one tab without `TabView` (avoids iOS 26 off-screen accessibility noise) |

Pattern for multi-tab flows:

1. `ensureSignedIn(reset: true)` once (sets `UITestSession.sharedSessionBootstrapped`).
2. `app.terminate()` then relaunch with `KOS_UI_TAB=search` (or `settings`, `home`) and `-ui-testing-skip-reset`.

Helpers: `apps/ios/KnowledgeOSUITests/UITestHelpers.swift`.

---

## mobile-mcp (alternative)

[mobile-mcp](https://www.npmjs.com/package/@mobilenext/mobile-mcp) supports **iOS Simulator, Android emulator, and physical devices** in one server.

| Choose | When |
|---|---|
| **ios-simulator-mcp** | iOS-only QA on Mac; tighter Simulator integration; this repo's scripts and docs |
| **mobile-mcp** | Cross-platform agents or real-device steps (see PHASE-PHONE-06) |

If using mobile-mcp, still follow the `kos.*` identifier contract and screenshot path rules in this doc.

---

## Accessibility identifier contract

**Pattern:** `kos.<screen>.<element>`

| Screen | Constant (Swift) | Identifier |
|---|---|---|
| Connect | `Kos.Connect.screen` | `kos.connect.screen` |
| Connect | `Kos.Connect.urlField` | `kos.connect.urlField` |
| Connect | `Kos.Connect.testConnectionButton` | `kos.connect.testConnectionButton` |
| Connect | `Kos.Connect.statusIdle` | `kos.connect.status.idle` |
| Login | `Kos.Login.emailField` | `kos.login.emailField` |
| Login | `Kos.Login.passwordField` | `kos.login.passwordField` |
| Login | `Kos.Login.submitButton` | `kos.login.submitButton` |
| Home | `Kos.Home.screen` | `kos.home.screen` |
| Home | `Kos.Home.recentList` | `kos.home.recentList` |
| Search | `Kos.Search.input` | `kos.search.input` |
| Search | `Kos.Search.resultsList` | `kos.search.resultsList` |
| Capture | `Kos.Capture.noteField` | `kos.capture.noteField` |
| Capture | `Kos.Capture.saveButton` | `kos.capture.saveButton` |
| Upload | `Kos.Upload.pickButton` | `kos.upload.pickButton` |
| Upload | `Kos.Upload.statusLabel` | `kos.upload.statusLabel` |
| AI | `Kos.AI.questionField` | `kos.ai.questionField` |
| AI | `Kos.AI.askButton` | `kos.ai.askButton` |

Full list: `AccessibilityID.swift`. **Wave 3 feature coders must** use `Kos.*` constants — no ad-hoc identifier strings in views.

### Migration from PHONE-01C (removed identifiers)

| Old (01C) | New (02B) |
|---|---|
| `connect.baseURL` | `kos.connect.urlField` |
| `connect.testConnection` | `kos.connect.testConnectionButton` |
| `connect.screen` | `kos.connect.screen` |
| `connect.status.*` | `kos.connect.status.*` |
| `home.placeholder` | `kos.home.placeholder` |

---

## Reusable agent QA prompts

Copy-paste into Cursor Agent / Claude Code after MCP is configured and `bash scripts/mobile_simulator_boot.sh` has run.

### 1. Boot, describe UI, return JSON tree

```
Boot the KnowledgeOS iOS app on the iPhone 16 simulator (or confirm it is running).
Use ui_describe_all on the booted simulator and return the full accessibility tree as JSON.
Save a screenshot to .tmp/mobile-qa/phone-02b/describe-<timestamp>.png.
Summarize: screen title, all elements with AXUniqueId matching kos.*, and any errors.
```

### 2. Login flow

```
Prerequisites: API at http://127.0.0.1:8001 with a test user.
On the login screen:
1. ui_find_element search ["kos.login.emailField"] matchMode exact — tap and ui_type the email.
2. ui_find_element search ["kos.login.passwordField"] — tap and ui_type the password.
3. ui_find_element search ["kos.login.submitButton"] — tap.
4. screenshot to .tmp/mobile-qa/phone-03a/login-result-<timestamp>.png
5. ui_describe_all — assert kos.home.screen or kos.home.recentList is visible; if kos.login.errorBanner appears, report its label.
```

### 3. Search flow

```
Assume logged in on Home.
1. Navigate to Search tab if needed; ui_find_element ["kos.search.input"] — tap and ui_type a query (e.g. "project").
2. Tap kos.search.submitButton if present, or submit via keyboard.
3. screenshot .tmp/mobile-qa/phone-03a/search-results-<timestamp>.png
4. Assert kos.search.resultsList or kos.search.resultRow appears in ui_describe_all.
```

### 4. Capture flow

```
From Home, tap kos.home.captureButton (or open Capture tab).
1. ui_find_element ["kos.capture.noteField"] — ui_type a short test note.
2. Tap kos.capture.saveButton.
3. screenshot .tmp/mobile-qa/phone-03b/capture-saved-<timestamp>.png
4. Report success or error state from the accessibility tree.
```

### 5. Upload flow

```
Open Upload / ingest UI.
1. Tap kos.upload.pickButton and select a small test image from the simulator photo library if the picker appears.
2. Wait for ingestion; screenshot .tmp/mobile-qa/phone-03b/upload-status-<timestamp>.png
3. Read kos.upload.statusLabel (or nearby status text) from ui_describe_all and report ingestion state.
```

---

## Coordination with parallel phases

| Phase | Owns | This phase does not touch |
|---|---|---|
| PHONE-02A | `Core/API/`, `Core/Auth/`, Keychain, DTOs, `LoginView` | API client implementation |
| PHONE-03A+ | Feature screens using `Kos.*` IDs | Full login/search/capture UI |
| PHONE-02B | This doc, scripts, `AccessibilityID.swift`, Connect AX migration | `SmokeFlow.swift` (Wave 3) |

**Bundle ID:** `com.knowledgeos.ios` — use in `launch_app` and boot script.

---

## Quick validation checklist

```bash
bash scripts/mobile_simulator_boot.sh
bash scripts/mobile_simulator_screenshot.sh
ls .tmp/mobile-qa/

cd apps/ios && xcodegen generate
xcodebuild -project KnowledgeOS.xcodeproj -scheme KnowledgeOS \
  -destination 'platform=iOS Simulator,name=iPhone 16' test
```

---

## References

- Phase spec: `project-phases/PHASE-PHONE-02B-SIMULATOR-AUTOMATION-AND-QA.md`
- ios-simulator-mcp: https://github.com/joshuayoes/ios-simulator-mcp (SECURITY.md — require >=1.3.3)
- Networking: `docs/MOBILE_NETWORKING.md`
