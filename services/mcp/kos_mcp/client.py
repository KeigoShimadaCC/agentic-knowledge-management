from __future__ import annotations

import httpx

from .config import McpSettings


class KosApiClient:
    """Async HTTP client for KnowledgeOS API. Used by MCP tools."""

    def __init__(self, settings: McpSettings) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.mcp_api_base_url,
            headers={"X-KOS-Internal-Token": settings.mcp_internal_token},
            timeout=30.0,
        )

    async def keyword_search(
        self,
        q: str,
        kind: str | None = None,
        limit: int = 10,
    ) -> dict:
        params: dict = {"q": q, "limit": limit}
        if kind:
            params["kind"] = kind
        r = await self._client.get("/api/v1/search/keyword", params=params)
        r.raise_for_status()
        return r.json()

    async def hybrid_search(
        self,
        query: str,
        kind: str | None = None,
        limit: int = 10,
    ) -> dict:
        body: dict = {"query": query, "limit": limit}
        if kind:
            body["kind"] = kind
        r = await self._client.post("/api/v1/search/hybrid", json=body)
        r.raise_for_status()
        return r.json()

    async def get_object(self, object_id: str) -> dict:
        r = await self._client.get(f"/api/v1/objects/{object_id}")
        r.raise_for_status()
        return r.json()

    async def get_page(self, page_id: str) -> dict:
        r = await self._client.get(f"/api/v1/pages/{page_id}")
        r.raise_for_status()
        return r.json()

    async def get_source(self, source_id: str) -> dict:
        r = await self._client.get(f"/api/v1/sources/{source_id}")
        r.raise_for_status()
        return r.json()

    async def get_related_objects(
        self,
        object_id: str,
        depth: int = 1,
        edge_types: list[str] | None = None,
        direction: str = "both",
        limit: int = 20,
    ) -> list[dict]:
        params: dict = {
            "depth": min(depth, 2),
            "direction": direction,
            "limit": min(limit, 50),
        }
        if edge_types:
            params["edge_types"] = edge_types
        r = await self._client.get(
            f"/api/v1/objects/{object_id}/related", params=params
        )
        r.raise_for_status()
        return r.json()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> KosApiClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()
