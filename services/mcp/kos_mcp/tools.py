from __future__ import annotations

import ipaddress
import json
from pathlib import Path
from urllib.parse import urlparse

import httpx
from mcp.server import Server
from mcp.types import TextContent, Tool

from .client import KosApiClient
from .config import WRITE_TOOL_NAMES, McpSettings
from .redaction import redact_dict

_BLOCKED_URL_SCHEMES = frozenset({"file", "ftp", "data", "javascript"})
_BLOCKED_HOSTNAMES = frozenset({
    "localhost", "127.0.0.1", "0.0.0.0", "::1",
    "metadata.google.internal", "kubernetes.default",
})

_VALID_EDGE_KINDS = frozenset({
    "links_to", "cites", "mentions", "supports",
    "contradicts", "related_to", "derives_from", "summarizes",
})

_PAGE_TEXT_LIMIT = 50_000
_SOURCE_TEXT_DEFAULT_LIMIT = 12_000


def register_tools(server: Server, client: KosApiClient, settings: McpSettings) -> None:
    allowed = set(settings.mcp_allowed_tools)

    tools: list[Tool] = []

    if "search_objects" in allowed:
        tools.append(
            Tool(
                name="search_objects",
                description=(
                    "Search KnowledgeOS using keyword matching over pages, sources, assets, "
                    "and chats. Read-only. Returns object summaries with IDs for follow-up "
                    "get_* calls. Does not modify the knowledge base."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "kind": {
                            "type": "string",
                            "description": "Filter by object kind: page, source, asset, chat",
                        },
                        "limit": {
                            "type": "integer",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                        },
                    },
                    "required": ["query"],
                },
            )
        )

    if "hybrid_search" in allowed:
        tools.append(
            Tool(
                name="hybrid_search",
                description=(
                    "Search KnowledgeOS using keyword + semantic vector search (hybrid). "
                    "Read-only. Falls back to keyword-only if embeddings are unavailable. "
                    "Returns object summaries. Does not modify the knowledge base."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "kind": {
                            "type": "string",
                            "description": "Filter by object kind: page, source, asset, chat",
                        },
                        "limit": {
                            "type": "integer",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                        },
                    },
                    "required": ["query"],
                },
            )
        )

    if "get_object" in allowed:
        tools.append(
            Tool(
                name="get_object",
                description=(
                    "Fetch metadata for any KnowledgeOS object by ID (page, source, asset, "
                    "chat). Read-only. Returns title, kind, tags, timestamps. Use get_page or "
                    "get_source for full content."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "object_id": {"type": "string", "description": "UUID of the object"},
                    },
                    "required": ["object_id"],
                },
            )
        )

    if "get_page" in allowed:
        tools.append(
            Tool(
                name="get_page",
                description=(
                    "Fetch a KnowledgeOS page by ID. Read-only. Returns title, plain-text "
                    "content, word count, and tags. The full Tiptap editor JSON is omitted "
                    "by default."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_id": {"type": "string", "description": "UUID of the page"},
                        "include_json": {
                            "type": "boolean",
                            "default": False,
                            "description": "Include full Tiptap editor JSON",
                        },
                    },
                    "required": ["page_id"],
                },
            )
        )

    if "get_source" in allowed:
        tools.append(
            Tool(
                name="get_source",
                description=(
                    "Fetch a KnowledgeOS source by ID (PDF, YouTube, web article, CSV, etc). "
                    "Read-only. Returns metadata, ingestion status, and optionally extracted "
                    "text (truncated). Does not stream raw files."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "source_id": {"type": "string", "description": "UUID of the source"},
                        "include_text": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include extracted text",
                        },
                        "max_chars": {
                            "type": "integer",
                            "default": _SOURCE_TEXT_DEFAULT_LIMIT,
                            "minimum": 100,
                            "maximum": 50000,
                        },
                    },
                    "required": ["source_id"],
                },
            )
        )

    if "get_related_objects" in allowed:
        tools.append(
            Tool(
                name="get_related_objects",
                description=(
                    "Traverse the KnowledgeOS knowledge graph from a given object. Read-only. "
                    "Returns related objects up to depth 2 with edge types and directions. "
                    "Does not modify the knowledge base."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "object_id": {"type": "string", "description": "UUID of the root object"},
                        "depth": {
                            "type": "integer",
                            "default": 1,
                            "minimum": 1,
                            "maximum": 2,
                        },
                        "limit": {
                            "type": "integer",
                            "default": 20,
                            "minimum": 1,
                            "maximum": 50,
                        },
                        "direction": {
                            "type": "string",
                            "enum": ["both", "outgoing", "incoming"],
                            "default": "both",
                        },
                        "edge_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by edge kind(s)",
                        },
                    },
                    "required": ["object_id"],
                },
            )
        )

    if "answer_from_kb" in allowed:
        tools.append(
            Tool(
                name="answer_from_kb",
                description=(
                    "Search the knowledge base and answer a question with citations. "
                    "Uses hybrid search + LLM reasoning over matching pages, sources, and chats. "
                    "Returns answer text, citation object IDs, and context count. "
                    "Read-only. Requires OPENAI_API_KEY on the server; returns an error object "
                    "if AI is disabled."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "The question to answer from the knowledge base",
                        },
                        "kind": {
                            "type": "string",
                            "description": "Restrict search to one object kind: page, source, chat",
                        },
                        "limit": {
                            "type": "integer",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 20,
                            "description": "Max number of KB chunks to retrieve as context",
                        },
                    },
                    "required": ["question"],
                },
            )
        )

    # Write tools — only registered when MCP_ALLOW_WRITE_TOOLS=true
    if settings.mcp_allow_write_tools:
        if "create_page" in allowed:
            tools.append(
                Tool(
                    name="create_page",
                    description=(
                        "Create a new page in the knowledge base. "
                        "Returns the new object id. Audited: creates an agent_runs row."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Page title (required)"},
                            "content_text": {
                                "type": "string",
                                "description": "Plain-text content for the page body",
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Tags to apply to the page",
                            },
                        },
                        "required": ["title"],
                    },
                )
            )

        if "update_page" in allowed:
            tools.append(
                Tool(
                    name="update_page",
                    description=(
                        "Update an existing page's title, content, or tags. "
                        "Writes an object_revisions row (before/after snapshot). "
                        "Use expected_version for optimistic locking (returns 409 on conflict)."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "page_id": {
                                "type": "string",
                                "description": "UUID of the page to update",
                            },
                            "title": {"type": "string"},
                            "content_text": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                            "expected_version": {
                                "type": "integer",
                                "description": "Current version number for optimistic locking",
                            },
                        },
                        "required": ["page_id"],
                    },
                )
            )

        if "create_edge" in allowed:
            tools.append(
                Tool(
                    name="create_edge",
                    description=(
                        "Create a typed edge between two objects. Idempotent on "
                        "(source_id, target_id, kind). Audited: creates an agent_runs row."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "source_id": {"type": "string", "description": "UUID of source object"},
                            "target_id": {"type": "string", "description": "UUID of target object"},
                            "kind": {
                                "type": "string",
                                "enum": [
                                    "links_to", "cites", "mentions", "supports",
                                    "contradicts", "related_to", "derives_from", "summarizes",
                                ],
                            },
                            "weight": {"type": "number", "default": 1.0},
                            "metadata": {"type": "object"},
                        },
                        "required": ["source_id", "target_id", "kind"],
                    },
                )
            )

        if "archive_object" in allowed:
            tools.append(
                Tool(
                    name="archive_object",
                    description=(
                        "Archive an object (sets is_archived=true). Reversible: "
                        "un-archive via PATCH /objects/{id} with is_archived=false. "
                        "Idempotent: second call is a no-op. Audited."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "object_id": {
                                "type": "string",
                                "description": "UUID of object to archive",
                            },
                            "reason": {
                                "type": "string",
                                "description": "Optional reason for archiving",
                            },
                        },
                        "required": ["object_id"],
                    },
                )
            )

        if "ingest_url" in allowed:
            tools.append(
                Tool(
                    name="ingest_url",
                    description=(
                        "Ingest a URL (web article, YouTube video, PDF link) as a new source. "
                        "Returns source id immediately; extraction runs in the background. "
                        "Rejects file://, localhost, and link-local addresses."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to ingest"},
                            "source_type": {
                                "type": "string",
                                "enum": ["web", "youtube", "pdf"],
                            },
                            "title": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["url"],
                    },
                )
            )

        if "ingest_file" in allowed:
            tools.append(
                Tool(
                    name="ingest_file",
                    description=(
                        "Ingest a local file as a new source. "
                        "File path must be under LIBRARY_ROOT. "
                        "Returns source id immediately; extraction runs in background."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Absolute path to file (must be under LIBRARY_ROOT)",
                            },
                            "source_type": {
                                "type": "string",
                                "enum": ["pdf", "image", "csv", "audio", "video"],
                            },
                            "title": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["file_path"],
                    },
                )
            )

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return tools

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name not in allowed:
            return [TextContent(type="text", text=f"Tool '{name}' is not enabled.")]

        if name in WRITE_TOOL_NAMES and not settings.mcp_allow_write_tools:
            return [TextContent(
                type="text",
                text=(
                    "Write tools are disabled. "
                    "Set MCP_ALLOW_WRITE_TOOLS=true to enable create/update/ingest tools."
                ),
            )]

        try:
            result = await _dispatch(name, arguments, client)
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 404:
                return [TextContent(type="text", text="Not found (404).")]
            return [TextContent(type="text", text=f"API error {status}: {exc.response.text[:200]}")]
        except Exception as exc:
            return [TextContent(type="text", text=f"Error: {exc}")]

        return [TextContent(type="text", text=json.dumps(result, default=str))]


