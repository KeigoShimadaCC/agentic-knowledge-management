# Mobile API Contract

> Endpoint contract the iPhone client consumes. Companion docs: [`MOBILE_APP.md`](./MOBILE_APP.md), [`MOBILE_NETWORKING.md`](./MOBILE_NETWORKING.md). All "Verified" endpoints below were cross-checked against `services/api/app/api/v1/` on the `phase-phone-00-mobile-contract` branch — no hallucinated routes.

---

## 1. Base URL and prefix

```
Base URL:   user-configured per profile (see MOBILE_NETWORKING.md)
Path prefix: /api/v1
```

Common bases:

| Profile | Base URL |
|---|---|
| iOS Simulator | `http://127.0.0.1:8001` |
| Same-Wi-Fi iPhone | `http://<mac-lan-ip>:8001` |
| Tailscale iPhone | `http://<mac-tailnet-name>:8001` (HTTPS later) |

---

## 2. Authentication

### 2.1 Header

All authenticated requests:

```http
Authorization: Bearer <opaque_mobile_token>
```

Tokens are opaque, high-entropy strings issued exactly once at login.

### 2.2 Proposed mobile auth endpoints — **NOT YET IMPLEMENTED**

These three endpoints are designed here but **do not exist in code today**. PHASE-PHONE-01A will implement them. iOS work depending on them must wait for that phase.

#### `POST /api/v1/auth/mobile-login` (Phase 01A)

Request:

```json
{
  "email": "you@example.com",
  "password": "correct horse battery staple",
  "device_name": "Example iPhone"
}
```

Success (`200 OK`):

```json
{
  "token": "opaque-mobile-token-returned-once",
  "user": {
    "id": "uuid",
    "email": "you@example.com",
    "display_name": "You"
  },
  "expires_at": "2026-06-16T00:00:00Z"
}
```

Failure: `401` with the standard error envelope (§7). Same shape for wrong password and unknown email — no enumeration.

#### `POST /api/v1/auth/mobile-logout` (Phase 01A)

Revokes the bearer token presented in the `Authorization` header. Idempotent. `200 OK` with `{"ok": true}` on success; `401` if the token is already revoked.

#### `GET /api/v1/mobile/bootstrap` (Phase 01A)

Returns the current user plus capability flags so the client can render disabled/enabled states without probing each endpoint.

```json
{
  "user": {
    "id": "uuid",
    "email": "you@example.com",
    "display_name": "You"
  },
  "capabilities": {
    "ai_enabled": true,
    "embeddings_enabled": true,
    "upload_enabled": true,
    "mobile_api_version": 1
  }
}
```

### 2.3 Token-handling rules

- The raw token is returned **only once**, in the `mobile-login` response. It is never echoed in any subsequent response, `/auth/me`, `/mobile/bootstrap`, or admin endpoint.
- The server stores only a SHA-256 (or stronger) hash, in the existing `sessions.token_hash` column. The existing cookie auth already uses this column with the same hash strategy.
- Sessions get a new `client_type` column (`"web"` | `"ios"`) and a nullable `device_name` (added by the Phase 01A migration). Existing cookie sessions backfill to `"web"`.
- `last_seen` is updated on each authenticated request.
- Tokens must never appear in server logs or response bodies. Phase 01A tests assert both.
- The bearer surface and the cookie surface flow through the same `get_current_user` dependency. Ownership filters (`user_id = current_user.id` + `deleted_at IS NULL`) are identical.

### 2.4 Hard rules

- **Never** reuse `MCP_INTERNAL_TOKEN` (the internal MCP credential) as a mobile token. They are separate concerns and the MCP token must not leave the host.
- Devices store the bearer token in **iOS Keychain**, never `UserDefaults`. Logout deletes the local token *and* calls `POST /auth/mobile-logout` to revoke it server-side.

---

## 3. Read-side endpoints (verified)

Every endpoint in this section exists in `services/api/app/api/v1/` and uses `get_current_user` auth. Mobile MVP screens map onto this subset; the broader endpoint surface is intentionally not exposed (see `MOBILE_APP.md` §5).

### 3.1 Health

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/health` | none | Returns `{status, db, redis}`. Used by Connect screen and `scripts/mobile_network_check.sh` (Phase 01B). |

### 3.2 Auth (existing, read-only on mobile)

| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/auth/me` | Current user from cookie *or* bearer token. Useful for session-validity checks. |

### 3.3 Objects

| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/objects` | Paginated list. Mobile Home uses this. Filters: `kind`, `q`, `limit`, `offset`. |
| GET | `/api/v1/objects/{id}` | Object envelope with `kind` discriminator. Mobile detail dispatcher reads this first, then fetches the kind-specific resource. |
| PATCH | `/api/v1/objects/{id}` | Title/tags edits (Phase 04 edit-lite only; not MVP). |
| GET | `/api/v1/objects/{id}/edges` | Edges originating from the object. |
| GET | `/api/v1/objects/{id}/backlinks` | Inbound edges. |
| GET | `/api/v1/objects/{id}/related` | Depth 1–2 Postgres traversal. |
| GET | `/api/v1/objects/{id}/index-status` | Chunk/embedding state — useful for "is this fully indexed?" hints in Settings. |

### 3.4 Pages

| Method | Path | Notes |
|---|---|---|
| POST | `/api/v1/pages` | Quick-note capture. Body accepts plain text → converted to simple Tiptap JSON server-side. |
| GET | `/api/v1/pages/{id}` | Page read. Response includes `content_text` + `content_doc` (Tiptap JSON). |
| PUT | `/api/v1/pages/{id}` | Full replacement. Phase 04 only. |
| PATCH | `/api/v1/pages/{id}` | Partial update (title, tags, body). Phase 04 only. |

### 3.5 Assets and sources

| Method | Path | Notes |
|---|---|---|
| POST | `/api/v1/assets/upload` | Multipart upload. With `?create_source=true`, also creates a `source` object and a `derives_from` edge (asset → source). |
| GET | `/api/v1/assets/{id}` | Asset metadata (sha256, mime, size, original filename). |
| GET | `/api/v1/assets/{id}/download` | Binary stream. Honor server `Content-Type`/`Content-Disposition`. |
| POST | `/api/v1/sources` | Create a source by URL (web, youtube, etc.). Body: `{source_type, url}` or `{source_type, asset_id}`. |
| GET | `/api/v1/sources` | List paginated sources for Home/recent. |
| GET | `/api/v1/sources/{id}` | Source detail including `ingestion_status` + `preview_data`. |
| PATCH | `/api/v1/sources/{id}` | Title/tag edits (Phase 04). |
| GET | `/api/v1/sources/{id}/text` | Streamed extracted text. Use for SourceDetail body. |
| GET | `/api/v1/sources/{id}/thumbnail` | Thumbnail binary. |

### 3.6 Chats (read-only on mobile MVP)

| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/chats` | List imported chats. |
| GET | `/api/v1/chats/{id}` | Structured chat. |
| GET | `/api/v1/chats/{id}/raw` | Raw original payload. Useful for "view source" link. |

`POST /api/v1/chats/import` is **excluded from mobile**; chat import is a desktop paste workflow.

### 3.7 Projects (read-only on mobile MVP)

| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/projects` | Paginated. |
| GET | `/api/v1/projects/{project_id}` | Project detail. |

### 3.8 Search

| Method | Path | Notes |
|---|---|---|
| POST | `/api/v1/search/hybrid` | Primary mobile search. Body: `{q, kind?, limit?, offset?, debug?}`. Response: `HybridSearchResponse` with combined score + per-result snippets. Degrades to keyword-only when embeddings are disabled — same response shape either way. |

`POST /api/v1/search/vector` and `GET /api/v1/search/keyword` exist but mobile must call only `/search/hybrid`. Single code path on the client.

### 3.9 AI (user-triggered only)

| Method | Path | Notes |
|---|---|---|
| POST | `/api/v1/ai/answer` | Grounded KB Q&A. Body: `{question, scope?: {object_ids?}}`. Response includes `answer` text and `citations[]` referencing chunks. **Show citations in the UI.** |
| POST | `/api/v1/ai/summarize` | Summarize a single object (Phase 03C). |
| POST | `/api/v1/ai/suggest-links` | Suggest links for an object (Phase 03C). |

All `/ai/*` endpoints return `503` with `code: "ai_disabled"` when no API key is configured. The mobile UI surfaces this state with a clear, non-blocking message — never silently retries.

---

## 4. Capabilities and disabled-state handling

The mobile client should call `GET /api/v1/mobile/bootstrap` after login and cache `capabilities` for the session. Use the flags to disable UI affordances **before** a request fails:

| Capability flag | UI behavior when `false` |
|---|---|
| `ai_enabled` | Hide or disable the "Ask" button and AI screen actions. |
| `embeddings_enabled` | Search still works; show a small note that results are keyword-only. |
| `upload_enabled` | Disable photo/file capture, show why. |

Endpoint-level `503` responses (with `code: "ai_disabled"` / `code: "embeddings_disabled"`) remain authoritative — capabilities are a hint, not a guarantee.

---

## 5. Pagination conventions

Paginated endpoints (`/objects`, `/projects`, `/sources`, `/ai/inbox` if ever used) return `PaginatedResponse[T]`:

```json
{
  "items": [ ... ],
  "total": 123,
  "limit": 25,
  "offset": 0
}
```

Mobile defaults:

- `limit=25` for list screens.
- `limit=10` for nested previews.
- Send `offset = pageIndex * limit`.
- Treat `items.length < limit` as "no more pages" without re-checking `total`.

---

## 6. Request and response basics

- All bodies are JSON unless explicitly multipart (`POST /api/v1/assets/upload`).
- Timestamps are ISO-8601 with timezone (`2026-05-17T12:34:56.789Z`). Decode centrally on the client.
- Unknown fields must **not** crash the decoder. DTOs ignore unknown keys.
- IDs are UUID strings.
- Object envelopes include a `kind` discriminator (`page`, `source`, `asset`, `chat`, `project`, `note`, `bookmark`, `collection`). Detail dispatching is on this field.

---

## 7. Error envelope

All error responses use:

```json
{
  "detail": "Human-readable error message",
  "code": "machine_readable_code"
}
```

| HTTP | `code` | When |
|---|---|---|
| 400 | `validation_error` | Request body fails validation. |
| 401 | `unauthenticated` | Missing/invalid/revoked bearer token (or cookie). |
| 403 | `forbidden` | Authenticated but not allowed (rare; ownership is generally enforced as 404). |
| 404 | `not_found` | Object doesn't exist or is owned by another user. **No enumeration** — same response either way. |
| 409 | `conflict` | Edit-lite version conflict (Phase 04). |
| 413 | `payload_too_large` | Upload exceeds server limit. |
| 503 | `ai_disabled` | AI endpoint called without `OPENAI_API_KEY`. |
| 503 | `embeddings_disabled` | Vector path called with embeddings off (hybrid auto-degrades; this only fires on `/search/vector`). |

Existing error responses in code may use different `code` strings; the contract above is the **target** shape. PHASE-PHONE-01A normalizes auth errors; later phases align the rest as needed. The client decoder must therefore tolerate a missing `code` field and fall back to `detail`.

---

## 8. Mobile-specific hard rules

| Rule | Why |
|---|---|
| Never log the bearer token. | Local-first invariant; logs may surface in screenshots and crash reports. |
| Never store the token in `UserDefaults`. | Keychain only. |
| Logout must call `POST /auth/mobile-logout` *and* clear Keychain. | Server-side revocation prevents stolen-device replay. |
| Never reuse `MCP_INTERNAL_TOKEN`. | MCP credential is internal-only. |
| Never call any endpoint listed in `MOBILE_APP.md` §5 from mobile MVP. | Scope creep / wrong-context use. |
| `POST /api/v1/search/hybrid` only — not `/search/vector` or `/search/keyword`. | Single client path that degrades cleanly. |
| AI calls are always user-triggered. Never auto-fire on view. | Cost + privacy. |

---

## 9. Future-phase endpoints (not in MVP scope)

These exist in the API today but are **not** consumed by mobile MVP. Listed here so the contract is complete and future phones don't accidentally re-derive them.

- `POST /api/v1/objects` (mobile creates objects only via `/pages` and `/sources`)
- `DELETE /api/v1/objects/{id}`, `POST /api/v1/objects/{id}/restore`, `POST /api/v1/objects/{id}/archive`
- `POST /api/v1/objects/{id}/revisions/{rev_id}/restore`
- `POST /api/v1/ai/triage`, `GET /api/v1/ai/inbox`
- `POST /api/v1/ai/extract-claims`, `POST /api/v1/ai/extract-tasks`, `POST /api/v1/ai/enrich-page`, `POST /api/v1/ai/complete`, `POST /api/v1/ai/transform`
- `POST /api/v1/ai/extract-project`, `POST /api/v1/ai/generate-resume-bullets`, `POST /api/v1/ai/generate-interview-story`
- `POST /api/v1/projects/{id}/resume-bullet-sets`, related list/get/delete; `POST /api/v1/projects/{id}/interview-stories`, related list/get/delete
- `POST /api/v1/chats/import`, `DELETE /api/v1/chats/{id}`, `POST /api/v1/chats/{id}/restore`, `POST /api/v1/chats/{id}/reindex`
- `POST /api/v1/chats/{id}/structured-summary`, `GET /api/v1/chats/{id}/structured-summary`, `POST /api/v1/chats/{id}/structured-summary/apply`
- `POST/GET/DELETE /api/v1/edges`
- `POST/GET/PATCH/DELETE /api/v1/workspaces`, `POST /api/v1/workspaces/{id}/restore`
- All `/api/v1/mcp-connections/*`
- `POST /api/v1/tutorial/seed`, `DELETE /api/v1/tutorial/reset`
- `DELETE /api/v1/assets/{id}`

---

## 10. Changelog

| Date | Phase | Change |
|---|---|---|
| 2026-05-17 | PHONE-00 | Initial contract. Mobile-login/logout/bootstrap proposed; read-side endpoint surface verified against `services/api/app/api/v1/`. |
