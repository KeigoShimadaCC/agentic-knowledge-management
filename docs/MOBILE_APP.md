# Mobile App — Product Spec

> Canonical product spec for the KnowledgeOS iPhone client. Companion docs: [`MOBILE_API_CONTRACT.md`](./MOBILE_API_CONTRACT.md), [`MOBILE_NETWORKING.md`](./MOBILE_NETWORKING.md). Concept source: [`project-phases/IDEA-iPHONE-APP.md`](../project-phases/IDEA-iPHONE-APP.md).

---

## 1. One-line goal

A thin native SwiftUI iPhone client that reads, searches, captures, and asks grounded questions against a Mac-hosted KnowledgeOS backend over `/api/v1`. The phone is a remote control and capture surface — never a second backend.

---

## 2. MVP user stories

The first useful build lets the user:

1. **Connect** to a Mac-hosted KnowledgeOS backend (Simulator, LAN, or Tailscale; see [`MOBILE_NETWORKING.md`](./MOBILE_NETWORKING.md)).
2. **Log in** via mobile-safe bearer auth (`POST /api/v1/auth/mobile-login` — Phase 01A).
3. **Browse recent objects** on Home.
4. **Search** the knowledge base via hybrid search (`POST /api/v1/search/hybrid`).
5. **Read** pages, sources, chats, and projects through a kind-dispatching detail view.
6. **Ask grounded KB questions** via `POST /api/v1/ai/answer`, with citations and AI-disabled fallback.
7. **Capture a quick text note** as a page (`POST /api/v1/pages`).
8. **Upload a file or photo** as an asset/source (`POST /api/v1/assets/upload`, optionally `?create_source=true`).
9. Run in **iOS Simulator** and later on a **physical iPhone** without App Store release.

---

## 3. Non-goals for MVP

The mobile app must **not** attempt any of these in the MVP track:

- A second backend, cloud sync, or multi-user mobile server administration.
- Direct database, Redis, Qdrant, Kùzu, or filesystem access. The REST API is the only surface.
- Full Tiptap rich-text editor parity. Edit-lite (title/tags/plain body) is Phase 04.
- Offline-first sync. Light caching + outgoing-note queue is deferred to Phase 05.
- App Store release. Private install + TestFlight only (Phase 06).
- Android, iPad-specific layouts, or watchOS companions.
- Generic multi-server SaaS client behavior.
- Re-using `MCP_INTERNAL_TOKEN` as a phone auth credential. It is internal-only and stays so.
- Arbitrary shell or MCP execution from the phone.

---

## 4. Screen map

| Screen | Purpose | Primary API calls |
|---|---|---|
| **Connect** | Configure base URL; verify reachability | `GET /api/v1/health` |
| **Login** | Email + password → bearer token | `POST /api/v1/auth/mobile-login` (Phase 01A) |
| **Home** | Recent objects list + capture entry point | `GET /api/v1/objects` |
| **Search** | Hybrid keyword + semantic search | `POST /api/v1/search/hybrid` |
| **ObjectDetail** | Kind dispatcher → routes to a kind-specific view | `GET /api/v1/objects/{id}` |
| **PageDetail** | Read a page; future edit-lite hook | `GET /api/v1/pages/{id}` |
| **SourceDetail** | Source metadata, extracted text, thumbnail | `GET /api/v1/sources/{id}`, `/text`, `/thumbnail` |
| **ChatDetail** | Read imported AI chat thread | `GET /api/v1/chats/{id}` |
| **ProjectDetail** | Read project metadata + linked objects | `GET /api/v1/projects/{project_id}` |
| **Capture** | Quick text note + photo/file upload | `POST /api/v1/pages`, `POST /api/v1/assets/upload` |
| **AI** | Grounded KB Q&A with citations | `POST /api/v1/ai/answer`, optional `POST /api/v1/ai/summarize`, `POST /api/v1/ai/suggest-links` |
| **Settings** | Server base URL, session, AI status, log out | `GET /api/v1/mobile/bootstrap`, `POST /api/v1/auth/mobile-logout` |

State management: SwiftUI + lightweight MVVM (`View → ViewModel → APIClient → URLSession`). No heavy frameworks. See [`IDEA-iPHONE-APP.md` §6](../project-phases/IDEA-iPHONE-APP.md) for the iOS architecture and DTO layout.

