Below is the full non-MVP product spec based on your constraints. I am making the remaining architecture decisions rather than asking more.

Product spec: Local AI Knowledge OS

0. Product thesis

Build a local-first personal AI knowledge base that combines:

1. Notion-like structured pages
2. Heptabase-like multi-pane research workflow
3. AI-native ingestion and search
4. MCP exposure so ChatGPT / Claude / coding agents can operate it
5. Local vector + graph retrieval
6. Rich media storage for PDFs, images, videos, YouTube, CSV, and future media types

This is not merely a note app. It is a personal knowledge operating system optimized for:

* dumping and organizing everything,
* storing lectures and sources,
* preserving personal/professional project memory,
* importing ChatGPT/Claude conversations,
* AI-assisted summarization,
* direct keyword search,
* semantic/vector search,
* graph-style knowledge traversal,
* agentic read/write workflows.

⸻

1. Key decisions

1.1 Final design choices

Area	Decision
Product scope	Personal local-first app
Deployment	Local Mac server via Docker Compose
UI	Browser app only
Access	localhost first; LAN/iPhone later
Backend	TypeScript web app + Python ingestion/RAG/agent services
Canonical data	Hybrid: Postgres metadata/content + local filesystem assets
Rich editor	Tiptap / ProseMirror-style JSON document model
Asset storage	Local content-addressed filesystem
Vector DB	Qdrant local as primary recommendation; Chroma acceptable alternative
Graph DB	Kùzu embedded graph DB
Search	Keyword + vector + graph + agentic search
AI	OpenAI first; local LLM via Ollama later
MCP	Built-in MCP server exposing search/read/write tools
Agent permission	Agents may directly write, but all actions are audited
Canvas	Not in v1 core; full product may add later
Chat import	Store raw chat + structured AI summary
Security	Local auth, encrypted API keys, audit log, backups

1.2 Why this stack

Next.js is appropriate because it supports self-hosting as a Node.js server, Docker image, or static export; for this app, Dockerized dynamic server mode is the relevant path.  ￼

Tiptap is a good editor choice because it is an open-source, headless rich-text framework built on ProseMirror and intended for custom Notion/Google Docs-like editing experiences.  ￼

MCP is the right agent integration layer because the official specification defines it as an open protocol for connecting LLM applications to external data sources and tools.  ￼

Qdrant is the primary vector DB recommendation because it is an open-source vector search engine written in Rust with local quickstart support and payload filtering.  ￼

Chroma remains a valid alternative because it is open-source search infrastructure for AI and supports vector, full-text, regex, and metadata search.  ￼

Kùzu is the graph DB recommendation because it is an embedded property graph database optimized for local analytical graph workloads and supports retrieval-oriented features such as full-text search and vector indices.  ￼

⸻

2. Product modules

2.1 Main modules

Local AI Knowledge OS
├── Wiki
│   ├── Pages
│   ├── Subpages
│   ├── Backlinks
│   ├── Tags
│   └── Typed links
├── Sources
│   ├── PDFs
│   ├── Images
│   ├── Videos
│   ├── YouTube
│   ├── Web articles
│   ├── CSV/Excel
│   └── Future media
├── Workspaces
│   ├── Multi-pane layouts
│   ├── Saved research desks
│   └── Context bundles
├── AI
│   ├── Page assistant
│   ├── Workspace assistant
│   ├── Ingestion assistant
│   ├── Search assistant
│   └── Agent action executor
├── Search
│   ├── Keyword search
│   ├── Vector search
│   ├── Graph search
│   ├── Hybrid search
│   └── Natural language Q&A
├── Projects
│   ├── Career memory
│   ├── Professional projects
│   ├── Resume bullets
│   └── Interview stories
├── Chats
│   ├── Raw ChatGPT/Claude imports
│   ├── Structured summaries
│   └── Extracted claims/tasks/projects
└── MCP
    ├── Agent-readable resources
    ├── Agent tools
    └── Agent prompts

⸻

3. UI specification

3.1 Core layout

The app should use a three-panel layout by default.

┌─────────────────┬───────────────────────────────┬────────────────────┐
│ Left sidebar    │ Main workspace                 │ Right AI/context   │
│                 │                               │                    │
│ - Page tree     │ - Page editor                  │ - AI chat          │
│ - Search        │ - Source reader                │ - Related pages    │
│ - Inbox         │ - Multi-pane views             │ - Backlinks        │
│ - Projects      │ - Media preview                │ - Agent actions    │
└─────────────────┴───────────────────────────────┴────────────────────┘

