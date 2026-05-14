# Security Model

## Local Auth

- Simple email/password login
- Session token = `secrets.token_urlsafe(32)`, stored as `sha256(token)` in DB
- HTTP-only cookie `kos_session`, SameSite=Lax, 30-day expiry
- All services bind to `127.0.0.1` by default

## API Key Storage

- OpenAI and other keys stored in `infra/.env` (gitignored)
- Never committed to the repository
- Never exposed through MCP tools

## Agent Safety

- No arbitrary shell execution through MCP
- No file access outside `~/KnowledgeOS`
- All agent actions logged in `agent_runs` table with before/after diffs
- Soft delete only — no hard deletes
- Rate limits on ingestion and AI calls (Phase 5+)

## Backups

- Daily local backup of Postgres dump + Qdrant storage + library assets
- Weekly compressed backup
- Manual one-click backup via `scripts/backup.sh`
