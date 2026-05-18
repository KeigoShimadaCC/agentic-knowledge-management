# Phase PHONE-07 — Mobile Hardening & Contract Repair

**Status:** In Progress
**Goal:** Fix mobile-track contract drift and harden shipped phone behavior without adding backend endpoints.
**Wave:** hardening
**Branch:** `phase-phone-07-mobile-hardening`
**Worktree:** `worktrees/kos-phone-07`
**Depends on:** PHONE-03A, PHONE-03B, PHONE-03C, PHONE-05, PHONE-06 docs/config
**Blocks:** mobile docs drift and queue durability regressions

## Scope

- iOS source download behavior in SourceDetail/read APIs.
- iOS pending-upload queue storage location and migration from the legacy cache DB.
- Mobile docs and phone phase docs whose current state affects future phase execution.
- Lightweight docs consistency tests.

No backend endpoint changes are part of this phase.

## Tasks

1. Replace SourceDetail's unauthenticated Safari `/sources/{id}/download` link with an authenticated in-app download from `source.asset_id` through `GET /api/v1/assets/{asset_id}/download`.
2. Hide the SourceDetail download action when `source.asset_id` is missing.
3. Keep cache data in `Library/Caches`, but move the persistent pending-upload queue DB to `Application Support`.
4. Copy existing `pending_uploads` rows from the legacy cache DB into the new queue DB on first launch so queued captures are not lost.
5. Synchronize phone phase docs with current statuses, in-repo worktree paths, dependency edges, PHONE-02A scope, PHONE-03B ownership, PHONE-06 completion wording, and exact validation commands.
6. Update mobile contract docs so implemented auth/networking and current phase numbering are not described as future or missing.
7. Add a docs consistency test that catches stale phone markers.

## Validation

```bash
cd apps/ios && xcodegen generate
cd apps/ios && xcodebuild -project KnowledgeOS.xcodeproj -scheme KnowledgeOS -destination 'platform=iOS Simulator,name=iPhone 16' build
cd apps/ios && xcodebuild -project KnowledgeOS.xcodeproj -scheme KnowledgeOS -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:KnowledgeOSTests test
cd tests && PYTHONPATH=../services/api uv run pytest unit/test_phone_phase_docs.py -q
bash scripts/mobile_network_check.sh
```

`scripts/mobile_network_check.sh` requires the Docker stack/profile to be available. PHONE-06 remains incomplete until a real physical-device smoke succeeds; simulator-only checks do not complete it.

## Definition of done

- Source downloads are authenticated and asset-backed.
- Source rows without assets have no download UI.
- Queue storage is non-purgeable under Application Support and migration-tested.
- Mobile docs and phase docs match current implementation truth.
- PHONE-06 remains marked device-smoke pending.
- Swift and Python validation gates pass, except Docker-dependent network checks may be reported as environment-blocked when services are unavailable.
