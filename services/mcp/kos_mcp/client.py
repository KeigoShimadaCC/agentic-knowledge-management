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

    async def answer_from_kb(
        self,
        q: str,
        kind: str | None = None,
        limit: int = 10,
    ) -> dict:
        body: dict = {"q": q, "limit": limit}
        if kind:
            body["kind"] = kind
        r = await self._client.post("/api/v1/ai/answer", json=body)
        r.raise_for_status()
        return r.json()

    # --- Write methods (Phase 7B) ---

    async def create_page(
        self,
        title: str,
        content_text: str | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        body: dict = {"title": title}
        if content_text is not None:
            body["content_text"] = content_text
        if tags:
            body["tags"] = tags
        r = await self._client.post("/api/v1/pages", json=body)
        r.raise_for_status()
        return r.json()

    async def update_page(
        self,
        page_id: str,
        title: str | None = None,
        content_text: str | None = None,
        tags: list[str] | None = None,
        expected_version: int | None = None,
    ) -> dict:
        body: dict = {}
        if title is not None:
            body["title"] = title
        if content_text is not None:
            body["content_text"] = content_text
        if tags is not None:
            body["tags"] = tags
        if expected_version is not None:
            body["expected_version"] = expected_version
        r = await self._client.patch(f"/api/v1/pages/{page_id}", json=body)
        r.raise_for_status()
        return r.json()

    async def create_edge(
        self,
        source_id: str,
        target_id: str,
        kind: str,
        weight: float | None = None,
        metadata: dict | None = None,
    ) -> dict:
        body: dict = {"source_id": source_id, "target_id": target_id, "kind": kind}
        if weight is not None:
            body["weight"] = weight
        if metadata is not None:
            body["metadata"] = metadata
        r = await self._client.post("/api/v1/edges", json=body)
        r.raise_for_status()
        return r.json()

    async def archive_object(self, object_id: str, reason: str | None = None) -> dict:
        body: dict = {}
        if reason is not None:
            body["reason"] = reason
        r = await self._client.post(f"/api/v1/objects/{object_id}/archive", json=body)
        r.raise_for_status()
        return r.json()

    async def ingest_url(
        self,
        url: str,
        source_type: str | None = None,
        title: str | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        body: dict = {"url": url}
        if source_type is not None:
            body["source_type"] = source_type
        if title is not None:
            body["title"] = title
        if tags:
            body["tags"] = tags
        r = await self._client.post("/api/v1/sources", json=body)
        r.raise_for_status()
        return r.json()

    async def ingest_file(
        self,
        file_path: str,
        source_type: str | None = None,
        title: str | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        from pathlib import Path

        path = Path(file_path)
        with path.open("rb") as fh:
            content = fh.read()

        # Step 1: upload binary to assets, create a linked source in one shot
        upload_resp = await self._client.post(
            "/api/v1/assets/upload",
            params={"create_source": "true"},
            files={"file": (path.name, content)},
        )
        upload_resp.raise_for_status()
        upload_data = upload_resp.json()

        # Step 2: if caller supplied title/tags/source_type, patch the source
        src_id = upload_data.get("source", {}).get("id")
        if src_id and (title or tags or source_type):
            patch: dict = {}
            if title:
                patch["title"] = title
            if tags:
                patch["tags"] = tags
            patch_resp = await self._client.patch(f"/api/v1/sources/{src_id}", json=patch)
            if patch_resp.is_success:
                return patch_resp.json()

        return upload_data.get("source", upload_data)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> KosApiClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()
