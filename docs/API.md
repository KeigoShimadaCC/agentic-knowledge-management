# KnowledgeOS API Reference

Base URL:

```text
http://localhost:8000
```

Versioned API prefix:

```text
/api/v1
```

All JSON examples show the stable shape clients should rely on. Extra fields may be returned as the implementation grows.

## Authentication

KnowledgeOS uses a local httponly session cookie named `kos_session`. The cookie is created by `POST /api/v1/auth/register` or `POST /api/v1/auth/login` and is sent automatically by the browser on later requests.

Clients outside the browser must preserve and resend the cookie. The raw session token is never stored in the database; the server stores a SHA-256 hash and resolves each request by session lookup.

## Errors

Error responses use:

```json
{
  "detail": "Human-readable error message",
  "code": "machine_readable_code"
}
```

Common status codes:

| Status | Meaning |
| ---: | --- |
| `400` | Invalid request body or unsupported operation |
| `401` | Missing, expired, or invalid session |
| `403` | Authenticated user is not allowed to access the resource |
| `404` | Resource not found, including soft-deleted resources outside trash routes |
| `409` | Conflict, such as duplicate registration email |
| `422` | Validation error |
| `500` | Unexpected server error |

## Pagination

List endpoints use:

```text
?page=1&limit=20
```

