# PHASE-FIX-02 — Forgotten and Undocumented

> **Type:** Remediation plan (post-Phase-7A audit)
> **Audit date:** 2026-05-15
> **Scope:** Things that nobody marked as "done" or "todo" — they fell between the cracks. Mostly config / docs / unblocked-but-not-noticed items. Lower-stakes than `PHASE-FIX-01`, but each one is a quiet papercut for new contributors and agents.
> **Out of scope:** Anything in `PHASE-FIX-01` (claimed-done gaps) or `PHASE-FIX-03` (visible weirdness).

This file is meant to be picked up by a coding agent. Each task includes **Goal**, **Situation**, and **Potential fixes / approaches**. Most are small enough to bundle into a single "infra cleanup" PR.

---

## F8 — Fix duplicate `MCP_INTERNAL_TOKEN` in `infra/.env.example`

> Maps to audit item **B4** and **E5 (part 1)**.

### Goal

`infra/.env.example` declares each variable exactly once. New users copying it to `.env` are not surprised by silent overrides.

### Situation

`infra/.env.example` currently contains two `MCP_INTERNAL_TOKEN=` lines:

```env
# MCP (Phase 7A): optional secret when MCP calls the API with X-KOS-Internal-Token (never commit real tokens).
MCP_INTERNAL_TOKEN=
...
# MCP Server (Phase 7A) — local-only stdio server for agent access
# Set MCP_ENABLED=true and generate a random MCP_INTERNAL_TOKEN to activate.
# The same token must be set in infra/.env for the API (MCP_INTERNAL_TOKEN).
# Run: uv run --project services/mcp kos-mcp
MCP_ENABLED=false
MCP_API_BASE_URL=http://127.0.0.1:8000
MCP_INTERNAL_TOKEN=        # <-- duplicate
```

Whichever line the dotenv parser keeps wins. Today both default to `""` so the duplication is silent, but if a user fills in the first one and the second one stays empty, the second wins on most parsers and MCP auth breaks. The duplication is also a code-review smell.

### Potential fixes / approaches

**Approach A — Single MCP block (recommended).**

Collapse the two MCP sections into one block at the bottom of the file:

```env
# ---------- MCP (Phase 7A) ----------
# Local-only stdio server for agent access (Claude Desktop, Cursor, Codex).
# Set MCP_ENABLED=true and generate a 32+ char random MCP_INTERNAL_TOKEN to activate.
# The API container and the kos-mcp process must share the same MCP_INTERNAL_TOKEN.
# Run: uv run --project services/mcp kos-mcp
MCP_ENABLED=false
MCP_API_BASE_URL=http://127.0.0.1:8001   # see F9 — host-side default matches docker compose
MCP_INTERNAL_TOKEN=
```

Delete the upper `MCP_INTERNAL_TOKEN=` block entirely.

**Approach B — Add a lint step.**

Add a tiny `scripts/check_env_example.py` (or pre-commit hook) that fails if any key appears twice in `.env.example`. Catches future regressions. Optional polish on top of A.

**Recommendation:** Approach A, optionally followed by B in a separate commit.

### Verification

- `grep -c "^MCP_INTERNAL_TOKEN=" infra/.env.example` returns `1`.
- No env-config tests break.

### Commit

`infra: deduplicate MCP_INTERNAL_TOKEN in .env.example`

---

## F9 — Fix `MCP_API_BASE_URL` default so it matches the dockerized API port

> Maps to audit item **B5** and **E5 (part 2)**.

### Goal

A user who runs the full stack with `docker compose up -d` and `kos-mcp` on the host can run an MCP tool call without overriding any env var.

### Situation

- `infra/.env.example` defaults `MCP_API_BASE_URL=http://127.0.0.1:8000`.
- `infra/docker-compose.yml` publishes the API at `127.0.0.1:8001:8000` (the in-container port is 8000; the host port is 8001 to avoid clashing with whatever the user has on 8000).
- If the user runs `kos-mcp` **on the host** against the dockerized API, the default URL is wrong — connection refused.
- If the user runs `kos-mcp` **inside the docker network** (a hypothetical future container), the URL should be `http://api:8000`, also wrong.

Either way, the documented default does not match any working topology.

### Potential fixes / approaches

**Approach A — Default to `8001` and document the override (recommended).**

- Set `MCP_API_BASE_URL=http://127.0.0.1:8001` in `infra/.env.example`.
- Add a comment block above the variable:
  ```env
  # Host-side default: matches the API port published by docker compose (8001 -> api:8000).
  # If you run `kos-mcp` inside the docker network, set this to http://api:8000 instead.
  # If you run the API natively on port 8000 (no docker), set this to http://127.0.0.1:8000.
  MCP_API_BASE_URL=http://127.0.0.1:8001
  ```