3.2 Required UI modes

Mode	Purpose
Page mode	Edit/read wiki pages
Source mode	Read PDFs, images, videos, YouTube, CSVs
Multi-pane workspace	Compare multiple pages/sources side by side
AI mode	Ask questions, summarize, extract, rewrite, link
Search mode	Keyword/vector/graph search
Inbox mode	Process unstructured dumped material
Project mode	Career/project memory management

3.3 Multi-pane workspace

A workspace is a saved layout of open objects.

Example:

Workspace: Anthropic Interview Prep
Pane 1: Anthropic moat analysis page
Pane 2: Claude Code source notes
Pane 3: OpenAI comparison notes
Pane 4: AI assistant scoped to these panes

Required behavior

* Open 2–4 panes side by side.
* Drag selected text from one pane into another.
* Link current page to another open page.
* Ask AI about:
    * current page,
    * selected text,
    * selected panes,
    * whole workspace,
    * linked graph neighborhood.
* Save workspace layout.
* Reopen workspace later.

⸻

4. Data model

4.1 Core object types

You do not need too many object classes, but the app should distinguish these at the schema level.

Object	Description
Page	General wiki page
Source	External or imported source: PDF, article, YouTube, lecture
Asset	Local file: image, PDF, video, CSV, attachment
Claim	Atomic factual assertion with evidence
Project	Personal/professional project record
Chat	Imported ChatGPT/Claude conversation
Concept	Topic, idea, theory, technology
Person	Person entity
Organization	Company, university, institution
Task	Action item
Workspace	Saved multi-pane layout
Edge	Typed relationship between objects
Chunk	Search/RAG chunk
Embedding	Vector representation of a chunk
AgentRun	AI or MCP action log
IngestionJob	File/chat/article import job

4.2 Typed links

Backlinks alone are insufficient. Use typed edges.

Edge type	Meaning
links_to	Generic link
contains	Parent page contains child page
derived_from	Claim/note derived from source
supports	Source supports claim
contradicts	Source contradicts claim
summarizes	Summary summarizes source/chat
belongs_to_project	Note/source/task belongs to project
mentions	Page mentions person/org/concept
evidence_for	Object is evidence for another object
similar_to	Semantic/conceptual similarity
next_action_for	Task belongs to project/page
created_by_agent	Object was created by AI/agent
revises	New object revises old object

4.3 Postgres tables

Use Postgres as the operational source of truth.

objects (
  id uuid primary key,
  type text not null,
  title text not null,
  slug text,
  summary text,
  status text default 'active',
  created_at timestamptz,
  updated_at timestamptz,
  deleted_at timestamptz,
  created_by text,
  updated_by text,
  metadata jsonb
)
pages (
  object_id uuid primary key references objects(id),
  parent_id uuid references objects(id),
  editor_json jsonb not null,
  plain_text text,
  markdown_export text,
  html_export text
)
sources (
  object_id uuid primary key references objects(id),
  source_type text,
  original_url text,
  author text,
  published_at timestamptz,
  accessed_at timestamptz,
  reliability text,
  citation jsonb
)
assets (
  object_id uuid primary key references objects(id),
  asset_kind text,
  mime_type text,
  original_filename text,
  storage_path text,
  sha256 text,
  size_bytes bigint,
  width int,
  height int,
  duration_seconds float,
  metadata jsonb
)
claims (
  object_id uuid primary key references objects(id),
  claim_text text not null,
  confidence text,
  verification_status text,
  last_verified_at timestamptz,
  stale_after timestamptz
)
projects (
  object_id uuid primary key references objects(id),
  period_start date,
  period_end date,
  role text,
  problem text,
  actions text,
  results text,
  metrics jsonb,
  skills text[]
)
chats (
  object_id uuid primary key references objects(id),
  provider text,
  imported_at timestamptz,
  raw_chat_path text,
  structured_summary jsonb,
  source_export_format text
)
edges (
  id uuid primary key,
  from_object_id uuid references objects(id),
  to_object_id uuid references objects(id),
  edge_type text not null,
  confidence float,
  created_by text,
  created_at timestamptz,
  metadata jsonb
)
chunks (
  id uuid primary key,
  object_id uuid references objects(id),
  chunk_index int,
  chunk_type text,
  text text,
  token_count int,
  source_locator jsonb,
  created_at timestamptz,
  updated_at timestamptz
)
agent_runs (
  id uuid primary key,
  agent_type text,
  provider text,
  model text,
  action text,
  status text,
  input jsonb,
  output jsonb,
  created_objects uuid[],
  updated_objects uuid[],
  started_at timestamptz,
  finished_at timestamptz,
  error text
)
ingestion_jobs (
  id uuid primary key,
  source_kind text,
  status text,
  input jsonb,
  output jsonb,
  error text,
  created_at timestamptz,
  finished_at timestamptz
)

