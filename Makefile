.PHONY: test-unit test-api test-worker test-mcp test-e2e test-all

test-unit:
	pnpm -F @kos/web test:run

test-api:
	cd tests && PYTHONPATH=../services/api uv run pytest api/ unit/ -q

test-worker:
	cd tests && PYTHONPATH=../services/api:../services/worker uv run pytest worker/ -q

test-mcp:
	cd services/mcp && uv run --extra dev pytest tests/ -q

test-e2e:
	pnpm test:e2e

test-all: test-unit test-api test-worker test-mcp test-e2e