- Update `docs/MCP_TOOLS.md` and `docs/SECURITY.md` with the same guidance.

**Approach B — Change the published port to 8000.**

Edit `docker-compose.yml` so the API binds `127.0.0.1:8000:8000`. Risk: collides with anyone running another local API on 8000. The team explicitly chose 8001 to avoid that; do not revert without consent.

**Approach C — Document only.**

Leave the default as-is, just add a fat comment. Cheapest, but new users still hit a config mismatch the first time they enable MCP. **Reject.**

**Recommendation:** Approach A.

### Verification

- Fresh clone → `bash scripts/setup.sh` → `docker compose up -d` → set `MCP_ENABLED=true` + a token → `kos-mcp` connects without any URL override.
- The two doc files have updated guidance.

### Commit

`infra: align default MCP_API_BASE_URL with docker compose api port`

---

## F10 — Document the Postgres host port (5433, not 5432)

> Maps to audit item **B6**.

### Goal

A developer reading any doc in this repo cannot find an example that hits the *wrong* Postgres port. `psql`, the worker dev command, and the README all converge on the published port.

### Situation

- `infra/docker-compose.yml`:
  ```yaml
  postgres:
    ports: ["127.0.0.1:5433:5432"]
  ```
- `PHASE-2-SOURCES.md` "Worker run command (dev)" example uses `postgresql://kos:kospass@localhost:5432/knowledgeos`.
- A user running `psql -h localhost -p 5432` gets connection refused; with `-p 5433`, it works.
- The integration test suite uses the in-container hostname `postgres:5432` (via Docker DNS), so tests aren't affected. The papercut is only for host-side dev commands and ad-hoc `psql` sessions.

### Potential fixes / approaches

**Approach A — Fix all docs to use 5433 + add a top-level "ports cheat sheet" (recommended).**

1. Update `PHASE-2-SOURCES.md` example URL to `:5433`.
2. Add a short table to `README.md` under "Development":
   ```markdown
   ### Local Ports (published by docker compose)
   | Service | Host | In-container |
   |---|---|---|
   | API | 127.0.0.1:8001 | 8000 |
   | Web | 127.0.0.1:3000 | 3000 |
   | Postgres | 127.0.0.1:5433 | 5432 |
   | Redis | 127.0.0.1:6379 | 6379 |
   | Qdrant HTTP | 127.0.0.1:6333 | 6333 |
   | Qdrant gRPC | 127.0.0.1:6334 | 6334 |
   ```
3. Update `docs/ARCHITECTURE.md` "Running locally" section accordingly.

**Approach B — Change the published port to 5432.**

Risk: collides with a system Postgres. The 5433 choice is deliberate. **Reject.**

**Recommendation:** Approach A.

### Verification

- `grep -rn "localhost:5432\|127.0.0.1:5432" .` returns nothing in `README.md`, `docs/`, or `project-phases/` (the docker-compose's internal `postgres:5432` is fine — that's the *in-container* hostname, not localhost).

### Commit

`docs: document published port mapping (api 8001, postgres 5433, …)`

---

## F11 — Plan and either build or remove `scripts/backup.sh`

> Maps to audit item **A3 / B-residual** — the README used to reference `backup.sh`, that reference was removed during the 2026-05-15 audit, but the *need* for a backup mechanism is still real and undocumented.

### Goal

KnowledgeOS is local-first. Either the project ships a one-command backup script that covers Postgres + library + (optionally) Qdrant snapshots, **or** it explicitly documents that there is no built-in backup and points users at their own tooling. Either way, no doc references a script that doesn't exist.

### Situation

- README "File Layout" previously listed `scripts/backup.sh` as if it existed. It did not. README was corrected.
- `CLAUDE.md` includes "Never hard-delete user data" — backup is the natural complement.
- `~/KnowledgeOS/library/` is bind-mounted into the API container; Postgres data lives in a Docker volume `postgres-data`; Qdrant data is in volume `qdrant-data`.
- There is no `pg_dump`-based snapshot, no `docker compose exec postgres pg_dumpall` automation, no tarball of `~/KnowledgeOS/`.

### Potential fixes / approaches

**Approach A — Ship a minimal `scripts/backup.sh` (recommended for the local-first ethos).**

```bash
#!/usr/bin/env bash
set -euo pipefail

ts=$(date +%Y%m%d-%H%M%S)
out="${HOME}/KnowledgeOS/backups/${ts}"
mkdir -p "$out"

# Postgres logical dump
docker compose -f infra/docker-compose.yml exec -T postgres \
  pg_dump -U "${POSTGRES_USER:-kos}" -d "${POSTGRES_DB:-knowledgeos}" -Fc \
  > "${out}/postgres.dump"

# Library tar (excluding tmp/)
tar --exclude '*/tmp/*' -C "${HOME}/KnowledgeOS" -czf "${out}/library.tar.gz" library

# Qdrant snapshot (best-effort; Qdrant is re-buildable)
curl -fsS -X POST http://127.0.0.1:6333/snapshots > "${out}/qdrant-snapshot.json" || true

echo "Backup written to ${out}"
```

