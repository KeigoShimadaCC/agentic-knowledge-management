# Phase PHONE-03C — Mobile AI

**Status:** Complete
**Goal:** Expose high-leverage AI on mobile: grounded KB Q&A, summarize current object, suggest links. Respect AI-disabled state.
**Wave:** 3 (parallel with 03A, 03B)
**Branch:** `phase-phone-03c-mobile-ai`
**Worktree:** `worktrees/kos-phone-03c`
**Depends on:** PHASE-PHONE-02A and PHASE-PHONE-03A. Coordinates with 03A through the shipped `AIActionsBar` hook in object detail surfaces.
**Blocks:** none

## Scope

Only `apps/ios/KnowledgeOS/Features/AI/**`, the **body** of `Features/Root/AITab.swift` (placeholder shipped by 02A), and small additive surfaces on 03A's detail views via a shared `AIActionsBar` component. Coordinate via a single shared file: `Features/AI/AIActionsBar.swift`. 03A renders the bar; 03C owns its content. Do **not** modify `MainTabView.swift` (tab order is frozen by 02A).

## Coordination with 03A

To prevent merge conflicts on detail views, 03A's detail views include a placeholder:

```swift
// Wave 3 coordination point
if let object = currentObject {
  AIActionsBar(object: object)
}
```

03A ships an empty stub of `AIActionsBar`. 03C replaces the stub with the real implementation. **`AIActionsBar.swift` is the single file 03C touches outside `Features/AI/`.**

## Endpoints consumed

- `POST /api/v1/ai/answer` (grounded KB Q&A)
- `POST /api/v1/ai/summarize`
- `POST /api/v1/ai/suggest-links`

## Tasks

1. **AI tab** with a "Ask KnowledgeOS" screen. Single text field + send. Renders streamed/non-streamed answer + citations list (each citation tap opens the source via ObjectDetail).
2. **Summarize** action on PageDetail/SourceDetail via `AIActionsBar`. Result shown in a sheet.
3. **Suggest links** action on ObjectDetail via `AIActionsBar`. Results are tappable.
4. **AI-disabled state**: bootstrap's `capabilities.ai_enabled == false` (or any 503 with `code: "ai_disabled"`) → grey out actions + explain via popover.
5. **Never auto-fire**. Every AI call is user-initiated. Document this rule inside the AI tab help text.
6. **Citations** display: title, kind badge, snippet, tap → open source.
7. Tests: AIDTO decoding (already in 02A), AI-disabled mapping in `APIError`, UI test for "ask → see answer + 1 citation".

## Definition of done

- Ask KB question from iPhone with backend AI enabled → grounded answer + ≥1 citation.
- With `OPENAI_API_KEY` unset, UI shows AI-disabled state, never crashes.
- No silent external API calls — every call traceable to a user tap.
- `PROGRESS.md` updated.

## Validation

```bash
# With AI enabled (OPENAI_API_KEY set)
docker compose -f infra/docker-compose.yml up -d
cd apps/ios
xcodebuild -project KnowledgeOS.xcodeproj -scheme KnowledgeOS \
  -destination 'platform=iOS Simulator,name=iPhone 16' \
  -only-testing:KnowledgeOSTests test

# With AI disabled (OPENAI_API_KEY unset)
# Re-run, manually confirm "AI disabled" state in app.
```

## Out of scope

- AI write tools (extract project, generate resume) — out of MVP.
- Edits driven by AI suggestions — out of MVP.