async def _dispatch(name: str, args: dict, client: KosApiClient) -> object:
    if name == "search_objects":
        return await _search_objects(client, **args)
    if name == "hybrid_search":
        return await _hybrid_search(client, **args)
    if name == "get_object":
        return await _get_object(client, **args)
    if name == "get_page":
        return await _get_page(client, **args)
    if name == "get_source":
        return await _get_source(client, **args)
    if name == "get_related_objects":
        return await _get_related_objects(client, **args)
    if name == "answer_from_kb":
        return await _answer_from_kb(client, **args)
    if name == "create_page":
        return await _create_page(client, **args)
    if name == "update_page":
        return await _update_page(client, **args)
    if name == "create_edge":
        return await _create_edge(client, **args)
    if name == "archive_object":
        return await _archive_object(client, **args)
    if name == "ingest_url":
        return await _ingest_url(client, **args)
    if name == "ingest_file":
        return await _ingest_file(client, **args)
    raise ValueError(f"Unknown tool: {name}")


async def _search_objects(
    client: KosApiClient,
    query: str,
    kind: str | None = None,
    limit: int = 10,
) -> list[dict]:
    raw = await client.keyword_search(q=query, kind=kind, limit=limit)
    items = raw if isinstance(raw, list) else raw.get("items", raw.get("results", []))
    compact = []
    for item in items:
        compact.append(
            redact_dict(
                {
                    "id": item.get("id"),
                    "kind": item.get("kind"),
                    "title": item.get("title"),
                    "snippet": item.get("snippet") or item.get("description"),
                    "tags": item.get("tags"),
                    "updated_at": item.get("updated_at"),
                    "score": item.get("score"),
                    "embeddings_used": False,
                }
            )
        )
    return compact


