# Phase 14B — Scenario Audit

## Test Run Summary

| Spec | Scenario | Tests | Passed | Failed |
|---|---|---|---|---|
| 24-s01-researcher | S01 Researcher | 5 | 5 | 0 |
| 25-s02-freelance-engineer | S02 Freelance Engineer | 5 | 5 | 0 |
| 26-s03-pm-chat-mining | S03 PM Chat Mining | 6 | 6 | 0 |
| 27-s04-ai-developer-mcp | S04 AI Developer MCP | 5 | 5 | 0 |
| 28-s05-bootcamp-grad | S05 Bootcamp Grad | 6 | 6 | 0 |

**Total: 27/27 passing**

---

## Bug Table

| ID | Scenario | Step | Severity | Symptom | Root Cause | Fix Applied |
|---|---|---|---|---|---|---|
| S02-BUG-001 | Freelance Engineer | Creates project | P2 | `page.getByText(/JavaScript\|Closures/)` resolved to 2 elements — strict mode violation | Sources list showed multiple matching elements; locator too broad | Added `.first()` to locator in spec 28 |
| S02-BUG-002 | Freelance Engineer | Cross-test state | P1 | Project created in test 1 was deleted before test 2 could navigate to it | `{ api }` fixture in test body called `softDeleteAllObjects()` in teardown, destroying seeded data between tests | Changed test 1 signature from `{ page, api }` to `{ page }` only; used module-level `seedApi` for API calls that must not trigger teardown |
| S01-INFO-001 | Researcher | AI answer | INFO | AI answer panel returns amber "no API key" state instead of a generated answer | OpenAI / Anthropic API keys not configured in local Docker stack | Not a bug — expected graceful degradation; `expectAiPanelOutcome()` helper accepts either generated content OR amber alert |
| S02-INFO-001 | Freelance Engineer | Resume bullets / Interview stories | INFO | AI panels return amber "no API key" state | Same as above | Same as above — `expectAiPanelOutcome()` handles both outcomes |

---

## Bugs Requiring Track 14C Fixes

None. All P0/P1 bugs were fixed inline during Track 14B development.

---

## Architecture Observations

1. **Single-user auth isolation**: App has no multi-user system. Test isolation is entirely via UUID tags + `cleanupByTag()`. This works correctly but means concurrent test runs could interfere.

2. **`softDeleteAllObjects()` in fixture teardown**: The `{ api }` fixture calls this after every test. Tests that share state across steps **must** use `createTestUser()` directly in `beforeAll` and store as module-level `seedApi`, never use `{ api }` in test bodies for those specs.

3. **IPv6 localhost issue**: `localhost:3000` resolved to `::1` returning HTTP 500 from Next.js. Fixed in `playwright.config.ts` by changing default URL to `http://127.0.0.1:3000`.

4. **Ingestion status field**: API returns `ingestion_status` (not `status`). Values: `pending | running | ready | error`. `waitForSource()` polls for `'ready'`.

5. **Chat import endpoint**: `POST /api/v1/chats/import` accepts multipart form with a `file` field containing JSON. Returns `{ imported: [{ id, title }] }`.

---

## Pass/Fail by Tag

```
@s01  5/5 ✅
@s02  5/5 ✅
@s03  6/6 ✅
@s04  5/5 ✅
@s05  6/6 ✅
```