⸻

5. Filesystem and storage design

5.1 Root folder

Default local root:

~/KnowledgeOS/
├── app/
│   ├── docker-compose.yml
│   ├── .env
│   └── backups/
├── data/
│   ├── postgres/
│   ├── qdrant/
│   ├── kuzu/
│   ├── redis/
│   └── logs/
├── library/
│   ├── assets/
│   ├── sources/
│   ├── chats/
│   ├── exports/
│   └── inbox/
├── indexes/
│   ├── text/
│   ├── vector/
│   └── graph/
├── config/
│   ├── app.yaml
│   ├── ai-providers.yaml
│   ├── ingestion.yaml
│   └── mcp.yaml
└── backups/
    ├── daily/
    ├── weekly/
    └── manual/

5.2 Asset storage

Use content-addressed storage to avoid duplicates.

library/assets/
├── sha256/
│   ├── ab/
│   │   └── abcd1234.../
│   │       ├── original.pdf
│   │       ├── metadata.json
│   │       ├── extracted_text.txt
│   │       ├── thumbnails/
│   │       │   ├── page-001.webp
│   │       │   └── page-002.webp
│   │       └── derivatives/
│   │           ├── transcript.vtt
│   │           ├── ocr.json
│   │           └── captions.json

Why this structure:

* deduplication by hash,
* stable file identity,
* safe renaming,
* generated derivatives separated from originals,
* future-proof for OCR, thumbnails, transcripts, embeddings.

5.3 Source storage

Sources are user-meaningful objects, assets are raw files.

library/sources/
├── pdf/
│   └── 2026/
│       └── source_<uuid>/
│           ├── source.json
│           ├── linked_asset.json
│           ├── notes.md
│           └── annotations.json
├── youtube/
│   └── source_<uuid>/
│       ├── source.json
│       ├── transcript.vtt
│       ├── timestamps.json
│       └── notes.md
├── web/
│   └── source_<uuid>/
│       ├── source.json
│       ├── article.html
│       ├── article.md
│       └── screenshot.webp
└── csv/
    └── source_<uuid>/
        ├── source.json
        ├── original.csv
        ├── profile.json
        └── preview.parquet

5.4 Chat storage

library/chats/
├── chatgpt/
│   └── 2026-05/
│       └── chat_<uuid>/
│           ├── raw.json
│           ├── raw.md
│           ├── summary.json
│           ├── extracted_claims.json
│           ├── extracted_tasks.json
│           └── linked_objects.json
├── claude/
│   └── 2026-05/
│       └── chat_<uuid>/
└── manual/

5.5 Inbox

library/inbox/
├── files/
├── urls/
├── pasted_text/
├── screenshots/
├── chats/
└── pending_jobs.jsonl

⸻

6. Media handling

6.1 General policy

Use this rule:

Copy local files into the app library by default. Keep external references for YouTube and web URLs. Allow manual override.

6.2 Media-specific behavior

Media	Storage	Processing
Image	Copy original	Thumbnail, OCR later, caption later
PDF	Copy original	Text extraction, thumbnails, annotations, page citations
MP4/video	Copy original unless huge	Metadata, thumbnails, transcription optional
YouTube	Store URL, metadata, transcript if available	Timestamped notes, no video download by default
CSV	Copy original	Schema inference, preview, optional dataframe profiling
Web article	Store URL + extracted readable content	Screenshot optional
Audio	Copy original	Transcription optional
Slides	Copy original	Extract text/images later
Code	Copy original or snippet	Syntax highlighting

6.3 PDF support

Required PDF features:

* embedded PDF viewer,
* page thumbnails,
* text extraction,
* annotations,
* highlights,
* page-based citation,
* link excerpt to note/claim,
* ask AI about selected pages.

Example citation object:

{
  "source_object_id": "uuid",
  "asset_object_id": "uuid",
  "locator": {
    "type": "pdf_page_range",
    "start_page": 12,
    "end_page": 14
  },
  "quote": "optional short excerpt"
}

6.4 YouTube support

For YouTube:

* store URL,
* fetch title/channel/date where possible,
* store transcript if available,
* store timestamped notes,
* do not download video by default.

Example:

