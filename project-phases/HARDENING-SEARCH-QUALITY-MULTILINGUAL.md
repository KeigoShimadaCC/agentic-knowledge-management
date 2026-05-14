# Hardening Plan: Search Quality + Multilingual Retrieval

**Branch**: `hardening/search-quality-multilingual`

## Goal
Strengthen Phase 3 Search by improving retrieval quality for multilingual content (Japanese focus), hardening security of search snippets, and increasing observability and debug visibility.

## Non-Goals
- Implementing new AI features (Phase 5).
- Major search architecture rewrite.
- Global object type refactor.
- Large UI redesign.
- Implementing Kùzu (Phase 4 deferred).

## Definition of Done
- [x] Subtask 0 — Audit and finalize plan. Add plan to `project-phases/` and update `PROGRESS.md`.
- [ ] Subtask 1 — Multilingual keyword fallback (FTS + ILIKE/pg_trgm).
- [ ] Subtask 2 — Search snippet sanitization (server-side/client-side).
- [ ] Subtask 3 — Search eval fixture expansion (Japanese/Mixed cases).
- [ ] Subtask 4 — Search debug visibility (UI score display).
- [ ] Subtask 5 — Index/reindex observability (Index status endpoint).
- [ ] Subtask 6 — Documentation and final validation. Update `PROGRESS.md` with hardening status.

## Subtask Details

### Subtask 1 — Multilingual keyword fallback
**Goal**: Support Japanese and mixed-language queries where Postgres English FTS fails.
**Implementation**:
- Modify `search_service.py` to include an `ILIKE` fallback for titles and content.
- Add `pg_trgm` extension via Alembic migration for better substring performance.
- Update scoring to combine FTS scores with substring match boosts.
- Ensure "asset" objects (naked assets) are included in keyword search.

### Subtask 2 — Search snippet sanitization
**Goal**: Prevent XSS by sanitizing search snippets containing HTML.
**Implementation**:
- Audit `dangerouslySetInnerHTML` in `SearchResultCard.tsx`.
- Implement sanitization in the backend (e.g., using `bleach` or similar if appropriate, or a custom safe-list for `<mark>`).
- Alternatively, return plain text + highlight ranges and render safely in React.
- Add security tests with malicious payload queries.

### Subtask 3 — Search eval fixture expansion
**Goal**: Add realistic test cases for Japanese and mixed-language retrieval.
**Implementation**:
- Expand `tests/fixtures/search_eval_cases.json` with Japanese and mixed English/Japanese queries.
- Ensure `test_search.py` covers these new cases.

### Subtask 4 — Search debug visibility
**Goal**: Make search ranking explainable in development.
**Implementation**:
- Add a "Debug Mode" toggle or developer-only display in `SearchModal.tsx`.
- Display `keyword_score`, `vector_score`, and `recency_boost` for each result when enabled.

### Subtask 5 — Index/reindex observability
**Goal**: Visibility into whether objects are indexed.
**Implementation**:
- Add `GET /api/v1/objects/{id}/index-status` endpoint.
- Return `embedding_status`, `chunk_count`, `last_indexed_at`.
- Document `reindex-all` and `reindex-object` usage.

### Subtask 6 — Documentation and final validation
**Goal**: Update documentation to reflect search hardening.
**Implementation**:
- Update `docs/API.md`, `docs/ARCHITECTURE.md`, `docs/SECURITY.md`.
- Ensure all tests pass.

## Risks and Mitigations
- **Performance**: `ILIKE` on large text. Mitigation: Use `pg_trgm` GIN indexes and limit fallback to top results.
- **Ranking Drift**: Fallback might push irrelevant results to top. Mitigation: Careful weight tuning and fixture testing.
- **Snippet Complexity**: Sanitizing HTML correctly. Mitigation: Use standard libraries or avoid HTML return values entirely.

## Validation Commands
- Backend: `PYTHONPATH=services/api uv run pytest tests/api -q`
- Frontend: `pnpm -F web typecheck && pnpm -F web build`
- Migration: `cd services/api && uv run alembic upgrade head`