Paginated responses use:

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "limit": 20,
  "pages": 0
}
```

## Health

### `GET /api/v1/health`

Checks whether the API process is running.

Request body: none.

Response:

```json
{
  "status": "ok"
}
```

Status codes: `200`.

## Auth Endpoints

### `POST /api/v1/auth/register`

Creates a user and starts a session.

Request:

```json
{
  "email": "you@example.com",
  "password": "correct horse battery staple",
  "display_name": "You"
}
```

Response:

```json
{
  "user": {
    "id": "uuid",
    "email": "you@example.com",
    "display_name": "You",
    "created_at": "2026-05-14T00:00:00Z"
  }
}
```

Status codes: `201`, `400`, `409`, `422`.

Side effect: sets httponly `kos_session` cookie.

### `POST /api/v1/auth/login`

Authenticates an existing user and starts a session.

Request:

```json
{
  "email": "you@example.com",
  "password": "correct horse battery staple"
}
```

Response:

```json
{
  "user": {
    "id": "uuid",
    "email": "you@example.com",
    "display_name": "You"
  }
}
```

Status codes: `200`, `400`, `401`, `422`.

Side effect: sets httponly `kos_session` cookie.

### `POST /api/v1/auth/logout`

Invalidates the current session.

Request body: none.

Response:

```json
{
  "ok": true
}
```

Status codes: `200`, `401`.

Side effect: clears or invalidates `kos_session`.

### `GET /api/v1/auth/me`

Returns the authenticated user.

Request body: none.

Response:

```json
{
  "user": {
    "id": "uuid",
    "email": "you@example.com",
    "display_name": "You"
  }
}
```

Status codes: `200`, `401`.

## Object Endpoints

Object responses share this base shape:

```json
{
  "id": "uuid",
  "kind": "page",
  "title": "Research Notes",
  "description": null,
  "tags": ["research"],
  "metadata": {},
  "is_pinned": false,
  "is_archived": false,
  "created_at": "2026-05-14T00:00:00Z",
  "updated_at": "2026-05-14T00:00:00Z",
  "deleted_at": null
}
```

### `GET /api/v1/objects`

Lists non-deleted objects for the current user.

Query parameters:

| Name | Type | Notes |
| --- | --- | --- |
| `page` | integer | Default `1` |
| `limit` | integer | Default `20` |
| `q` | string | Optional keyword search |
| `kind` | string | Optional object kind filter |

Request body: none.

Response:

```json
{
  "items": [
    {
      "id": "uuid",
      "kind": "page",
      "title": "Research Notes",
      "description": null,
      "tags": [],
      "metadata": {},
      "is_pinned": false,
      "is_archived": false,
      "created_at": "2026-05-14T00:00:00Z",
      "updated_at": "2026-05-14T00:00:00Z",
      "deleted_at": null
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 20,
  "pages": 1
}
```

Status codes: `200`, `401`, `422`.

### `POST /api/v1/objects`

Creates a base object. Use specialized endpoints for pages and assets when content or files are involved.

Request:

```json
{
  "kind": "note",
  "title": "Inbox note",
  "description": "Optional summary",
  "tags": ["inbox"],
  "metadata": {},
  "is_pinned": false,
  "is_archived": false
}
```

Response: object shape.

Status codes: `201`, `400`, `401`, `422`.

### `GET /api/v1/objects/trash`

Lists soft-deleted objects.

Query parameters: `page`, `limit`, optional `kind`.

Request body: none.

Response: paginated object response.

Status codes: `200`, `401`, `422`.

### `GET /api/v1/objects/{id}`

Returns one non-deleted object.

Request body: none.

Response: object shape.

Status codes: `200`, `401`, `403`, `404`.

### `PATCH /api/v1/objects/{id}`

Updates common object metadata.

Request:

```json
{
  "title": "Updated title",
  "description": "Updated description",
  "tags": ["project", "draft"],
  "metadata": {"source": "manual"},
  "is_pinned": true,
  "is_archived": false
}
```

All fields are optional. Omitted fields are unchanged.

Response: object shape.

Status codes: `200`, `400`, `401`, `403`, `404`, `422`.

### `DELETE /api/v1/objects/{id}`

Soft-deletes an object by setting `deleted_at`.

Request body: none.

Response:

```json
{
  "ok": true
}
```

Status codes: `200`, `401`, `403`, `404`.

### `POST /api/v1/objects/{id}/restore`

Restores a soft-deleted object.

Request body: none.

Response: object shape with `deleted_at: null`.

Status codes: `200`, `401`, `403`, `404`.

## Page Endpoints

### `POST /api/v1/pages`

Creates a page object and page content row.

Request:

```json
{
  "title": "New page",
  "content": {
    "type": "doc",
    "content": []
  },
  "tags": [],
  "metadata": {}
}
```

Response:

```json
{
  "id": "uuid",
  "kind": "page",
  "title": "New page",
  "description": null,
  "tags": [],
  "metadata": {},
  "content": {
    "type": "doc",
    "content": []
  },
  "content_text": "",
  "created_at": "2026-05-14T00:00:00Z",
  "updated_at": "2026-05-14T00:00:00Z"
}
```

Status codes: `201`, `400`, `401`, `422`.

### `GET /api/v1/pages/{id}`

Returns a page and its Tiptap document JSON.

Request body: none.

Response: page response shape.

Status codes: `200`, `401`, `403`, `404`.

### `PUT /api/v1/pages/{id}`

Replaces page content and updatable page metadata.

Request:

```json
{
  "title": "Updated page",
  "content": {
    "type": "doc",
    "content": [
      {
        "type": "paragraph",
        "content": [{"type": "text", "text": "Hello"}]
      }
    ]
  },
  "tags": ["draft"],
  "metadata": {}
}
```

Response: page response shape.

Status codes: `200`, `400`, `401`, `403`, `404`, `422`.

### `PATCH /api/v1/pages/{id}`

Partially updates a page.

Request:

```json
{
  "title": "Partially updated page",
  "content": {
    "type": "doc",
    "content": []
  }
}
```

All fields are optional. Omitted fields are unchanged.

Response: page response shape.

Status codes: `200`, `400`, `401`, `403`, `404`, `422`.

## Asset Endpoints

### `POST /api/v1/assets/upload`

Uploads a file and creates an asset object.

Request content type: `multipart/form-data`.

Form fields:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `file` | file | yes | Original file |
| `title` | string | no | Defaults to filename |
| `description` | string | no | Optional |
| `tags` | string / JSON | no | Client-dependent tag representation |
| `metadata` | JSON string | no | Optional object metadata |

Response:

```json
{
  "id": "uuid",
  "kind": "asset",
  "title": "paper.pdf",
  "description": null,
  "tags": [],
  "metadata": {},
  "filename": "paper.pdf",
  "content_type": "application/pdf",
  "size_bytes": 123456,
  "sha256": "hex_digest",
  "storage_path": "~/KnowledgeOS/library/assets/ab/ab12.../original.pdf",
  "status": "ready",
  "width": null,
  "height": null,
  "duration_secs": null,
  "created_at": "2026-05-14T00:00:00Z",
  "updated_at": "2026-05-14T00:00:00Z"
}
```

Status codes: `201`, `400`, `401`, `413`, `422`.

### `GET /api/v1/assets/{id}`

Returns asset metadata.

Request body: none.

Response: asset response shape.

Status codes: `200`, `401`, `403`, `404`.

### `GET /api/v1/assets/{id}/download`

Downloads the original file.

Request body: none.

Response: binary file stream with appropriate `Content-Type` and download headers.

Status codes: `200`, `401`, `403`, `404`.

### `DELETE /api/v1/assets/{id}`

Soft-deletes the asset object. The stored original is retained so the asset can be restored or audited.

Request body: none.

Response:

```json
{
  "ok": true
}
```

Status codes: `200`, `401`, `403`, `404`.

## Coming in Phase 2

### Sources

Source endpoints will create and manage first-class source objects:

```text
POST /api/v1/sources
GET /api/v1/sources
GET /api/v1/sources/{id}
PATCH /api/v1/sources/{id}
DELETE /api/v1/sources/{id}
```

Expected create request:

```json
{
  "source_type": "pdf",
  "asset_id": "uuid",
  "url": null,
  "title": "Optional title"
}
```

### Edges

Edge endpoints will expose object relationships:

```text
POST /api/v1/edges
GET /api/v1/edges
GET /api/v1/objects/{id}/edges
DELETE /api/v1/edges/{id}
```

Expected create request:

```json
{
  "source_id": "uuid",
  "target_id": "uuid",
  "kind": "cites",
  "weight": 1.0,
  "metadata": {}
}
```
