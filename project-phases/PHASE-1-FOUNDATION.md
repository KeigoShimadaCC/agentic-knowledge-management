# Phase 1 — Foundation

**Status:** Complete ✓  
**Goal:** Docker, schema, page CRUD, Tiptap editor, auth, asset upload

---

## Subtask Checklist

- [x] 0 — Monorepo scaffold (root configs, directory tree, doc stubs)
- [x] 1 — Docker Compose + Dockerfiles (postgres, redis, qdrant, api, web)
- [x] 2 — Postgres schema + SQLAlchemy models + Alembic migrations
- [x] 3 — FastAPI shell + session auth endpoints (register/login/logout/me)
- [x] 4 — Objects, pages, assets CRUD API + content-addressed storage
- [x] 5 — Next.js app shell + 3-panel layout + auth flow
- [x] 6 — Tiptap page editor with auto-save
- [x] 7 — Asset upload UI (drag-and-drop + gallery)
- [x] 8 — Integration test suite

---

## Subtask 0 — Monorepo Scaffold

**Commit:** `chore: monorepo scaffold`  
**Validation:** `git log --oneline -1` shows the commit

Creates root configs and empty directory tree:
- `.gitignore`, `.editorconfig`, `README.md`
- `pnpm-workspace.yaml`, `package.json` (root)
- `pyproject.toml` (uv workspace), `uv.toml`
- `.gitkeep` files in: `apps/web/`, `services/api/`, `services/worker/`, `services/mcp/`, `packages/shared-types/`, `packages/schemas/`, `packages/prompts/`, `infra/`, `scripts/`, `tests/api/`, `tests/e2e/`
- Doc stubs: `docs/ARCHITECTURE.md`, `DATA_MODEL.md`, `API.md`, `MCP_TOOLS.md`, `INGESTION.md`, `SECURITY.md`, `AGENT_GUIDE.md`

---

## Subtask 1 — Docker Compose + Dockerfiles

**Commit:** `feat(infra): docker compose + dockerfiles`  
**Validation:** `docker compose -f infra/docker-compose.yml config` exits 0

Files:
- `infra/docker-compose.yml` — 5 services: postgres, redis, qdrant, api, web
  - All host ports bind to `127.0.0.1` only
  - postgres/redis/qdrant have working healthchecks
  - api depends_on all three (condition: service_healthy)
  - web depends_on api (condition: service_healthy)
  - library-data: bind mount to `${HOME}/KnowledgeOS/library`
- `infra/docker-compose.override.yml` — dev hot-reload (source mounts, --reload)
- `infra/.env.example` — all env vars with placeholder values
- `infra/Dockerfile.api` — multi-stage: base / development / production (python:3.12-slim + uv)
- `infra/Dockerfile.web` — multi-stage: base / development / builder / production (node:20-alpine + pnpm)
- `scripts/setup.sh` — creates `~/KnowledgeOS/{library/assets,library/tmp,library/exports,backups,logs,data/kuzu}`, copies `.env.example`

---

## Subtask 2 — Postgres Schema + SQLAlchemy + Alembic

**Commit:** `feat(api): sqlalchemy models and alembic migrations`  
**Validation:** `cd services/api && uv run python -c "from app.models import *; print('OK')"` exits 0

Services API dependencies:
```
fastapi>=0.111, uvicorn[standard]>=0.30, sqlalchemy[asyncio]>=2.0, asyncpg>=0.29,
alembic>=1.13, pydantic>=2.7, pydantic-settings>=2.2, python-multipart>=0.0.9,
redis[hiredis]>=5.0, rq>=1.16, passlib[bcrypt]>=1.7, itsdangerous>=2.2,
aiofiles>=23.2, python-jose>=3.3
```

Tables (SQLAlchemy 2.0 Mapped/mapped_column syntax, all UUIDs, all timestamps timezone-aware):
- `users` — id, email (unique), display_name, password_hash, created_at, updated_at, deleted_at
- `sessions` — id, user_id→users, token_hash (unique), user_agent, ip_address, expires_at, created_at, last_seen
- `objects` — id, user_id→users, kind (page/asset/note/bookmark/collection), title, description, tags (ARRAY), metadata (JSONB), is_pinned, is_archived, created_at, updated_at, deleted_at; GIN index on tags and FTS
- `pages` — id→objects, content_json (JSONB), content_text, word_count, version, created_at, updated_at
- `assets` — id→objects, filename, content_type, size_bytes, sha256 (indexed), storage_path, status (uploading/ready/error), width, height, duration_secs, created_at, updated_at
- `edges` — id, user_id→users, source_id→objects, target_id→objects, kind (link/embed/child/tag/related/citation), weight, metadata (JSONB), created_at, deleted_at; UniqueConstraint(source_id, target_id, kind)
- `chunks` — id, object_id→objects, chunk_idx, content, token_count, metadata (JSONB), created_at; UniqueConstraint(object_id, chunk_idx)
- `ingestion_jobs` — id, user_id→users, object_id→objects (nullable), status, job_type, payload (JSONB), result, error, attempts, max_attempts, enqueued_at, started_at, finished_at, created_at
- `agent_runs` — id, user_id→users, status, agent_type, input (JSONB), output, error, model, input_tokens, output_tokens, cost_usd, started_at, finished_at, created_at

Also: `docs/schema.sql` (raw CREATE TABLE statements for documentation)

---

## Subtask 3 — FastAPI Shell + Auth

