# KnowledgeOS E2E Tests

Run these tests against a local Docker Compose stack. Use a sandbox library root:

```bash
LIBRARY_ROOT=$PWD/tests/e2e/.tmp/library docker compose -f infra/docker-compose.yml up -d
pnpm test:e2e
```

Reports are written under `tests/e2e/playwright-report/`. Failure traces, screenshots, and videos are under `tests/e2e/test-results/`.
