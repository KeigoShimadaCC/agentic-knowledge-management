# Phase PHONE-06 — Device Install & Private Release

**Status:** Planned
**Goal:** Run on physical iPhone without App Store. Document recovery.
**Wave:** 6
**Branch:** `phase-phone-06-device-install`
**Worktree:** `../kos-phone-06`
**Depends on:** simulator MVP (03A–03C) green
**Blocks:** none

## Scope

Only signing/bundle config + `apps/ios/README.md` and `docs/MOBILE_APP.md` updates. May add a TestFlight section but TestFlight is optional.

## Tasks

1. Configure bundle identifier (`com.<owner>.knowledgeos`) in `project.yml`.
2. Configure signing team for personal Apple ID development signing.
3. Document direct install via Xcode "Run on Device".
4. Document network profile selection for device (LAN vs Tailscale).
5. Document recovery: how to reinstall after the 7-day personal-team cert expires.
6. Optional TestFlight section — recommend deferring unless multi-tester needed.
7. Final smoke: login → search → open → capture → ask AI on a real iPhone hitting the Mac backend over LAN or Tailscale.

## Definition of done

- App installs on a physical iPhone.
- Real device successfully logs in, searches, captures.
- Private release checklist exists in `apps/ios/README.md`.
- Recovery checklist exists.
- `PROGRESS.md` updated.

## Out of scope

- App Store submission.
- Android.