**Commit:** `feat(api): FastAPI shell + session auth endpoints`  
**Validation:** `curl http://localhost:8000/health` returns `{"status":"ok"}`

Endpoints:
- `POST /api/v1/auth/register` — creates user + session, sets `kos_session` HTTP-only cookie
- `POST /api/v1/auth/login` — verifies bcrypt password, creates session, sets cookie
- `POST /api/v1/auth/logout` — deletes session, clears cookie
- `GET /api/v1/auth/me` — returns UserOut
- `GET /health` — checks DB + Redis, returns `{status, version, db, redis}`

Security:
- `passlib[bcrypt]` for password hashing
- Session token = `secrets.token_urlsafe(32)`, stored as `sha256(token)` in DB
- Cookie: `kos_session`, httponly=True, samesite="lax", max_age=30 days
- `get_current_user` dep: reads cookie → lookup session → update last_seen → return User

---

## Subtask 4 — Objects, Pages, Assets CRUD

**Commit:** `feat(api): objects, pages, assets CRUD + content-addressed storage`  
**Validation:** Full CRUD cycle via curl (register → login → POST /pages → GET → PATCH → DELETE → GET trash)

Routes:
```
GET/POST  /api/v1/objects               list (FTS, kind, tag filters) / create
GET       /api/v1/objects/trash         soft-deleted items
GET/PATCH/DELETE /api/v1/objects/{id}   get / update / soft-delete
POST      /api/v1/objects/{id}/restore  undelete

POST      /api/v1/pages                 create Object(kind=page) + Page atomically
GET/PUT/PATCH /api/v1/pages/{id}        get / full-replace / partial-update

POST      /api/v1/assets/upload         multipart; SHA256 dedup; content-addressed storage
GET       /api/v1/assets/{id}           metadata
GET       /api/v1/assets/{id}/download  stream file
DELETE    /api/v1/assets/{id}           soft-delete
```

Content-addressed storage (`core/storage.py`):
- Path: `assets/{sha256[:2]}/{sha256}/original.{ext}` under LIBRARY_ROOT
- Atomic write: write to `.tmp` then `rename()`
- Dedup: if path exists, skip write

---

## Subtask 5 — Next.js App Shell

**Commit:** `feat(web): Next.js app shell with auth + 3-panel layout`  
**Validation:** `pnpm typecheck` exits 0; `http://localhost:3000` renders after login

Key packages: next@14.2.3, react@18, @tiptap/react@2.4, tailwindcss@3, swr@2, lucide-react

Layout:
- Root `/` → redirect to `/app`
- `(auth)/login` + `(auth)/register` — public pages
- `(app)/layout.tsx` — server component: fetch `/api/v1/auth/me`, redirect to `/login` if 401
- `AppShell`: 3-panel — left sidebar (w-60), main (flex-1), right detail (w-80, toggleable)
- Sidebar nav: All Objects / Pages / Assets / Trash + "New Page" button

TypeScript: strict mode, noUncheckedIndexedAccess, exactOptionalPropertyTypes, no `any`

---

## Subtask 6 — Tiptap Page Editor

**Commit:** `feat(web): Tiptap page editor with auto-save`  
**Validation:** Type text → wait 800ms → GET /pages/{id} shows updated content

Components:
- `PageEditor.tsx` — Tiptap useEditor with StarterKit, Placeholder, Typography, Link, Image
- `EditorToolbar.tsx` — Bold/Italic/Strike/Code/H1-H3/BulletList/OrderedList/Blockquote/CodeBlock
- `PageTitle.tsx` — contentEditable h1, onBlur triggers title save
- `PageView.tsx` — title + toolbar + editor + word count footer
- `useAutoSave.ts` — debounced 800ms, PATCH /api/v1/pages/{id}, returns status: idle/saving/saved/error
- `usePage.ts` — SWR hook for GET /pages/{id}

---

## Subtask 7 — Asset Upload UI

**Commit:** `feat(web): asset upload UI with drag-and-drop`  
**Validation:** Drag file → see progress → asset in grid → click to preview

Components:
- `useUpload.ts` — XHR upload with progress events, per-file UploadState
- `AssetUploader.tsx` — drag-and-drop zone + file input + per-file progress bars
- `AssetCard.tsx` — image thumbnail or file-type icon, filename, size, date
- `AssetGrid.tsx` — 4-column CSS grid, empty state
- `AssetPreview.tsx` — modal overlay, full image or download link

---

## Subtask 8 — Integration Tests

**Commit:** `test: Phase 1 integration test suite`  
**Validation:** `cd tests && uv run pytest -v` — all tests pass

Coverage:
- `test_health.py` — health endpoint returns ok
- `test_auth.py` — register, login, me, logout, duplicate email, wrong password
- `test_objects.py` — CRUD, pagination, FTS, soft-delete, trash, restore
- `test_pages.py` — create (atomic), get, put, patch
- `test_assets.py` — upload, dedup (same file twice), download

Uses: pytest-asyncio, httpx.AsyncClient with ASGITransport, function-scoped fixtures

---

## Phase 1 Definition of Done

- [ ] `docker compose up` — all 5 services healthy
- [ ] `GET http://localhost:8000/health` → `{"status":"ok","db":true,"redis":true}`
- [ ] Register + login at `http://localhost:3000`
- [ ] Create page → type in Tiptap → auto-saves within 1s
- [ ] Drag-drop file → uploads → appears in asset grid
- [ ] `pytest -v` — all tests pass
- [ ] `pnpm typecheck` — zero errors
- [ ] All commits pushed to GitHub remote
