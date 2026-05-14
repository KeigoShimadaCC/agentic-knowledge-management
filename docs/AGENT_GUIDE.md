# Agent Guide

This is a local-first personal knowledge base called KnowledgeOS.

## Rules for Coding Agents

- Do NOT store canonical content only in generated exports
- Postgres is the operational source of truth
- Large files live in `~/KnowledgeOS/library/assets/`
- All agent writes must create AgentRun records
- Never hard-delete objects — use soft delete (set deleted_at)
- Never read files outside `~/KnowledgeOS` unless explicitly configured
- All new object types must be reflected in: database schema, API schema, MCP tools, index pipeline, UI type registry

## How to Interact

Use the REST API or MCP tools (Phase 6+). Never mutate the database directly.

## When Adding New Features

1. Add migration to `services/api/alembic/versions/`
2. Add SQLAlchemy model in `services/api/app/models/`
3. Add Pydantic schema in `services/api/app/schemas/`
4. Add API route in `services/api/app/api/v1/`
5. Add TypeScript type in `apps/web/src/types/index.ts`
6. Add API client function in `apps/web/src/lib/api.ts`
7. Write tests in `tests/api/`
