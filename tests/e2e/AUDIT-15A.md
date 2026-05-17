# AUDIT-15A: Real AI Playwright E2E Specs

Run command:

```bash
E2E_WEB_URL=http://127.0.0.1:3000 pnpm --dir tests/e2e test specs/29-sai01-career-ai.spec.ts specs/30-sai02-page-intelligence.spec.ts specs/31-sai03-inbox-triage.spec.ts specs/32-sai04-context7-mcp.spec.ts --reporter=line 2>&1
```

## Pass/Fail Summary

| Spec | Scenario | Result | Notes |
|---|---|---:|---|
| `specs/29-sai01-career-ai.spec.ts` | Career AI resume bullets and STAR stories | BLOCKED | Playwright timed out waiting for `http://127.0.0.1:3000` before spec execution. |
| `specs/30-sai02-page-intelligence.spec.ts` | Page summarize and claim extraction | BLOCKED | Playwright timed out waiting for `http://127.0.0.1:3000` before spec execution. |
| `specs/31-sai03-inbox-triage.spec.ts` | Inbox AI triage | BLOCKED | Playwright timed out waiting for `http://127.0.0.1:3000` before spec execution. |
| `specs/32-sai04-context7-mcp.spec.ts` | Context7 MCP connection and docs enrichment | BLOCKED | Playwright timed out waiting for `http://127.0.0.1:3000` before spec execution. |

## Bug Table

| ID | Scenario | Step | Severity | Symptom | Root Cause Hypothesis |
|---|---|---|---|---|---|
| AUDIT-15A-001 | All four real AI E2E specs | Playwright webServer readiness check | P0 | Runner failed with `Error: Timed out waiting 30000ms from config.webServer.` before any spec body ran. `curl` also failed to connect to `127.0.0.1:3000` and `127.0.0.1:8001`. | Local Next.js web app and FastAPI backend were not running or not reachable on the expected E2E ports. |

## Runner Output

```text
> knowledgeos-e2e@ test /Users/keigoshimada/Documents/agentic-knowledge-management/tests/e2e
> playwright test specs/29-sai01-career-ai.spec.ts specs/30-sai02-page-intelligence.spec.ts specs/31-sai03-inbox-triage.spec.ts specs/32-sai04-context7-mcp.spec.ts --reporter=line

Error: Timed out waiting 30000ms from config.webServer.

ELIFECYCLE Test failed. See above for more details.
```

## Endpoint Checks

```text
curl -I --max-time 5 http://127.0.0.1:3000
curl: (7) Failed to connect to 127.0.0.1 port 3000 after 0 ms: Couldn't connect to server

curl -I --max-time 5 http://127.0.0.1:8001/api/v1/auth/me
curl: (7) Failed to connect to 127.0.0.1 port 8001 after 0 ms: Couldn't connect to server
```
