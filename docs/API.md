# API Reference

Base URL: `http://localhost:8000`

## Auth

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/auth/register | Create account, set session cookie |
| POST | /api/v1/auth/login | Login, set session cookie |
| POST | /api/v1/auth/logout | Clear session |
| GET | /api/v1/auth/me | Current user |

## Objects

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/objects | List (filter: kind, tag, q) |
| POST | /api/v1/objects | Create |
| GET | /api/v1/objects/trash | Soft-deleted items |
| GET | /api/v1/objects/{id} | Get by id |
| PATCH | /api/v1/objects/{id} | Update |
| DELETE | /api/v1/objects/{id} | Soft delete |
| POST | /api/v1/objects/{id}/restore | Restore |

## Pages

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/pages | Create page (atomic) |
| GET | /api/v1/pages/{id} | Get content |
| PUT | /api/v1/pages/{id} | Full replace |
| PATCH | /api/v1/pages/{id} | Partial update |

## Assets

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/assets/upload | Upload file (multipart) |
| GET | /api/v1/assets/{id} | Get metadata |
| GET | /api/v1/assets/{id}/download | Stream file |
| DELETE | /api/v1/assets/{id} | Soft delete |

## Health

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Service health check |