{
  "source_type": "youtube",
  "url": "...",
  "title": "...",
  "channel": "...",
  "transcript_path": "library/sources/youtube/source_uuid/transcript.vtt",
  "timestamps": [
    {
      "time": "00:12:34",
      "note": "Important explanation of MCP tools"
    }
  ]
}

⸻

7. Search and retrieval

7.1 Search modes

The product should expose four search modes.

Mode	Purpose
Keyword search	Exact lookup, titles, terms, filenames
Vector search	Semantic similarity
Graph search	Traverse linked objects
Agentic search	AI decomposes query, searches multiple ways, synthesizes answer

7.2 Keyword search

Use Postgres full-text search for:

* object titles,
* page plain text,
* source metadata,
* claims,
* project fields,
* chat summaries.

7.3 Vector search

Recommended: Qdrant local.

Rationale: Qdrant is open-source, local-friendly, Docker-friendly, supports payloads/filters, and is more production-shaped than a pure prototype DB.  ￼

Chroma is acceptable if you want faster prototyping and simpler Python-native ergonomics; its documentation positions it as open-source search infrastructure with vector, full-text, regex, and metadata search.  ￼

7.4 Graph search

Recommended: Kùzu.

Rationale: Kùzu is embedded, local-first, and built for analytical graph workloads, which fits a personal local graph better than running a heavier graph server.  ￼

7.5 Hybrid retrieval pipeline

User query
  ↓
Query understanding
  ↓
Parallel retrieval
  ├── keyword search in Postgres
  ├── vector search in Qdrant
  ├── graph neighborhood from Kùzu
  └── metadata filters
  ↓
Reranking
  ↓
Context pack construction
  ↓
LLM answer with citations

7.6 Agentic search behavior

For vague queries, the agent should:

1. rewrite the query into multiple search queries,
2. run keyword search,
3. run vector search,
4. retrieve graph neighbors,
5. detect relevant sources,
6. produce answer with citations,
7. optionally suggest new links/tags.

Example:

User:
"What did I do at Coral that relates to agentic CRM?"
Agent:
1. Search projects for Coral + CRM + agentic.
2. Search chats for Coral/project-tako/HubSpot.
3. Search graph neighbors around Organization: Coral Capital.
4. Retrieve related Project objects.
5. Return synthesized answer with project evidence.

⸻

8. AI system

8.1 AI providers

Initial:

* OpenAI API
* local LLM later via Ollama

Later:

* Anthropic API
* Gemini
* local embedding models

8.2 AI actions

Action	Description
summarize_page	Summarize current page
summarize_source	Summarize PDF/article/video
extract_claims	Extract atomic claims
extract_tasks	Extract tasks
extract_entities	Extract people/orgs/concepts
suggest_links	Suggest links to existing objects
create_page	Create structured page
update_page	Directly update an existing page
create_claims	Create claims with source links
create_project_memory	Turn notes into project record
generate_resume_bullets	Generate evidence-linked career bullets
compare_pages	Compare selected pages
answer_from_kb	RAG answer from KB
import_chat_summary	Summarize raw ChatGPT/Claude export
triage_inbox	Process raw inbox items

8.3 Direct write policy

You chose direct agent edits allowed. Therefore the app needs guardrails.

Required:

* every agent action logged,
* before/after diff for page edits,
* undo support,
* soft delete only,
* source label: created_by = agent,
* model/provider recorded,
* prompt/input/output stored in agent_runs.

8.4 AI content labels

Every AI-generated object should store:

{
  "created_by": "agent",
  "agent_run_id": "uuid",
  "provider": "openai",
  "model": "gpt-...",
  "confidence": "medium",
  "requires_review": true
}

Even if direct writes are allowed, the UI should visually indicate AI-generated content.

⸻

9. MCP server specification

9.1 Purpose

The app exposes an MCP server so external agents can:

* search the KB,
* read pages/sources/projects,
* create new pages,
* update existing pages,
* attach files,
* import chats,
* run ingestion jobs,
* create typed links,
* ask retrieval questions.

MCP is appropriate because it standardizes how LLM applications connect to tools and external data sources.  ￼

9.2 MCP architecture

Claude / ChatGPT / Codex / Cursor
        ↓ MCP
KnowledgeOS MCP Server
        ↓
Internal API
        ↓
Postgres + Qdrant + Kùzu + filesystem

9.3 MCP tools

Read/search tools

search_objects(query, filters?)
hybrid_search(query, filters?, limit?)
get_object(object_id)
get_page(page_id)
get_source(source_id)
get_project(project_id)
get_related_objects(object_id, edge_types?, depth?)
answer_from_kb(question, scope?)

