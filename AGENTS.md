# Repository Guidelines

## Project Structure & Module Organization

KnowledgeOS is a local-first monorepo. The web UI lives in `apps/web/src`, with routes in `app/`, UI in `components/`, hooks/API helpers in `lib/`, and shared types in `types/`. The FastAPI backend is in `services/api/app`, organized by `api/v1`, `models`, `schemas`, `services`, `core`, `db`, and `search`. Worker ingestion code is in `services/worker/kos_worker`; MCP code is in `services/mcp/kos_mcp`. Tests are in `tests/api`, fixtures in `tests/fixtures`, infrastructure in `infra`, and design docs in `docs`. `tests/dummy_pkg` is a Hatchling placeholder documented in `tests/dummy_pkg/README.md`; do not import from it or add code there.

## Build, Test, and Development Commands

- `bash scripts/setup.sh`: create local KnowledgeOS directories and seed `infra/.env`.
- `docker compose -f infra/docker-compose.yml up -d`: start local services.
- `pnpm dev`: run all workspace dev servers; `apps/web` serves Next.js on port `3000`.
- `pnpm build`: build all pnpm packages.
- `pnpm lint` and `pnpm typecheck`: run frontend linting and TypeScript checks.
- `cd services/api && uv run uvicorn app.main:app --reload --port 8000`: run the API.
- `cd services/api && uv run ruff check . && uv run ruff format .`: lint and format Python.
- `cd tests && PYTHONPATH=../services/api uv run pytest api/ unit/ -v`: run integration tests plus unit tests (requires Postgres on `DATABASE_URL`, typically port matching Docker).

## Coding Style & Naming Conventions

Use TypeScript for frontend code and Python 3.12 for services. Python uses Ruff with 100-character lines and `E`, `F`, and `I` rules. Prefer service-layer functions in `services/api/app/services` over route-level business logic. Name API tests `test_<resource>.py`, React components `PascalCase.tsx`, and hooks `useThing.ts`.

## Testing Guidelines

Tests are pytest-based integration tests using real FastAPI and Postgres. Add or update `tests/api` coverage for endpoint, schema, database, or ingestion changes. Run targeted tests first, for example `cd tests && uv run pytest api/test_pages.py -v`, then the full API suite. Frontend changes should pass `pnpm typecheck` and `pnpm lint`; browser-check the changed flow at `http://localhost:3000`.

## Commit & Pull Request Guidelines

Git history uses conventional prefixes such as `feat(search):`, `fix:`, `test:`, and `docs:`. Keep commits focused and include tests or docs when behavior changes. Before handing off or committing completed project work, update `PROGRESS.md` so the finished subtasks, current phase status, and repo state notes match the actual code. Pull requests should summarize the change, list verification commands, link related issues or phase docs, and include screenshots for UI changes.

## Security & Agent-Specific Instructions

Follow `CLAUDE.md` for agent rules. Do not hard-delete user data; use soft deletes. Keep user files under `~/KnowledgeOS/` or `LIBRARY_ROOT`. Never expose secrets, API keys, session secrets, or password hashes through API or MCP responses. Treat Postgres plus local files as canonical; Qdrant and Kuzu are rebuildable indexes.
