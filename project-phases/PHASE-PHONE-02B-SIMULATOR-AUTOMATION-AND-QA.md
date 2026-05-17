# Phase PHONE-02B — Simulator Automation & QA

**Status:** Planned
**Goal:** Give AI coders eyes/hands inside the iOS Simulator. Document `ios-simulator-mcp` and `mobile-mcp` setup. Add reusable QA prompts and accessibility identifiers contract.
**Wave:** 2 (parallel with 02A)
**Branch:** `phase-phone-02b-simulator-qa`
**Worktree:** `../kos-phone-02b`
**Depends on:** PHASE-PHONE-01C (scaffold must build)
**Blocks:** none (informs Wave 3 coders)

## Scope

Only `docs/MOBILE_QA.md` (new), `scripts/mobile_simulator_*.sh` (optional helpers), and an accessibility-identifiers convention doc. Do **not** add product code. May add `KnowledgeOSUITests/SmokeFlow.swift` once Wave 3 lands; for now ship the **contract** and **agent prompts**.

## Files to create

- `docs/MOBILE_QA.md` — MCP setup, QA prompts, AX-id naming rules
- `scripts/mobile_simulator_boot.sh` — boots iPhone 16 simulator + installs latest build
- `scripts/mobile_simulator_screenshot.sh` — saves to `.tmp/mobile-qa/<timestamp>.png`
- `.tmp/mobile-qa/.gitkeep` (committed empty)
- `apps/ios/KnowledgeOS/Core/UI/AccessibilityID.swift` — central registry of AX identifiers

## Tasks

1. Document MCP setup in `docs/MOBILE_QA.md`:
   - `ios-simulator-mcp` (pin `>=1.3.3` for the documented command-injection fix). Provide `claude mcp add ios-simulator npx ios-simulator-mcp` example.
   - `mobile-mcp` as broader alternative (iOS + Android + real devices).
   - Filter dangerous/unneeded tools; only allow describe/tap/type/swipe/screenshot/install/launch.
2. Add an **accessibility-identifier convention**: `kos.<screen>.<element>` (e.g. `kos.connect.urlField`, `kos.login.submitButton`, `kos.search.input`). Wave 3 coders must use these.
3. `AccessibilityID.swift` exposes a `Kos` namespace with string constants Wave 3 coders consume.
4. Write reusable agent QA prompts (in `docs/MOBILE_QA.md`):
   - "Boot, screenshot, describe UI, return JSON tree."
   - "Login flow: type email/password, tap submit, screenshot result, assert Home visible."
   - "Search flow: type query in search input, screenshot results."
   - "Capture flow: tap capture, type note, save, screenshot."
   - "Upload flow: tap upload, pick test image, screenshot ingestion status."
5. Document screenshot conventions: write to `.tmp/mobile-qa/<phase>/<step>-<timestamp>.png`; never commit.
6. Boot/install helper scripts use `xcrun simctl`. Idempotent (re-runnable). Document required env (`SIMULATOR_NAME=iPhone 16`).

## Definition of done

- `docs/MOBILE_QA.md` is operator-ready.
- Helper scripts boot a simulator on a clean Mac.
- `AccessibilityID.swift` is committed and importable.
- `.tmp/mobile-qa/` is gitignored except for `.gitkeep`.
- `PROGRESS.md` updated.

## Validation

```bash
bash scripts/mobile_simulator_boot.sh
bash scripts/mobile_simulator_screenshot.sh
ls .tmp/mobile-qa/
```

## Out of scope

- E2E UI tests for Wave 3 features (those phases own their own flows).
- Real-device automation (PHASE-PHONE-06).