Write tools

create_page(title, content, parent_id?, metadata?)
update_page(page_id, patch, edit_summary?)
create_source(source_input)
attach_asset(object_id, file_reference)
create_claim(claim_text, evidence_object_ids?, confidence?)
create_edge(from_id, to_id, edge_type, metadata?)
import_chat(raw_chat, provider, summarize?)
run_ingestion_job(input)
archive_object(object_id, reason?)

Agent workflow tools

triage_inbox(limit?)
summarize_source(source_id)
extract_claims(object_id)
suggest_links(object_id)
create_project_memory(input)
generate_resume_bullets(project_id, target_role?)

9.4 MCP resources

Expose stable resources:

knowledgeos://objects/{id}
knowledgeos://pages/{id}
knowledgeos://sources/{id}
knowledgeos://projects/{id}
knowledgeos://claims/{id}
knowledgeos://workspaces/{id}
knowledgeos://search?q=...

9.5 MCP prompts

Provide reusable prompts:

kb_search_prompt
source_summary_prompt
lecture_note_cleanup_prompt
career_project_extraction_prompt
claim_extraction_prompt
chat_import_summary_prompt
resume_bullet_generation_prompt

9.6 MCP security

MCP/tool execution requires caution because tool-bearing AI systems can expose powerful local actions; a 2026 security report about MCP highlighted risks around remote code execution and unsafe tool handling, so this app should avoid shell execution tools by default and keep a strict tool allowlist.  ￼

Required protections:

* no arbitrary shell execution,
* no arbitrary file read outside ~/KnowledgeOS,
* write actions audited,
* delete is soft-delete only,
* per-tool permission levels,
* API key never exposed through MCP,
* explicit agent_id for every external agent,
* local-only binding by default.

⸻

10. ChatGPT / Claude conversation import

10.1 Supported import methods

Initial:

1. paste chat transcript,
2. upload exported JSON/Markdown,
3. import via MCP tool call,
4. browser copy-paste.

Later:

1. browser extension,
2. watched folder,
3. provider-specific export parsers.

10.2 Chat import pipeline

Raw chat input
  ↓
Store raw chat unchanged
  ↓
Parse turns
  ↓
Generate structured summary
  ↓
Extract:
  ├── decisions
  ├── claims
  ├── tasks
  ├── projects
  ├── concepts
  ├── sources
  └── open questions
  ↓
Create Chat object
  ↓
Create/update linked pages
  ↓
Index chunks
  ↓
Update graph

10.3 Chat summary schema

{
  "title": "Knowledge base app architecture discussion",
  "provider": "chatgpt",
  "date": "2026-05-14",
  "summary": "...",
  "key_decisions": [
    {
      "decision": "Use browser app only for now",
      "rationale": "Desktop wrapper unnecessary if local web app is useful"
    }
  ],
  "open_questions": [],
  "action_items": [],
  "claims": [],
  "projects": [],
  "concepts": ["MCP", "GraphRAG", "local-first storage"],
  "linked_objects": []
}

⸻

11. Ingestion system

11.1 Ingestion inputs

Input	Method
Manual page	Editor
File	Drag/drop or upload
Folder	Watched inbox folder
URL	Paste URL
YouTube	Paste URL
Chat	Upload/paste/import
CSV	Upload
Screenshot	Upload or clipboard
Agent-created object	MCP/API
Auto-generated source	Ingestion pipeline

11.2 Ingestion stages

1. Capture
2. Normalize
3. Store original
4. Extract metadata
5. Extract text/transcript
6. Generate thumbnails/previews
7. Chunk for retrieval
8. Generate embeddings
9. Extract entities/claims/tasks
10. Create graph links
11. Mark as processed

11.3 Ingestion job types

file_import
url_import
youtube_import
pdf_import
image_import
video_import
csv_import
chat_import
folder_watch_import
agent_generated_import

⸻

12. Project and career memory module

This should be first-class because your KB is partly for personal/professional history.

12.1 Project schema

{
  "name": "CoralCareers AI talent platform",
  "period": {
    "start": "2026-02",
    "end": "2026-05"
  },
  "role": "Engineer / Data Scientist",
  "context": "...",
  "problem": "...",
  "actions": ["..."],
  "technical_details": ["..."],
  "business_impact": ["..."],
  "metrics": {
    "startups_supported": 100,
    "candidate_profiles": 18000
  },
  "skills": ["RAG", "matching", "Vercel", "UX", "analytics"],
  "artifacts": [],
  "evidence": [],
  "resume_bullets": [],
  "interview_stories": []
}

