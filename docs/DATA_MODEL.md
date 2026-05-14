# Data Model

See `docs/schema.sql` for full SQL. Summary of object types:

| Object | Description |
|--------|-------------|
| Page | Rich-text wiki page (Tiptap JSON) |
| Asset | Uploaded file (PDF, image, video, CSV, etc.) |
| Note | Short unstructured note |
| Bookmark | Web URL with metadata |
| Collection | Group of objects |
| Edge | Typed relationship between objects |
| Chunk | Text fragment for vector search |
| IngestionJob | Background processing job |
| AgentRun | AI/MCP action audit record |

## Typed Edges

| Edge Kind | Meaning |
|-----------|---------|
| link | Generic link |
| embed | Object embedded in another |
| child | Parent→child containment |
| tag | Object tagged with concept |
| related | Semantic/conceptual similarity |
| citation | Source cited in page/claim |
