# Phase 10B — Documentation Audit and Sync

> **Status:** ✅ Complete (merged to `main` — 6 commits, 2026-05-16)
> **Owner:** Claude (orchestration + execution)
> **Audience:** AI coder — context on what changed and why.
> **Estimated effort:** 1 session, 6 commits, ~400 LOC net additions.
> **Blocks:** nothing — prerequisite for any future AI coder session starting clean.
> **Blocked by:** Phase 9D (all schema and code changes must be final before auditing docs).
> **Branch:** `main` (applied directly — doc-only, no code changes).

---

## 0. North Star

All 14 files in `docs/` were written incrementally during Phases 1–9D and had drifted from the actual system state. `schema.sql` was 8 migrations behind; `DATA_MODEL.md` had wrong field names; `AI-CODER-BRIEFING.md` showed Phase 7B and 9A–9D as "in flight" or "planned" despite being complete. A future AI coder reading these docs cold would get incorrect schema, wrong field names, and outdated phase status — leading to subtle bugs and wasted planning time.

This phase does a zero-skim audit of every file against the actual Alembic migrations, source code, and PROGRESS.md, then applies targeted corrections.

---

## 1. Non-breakage contract

- No code changes — all edits are to `docs/` files only.
- No schema changes — `docs/schema.sql` is a reference document, not applied DDL.
- No API changes — doc corrections must not redefine API behavior; they describe existing behavior.
- All existing tests continue to pass (no code touched).

---

## 2. Files audited

| File | Severity | Changes |
|---|---|---|
| `docs/schema.sql` | Critical | Complete rewrite — was at migration 0001 state; added all tables from 0002–0009 |
| `docs/DATA_MODEL.md` | Significant | Fixed 4 table field discrepancies; added Phase 9 table docs |
| `docs/AI-CODER-BRIEFING.md` | Major | Phase truth table, worktrees, migration gotcha, test counts |
| `docs/ARCHITECTURE.md` | Moderate | Worker service, Postgres table list, shipped-features table |
| `docs/AGENT_GUIDE.md` | Moderate | Missing MCP tool, stale workspace section |
| `docs/INGESTION.md` | Minor | 3 missing source types |
| `docs/MCP_TOOLS.md` | Minor | Write tool count (6 → 14) |
| `docs/SECURITY.md` | Minor | AI provider clarification, Phase 9 note |
| `docs/SEARCH_EVAL.md` | Trivial | Future tense → present |
| `docs/REVISION_HISTORY.md` | Trivial | Phase 8C note corrected |
| `docs/A11Y.md` | None | Already current |
| `docs/SHORTCUTS.md` | None | Already current |
| `docs/UX_GUIDE.md` | None | Already current |
| `docs/API.md` | None | Already current |

---

## 3. Schema gaps closed (most critical)

`docs/schema.sql` was Phase 1 state only. The following were missing:

| Migration | What it adds |
|---|---|
| 0002 | `source_type_enum` (8 types: pdf/image/video/audio/youtube/web/csv/file), `sources` table |
| 0003 | `chunks` Phase 3 fields: user_id, source_locator, content_hash, embedding_status, embedding_model, embedded_at, qdrant_point_id, updated_at |
| 0004 | `object_revisions` table; `objects.ai_generated` column |
| 0005 | `chats` table |
| 0006 | `chats` structured_summary_* columns |
| 0007 | `projects` table |
| 0008 | `workspaces` table |
| 0009 | `resume_bullet_sets` + `interview_story_records` tables |

Existing tables also had errors:
- `objects.kind`: had a DB `CHECK` constraint in schema.sql — actual code uses `String(32)` with application-layer validation, no DB constraint.
- `sessions`: schema.sql had correct `last_seen`; DATA_MODEL.md incorrectly showed `revoked_at`.
- `pages`: DATA_MODEL.md showed field as `content`; actual column is `content_json`. Missing `word_count` and `version`.
- `ingestion_jobs`: DATA_MODEL.md showed `metadata` field (wrong); actual columns are `payload`, `result`, `attempts`, `max_attempts`, `enqueued_at`, `started_at`, `finished_at`. Status values are `done`/`failed` not `ready`/`error`.
- `agent_runs`: DATA_MODEL.md showed `agent_name`, `action`, `updated_at` (all wrong); actual columns are `agent_type`, `model`, `input_tokens`, `output_tokens`, `cost_usd`, `started_at`, `finished_at`.

---

## 4. AI provider clarification

All docs now accurately reflect that **OpenAI is the only external AI provider in use** (`OPENAI_API_KEY` for both embeddings and LLM calls via `openai.AsyncOpenAI`). Anthropic remains a planned future option behind the `EmbeddingProvider`/`call_ai()` abstraction. Several docs previously implied Anthropic was wired, which was incorrect.

Confirmed from: `services/api/app/ai/client.py` — uses `openai.AsyncOpenAI` exclusively.

---

## 5. Commit sequence

| # | Commit | Files |
|---|---|---|
| 1 | `docs: update schema.sql to include all migrations 0001–0009` | `docs/schema.sql` |
| 2 | `docs: fix DATA_MODEL.md field discrepancies and add Phase 9 tables` | `docs/DATA_MODEL.md` |
| 3 | `docs: update ARCHITECTURE.md — add worker service, Phase 9, feature list` | `docs/ARCHITECTURE.md` |
| 4 | `docs: fix gaps in MCP_TOOLS, INGESTION, SECURITY, AGENT_GUIDE` | 4 files |
| 5 | `docs: update AI-CODER-BRIEFING.md phase truth table and gotchas to current state` | `docs/AI-CODER-BRIEFING.md` |
| 6 | `docs: trivial updates to SEARCH_EVAL and REVISION_HISTORY` | 2 files |

---

## 6. Definition of Done

- [x] All 14 `docs/` files audited
- [x] `docs/schema.sql` matches actual deployed schema (migrations 0001–0009)
- [x] `docs/DATA_MODEL.md` field names match actual ORM models and migrations
- [x] `docs/AI-CODER-BRIEFING.md` phase truth table matches `PROGRESS.md`
- [x] No stale branch references (`phase8a-workspace-lite`, `phase-7b-mcp-write`) in any doc
- [x] `answer_from_kb` present in `AGENT_GUIDE.md` MCP tools table
- [x] Write tool count in `MCP_TOOLS.md` safety model updated to 14
- [x] All 8 source types documented in `INGESTION.md`
- [x] 6 commits applied to `main`
