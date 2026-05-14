# KnowledgeOS

A local-first personal AI knowledge base — Notion-style pages, rich media ingestion, semantic search, graph traversal, and an MCP server for agentic access.

Runs locally on Mac via Docker Compose. Browser-only UI at http://localhost:3000.

## Quick Start

```bash
bash scripts/setup.sh
docker compose -f infra/docker-compose.yml up -d
```

## Stack

- Frontend: Next.js 14 + Tiptap
- Backend: FastAPI + SQLAlchemy 2.0
- Storage: Postgres 16 + Qdrant (vector) + Kùzu (graph) + local filesystem
- Queue: Redis + RQ
- AI: OpenAI (Phase 5+)

## Project Phases

See `project-phases/` for the detailed implementation plan.