- Wire `~/KnowledgeOS/backups/` directory creation into `scripts/setup.sh` (already partially there per `PHASE-1-FOUNDATION.md`).
- Add a "Backup & Restore" section to `README.md` and `docs/ARCHITECTURE.md`.

**Approach B — Explicitly say "no built-in backup".**

Add a one-paragraph note to `docs/SECURITY.md` or `docs/ARCHITECTURE.md` directing users to their own snapshot strategy (Time Machine for the library tree; `pg_dump` for the DB). Smaller surface area but doesn't deliver the local-first promise.

**Recommendation:** Approach A. Keep it small.

### Verification

- `scripts/backup.sh` runs to completion against a populated local stack and writes three files under `~/KnowledgeOS/backups/<ts>/`.
- README references it correctly.

### Commit

`feat(scripts): minimal backup.sh for postgres dump + library tarball`

---

## F12 — Document the `tests/dummy_pkg` placeholder or remove it

> Maps to audit item **B7**.

### Goal

Future contributors and agents do not waste time wondering what `tests/dummy_pkg/` is, why it has a one-line `__init__.py`, and whether deleting it is safe.

### Situation

- `tests/dummy_pkg/__init__.py` contains exactly:
  ```python
  """Placeholder package so the tests project builds under hatchling."""
  ```
- `tests/pyproject.toml` presumably has `[tool.hatch.build.targets.wheel] packages = ["dummy_pkg"]` or similar. (Verify before changing.)
- Nothing imports `dummy_pkg`. It exists purely to satisfy a build-backend constraint when `tests/` is treated as a Python package.

### Potential fixes / approaches

**Approach A — Keep the placeholder and document it (recommended; minimal risk).**

1. Add a `tests/dummy_pkg/README.md`:
   ```markdown
   # dummy_pkg

   Placeholder Python package so the `tests` workspace builds under hatchling.
   The `tests` project ships no production code; this package satisfies
   `[tool.hatch.build.targets.wheel] packages` so `uv` can resolve the
   workspace member. Do not import from it. Do not add code here.
   ```
2. Add a one-line note to `AGENTS.md` and `tests/pyproject.toml` referencing the README.

**Approach B — Restructure `tests/` so it isn't a Python package.**

If `tests` doesn't need to be a uv workspace member, drop it from the workspace and remove `dummy_pkg`. Risk: changes how `uv run pytest` discovers the test deps. Verify with the existing test runners before doing this.

**Approach C — Move tests under each service (`services/api/tests/...`).**

Long-term cleaner, but a big refactor and out of scope for a "forgotten" cleanup.

**Recommendation:** Approach A.

### Verification

- `cat tests/dummy_pkg/README.md` exists and explains the package.
- All test commands still work.

### Commit

`docs(tests): explain dummy_pkg placeholder`

---

## F13 — Trigger explicit Phase 7B kickoff (now unblocked)

> Maps to audit item **E7** — "Phase 7B is now unblocked".

### Goal

Phase 7B (MCP write tools) is no longer blocked by the missing `object_revisions` table — Phase 5 shipped that. Make sure this is reflected so the next planning pass can pick Phase 7B up cleanly.

### Situation

- `PROGRESS.md` Phase 7B section lists "MCP Write Tools — Planned" but the prerequisite note ("Requires Phase 5 `object_revisions` table") is now stale.
- `services/api/app/models/revision.py` and `services/api/app/services/revision_service.py` are live. Migration 0004 ran. `ai_generated` column exists on objects.
- The Phase 7A plan doc (`PHASE-7A-MCP.md`) explicitly deferred `create_page`, `update_page`, `create_edge`, `archive_object`, `ingest_url`, `ingest_file` to 7B.
- There is no `PHASE-7B-MCP-WRITE.md` file in `project-phases/` yet.

### Potential fixes / approaches

**Approach A — Write a `PHASE-7B-MCP-WRITE.md` plan and update the unblocked status (recommended).**

1. Create `project-phases/PHASE-7B-MCP-WRITE.md` with the same structure as `PHASE-7A-MCP.md`:
   - Context (Phase 7A complete, Phase 5 `object_revisions` live).
   - Goal (write tools: `create_page`, `update_page`, `create_edge`, `archive_object`, `ingest_url`, `ingest_file`).
   - Safety constraints: every write must produce both an `agent_runs` row *and* an `object_revisions` row; soft-delete only; rate-limit per agent identity; reject any path outside `LIBRARY_ROOT`.
   - Tool plan table mapping each tool to its FastAPI endpoint (most already exist; `archive_object` may need a new endpoint).
   - Subtask checklist (config flag `MCP_ALLOW_WRITE_TOOLS`, per-tool implementation, audit-row assertions in tests, docs).