async def _hybrid_search(
    client: KosApiClient,
    query: str,
    kind: str | None = None,
    limit: int = 10,
) -> dict:
    try:
        raw = await client.hybrid_search(query=query, kind=kind, limit=limit)
        embeddings_used = raw.get("embeddings_used", True) if isinstance(raw, dict) else True
        items = raw if isinstance(raw, list) else raw.get("items", raw.get("results", []))
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 503:
            # Embeddings disabled — fall back to keyword
            raw = await client.keyword_search(q=query, kind=kind, limit=limit)
            items = raw if isinstance(raw, list) else raw.get("items", raw.get("results", []))
            compact = [
                redact_dict(
                    {
                        "id": it.get("id"),
                        "kind": it.get("kind"),
                        "title": it.get("title"),
                        "snippet": it.get("snippet") or it.get("description"),
                        "tags": it.get("tags"),
                        "updated_at": it.get("updated_at"),
                        "score": it.get("score"),
                    }
                )
                for it in items
            ]
            return {
                "results": compact,
                "embeddings_used": False,
                "warning": "embeddings_disabled, fell back to keyword search",
            }
        raise

    compact = [
        redact_dict(
            {
                "id": it.get("id"),
                "kind": it.get("kind"),
                "title": it.get("title"),
                "snippet": it.get("snippet") or it.get("description"),
                "tags": it.get("tags"),
                "updated_at": it.get("updated_at"),
                "score": it.get("score"),
            }
        )
        for it in items
    ]
    return {"results": compact, "embeddings_used": embeddings_used}


