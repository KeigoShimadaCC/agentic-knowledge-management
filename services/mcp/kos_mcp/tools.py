from __future__ import annotations

import json

import httpx
from mcp.server import Server
from mcp.types import TextContent, Tool

from .client import KosApiClient
from .config import McpSettings
from .redaction import redact_dict

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
                    "[UNAVAILABLE] KB Q&A with citations. Requires Phase 5 AI endpoint "
                    "which is not yet implemented."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["question"],
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

        try:
            result = await _dispatch(name, arguments, client)
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 404:
                return [TextContent(type="text", text=f"Not found (404).")]
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
        raise RuntimeError(
            "answer_from_kb is not available: Phase 5 AI assistant endpoint has not been "
            "implemented yet."
        )
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
