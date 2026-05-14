# PHASE-FIX-03 — Repo Oddities

> **Type:** Remediation plan (post-Phase-7A audit)
> **Audit date:** 2026-05-15
> **Scope:** Visible weirdness in the repo — broken nav links, inconsistent routing, stale checked-in files, leftover plan items. None of these block functionality on a happy path, but each one is something a new contributor or agent has to ask "what is this?" about.
> **Out of scope:** Anything in `PHASE-FIX-01` (claimed-done gaps) or `PHASE-FIX-02` (forgotten/undocumented).

This file is meant to be picked up by a coding agent. Each task includes **Goal**, **Situation**, and **Potential fixes / approaches**.

Tasks F15 and F16 are the most user-facing (broken nav). F17 (route grouping) is the largest cleanup. F18–F22 are small polish.

---

## F15 — Fix the broken `/app/trash` Sidebar link

> Maps to audit item **C1** and part of **E3** ("Fix Sidebar.tsx … drop the /app/trash link until a Trash view exists").

### Goal

Clicking "Trash" in the sidebar takes the user somewhere useful, *or* the entry is removed. Either way, there is no 404 path from the primary navigation.

### Situation

- `apps/web/src/components/layout/Sidebar.tsx` declares:
  ```ts
  { href: "/app/trash", label: "Trash", icon: Trash2 },
  ```
- No file exists at `apps/web/src/app/(app)/app/trash/page.tsx` (and no alternative trash route under any other path).
- The backend API for trash exists: `GET /api/v1/objects/trash` is implemented in `services/api/app/api/v1/objects.py` and tested. So the data is reachable; just no UI.

### Potential fixes / approaches

**Approach A — Remove the link until a Trash view ships (cheapest, recommended short-term).**

1. Delete the `Trash` entry from `navItems` in `Sidebar.tsx`.
2. Remove the unused `Trash2` import.
3. Add a one-line TODO referencing a future task or a tracking issue.