async def _get_object(client: KosApiClient, object_id: str) -> dict:
    raw = await client.get_object(object_id)
    return redact_dict(
        {
            "id": raw.get("id"),
            "kind": raw.get("kind"),
            "title": raw.get("title"),
            "description": raw.get("description"),
            "tags": raw.get("tags"),
            "metadata": raw.get("metadata"),
            "is_pinned": raw.get("is_pinned"),
            "is_archived": raw.get("is_archived"),
            "created_at": raw.get("created_at"),
            "updated_at": raw.get("updated_at"),
        }
    )


async def _get_page(
    client: KosApiClient,
    page_id: str,
    include_json: bool = False,
) -> dict:
    raw = await client.get_page(page_id)
    content_text = raw.get("content_text") or ""
    truncated = len(content_text) > _PAGE_TEXT_LIMIT
    result: dict = redact_dict(
        {
            "id": raw.get("id"),
            "title": raw.get("title"),
            "content_text": content_text[:_PAGE_TEXT_LIMIT],
            "truncated": truncated,
            "word_count": raw.get("word_count"),
            "version": raw.get("version"),
            "tags": raw.get("tags"),
            "metadata": raw.get("metadata"),
            "created_at": raw.get("created_at"),
            "updated_at": raw.get("updated_at"),
        }
    )
    if include_json:
        result["content_json"] = raw.get("content_json")
    return result


async def _get_source(
    client: KosApiClient,
    source_id: str,
    include_text: bool = True,
    max_chars: int = _SOURCE_TEXT_DEFAULT_LIMIT,
) -> dict:
    raw = await client.get_source(source_id)
    result = redact_dict(
        {
            "id": raw.get("id"),
            "kind": raw.get("kind"),
            "title": raw.get("title"),
            "description": raw.get("description"),
            "tags": raw.get("tags"),
            "source_type": raw.get("source_type"),
            "url": raw.get("url"),
            "ingestion_status": raw.get("ingestion_status"),
            "page_count": raw.get("page_count"),
            "thumbnail_path": raw.get("thumbnail_path"),
            "preview_data": raw.get("preview_data"),
            "created_at": raw.get("created_at"),
            "updated_at": raw.get("updated_at"),
        }
    )
    if include_text:
        text = raw.get("extracted_text") or ""
        result["extracted_text"] = text[:max_chars]
        result["text_truncated"] = len(text) > max_chars
    return result


async def _answer_from_kb(
    client: KosApiClient,
    question: str,
    kind: str | None = None,
    limit: int = 10,
) -> dict:
    try:
        data = await client.answer_from_kb(q=question, kind=kind, limit=int(limit))
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 503:
            return {
                "error": "ai_disabled",
                "message": "Server has no OPENAI_API_KEY configured.",
            }
        raise
    return redact_dict(
        {
            "answer": data.get("answer"),
            "citations": data.get("citations"),
            "context_count": data.get("context_count"),
            "agent_run_id": data.get("agent_run_id"),
        }
    )


async def _get_related_objects(
    client: KosApiClient,
    object_id: str,
    depth: int = 1,
    limit: int = 20,
    direction: str = "both",
    edge_types: list[str] | None = None,
) -> list[dict]:
    raw = await client.get_related_objects(
        object_id=object_id,
        depth=depth,
        edge_types=edge_types,
        direction=direction,
        limit=limit,
    )
    items = raw if isinstance(raw, list) else raw.get("items", raw.get("results", []))
    return [
        redact_dict(
            {
                "id": it.get("id"),
                "kind": it.get("kind"),
                "title": it.get("title"),
                "direction": it.get("direction"),
                "edge_kind": it.get("edge_kind") or it.get("edge_type"),
                "depth": it.get("depth"),
            }
        )
        for it in items
    ]


# ---------------------------------------------------------------------------
# Write tool handlers (Phase 7B)
# ---------------------------------------------------------------------------

