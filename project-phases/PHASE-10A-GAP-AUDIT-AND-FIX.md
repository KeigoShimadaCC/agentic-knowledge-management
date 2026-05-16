# Phase 10A — Full Gap Audit & Fix

> **Status:** ✅ Complete  
> **Type:** Remediation / cleanup  
> **Audit date:** 2026-05-16  
> **Scope:** Cross-project audit of all 24 phase plan documents against the live codebase and `PROGRESS.md`. Fixes every identified gap — documentation inconsistencies, code quality drift, and the one explicitly deferred optimization.

---

## 0. Why this phase exists

After phases 1–9D plus FIX-01/02/03 and ENHANCE-01/02/03 all shipped, `PROGRESS.md` had accumulated stale sections, phantom unchecked items, and an outdated total count. Four backend files also had format-only ruff drift that was intentionally hard-fenced during Phase 9C. This phase cleans the slate so the repository is fully consistent and CI-clean.

**The codebase is feature-complete.** No missing features were found. All gaps are documentation inconsistencies, code quality drift, or a single deferred optimization (pg_trgm).

---

## 1. Gaps identified and fixed

### Category A — PROGRESS.md documentation (8 items)

| ID | Gap | Fix |
|---|---|---|
| A1 | Stale ENHANCE-03 "🚧 In Progress" section (lines 226–239) with UX-T2 through UX-T6 unchecked — predates the work; never removed | Deleted the stale block |
| A2 | Stale "Phase 8 — Multi-Pane Workspaces ⬜ Planned" section with 8 phantom unchecked subtasks — superseded by 8A/8B/8C (all ✅) | Deleted the stale section |
| A3 | Phase 9A had `[ ] Follow-up (9B+)` unchecked even though 9B/9C/9D are all ✅ | Checked off; added note |
| A4 | Hardening track header said `🚧 Partial` but all 7 subtasks are ✅ | Changed header to `✅ Complete` |
| A5 | Hardening summary count showed "6 / 7 subtasks (pg_trgm deferred)" — all 7 checkboxes are ✅ | Updated count; pg_trgm now addressed in migration 0010 |
| A6 | Total count "109 / 123 subtasks complete" was last updated before many later phases were added; inflated by the phantom Phase 8 section | Replaced with "All phases complete" + real test totals |
| A7 | Phase 7A description still called `answer_from_kb` a "disabled stub" — it was wired to `/api/v1/ai/answer` in Fix-01 | Updated description |
| A8 | Phase 8B and ENHANCE-02 were missing from the summary table | Added rows |

### Category B — Code quality (1 item)

| ID | Gap | Fix |
|---|---|---|
| B1 | `ruff format --check` failed on 4 files: `search.py`, `rate_limit.py`, `audited_write_service.py`, `page_service.py` — deliberately deferred during Phase 9C | Ran `ruff format` on all 4; CI is now clean on both lint and format |

### Category C — Deferred optimization (1 item)

| ID | Gap | Fix |
|---|---|---|
| C1 | Hardening Subtask 1: multilingual ILIKE fallback used sequential scan (no pg_trgm index). Performance degrades O(n) at scale. | Added Alembic migration `0010` (see §2) |

---

## 2. Migration 0010 — pg_trgm GIN indexes

**File:** `services/api/alembic/versions/0010_add_pg_trgm_index.py`

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_objects_title_trgm
  ON objects USING gin (title gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_objects_description_trgm
  ON objects USING gin (description gin_trgm_ops)
  WHERE description IS NOT NULL;
```

**Why only title and description, not content_text / extracted_text:**  
`pages.content_text` and `sources.extracted_text` can be many kilobytes per row. GIN trigram indexes on those columns would be larger than the data and slow to maintain. FTS (`ts_vector`) already covers those columns for the languages it can tokenize. The ILIKE fallback on large text is acceptable for the local-first single-user context.

**No code change in `search_service.py`:** Postgres uses the GIN index automatically when the query planner sees an ILIKE on an indexed column.

---

## 3. Docs updated

| File | Change |
|---|---|
| `PROGRESS.md` | Fixes A1–A8 (see above) |
| `docs/INGESTION.md` | Added "Multilingual keyword search — pg_trgm GIN index" section explaining the index, its scope, and why large text columns are excluded |

---

## 4. Subtask checklist

- [x] **10A-1** — Full audit: read all 24 phase plan documents, cross-reference against codebase and `PROGRESS.md`
- [x] **10A-2** — Code quality: `ruff format` on 4 drifted files; `ruff check . && ruff format --check .` → clean
- [x] **10A-3** — PROGRESS.md: fix A1–A8 (stale sections, unchecked items, count, table gaps)
- [x] **10A-4** — Migration 0010: pg_trgm extension + GIN indexes on `objects.title` and `objects.description`
- [x] **10A-5** — Docs: `docs/INGESTION.md` pg_trgm section added
- [x] **10A-6** — Verification: `pytest api/ unit/ -q` → 217 passed; `alembic heads` → 0010; ruff → clean

---

## 5. Verification

| Gate | Result |
|---|---|
| `ruff check . && ruff format --check .` | ✅ 105 files clean |
| `python3 -c "ast.parse(...)"` on migration 0010 | ✅ syntax OK |
| `uv run alembic heads` | ✅ 0010 (head) |
| `pytest api/ unit/ -q` | ✅ 217 passed, 1 warning (Qdrant version — pre-existing) |
| `PROGRESS.md` unchecked `[ ]` items | ✅ zero |

---

## 6. What was NOT changed

- No API, model, service, schema, or route changes
- No frontend changes
- No MCP tool changes
- No worker changes
- No test additions (all existing tests pass unchanged; the ruff fix is format-only)
- Kùzu graph DB remains deferred (Postgres traversal is sufficient at current scale)