**Approach B — Build a minimal `/app/trash` view (recommended if there's time).**

1. Create `apps/web/src/app/(app)/app/trash/page.tsx` (note: respect whatever path convention F17 lands on).
2. The page fetches `GET /api/v1/objects/trash` via a new `useTrash()` hook (or extend `useObjects` with a `trashed=true` flag).
3. Render a list with title, kind, deleted_at, and an action button: **Restore** → `POST /api/v1/objects/{id}/restore`, mutate the SWR cache.
4. No hard-delete UI. The backend doesn't offer one and `CLAUDE.md` forbids it.
5. Add an integration test in `tests/api/` only if backend changes; otherwise the existing trash endpoint coverage is enough.

**Recommendation:** Approach B. The backend already supports it; the missing UI is roughly an hour of work and it fulfils the "soft-everything" promise visibly.

### Verification

- Approach A: Sidebar has no "Trash" entry; no broken link.
- Approach B: clicking "Trash" loads a list; clicking Restore on an item un-deletes it and the item disappears from the trash list.

### Commit

- Approach A: `fix(web): remove sidebar link to non-existent /app/trash`
- Approach B: `feat(web): trash view with restore action`

---

## F16 — Resolve the `/app/assets` vs `/assets` route mismatch

> Maps to audit item **C2** and part of **E3** ("Fix Sidebar.tsx — either build (app)/app/assets/page.tsx, or change the href values to /assets").

### Goal

The "Assets" sidebar link points at the actual route file, and the route file lives in the path the rest of the app uses. No 404, no surprise.

### Situation

- `apps/web/src/components/layout/Sidebar.tsx` links to `/app/assets`.
- The actual route file is at `apps/web/src/app/(app)/assets/page.tsx`, which Next.js App Router serves at `/assets` (the `(app)` route group is not part of the URL).
- Result: clicking "Assets" in the sidebar 404s. Typing `/assets` in the URL bar works.
- The route group choice for assets disagrees with pages, chats, and trash, all of which live under `/app/...`. Resolved here at the sidebar level; the deeper structural fix is F17.

### Potential fixes / approaches

**Approach A — Change the sidebar href to `/assets` (matches current file).**

One-line change. Resolves the 404 today. Leaves the deeper route inconsistency for F17.

**Approach B — Move the route file to `(app)/app/assets/page.tsx` (matches sidebar).**

1. Move `apps/web/src/app/(app)/assets/page.tsx` → `apps/web/src/app/(app)/app/assets/page.tsx`.
2. Update any in-code references (e.g. `objectRoute` returns `/app/assets` already, which would now be correct).
3. Verify no other code links to `/assets` directly (asset detail uses `/assets/[id]` if it exists — check `lib/objectRouting.ts`).

**Recommendation:** Approach B. It aligns assets with pages/chats/trash under `/app/...`. Should be done together with F17 (or F17 should explicitly include it).

### Verification

- Click "Assets" → renders the asset grid.
- The asset upload flow still completes (drag a file → grid refreshes).
- `pnpm -F web build` passes.

### Commit

- Approach A: `fix(web): point sidebar Assets link at the actual /assets route`
- Approach B: `refactor(web): move assets route under /app to match pages and chats`

---

## F17 — Unify the route grouping under `(app)/`

> Maps to audit item **C3**.

### Goal

Routes for "objects the user owns" live under a single, predictable prefix. New contributors don't have to read the file tree to guess where a page lives.

### Situation

Current state under `apps/web/src/app/(app)/`:

| URL | File |
|---|---|
| `/app` | `(app)/app/page.tsx` (All Objects) |
| `/app/pages` | `(app)/app/pages/page.tsx` (Pages list) |
| `/pages/[id]` | `(app)/pages/[id]/page.tsx` (Page detail) |
| `/app/chats` | `(app)/app/chats/page.tsx` (Chats list) |
| `/app/chats/[id]` | `(app)/app/chats/[id]/page.tsx` (Chat detail) |
| `/sources` | `(app)/sources/page.tsx` (Sources list) |
| `/sources/[id]` | `(app)/sources/[id]/page.tsx` (Source detail) |
| `/assets` | `(app)/assets/page.tsx` (Assets list) |
| `/inbox` | `(app)/inbox/page.tsx` (Inbox) |

So we have three different conventions in one tree:

- `pages`: list under `/app/pages`, detail under `/pages/{id}` — split across two prefixes.
- `chats`: everything under `/app/chats/...` — consistent.
- `sources`: everything under `/sources/...` — consistent but different prefix from chats.
- `assets` and `inbox`: top-level singletons.
- `/app` itself is the "All Objects" dashboard.

The sidebar amplifies this with `/app/pages`, `/app/assets` (broken — see F16), `/sources`, `/app/chats`, `/inbox`, `/app/trash` (broken — see F15).

### Potential fixes / approaches

**Approach A — Everything under `/app/...` (preferred).**

Move:
- `(app)/sources/page.tsx` → `(app)/app/sources/page.tsx`
- `(app)/sources/[id]/page.tsx` → `(app)/app/sources/[id]/page.tsx`
- `(app)/assets/page.tsx` → `(app)/app/assets/page.tsx`
- `(app)/inbox/page.tsx` → `(app)/app/inbox/page.tsx`
- `(app)/pages/[id]/page.tsx` → `(app)/app/pages/[id]/page.tsx`

Then update:
- `apps/web/src/lib/objectRouting.ts` — change `objectRoute` mappings:
  ```ts
  if (kind === "page") return `/app/pages/${id}`;
  if (kind === "source") return `/app/sources/${id}`;
  if (kind === "chat") return `/app/chats/${id}`;
  if (kind === "asset") return "/app/assets";
  ```
- `apps/web/src/components/layout/Sidebar.tsx` — all hrefs use `/app/...`.
- Any hard-coded `/pages/`, `/sources/`, `/inbox` strings in components or tests.

Pro: one consistent root, mirrors the existing sidebar grouping, easy mental model.
Con: largest diff. Any external bookmarks break (but this is a local-first single-user app — bookmarks won't exist in practice).

**Approach B — Everything at the top level (drop `/app/` prefix entirely).**

Move:
- `(app)/app/page.tsx` → `(app)/page.tsx` (or rename to a `/dashboard` route)
- `(app)/app/pages/page.tsx` → `(app)/pages/page.tsx`
- `(app)/app/chats/...` → `(app)/chats/...`

Pro: shorter URLs.
Con: `/page.tsx` at the route group root can collide with the Next 14 marketing root; you'd need to keep `/` for unauthenticated landing.

**Approach C — Status quo + heavy documentation.**

Add a `README.md` in `apps/web/src/app/(app)/` explaining the inconsistency. Lowest-risk but doesn't fix the underlying confusion.

**Recommendation:** Approach A. Bundle with F15 and F16 in a single PR so the routing reorg is one atomic change.

### Verification

- Click every nav item → the correct list renders.
- Click an object from search / backlinks / related → opens the correct detail page.
- "Open in side pane" still works for every kind (Workspace Lite from Phase 8A).
- `pnpm -F web typecheck && pnpm -F web build` pass.
- All API client calls in `apps/web/src/lib/api.ts` are unchanged (the API surface doesn't move).

### Commit

`refactor(web): unify route grouping under /app for pages, sources, assets, chats, inbox`

---

## F18 — `.gitignore` the `test_output*.txt` dumps and remove them from the tree

> Maps to audit item **C4** and **E6** (".gitignore the test_output*.txt dumps and remove them from the tree").

### Goal

The repo root is not littered with pytest log dumps. Future runs do not accidentally commit fresh dumps.

### Situation

- `test_output.txt` (~21 KB) and `test_output_2.txt` (~260 KB) are checked in at the repo root.
- They appear to be raw pytest stdout from prior debugging sessions.
- `.gitignore` does not exclude them.

### Potential fixes / approaches

**Approach A — Delete + gitignore (recommended).**

1. `git rm test_output.txt test_output_2.txt`.
2. Add to `.gitignore`:
   ```
   # Pytest stdout captures from interactive runs
   test_output*.txt
   /test_output.txt
   /test_output_2.txt
   ```
3. Commit and push.

**Approach B — Move to `docs/` as historical artifacts.**

If they document an important failure mode, move under `docs/dev-notes/` and reference from a README. Unlikely to be worth it — most pytest dumps go stale fast.

**Recommendation:** Approach A.

### Verification

- `ls test_output*.txt` → "No such file or directory".
- `cat .gitignore | grep test_output` shows the new patterns.
- A subsequent `pytest > test_output.txt` in the repo root is not staged by `git add .`.

### Commit

`chore: gitignore and remove stray pytest output dumps`

---

## F19 — Add a smoke test under `tests/e2e/` or drop the directory

> Maps to audit item **C6**.

### Goal

`tests/e2e/` either contains at least one running smoke test or doesn't exist at all. Empty placeholder directories with a single `.gitkeep` mislead new contributors into thinking E2E exists.

### Situation

- `tests/e2e/` contains only `.gitkeep`.
- `PHASE-1-FOUNDATION.md` mentioned `tests/e2e/` as part of the initial scaffold.
- No phase plan has actually filled it in. There is no Playwright/Cypress config.

### Potential fixes / approaches

**Approach A — Add one Playwright smoke test (recommended).**

1. `pnpm -F web add -D @playwright/test`.
2. Create `tests/e2e/playwright.config.ts` pointing at `http://localhost:3000`.
3. Add `tests/e2e/smoke.spec.ts`:
   - Visit `/login`, register a test user (or seed a demo user), navigate to `/app`, click "New Page", type into the editor, assert the title saves.
4. Document running it in README under a new "End-to-end smoke test" subsection.
5. Optional: gate it behind `pnpm test:e2e` so CI runs are explicit.

**Approach B — Delete the directory and the README mention.**

Remove `tests/e2e/.gitkeep`. Edit `PHASE-1-FOUNDATION.md` and README references. Bare minimum if E2E is not on the near-term roadmap.

**Recommendation:** Approach A. Phase 8 and Phase 5 are both UI-heavy now; a single smoke test pays off the next time the editor regresses silently.

### Verification

- Approach A: `pnpm -F web test:e2e` runs the smoke test against a locally running stack and passes.
- Approach B: `tests/e2e/` is gone; no doc references it.

### Commit

- Approach A: `test(e2e): add playwright smoke test for register → page edit → save`
- Approach B: `chore: remove empty tests/e2e placeholder`

---

## F20 — Decide and document `SESSION_SECRET` requirement

> Maps to audit item **C8**.

### Goal

A single source of truth says whether `SESSION_SECRET` is required, what it's for, and what happens if it's empty. README, `.env.example`, and code all agree.

### Situation

- `README.md` "Environment Variables" table says `SESSION_SECRET` is **Yes — min 32 chars**.
- `infra/.env.example` says: `# Optional: reserved for future CSRF / signed URLs (session cookies use DB-backed opaque tokens).`
- Code path (`services/api/app/core/security.py`, `services/api/app/core/deps.py`): session cookies are DB-backed opaque tokens (`secrets.token_urlsafe(32)` stored as `sha256(token)` in `sessions.token_hash`). `SESSION_SECRET` is not actively used for cookie integrity.

So README says "required", but code doesn't use it. Either the README is wrong or the code is missing a planned use of the secret (e.g. for signed cookies, CSRF tokens, or password-reset links — none of which exist yet).

### Potential fixes / approaches

**Approach A — Match docs to code: mark `SESSION_SECRET` optional (recommended for now).**

1. Update README table to mark `SESSION_SECRET` as **No (reserved for future signed URLs)**.
2. Keep `infra/.env.example` as-is (already says "Optional").
3. Add a one-paragraph note in `docs/SECURITY.md` explaining the actual session model (opaque, DB-backed, sha256-hashed, 30-day TTL).

**Approach B — Actually use `SESSION_SECRET` for something.**

If we want signed CSRF tokens or itsdangerous-signed cookies, plan that as a Phase 7B / 8 dependency. Don't do it inside this cleanup plan.

**Recommendation:** Approach A.

### Verification

- README mentions `SESSION_SECRET` as optional + reserved.
- `docs/SECURITY.md` has a "Session model" section.
- `grep -r 'SESSION_SECRET' services/api/app` shows no active use (or the active use is documented).

### Commit

`docs(security): clarify SESSION_SECRET is reserved (sessions are db-backed opaque tokens)`

---

## F21 — Annotate or relocate the demo-seed legacy-email migration logic

> Maps to audit item **C7**.

### Goal

Future contributors reading `services/api/app/services/demo_seed_service.py` can immediately tell why a legacy email address is referenced and whether the migration shim can be removed.

### Situation

- `demo_seed_service.py` carries:
  ```python
  # Earlier seeds used demo@knowledgeos.local; pydantic EmailStr rejects ".local".
  # Renamed on startup via migrate_legacy_demo_email.
  LEGACY_DEMO_EMAIL = "demo@knowledgeos.local"
  ```
- The reason is reasonable (older local dev DBs used a `.local` TLD that no longer passes validation).
- No doc anywhere explains when this shim can be deleted. It will quietly stay forever.

### Potential fixes / approaches

**Approach A — Inline expiry note (recommended).**

Extend the comment to include a removal criterion:
```python
# LEGACY: Earlier dev seeds used demo@knowledgeos.local. pydantic EmailStr
# rejects ".local", so on startup we rename any existing row to settings.DEMO_SEED_EMAIL.
# Safe to remove when all known local databases have been re-seeded (target: after
# v0.3 release, see docs/REVISION_HISTORY.md). Last touched 2026-05-15.
```

**Approach B — Move the migration into Alembic.**

Add a small Alembic data migration that does the same rename, then delete the runtime shim. This is more correct but only worth doing if we want to drop the runtime branch entirely.

**Recommendation:** Approach A first. Convert to B when the next major version bump lands.

### Verification

- `git blame` on the comment lines a future contributor will see explains the lifecycle.

### Commit

`chore(demo-seed): annotate legacy-email shim with removal criterion`

---

## F22 — Prune the superseded Phase 6A "Structured Import" subtask list

> Maps to audit item **C9**.

### Goal

`PROGRESS.md` Phase 6A section is not ambiguous about which subtasks are live and which were absorbed into Phase 6B.

### Situation

- During the 2026-05-15 audit, `PROGRESS.md` Phase 6A section had three unchecked subtasks at the bottom labelled "Structured Import (requires Phase 5 AI)". These are exactly the things Phase 6B did and shipped.
- A "Historical note" sentence was added above them in the audit. The unchecked checkboxes are still there.
- Net effect: a reader scanning the summary table at the bottom sees Phase 6A as "Complete" but the Phase 6A section itself has open checkboxes. Confusing.

### Potential fixes / approaches

**Approach A — Replace the unchecked list with a single resolved bullet (recommended).**

Replace:
```markdown
**Structured Import (requires Phase 5 AI):**
- [ ] **Subtask 1** — LLM summarizer...
- [ ] **Subtask 2** — Object extraction...
- [ ] **Subtask 3** — Tests + docs...
```

With:
```markdown
**Structured Import (superseded by Phase 6B):**
- ✅ Implemented in [Phase 6B — Structured Chat Import](#phase-6b--structured-chat-import--complete).
  See subtasks 1–8 under Phase 6B; that section is the canonical record.
```

**Approach B — Delete the subsection entirely.**

Risk: someone reading `PHASE-6A-CHAT-IMPORT-LITE.md` may still see references to "structured import — see PROGRESS". Keep a pointer.

**Recommendation:** Approach A.

### Verification

- `PROGRESS.md` Phase 6A section has no `[ ]` checkboxes.
- Summary table at the bottom still shows 6A complete.

### Commit

`docs(progress): collapse Phase 6A structured-import remainder into 6B pointer`

---

## Suggested ordering and grouping

Most of these are short. Group them into roughly three PRs:

```
PR 1 — UI routing cleanup:
  F15 (broken /app/trash) + F16 (broken /app/assets) + F17 (route unification).
  Bundle so the routing reorg is one atomic change.

PR 2 — Repo hygiene:
  F18 (.gitignore test_output) + F19 (e2e smoke or remove) + F21 (legacy email annotate) + F22 (Phase 6A pruning).
  These have no code interactions.

PR 3 — Docs alignment:
  F20 (SESSION_SECRET clarification).
  Can fold into F14 (PHASE-FIX-02 doc sweep) if executed together.
```

After all three PRs land, the only "weirdness" left in the repo should be intentional — and PROGRESS.md can drop the "Frontend routing oddities" and "Infrastructure oddities" subsections from its current-state notes.
