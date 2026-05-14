# MCP Tools

> Phase 6 — not yet implemented.

## Read / Search Tools

- `search_objects(query, filters?)` — keyword + vector search
- `hybrid_search(query, filters?, limit?)` — combined search
- `get_object(object_id)` — retrieve any object
- `get_page(page_id)` — retrieve page with content
- `get_source(source_id)` — retrieve source metadata
- `get_project(project_id)` — retrieve project record
- `get_related_objects(object_id, edge_types?, depth?)` — graph neighborhood
- `answer_from_kb(question, scope?)` — RAG answer with citations

## Write Tools

- `create_page(title, content, parent_id?, metadata?)`
- `update_page(page_id, patch, edit_summary?)`
- `create_source(source_input)`
- `attach_asset(object_id, file_reference)`
- `create_claim(claim_text, evidence_object_ids?, confidence?)`
- `create_edge(from_id, to_id, edge_type, metadata?)`
- `import_chat(raw_chat, provider, summarize?)`
- `run_ingestion_job(input)`
- `archive_object(object_id, reason?)`

## Security

- No shell execution tool
- No arbitrary filesystem access outside ~/KnowledgeOS
- All write actions audited in agent_runs table
- Soft delete only