---

## 5. Backend endpoints intentionally NOT exposed on mobile MVP

The backend has many endpoints that are valid but **out of scope for mobile MVP**. Listed explicitly so future coders don't accidentally implement screens for them. All paths verified against `services/api/app/api/v1/`.

### 5.1 Chat ingestion

- `POST /api/v1/chats/import` — chat import is a **desktop paste-and-upload** workflow. The mobile app reads chats, never imports them.

### 5.2 Bulk triage

- `POST /api/v1/ai/triage` — bulk inbox triage isn't a mobile use case.
- `GET /api/v1/ai/inbox` — the inbox is a desktop review surface; mobile may revisit in a later phase but not MVP.

### 5.3 Destructive object ops

- `DELETE /api/v1/objects/{id}`
- `POST /api/v1/objects/{id}/restore`
- `POST /api/v1/objects/{id}/archive`

Deferred until edit-lite (Phase 04) stabilizes. Mobile MVP is read + capture only.

### 5.4 Lower-level search

- `POST /api/v1/search/vector` — embeddings-only path.
- `GET /api/v1/search/keyword` — keyword-only path.

Mobile uses `POST /api/v1/search/hybrid` exclusively. Hybrid degrades to keyword-only when embeddings are off, so a single client path handles both states.

### 5.5 Career generators

- `POST /api/v1/ai/extract-project`
- `POST /api/v1/ai/generate-resume-bullets`
- `POST /api/v1/ai/generate-interview-story`
- `POST /api/v1/projects/{id}/resume-bullet-sets`, `GET /api/v1/projects/{id}/resume-bullet-sets`
- `GET /api/v1/resume-bullet-sets/{id}`, `DELETE /api/v1/resume-bullet-sets/{id}`
- `POST /api/v1/projects/{id}/interview-stories`, `GET /api/v1/projects/{id}/interview-stories`
- `GET /api/v1/interview-stories/{id}`, `DELETE /api/v1/interview-stories/{id}`

Career-memory authoring is a desktop deep-work flow. Mobile may surface read-only views later.

### 5.6 Web-editor AI helpers

- `POST /api/v1/ai/extract-claims`
- `POST /api/v1/ai/extract-tasks`
- `POST /api/v1/ai/enrich-page`
- `POST /api/v1/ai/complete`
- `POST /api/v1/ai/transform`

These are bound to the Tiptap editor. Not relevant until edit-lite expands.

### 5.7 Graph & workspace surfaces

- `POST/GET/DELETE /api/v1/edges` — graph authoring belongs in the editor; mobile only consumes via `/objects/{id}/edges`, `/backlinks`, `/related` (read-only).
- `POST/GET/PATCH/DELETE /api/v1/workspaces` — split-pane workspaces are a desktop layout concept.

### 5.8 MCP connections, tutorial, chat structured-summary

- `/api/v1/mcp-connections/*` — admin/integration surface; deferred indefinitely.
- `/api/v1/tutorial/*` — web onboarding only.
- `POST /api/v1/chats/{id}/structured-summary`, `GET /api/v1/chats/{id}/structured-summary`, `POST /api/v1/chats/{id}/structured-summary/apply` — chat summary authoring is a desktop flow.

---

## 6. UI principles

- **Mobile-first, one-handed.** Search and Capture must reach from the thumb.
- **Reading should be calm.** No dense desktop layouts.
- **Capture is one tap from Home.**
- **AI actions are explicit.** Never auto-fire on view; always user-triggered. Show citations on grounded answers. Show a clear AI-disabled state (503).
- **Show network state.** Connection profile and reachability are visible in Settings and surfaced on failure screens.
- **Do not chase desktop parity.** Optimize for the mobile tasks above.

---

## 7. Phase ownership

Phase 00 (this contract) blocks PHASE-PHONE-01A (backend auth), 01B (networking + Compose override), and 01C (iOS scaffold). Subsequent phases (02A API client, 02B simulator QA, 03A read/search, 03B capture, 03C mobile AI, 04 edit-lite, 05 offline cache, 06 device install) are sequenced in [`IDEA-iPHONE-APP.md` §9](../project-phases/IDEA-iPHONE-APP.md).
