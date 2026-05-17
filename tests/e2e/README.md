# KnowledgeOS E2E Tests

Run these tests against a local Docker Compose stack. Use a sandbox library root:

```bash
mkdir -p tests/e2e/.tmp/library
# AI summarize spec uses the API stub key (no real OpenAI calls).
grep -q '^OPENAI_API_KEY=' infra/.env && \
  sed -i.bak 's/^OPENAI_API_KEY=.*/OPENAI_API_KEY=sk-test-stub/' infra/.env || \
  echo 'OPENAI_API_KEY=sk-test-stub' >> infra/.env
LIBRARY_ROOT=$PWD/tests/e2e/.tmp/library docker compose -f infra/docker-compose.yml up -d --build
pnpm test:e2e
```

Reports are written under `tests/e2e/playwright-report/`. Failure traces, screenshots, and videos are under `tests/e2e/test-results/`.

---

## Spec Inventory (76 tests across 22 spec files)

| Spec | Tests | Features Covered |
|---|---|---|
| `01-auth.spec.ts` | 3 | Auth redirect, /me API, no-session redirect |
| `02-page-crud.spec.ts` | 1 | Create/edit page, autosave, persist after reload |
| `03-search.spec.ts` | 3 | Cmd+K, keyword results, result navigation |
| `04-source-ingestion.spec.ts` | 2 | URL ingest, status polling, modal renders |
| `05-graph-edges.spec.ts` | 3 | Backlink create, RelatedPanel, edge persistence |
| `06-ai-summarize.spec.ts` | 3 | Summarize button, audit row, from-cache label |
| `07-workspace-side-pane.spec.ts` | 3 | Open in side pane, content visible, close pane |
| `08-chat-import.spec.ts` | 2 | File import, paste transcript import |
| `09-trash-restore.spec.ts` | 3 | Soft-delete, restore, trash list visibility |
| `10-mcp-read.spec.ts` | 3 | stdio tools/list, object read via MCP |
| `11-career-project.spec.ts` | 3 | Create project, link evidence, resume bullets |
| `12-tutorial.spec.ts` | 5 | Seed tour, tour steps, Esc close, localStorage flag |
| `13-route-crawl.spec.ts` | 14 | Visit every major route, assert no critical JS errors |
| `14-feature-smoke.spec.ts` | 8 | Slash menu, bubble menu, AI panel tabs, multi-pane, shortcut overlay, bulk action bar, search filters, sidebar collapse |
| `15-inbox.spec.ts` | 3 | Inbox list renders, per-item triage modal, bulk select action bar |
| `16-multi-pane.spec.ts` | 3 | Open page in side pane, close pane, save workspace button |
| `17-mcp-settings.spec.ts` | 4 | Settings page renders, Add modal opens + has fields, Test button for existing connection |
| `18-career-ai.spec.ts` | 3 | Interview stories tab, generate preview (mocked), save story (mocked) |
| `19-editor-ux.spec.ts` | 5 | Toolbar Bold/Italic/H1, slash menu (V2), bubble menu (V2) |
| `20-ai-panel-advanced.spec.ts` | 7 | Extract Claims, Extract Tasks, Suggest Links, Ask KB input, Enrich with Docs input, mocked claims, web search toggle |
| `21-shortcut-overlay.spec.ts` | 4 | `?` opens overlay, Esc closes, shortcut list renders, sidebar collapse via ⌘\ |
| `22-asset-upload.spec.ts` | 3 | Drop zone visible, file upload shows card, grid view with heading |

**Total: 76 tests** (71 active + 5 skipped — V2 editor tests skipped unless `NEXT_PUBLIC_UX_EDITOR_V2=1`)

---

## Environment Variables

| Variable | Purpose |
|---|---|
| `E2E_WEB_URL` | Override base URL (default: `http://localhost:3000`) |
| `NEXT_PUBLIC_UX_EDITOR_V2` | Set to `1` to enable slash menu and bubble menu tests |

---

## Known Flaky Tests

- `02-page-crud` — Autosave timing; passes when run in isolation, occasionally flaky in the full suite under heavy load.
