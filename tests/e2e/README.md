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