12.2 Resume bullet generator

Input:

* target role,
* target company,
* selected projects,
* desired emphasis.

Output:

* bullet variants,
* evidence links,
* confidence flags,
* missing evidence warnings.

Example:

Generated bullet:
Built an AI-powered startup talent matching platform used by 100+ startups and grounded in 18,000+ candidate profiles.
Evidence:
- Project: CoralCareers AI talent platform
- Metric: startups_supported = 100+
- Metric: candidate_profiles = 18,000+

⸻

13. API specification

13.1 Internal REST API

Objects

GET    /api/objects
POST   /api/objects
GET    /api/objects/:id
PATCH  /api/objects/:id
DELETE /api/objects/:id

Pages

GET    /api/pages/:id
POST   /api/pages
PATCH  /api/pages/:id
POST   /api/pages/:id/link
GET    /api/pages/:id/backlinks

Assets

POST   /api/assets/upload
GET    /api/assets/:id
GET    /api/assets/:id/file
GET    /api/assets/:id/thumbnail
POST   /api/assets/:id/process

Sources

POST   /api/sources
GET    /api/sources/:id
POST   /api/sources/import-url
POST   /api/sources/import-youtube
POST   /api/sources/import-pdf
POST   /api/sources/:id/extract

Search

GET    /api/search/keyword?q=
POST   /api/search/vector
POST   /api/search/hybrid
POST   /api/search/graph
POST   /api/search/answer

AI

POST   /api/ai/summarize
POST   /api/ai/extract-claims
POST   /api/ai/suggest-links
POST   /api/ai/compare
POST   /api/ai/generate-resume-bullets
POST   /api/ai/triage-inbox

Chats

POST   /api/chats/import
GET    /api/chats/:id
POST   /api/chats/:id/summarize
POST   /api/chats/:id/extract

Workspaces

GET    /api/workspaces
POST   /api/workspaces
GET    /api/workspaces/:id
PATCH  /api/workspaces/:id

⸻

14. Docker architecture

14.1 Services

services:
  web:
    build: ./apps/web
    ports:
      - "3000:3000"
    depends_on:
      - api
  api:
    build: ./services/api
    ports:
      - "8000:8000"
    volumes:
      - ~/KnowledgeOS/library:/knowledgeos/library
      - ~/KnowledgeOS/config:/knowledgeos/config
    depends_on:
      - postgres
      - qdrant
      - redis
  worker:
    build: ./services/worker
    volumes:
      - ~/KnowledgeOS/library:/knowledgeos/library
      - ~/KnowledgeOS/config:/knowledgeos/config
    depends_on:
      - postgres
      - qdrant
      - redis
  mcp:
    build: ./services/mcp
    ports:
      - "8765:8765"
    depends_on:
      - api
  postgres:
    image: postgres:16
    volumes:
      - ~/KnowledgeOS/data/postgres:/var/lib/postgresql/data
  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
    volumes:
      - ~/KnowledgeOS/data/qdrant:/qdrant/storage
  redis:
    image: redis:7
    volumes:
      - ~/KnowledgeOS/data/redis:/data

Kùzu can be embedded in the Python worker/API process and stored under:

~/KnowledgeOS/data/kuzu/

⸻

15. Monorepo structure

knowledge-os/
├── apps/
│   └── web/
│       ├── app/
│       ├── components/
│       ├── features/
│       │   ├── editor/
│       │   ├── search/
│       │   ├── sources/
│       │   ├── workspaces/
│       │   ├── ai/
│       │   └── projects/
│       ├── lib/
│       └── package.json
├── services/
│   ├── api/
│   │   ├── app/
│   │   │   ├── routes/
│   │   │   ├── models/
│   │   │   ├── repositories/
│   │   │   ├── services/
│   │   │   └── main.py
│   │   └── pyproject.toml
│   ├── worker/
│   │   ├── ingestion/
│   │   ├── extraction/
│   │   ├── embeddings/
│   │   ├── graph/
│   │   └── main.py
│   └── mcp/
│       ├── tools/
│       ├── resources/
│       ├── prompts/
│       └── server.py
├── packages/
│   ├── shared-types/
│   ├── schemas/
│   └── prompts/
├── infra/
│   ├── docker-compose.yml
│   ├── Dockerfile.web
│   ├── Dockerfile.api
│   ├── Dockerfile.worker
│   └── Dockerfile.mcp
├── scripts/
│   ├── setup.sh
│   ├── backup.sh
│   ├── restore.sh
│   ├── reindex.py
│   └── import_chat.py
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DATA_MODEL.md
│   ├── MCP_TOOLS.md
│   ├── AGENT_GUIDE.md
│   ├── INGESTION.md
│   └── SECURITY.md
└── tests/
    ├── api/
    ├── worker/
    ├── mcp/
    └── e2e/