def _validate_url_safe(url: str) -> None:
    """Lightweight SSRF guard applied before sending URLs to the API."""
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise ValueError(
            f"URL scheme '{scheme}' is not allowed. Only http:// and https:// are accepted."
        )
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise ValueError("URL has no hostname.")
    if host in _BLOCKED_HOSTNAMES:
        raise ValueError(f"Host '{host}' is blocked (SSRF policy).")
    # Reject literal link-local / loopback IP addresses
    try:
        addr = ipaddress.ip_address(host)
        if addr.is_loopback or addr.is_link_local or addr.is_private:
            raise ValueError(f"IP address '{host}' is not globally routable.")
    except ValueError as exc:
        if "is blocked" in str(exc) or "is not globally" in str(exc) or "not allowed" in str(exc):
            raise
        # Not an IP address — hostname is fine


async def _create_page(
    client: KosApiClient,
    title: str,
    content_text: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    if not title or not title.strip():
        raise ValueError("'title' is required and must not be empty.")
    data = await client.create_page(
        title=title.strip(),
        content_text=content_text,
        tags=tags,
    )
    obj = data.get("object", data)
    return redact_dict({
        "id": obj.get("id"),
        "kind": obj.get("kind", "page"),
        "title": obj.get("title"),
        "created_at": obj.get("created_at"),
    })


async def _update_page(
    client: KosApiClient,
    page_id: str,
    title: str | None = None,
    content_text: str | None = None,
    tags: list[str] | None = None,
    expected_version: int | None = None,
) -> dict:
    try:
        data = await client.update_page(
            page_id=page_id,
            title=title,
            content_text=content_text,
            tags=tags,
            expected_version=expected_version,
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 409:
            return {
                "error": "version_conflict",
                "message": (
                    "Page was modified by another writer. "
                    "Re-fetch the page and retry with the updated expected_version."
                ),
            }
        raise
    return redact_dict({
        "id": data.get("id"),
        "version": data.get("version"),
        "updated_at": data.get("updated_at"),
    })


async def _create_edge(
    client: KosApiClient,
    source_id: str,
    target_id: str,
    kind: str,
    weight: float | None = None,
    metadata: dict | None = None,
) -> dict:
    if kind not in _VALID_EDGE_KINDS:
        raise ValueError(
            f"Unknown edge kind '{kind}'. Valid kinds: {sorted(_VALID_EDGE_KINDS)}"
        )
    data = await client.create_edge(
        source_id=source_id,
        target_id=target_id,
        kind=kind,
        weight=weight,
        metadata=metadata,
    )
    return redact_dict({
        "id": data.get("id"),
        "source_id": data.get("source_id"),
        "target_id": data.get("target_id"),
        "kind": data.get("kind"),
    })


async def _archive_object(
    client: KosApiClient,
    object_id: str,
    reason: str | None = None,
) -> dict:
    data = await client.archive_object(object_id=object_id, reason=reason)
    return redact_dict({
        "id": data.get("id"),
        "is_archived": data.get("is_archived"),
        "updated_at": data.get("updated_at"),
    })


async def _ingest_url(
    client: KosApiClient,
    url: str,
    source_type: str | None = None,
    title: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    _validate_url_safe(url)
    data = await client.ingest_url(
        url=url,
        source_type=source_type,
        title=title,
        tags=tags,
    )
    return redact_dict({
        "id": data.get("id"),
        "ingestion_status": data.get("ingestion_status", "pending"),
        "url": data.get("url"),
    })


async def _ingest_file(
    client: KosApiClient,
    file_path: str,
    source_type: str | None = None,
    title: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    # Client-side path safety guard (belt-and-suspenders; API enforces it too)
    resolved = Path(file_path).resolve()
    if not resolved.exists():
        raise ValueError(f"File not found: '{file_path}'")
    if not resolved.is_file():
        raise ValueError(f"Path is not a file: '{file_path}'")

    data = await client.ingest_file(
        file_path=str(resolved),
        source_type=source_type,
        title=title,
        tags=tags,
    )
    return redact_dict({
        "id": data.get("id"),
        "ingestion_status": data.get("ingestion_status", "pending"),
        "file_path": str(resolved),
    })
