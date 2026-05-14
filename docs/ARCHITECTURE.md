# Architecture

KnowledgeOS is a local-first personal AI knowledge base running on Mac via Docker Compose.

## Service Topology

```
Browser (localhost:3000)
    ↓
Next.js web (Docker)
    ↓
FastAPI api (Docker, port 8000)
    ↓
┌──────────────────────────────────────────┐
│            Core Storage                  │
├──────────────────────────────────────────┤
│ Postgres 16: objects, pages, edges, ...  │
│ Filesystem: ~/KnowledgeOS/library/       │
│ Qdrant: vector index (Phase 3+)          │
│ Kùzu: graph index (Phase 4+)             │
│ Redis: background job queue              │
└──────────────────────────────────────────┘
    ↓
Python Workers (ingestion, embeddings, graph sync)
    ↑
MCP Server (Phase 6+)
    ↑
External agents (Claude, ChatGPT, Codex)
```

## Data Flow

All canonical data lives in Postgres (metadata) and `~/KnowledgeOS/library/` (binary assets).
Vector and graph indexes are derived from Postgres and can be rebuilt from scratch.
