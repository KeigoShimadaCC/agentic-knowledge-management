# PHASE-FIX-01 — Claimed-Done Gaps

> **Type:** Remediation plan (post-Phase-7A audit)
> **Audit date:** 2026-05-15
> **Scope:** Items where a phase plan or `PROGRESS.md` checkbox is ticked, but the corresponding code, container, or test is missing, broken, or only partially implemented.
> **Out of scope:** Anything in `PHASE-FIX-02` (forgotten/undocumented) or `PHASE-FIX-03` (repo oddities).

This file is meant to be picked up by a coding agent (Codex / Claude Code) and executed top-to-bottom. Each task includes **Goal**, **Situation**, and **Potential fixes / approaches**. Pick one approach per task; do not implement all of them.

Tasks are ordered by priority. F1 is a five-minute fix that immediately stops shipping a broken MCP tool. F2 is the most user-visible defect (`docker compose up` silently doesn't ingest). F3–F6 follow.

---

## F1 — Wire `answer_from_kb` MCP tool to the real Phase 5 endpoint

> Maps to audit item **A4** and **E1** ("Five-minute fix, removes a known-broken tool from the MCP surface").

### Goal

Make `answer_from_kb` a working read-only MCP tool that delegates to `POST /api/v1/ai/answer`, so external agents (Claude Desktop, Cursor, Codex) get grounded KB Q&A with citations through MCP. Keep the tool **read-only** — no writes, no Phase 7B scope creep.

### Situation

- Phase 7A registered `answer_from_kb` as a *disabled stub*. The tool dispatcher in `services/mcp/kos_mcp/tools.py` (`_dispatch`) still raises:
  ```text
  RuntimeError: answer_from_kb is not available: Phase 5 AI assistant endpoint has not been implemented yet.
  ```
- Phase 5 is now complete. `POST /api/v1/ai/answer` exists, is tested (`tests/api/test_ai.py`), and accepts `{q, kind?, limit?}` returning `{answer, citations[], agent_run_id, context_count}`.
- The tool is still in `DEFAULT_ALLOWED_TOOLS` in `services/mcp/kos_mcp/config.py`, so it is *advertised* via `list_tools` and breaks the moment any agent calls it.
- The tool's `description` field still says `[UNAVAILABLE]`.

### Potential fixes / approaches

**Approach A — Wire it through `KosApiClient` (recommended).**

1. In `services/mcp/kos_mcp/client.py`, add an `answer_from_kb` method:
   ```python
   async def answer_from_kb(self, q: str, kind: str | None = None, limit: int = 10) -> dict:
       body = {"q": q, "limit": limit}
       if kind:
           body["kind"] = kind
       r = await self._http.post("/api/v1/ai/answer", json=body)
       r.raise_for_status()
       return r.json()
   ```
2. In `services/mcp/kos_mcp/tools.py`:
   - Drop the `[UNAVAILABLE]` from the tool description; replace with a real description that documents `question`, optional `kind`, optional `limit`.
   - Add the dispatch branch:
     ```python
     if name == "answer_from_kb":
         return await _answer_from_kb(client, **args)
     ```
   - Implement `_answer_from_kb` that returns a `redact_dict` payload: `answer`, `citations`, `context_count`, plus `agent_run_id` (this is *not* a secret; it is referenced in audit log inspection).
   - Handle `HTTPStatusError 503` gracefully: return `{"error": "ai_disabled", "message": "Server has no OPENAI_API_KEY configured."}` instead of bubbling a stack trace.
3. Update `services/mcp/tests/test_tools.py` to add at least:
   - Happy-path test (mocked `httpx` returns a valid answer payload).
   - 503 fallback test.
4. Update `docs/MCP_TOOLS.md`: move `answer_from_kb` from "disabled" to "available", document arguments and the AI-disabled error.

**Approach B — Drop the tool entirely until Phase 7B.**

If we don't want any AI calls through MCP yet, remove `answer_from_kb` from `DEFAULT_ALLOWED_TOOLS`, delete the `Tool(...)` registration block, and delete the `_dispatch` branch. Document in `docs/MCP_TOOLS.md` that KB Q&A is currently HTTP-only.

**Recommendation:** Approach A. The endpoint already exists and is audited via `agent_runs`. There is no Phase 7B prerequisite for a read-only tool.

### Verification

- `services/mcp/tests/test_tools.py` adds passing test for `answer_from_kb` happy path + 503.
- Manual smoke (MCP enabled): `kos-mcp` → `tools/list` returns updated description; `tools/call answer_from_kb` returns an answer.
- `docs/MCP_TOOLS.md` no longer says "disabled stub".

### Commit

`feat(mcp): wire answer_from_kb to /api/v1/ai/answer with 503 fallback`

---

## F2 — Add an RQ worker service to `infra/docker-compose.yml`

> Maps to audit item **A1** and **E2** ("`docker compose up -d` advertises full ingestion but doesn't deliver it").

### Goal

After `docker compose -f infra/docker-compose.yml up -d`, every job the API enqueues to Redis (PDF/CSV/YouTube/web extraction, chunking, embedding, reindex) is actually processed without the user manually launching `rq worker kos-ingest` on the host.

### Situation

- `infra/docker-compose.yml` defines five services: `postgres`, `redis`, `qdrant`, `api`, `web`. **There is no `worker` service.**
- `services/worker/kos_worker/worker.py` is the RQ entry point; `services/worker/pyproject.toml` has its own dependency set (`rq`, `psycopg2-binary`, `pypdf`, `pillow`, `httpx`, `beautifulsoup4`, `youtube-transcript-api`, `qdrant-client`, `openai`).
- `PHASE-2-SOURCES.md` documents `uv run --package kos-worker rq worker kos-ingest` as a "dev" command, but the README's Quick Start tells the user to just run `docker compose up -d` and visit `localhost:3000`.
- Net effect: a new user uploads a PDF, the API creates a `Source(ingestion_status="pending")` row and enqueues a job, and the job sits in Redis forever. The Sources UI keeps polling `pending`. Looks broken.

### Potential fixes / approaches

**Approach A — Add a new container `kos-worker` (recommended).**

1. **Dockerfile:** add a new stage to `infra/Dockerfile.api` *or* create `infra/Dockerfile.worker`. Easiest is to reuse `Dockerfile.api`'s `development` stage and just change the command — `uv` already has the worker package as a workspace member.
2. **Compose service:**
   ```yaml
   worker:
     build:
       context: ..
       dockerfile: infra/Dockerfile.api   # or Dockerfile.worker
       target: development
     container_name: kos-worker
     restart: unless-stopped
     working_dir: /app
     env_file: .env
     environment:
       DATABASE_URL: postgresql://${POSTGRES_USER:-kos}:${POSTGRES_PASSWORD:-kospass}@postgres:5432/${POSTGRES_DB:-knowledgeos}
       REDIS_URL: redis://redis:6379/0
       QDRANT_URL: http://qdrant:6333
       LIBRARY_ROOT: /library
       PYTHONPATH: /app:/worker
     volumes:
       - ../services/api:/app
       - ../services/worker:/worker
       - library-data:/library
     command:
       - sh
       - -c
       - "cd /worker && exec uv run rq worker kos-ingest --url $REDIS_URL"
     depends_on:
       postgres: { condition: service_healthy }
       redis: { condition: service_healthy }
       qdrant: { condition: service_healthy }
     logging: *default-logging
   ```
   Note: the worker uses **sync** SQLAlchemy + `psycopg2`, so the URL should be `postgresql://` (no `+asyncpg`). Double-check `services/worker/kos_worker/db.py` for the expected scheme.
3. **Healthcheck:** RQ doesn't expose a trivial HTTP healthcheck. Either skip the healthcheck, or add a `rq info --url $REDIS_URL kos-ingest` based one with `interval: 30s`.
4. **Concurrency:** start with 1 worker process. The compose file should make it obvious how to scale: `docker compose -f infra/docker-compose.yml up -d --scale worker=3`.
5. **Optional:** add a separate `embedder` queue later if embedding latency dominates ingestion. For now, one queue (`kos-ingest`) is fine.

**Approach B — Add a "worker profile" so the worker is opt-in.**

Use Compose `profiles: ["worker"]`. Default `docker compose up` doesn't start it; `docker compose --profile worker up` does. **Reject unless we explicitly want this** — it just kicks the can.

**Approach C — Document the host-side worker as required.**

Update README to say "in another terminal, run `cd services/worker && uv run rq worker kos-ingest`". This is the minimum-effort fix but doesn't deliver "local-first, one command up". **Not recommended.**

**Recommendation:** Approach A.

### Verification

1. `docker compose -f infra/docker-compose.yml up -d` → `docker compose ps` shows `kos-worker` healthy.
2. Upload a small PDF via the UI → the Source row transitions `pending → running → success` within ~15 seconds.
3. `docker compose logs worker` shows the job pickup and completion.
4. Existing integration tests still pass (they don't depend on a live worker).

### Commit

`infra(compose): add rq worker service for source ingestion and reindex`

---

## F3 — Sanitize search snippets (Hardening Subtask 2)

> Maps to audit item **A5 → Hardening Subtask 2** and **E4**.

### Goal

Eliminate the XSS vector in highlighted search snippets. After this task, no user-controlled HTML reaches `dangerouslySetInnerHTML` in the search UI.

### Situation

- `services/api/app/services/search_service.py` builds snippets with Postgres `ts_headline(...)`, passing `StartSel=<mark>, StopSel=</mark>`. `ts_headline` does **not** escape HTML in the underlying document — it preserves whatever was in `content_text` or `extracted_text` verbatim.
- `apps/web/src/components/search/SearchResultCard.tsx` line 49 does:
  ```tsx
  <p
    className="line-clamp-2 text-xs text-gray-400 [&_mark]:rounded ..."
    dangerouslySetInnerHTML={{ __html: snippetHtml }}
  />
  ```
  No sanitizer, no escaping.
- Attack surface: a user pastes `<script>fetch('/api/v1/...')</script>` (or `<img onerror=...>`) into a Tiptap page, or imports a web article whose text contains script tags. Any search that hits that page renders the snippet as live HTML inside the user's browser session. Cookie-auth means the script can hit the full API as the logged-in user.
- This is a local-first single-user app, so the blast radius is small, but it still violates the "soft everything / never silently lose user data" principle in `CLAUDE.md`, and any future multi-user mode breaks open.

### Potential fixes / approaches

**Approach A — Plain text + match ranges from the backend (cleanest).**

1. Change the snippet shape returned by `/search/keyword`, `/search/vector`, `/search/hybrid` from `snippet: string` (HTML) to:
   ```python
   class SearchSnippet(BaseModel):
       text: str            # raw plain text, no markup
       highlights: list[tuple[int, int]]   # [start, end) byte/char ranges in `text`
   ```
2. Strip `<mark>...</mark>` server-side by either:
   - Calling `ts_headline` with `StartSel=\x01, StopSel=\x02` (or any non-printable pair) and then scanning the string to build `highlights`, or
   - Switching to `ts_headline` with `HighlightAll=TRUE, MaxFragments=0` and parsing.
3. In `SearchResultCard.tsx`, render highlights as React nodes:
   ```tsx
   {segments.map((seg, i) =>
     seg.highlighted
       ? <mark key={i} className="rounded bg-yellow-700 text-yellow-100">{seg.text}</mark>
       : <span key={i}>{seg.text}</span>
   )}
   ```
   No `dangerouslySetInnerHTML` anywhere.
4. Update `tests/api/test_search.py` to assert snippet shape (text + ranges) and add a malicious-payload test: insert `<script>alert(1)</script>` into a page, search it, assert that the response is plain text and contains the literal `<script>...` (i.e. not parsed as HTML when rendered later).

**Approach B — Server-side whitelist sanitizer.**

Keep the snippet as a string, but run it through a whitelist that only allows `<mark>`. Options:
- Python `bleach` with `tags=["mark"], attributes={}, strip=True`. Add `bleach>=6.0` to `services/api/pyproject.toml`.
- Or hand-rolled: escape the full string with `html.escape`, then run a regex pass that unescapes `&lt;mark&gt;` → `<mark>` and `&lt;/mark&gt;` → `</mark>`.
- Apply once in the service layer right before returning, so all three search endpoints share it.
- Frontend stays the same.

Add a fixture test with `<script>`, `<img onerror>`, `<svg onload>`, `javascript:` URL, and a nested `<mark><script>` attack.

**Approach C — Sanitize client-side with DOMPurify.**

Add `dompurify` + `@types/dompurify`. Wrap the snippet in `DOMPurify.sanitize(snippet, { ALLOWED_TAGS: ["mark"], ALLOWED_ATTR: [] })` before passing to `dangerouslySetInnerHTML`. Cheapest implementation, but defense-in-depth is weaker (server still emits unsafe HTML).

**Recommendation:** Approach A. It is the only one that lets us delete `dangerouslySetInnerHTML` outright and is also the foundation for Hardening Subtask 4 (showing per-segment debug scores in the UI).

### Verification

- `tests/api/test_search.py` has a "snippet does not contain script tag literals as HTML" regression test.
- Frontend has no `dangerouslySetInnerHTML` left in `apps/web/src/components/search/`.
- Manual smoke: paste `<script>document.title='pwned'</script>` into a page, search for the surrounding text. Document title does **not** change.

### Commit

`fix(search): return safe snippet ranges instead of HTML markup`

---

## F4 — Add `tests/worker/` extractor coverage (Phase 2 backfill)

> Maps to audit item **A2**.

### Goal

Worker extractors (PDF, image, CSV, YouTube, web article) have automated regression coverage so future refactors don't silently break ingestion.

### Situation

- `services/worker/kos_worker/extractors/` ships PDF text extraction (`pypdf`), image metadata + thumbnail (`Pillow`), CSV preview (first 20 rows), YouTube oEmbed + transcript, and web article (`httpx + BeautifulSoup4`) extraction.
- `PHASE-2-SOURCES.md` planned `tests/worker/test_extractors.py` plus a `tests/worker/conftest.py` with a `psycopg2` sync session fixture, and `tests/worker/fixtures/sample.pdf`, `sample.csv`, `sample.jpg`.
- **None of this exists.** No `tests/worker/` directory at all.
- Net effect: the extractor logic is unverified and is the most failure-prone part of the system (network errors, weird PDFs, missing transcripts, encoding issues).

### Potential fixes / approaches

**Approach A — Pure unit tests, no DB (recommended start).**

1. Create `tests/worker/` with `conftest.py`, `fixtures/`, `test_pdf_extractor.py`, `test_image_extractor.py`, `test_csv_extractor.py`.
2. Generate fixtures programmatically in `conftest.py` (don't commit large binaries):
   - PDF: use `reportlab` (already a transitive dep of many libs; if not, add as a *dev* dep) to render a 2-page PDF with known text.
   - Image: use `Pillow` to write a 100×60 PNG.
   - CSV: write a 5-row CSV string with `csv` stdlib.
3. Each test invokes the extractor function directly with a `tmp_path` workspace, asserts the returned text/dimensions/preview JSON, and verifies any derivatives (thumbnail file exists, has the right size).
4. **Mock network for YouTube/web extractors:** use `respx` or `pytest-httpx` to mock `httpx` responses. Do not hit real `youtube.com` or any external host.

**Approach B — Integration tests with a real RQ worker.**

End-to-end: enqueue a real RQ job, run a worker in-process via `rq.Worker(...)`, wait for the source row to flip to `success`. Higher coverage but slower and flakier. Defer until Approach A is in place.

**Approach C — Skip and rely on integration tests via the API.**

Add a few "upload a PDF, poll until ingestion success" tests in `tests/api/`. This requires F2 (worker container) to be done first. Useful as smoke coverage but does not isolate extractor failures.

**Recommendation:** Approach A first. Add Approach C as a separate follow-up after F2 ships.

### Verification

- `cd tests && uv run pytest worker/ -v` passes.
- Total test count crosses 130+ (currently ~147 with API/unit/MCP combined).
- Mutating any extractor function fails at least one test.

### Commit

`test(worker): add unit coverage for pdf, image, csv, youtube, web extractors`

---

## F5 — Resolve Hardening Subtasks 3–5 (multilingual eval, debug UI, index status)

> Maps to audit item **A5** (the rest of the hardening track beyond F3).

### Goal

Close out the Hardening Search Quality + Multilingual track so `PHASE-FIX-01` can mark the track ✅. F3 already covers Subtask 2; this task handles 3, 4, 5. Subtask 6 (docs) is bundled here.

### Situation

| Subtask | Status |
|---|---|
| 0 Plan | ✅ |
| 1 Multilingual ILIKE fallback | ✅ (commits `8bfc61d`, `f42287f`). No `pg_trgm` GIN index yet — ILIKE is sequential. |
| 2 Snippet sanitization | ❌ → see F3 |
| 3 Japanese / mixed fixtures | ❌ — `tests/fixtures/search_eval_cases.json` has only English |
| 4 Debug visibility | ⚠️ Backend supports `HybridRequest.debug: bool`. UI has no toggle, never renders scores. |
| 5 Index/reindex observability | ❌ — no `GET /api/v1/objects/{id}/index-status`; no doc on `reindex_object` / `reindex_all_objects` |
| 6 Docs | ❌ |

### Potential fixes / approaches

**Subtask 3 — JP / mixed eval cases:**

- Extend `tests/fixtures/search_eval_cases.json` with at least 4 new entries:
  - Pure Japanese query (e.g. `"会議メモ"`) over a Japanese-only page.
  - Mixed English + Japanese query (`"meeting メモ"`).
  - Latin-script query against a katakana-transliterated source title.
  - A "no-FTS-hit, ILIKE-fallback wins" case.
- Add a parametric test in `tests/api/test_search.py` that loops over these cases, creates the seed pages, and asserts the expected kinds appear.

**Subtask 4 — Debug UI:**

- Add a "Show ranking scores" toggle in `SearchModal.tsx`. Persist in `localStorage`. When on, pass `debug=true` to `/search/hybrid` and render `keyword_score`, `vector_score`, `combined_score` under each card.
- Backend already accepts `debug`; verify it returns per-result score breakdown. If not, extend `HybridSearchResponse` accordingly.

**Subtask 5 — Index status endpoint:**

- Add `GET /api/v1/objects/{id}/index-status` returning:
  ```python
  class IndexStatusOut(BaseModel):
      embedding_status: Literal["disabled", "pending", "running", "success", "failed"]
      embedding_model: str | None
      embedded_at: datetime | None
      chunk_count: int
      last_indexed_at: datetime | None
  ```
- Source the fields from the `chunks` table (already has `embedding_status`, `embedding_model`, `embedded_at`).
- Document in `docs/API.md` and `docs/ARCHITECTURE.md`.
- Add a short section to `docs/INGESTION.md` on how to run `reindex_object(object_id)` and `reindex_all_objects()` worker jobs.

**Subtask 6 — Docs:**

- Update `docs/API.md` (snippet shape, debug param, index-status), `docs/SECURITY.md` (XSS-mitigation note for snippets), `docs/ARCHITECTURE.md` (multilingual fallback + index observability).

### Verification

- Hardening section in `PROGRESS.md` is fully checked.
- `tests/api/test_search.py` passes with new JP cases.
- `index-status` endpoint returns `200` for an indexed page and `404` for an unknown id.
- `/inbox` is unaffected (this task touches search only).

### Commits

- `feat(search): japanese and mixed-language eval fixtures + assertions`
- `feat(web): search debug score toggle`
- `feat(api): object index-status endpoint`
- `docs: complete search hardening writeups`

---

## F6 — Reconcile Phase 5 inbox endpoint path

> Maps to audit item **A6**.

### Goal

Eliminate the spec-vs-code drift on the inbox endpoint so future agents reading `PHASE-5-AI-ASSISTANT.md` see what the code actually does.

### Situation

- `PHASE-5-AI-ASSISTANT.md` Definition of Done line: `GET /api/v1/objects/inbox`.
- Code: `services/api/app/api/v1/ai.py` exposes `GET /api/v1/ai/inbox`.
- Frontend (`apps/web/src/lib/api.ts → getInbox`) and Inbox UI already call the real path. There is no live bug — only a stale plan.

### Potential fixes / approaches

**Approach A — Update the plan to match code (recommended).**

- Edit `project-phases/PHASE-5-AI-ASSISTANT.md`:
  - Replace the row in the "API Endpoints" table.
  - Replace the `GET /api/v1/objects/inbox` line in Definition of Done.
- One-liner in `PROGRESS.md` "Current repo state notes" to mark this resolved.

**Approach B — Move the endpoint under `/api/v1/objects/inbox`.**

- Move the handler from `ai_router` to `objects_router`. Update `apps/web/src/lib/api.ts → getInbox` URL. Add a deprecation alias under `/api/v1/ai/inbox` that 301-redirects (or simply duplicates) for one release.
- Slightly cleaner semantically (it's an object query, not an AI action) but introduces a breaking change and a redirect to maintain. **Reject unless we have a reason.**

**Recommendation:** Approach A.

### Verification

- `grep -r "/api/v1/objects/inbox" .` returns no occurrences in plans or docs.
- `PHASE-5-AI-ASSISTANT.md` Definition of Done lists `GET /api/v1/ai/inbox`.

### Commit

`docs(phase5): reconcile inbox endpoint path with shipping code`

---

## F7 — Add `scripts/reindex.py` (referenced but missing)

> Maps to audit item **A3** (partial; the rest moves to `PHASE-FIX-02`).

### Goal

Ship a small CLI script that exercises the `reindex_object` / `reindex_all_objects` worker entry points so users (and Hardening Subtask 5 docs) have a documented recovery path when Qdrant goes missing or migration 0003 changes.

### Situation

- README previously listed `scripts/backup.sh, reindex.py (Phase 3+)`. README was corrected to drop both references, but the underlying need is real: there is no documented path to rebuild the Qdrant index from Postgres if the index is wiped.
- `services/worker/kos_worker/tasks.py` exposes `reindex_object(object_id)` and `reindex_all_objects()` already.
- (`backup.sh` is out of scope for this task — see `PHASE-FIX-02` if we want to actually plan it.)

### Potential fixes / approaches

**Approach A — Thin Python CLI under `scripts/`.**

```python
# scripts/reindex.py
import sys, uuid
from kos_worker.tasks import reindex_object, reindex_all_objects

def main() -> int:
    if len(sys.argv) == 1 or sys.argv[1] == "--all":
        reindex_all_objects()
        return 0
    for arg in sys.argv[1:]:
        reindex_object(uuid.UUID(arg))
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

Run with `PYTHONPATH=services/api:services/worker uv run python scripts/reindex.py [--all | <uuid> ...]`.

Document in `docs/INGESTION.md` and the Hardening Subtask 5 doc rollup (F5).

**Approach B — Add `kos-cli reindex` as a real Typer/Click CLI.**

Heavier; only worth it if we plan more admin commands (`kos-cli backup`, `kos-cli prune`, etc.). Defer.

**Recommendation:** Approach A.

### Verification

- `scripts/reindex.py <existing-page-id>` triggers a worker job and the page's `chunks.embedding_status` flips to `success`.
- `scripts/reindex.py --all` enqueues one job per indexable object.

### Commit

`feat(scripts): add reindex.py CLI for rebuilding chunk/vector indexes`

---

## Suggested ordering and grouping

A single agent run can land F1, F6 (both tiny) and the F3 plumbing in one sitting. F2 and F4 are larger and should be their own PRs. F5 should follow F3 because the snippet sanitization changes the response shape that the debug UI will render.

```
day 1: F1, F6
day 2: F2          (one PR: docker-compose worker)
day 3: F3, F4      (one PR each)
day 4: F5          (one or two PRs — search debug + index-status)
day 5: F7          (one tiny PR)
```

Each PR must:

- Touch only the files listed in its task.
- Add or update tests in the same commit as behavior changes.
- Update `PROGRESS.md` to flip its checkbox once verified.
- Not skip the relevant quality gate (`pnpm typecheck`, `pnpm lint`, `uv run ruff check services/api`, `uv run pytest`).