⸻

16. Agent-readiness

16.1 Agent guide

Create docs/AGENT_GUIDE.md.

It should tell coding agents:

This is a local-first personal knowledge base.
Do not store canonical content only in generated exports.
Postgres is the operational source of truth.
Large files live in ~/KnowledgeOS/library/assets.
All agent writes must create AgentRun records.
Never hard-delete objects.
Never read files outside ~/KnowledgeOS unless explicitly configured.
All new object types must be reflected in:
- database schema
- API schema
- MCP tools
- index pipeline
- UI type registry

16.2 Agent-safe internal APIs

Agents should not mutate DB directly. They should use:

* REST API,
* MCP tools,
* typed service functions.

16.3 Agent action log

Every agent action records:

* agent identity,
* model,
* provider,
* input,
* output,
* changed objects,
* before/after diff,
* timestamp,
* success/failure.

⸻

17. Security model

17.1 Local security

Required:

* local login/password,
* session cookie,
* API keys encrypted at rest,
* .env excluded from backups unless encrypted,
* app binds to 127.0.0.1 by default,
* LAN access opt-in,
* MCP server disabled by default until configured,
* MCP write tools can be individually disabled.

17.2 Agent safety

Required:

* no shell tool,
* no arbitrary filesystem tool,
* no destructive hard delete,
* tool allowlist,
* audit log,
* rollback for page edits,
* rate limits for ingestion and AI calls.

17.3 Backups

Backup should include:

Postgres dump
Qdrant storage
Kùzu graph files
library/assets
library/sources
library/chats
config

Backup schedule:

Daily local backup
Weekly compressed backup
Manual one-click backup
Optional external drive backup

⸻

18. Implementation roadmap

Phase 1 — Foundation

Build:

* Docker Compose
* Postgres schema
* filesystem library
* object model
* basic REST API
* Next.js shell UI
* auth
* page CRUD
* Tiptap editor
* asset upload
* soft delete

Deliverable:

You can create/edit pages, upload files, and store everything locally.

Phase 2 — Sources and rich media

Build:

* PDF import/viewer,
* image preview,
* local video preview,
* YouTube source object,
* CSV upload/preview,
* source metadata extraction,
* asset hashing/deduplication.

Deliverable:

You can use it as a rich media personal wiki.

Phase 3 — Search

Build:

* Postgres full-text search,
* Qdrant vector index,
* chunking pipeline,
* embedding pipeline,
* hybrid search endpoint,
* search UI.

Deliverable:

You can search by keyword and semantic similarity.

Phase 4 — Graph

Build:

* edges table,
* typed links UI,
* Kùzu graph sync,
* graph neighborhood retrieval,
* related objects UI.

Deliverable:

The system can traverse relationships, not just search text.

Phase 5 — AI assistant

Build:

* OpenAI integration,
* AI sidebar,
* summarize page,
* summarize source,
* extract claims,
* suggest links,
* triage inbox,
* answer from KB with citations.

Deliverable:

The app becomes AI-assisted inside the interface.

Phase 6 — MCP

Build:

* MCP server,
* read/search tools,
* write tools,
* ingestion tools,
* prompts/resources,
* audit logs,
* permission config.

Deliverable:

Claude/ChatGPT/Codex can operate the knowledge base.

Phase 7 — Chat import

Build:

* raw chat upload,
* provider parser,
* LLM summarizer,
* structured summary,
* extracted claims/tasks/projects,
* link suggestions.

Deliverable:

ChatGPT/Claude conversations become durable knowledge objects.

Phase 8 — Multi-pane workspaces

Build:

* pane layout system,
* saved workspaces,
* drag/drop between panes,
* AI scoped to workspace,
* related context panel.

Deliverable:

The app becomes a serious research workspace.

Phase 9 — Career/project memory

Build:

* project schema UI,
* project extraction assistant,
* resume bullet generator,
* interview story generator,
* evidence-linked outputs.

Deliverable:

The app becomes useful for career positioning and personal/professional memory.

⸻

19. Testing plan

19.1 Unit tests