2. Update `PROGRESS.md` Phase 7B section to remove "Requires Phase 5" and link to the new plan doc.
3. Update `docs/MCP_TOOLS.md` to mark the write tools as "Planned — see PHASE-7B-MCP-WRITE.md".

**Approach B — Just unblock the status without writing the plan.**

Edit `PROGRESS.md` Phase 7B blurb. Defer the actual plan until someone picks it up. Slightly faster but the next agent has to do the planning work anyway.

**Recommendation:** Approach A. The act of writing the plan surfaces edge cases (rollback semantics for `archive_object`, idempotency for `ingest_url`, rate-limit storage location) before code is written.

### Verification

- `project-phases/PHASE-7B-MCP-WRITE.md` exists and matches the structure of other phase docs.
- `PROGRESS.md` no longer lists Phase 5 as a Phase 7B prerequisite.

### Commit

`docs(phase7b): plan MCP write tools now that object_revisions ships`

---

## F14 — Audit and update remaining docs touched by Phase 5 / 6B / 7A / 8A

> A cleanup that picks up the smaller doc drifts that escaped the 2026-05-15 audit.

### Goal

`docs/ARCHITECTURE.md`, `docs/DATA_MODEL.md`, `docs/API.md`, `docs/AGENT_GUIDE.md`, `docs/SECURITY.md`, `docs/INGESTION.md`, `docs/MCP_TOOLS.md`, and `docs/REVISION_HISTORY.md` all reflect the shipped state — not an in-flight plan.

### Situation

The 2026-05-15 audit verified that Phases 5, 6A, 6B, 7A, and 8A are implemented in code, but did **not** do a line-by-line pass on each `docs/*.md` file. Likely drift points to check:

- `docs/ARCHITECTURE.md` — does the sequence diagram include the AI router and the MCP stdio server, or only the older Phase 4 picture?
- `docs/DATA_MODEL.md` — does it list `chats`, `object_revisions`, structured-summary fields, `ai_generated` on `objects`?
- `docs/API.md` — does it have the chat structured-summary endpoints and all AI endpoints? (`/ai/summarize`, `/ai/extract-claims`, `/ai/extract-tasks`, `/ai/suggest-links`, `/ai/answer`, `/ai/triage`, `/ai/inbox`)
- `docs/AGENT_GUIDE.md` — does it mention the MCP read tools and the internal-token auth path?
- `docs/SECURITY.md` — does it document the `X-KOS-Internal-Token` header, the redaction policy, and the soft-delete + revision invariant?
- `docs/MCP_TOOLS.md` — F1 will rewrite parts of this; this task picks up anything F1 doesn't cover.
- `docs/REVISION_HISTORY.md` — should reflect that revisions are now created on AI writes and on apply-structured-summary.

### Potential fixes / approaches

**Approach A — Page-by-page audit and PR per doc.**

For each file:
1. Read the current contents.
2. Diff against shipped code (`grep` for endpoint names, table names, env vars).
3. Land one PR per doc (`docs(api): document phase 5 ai endpoints`, etc.).

Smaller commits, easier review.

**Approach B — Single sweeping docs PR.**

One big commit "docs: bring all docs/ in sync with phases 5/6B/7A/8A". Faster to write, harder to review. Acceptable if the diff is mostly additive.

**Recommendation:** Approach A.

### Verification

- For each shipped endpoint, `grep` finds it in `docs/API.md`.
- For each shipped table, `grep` finds it in `docs/DATA_MODEL.md`.
- For each shipped MCP tool, `grep` finds it in `docs/MCP_TOOLS.md`.
- For each new audit invariant, `grep` finds it in `docs/SECURITY.md` or `docs/AGENT_GUIDE.md`.

### Commits

- `docs(architecture): bring diagram in sync with phase 5/7a/8a`
- `docs(api): document all shipped AI and chat-summary endpoints`
- `docs(security): document MCP internal-token auth and redaction`
- `docs(mcp): cover read-tool catalogue and disabled stubs`
- … (one per doc that needs it)

---

## Suggested ordering and grouping

Most tasks here can land in a single "infra + docs cleanup" sprint:

```
PR 1: F8 + F9 + F10        (env.example dedupe, port alignment, ports cheat sheet)
PR 2: F11                   (backup.sh)
PR 3: F12                   (dummy_pkg readme)
PR 4: F13                   (PHASE-7B plan)
PR 5: F14                   (sweep docs/) — can be split into one PR per doc
```

None of these block each other. F13 is the "unblocks future work" task — pick it up before starting any new feature work.