* object creation,
* edge creation,
* asset hashing,
* chunking,
* embedding job creation,
* graph sync,
* MCP tool validation.

19.2 Integration tests

* upload PDF → extract text → chunk → embed → search,
* import chat → summarize → create objects,
* create page → update page → audit log,
* MCP create page → page appears in UI,
* graph edge → related object retrieval.

19.3 End-to-end tests

Use Playwright-style E2E tests:

Create page
Upload PDF
Highlight PDF text
Create claim
Ask AI about claim
Search claim
Open related project
Generate resume bullet

⸻

20. Recommended defaults

20.1 Default tech stack

Layer	Choice
Frontend	Next.js + React
Editor	Tiptap
Backend API	FastAPI
Worker	Python
App DB	Postgres
Vector DB	Qdrant
Graph DB	Kùzu
Queue	Redis + RQ / Celery-lite
AI API	OpenAI first
Local LLM	Ollama later
MCP server	Python MCP server
Asset storage	Local filesystem
Deployment	Docker Compose

20.2 Why not pure Chroma?

Chroma is simpler to start, and it supports local AI search workflows. However, for your full-product spec, I would prefer Qdrant because it is a more explicit vector search service with strong filtering and Docker-local deployment. Chroma remains a viable substitution if initial implementation speed matters more. と私は思います。

20.3 Why not pure SQLite?

SQLite is excellent for small local apps, but this app wants:

* structured object model,
* JSON metadata,
* full-text search,
* concurrent web access,
* worker jobs,
* agent writes,
* future LAN access.

Postgres is heavier but more future-proof. と私は思います。

⸻

21. Build instruction for an AI coding agent

Use this as the instruction block.

You are building a local-first personal AI knowledge base called KnowledgeOS.
The app runs locally on a Mac via Docker Compose. It is a browser app only. Do not build a desktop app.
Core requirements:
1. Local data ownership.
2. Rich wiki pages with Tiptap editor.
3. Local asset library for PDFs, images, videos, CSVs, YouTube metadata, and future media.
4. Postgres as operational source of truth.
5. Filesystem for large assets.
6. Qdrant for vector search.
7. Kùzu for graph retrieval.
8. FastAPI backend.
9. Next.js frontend.
10. Python worker for ingestion, extraction, embeddings, and graph sync.
11. Built-in MCP server exposing read/search/write/ingestion tools.
12. AI sidebar using OpenAI first.
13. Agents may directly write, but every action must be audited.
14. Never hard-delete user data; use soft delete.
15. No arbitrary shell execution through MCP.
16. All files must remain under ~/KnowledgeOS unless explicitly configured.
Implement in phases:
Phase 1: Docker, schema, page CRUD, Tiptap editor, asset upload.
Phase 2: sources/media ingestion.
Phase 3: keyword/vector search.
Phase 4: graph links and Kùzu.
Phase 5: AI assistant.
Phase 6: MCP server.
Phase 7: chat import.
Phase 8: multi-pane workspaces.
Phase 9: career/project memory.
Before writing code, create:
- docs/ARCHITECTURE.md
- docs/DATA_MODEL.md
- docs/API.md
- docs/MCP_TOOLS.md
- docs/INGESTION.md
- docs/SECURITY.md
- docs/AGENT_GUIDE.md
Use typed schemas wherever possible.
Prefer explicit service boundaries.
Write tests for ingestion, search, MCP tools, and agent audit logs.

⸻

22. Final architecture diagram

Browser UI
Next.js / React / Tiptap
        ↓
FastAPI Backend
        ↓
┌─────────────────────────────────────────────┐
│                 Core Storage                 │
├─────────────────────────────────────────────┤
│ Postgres: objects, pages, edges, metadata    │
│ Filesystem: assets, sources, chats           │
│ Qdrant: vector index                         │
│ Kùzu: graph index                            │
│ Redis: background jobs                       │
└─────────────────────────────────────────────┘
        ↓
Python Workers
- ingestion
- text extraction
- embeddings
- graph sync
- AI extraction
        ↑
MCP Server
        ↑
ChatGPT / Claude / Codex / Cursor / local agents

Bottom line

Build the full product as:

A local browser-based AI knowledge OS with Postgres + filesystem as canonical storage, Qdrant for semantic search, Kùzu for graph traversal, Tiptap for rich editing, FastAPI/Python for ingestion and AI workflows, and an embedded MCP server for agentic access.

This is substantially more ambitious than a note app, but still realistic because you are not doing multiplayer, cloud sync, mobile native apps, or public deployment yet.