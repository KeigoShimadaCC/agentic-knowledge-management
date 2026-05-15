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

    # --- Career / Project methods (Phase 9D) ---

    async def get_project(self, project_id: str) -> dict:
        r = await self._client.get(f"/api/v1/projects/{project_id}")
        r.raise_for_status()
        return r.json()

    async def list_projects(
        self,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
        skill: str | None = None,
    ) -> dict:
        params: dict = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        if skill:
            params["skill"] = skill
        r = await self._client.get("/api/v1/projects", params=params)
        r.raise_for_status()
        return r.json()

    async def create_project(
        self,
        title: str,
        description: str | None = None,
        period_start: str | None = None,
        period_end: str | None = None,
        role: str | None = None,
        organization: str | None = None,
        problem: str | None = None,
        actions: str | None = None,
        results: str | None = None,
        metrics: dict | None = None,
        skills: list[str] | None = None,
        status: str | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        body: dict = {"title": title}
        for key, val in {
            "description": description,
            "period_start": period_start,
            "period_end": period_end,
            "role": role,
            "organization": organization,
            "problem": problem,
            "actions": actions,
            "results": results,
            "metrics": metrics,
            "skills": skills,
            "status": status,
            "tags": tags,
        }.items():
            if val is not None:
                body[key] = val
        r = await self._client.post("/api/v1/projects", json=body)
        r.raise_for_status()
        return r.json()

    async def update_project(
        self,
        project_id: str,
        title: str | None = None,
        description: str | None = None,
        period_start: str | None = None,
        period_end: str | None = None,
        role: str | None = None,
        organization: str | None = None,
        problem: str | None = None,
        actions: str | None = None,
        results: str | None = None,
        metrics: dict | None = None,
        skills: list[str] | None = None,
        status: str | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        body: dict = {}
        for key, val in {
            "title": title,
            "description": description,
            "period_start": period_start,
            "period_end": period_end,
            "role": role,
            "organization": organization,
            "problem": problem,
            "actions": actions,
            "results": results,
            "metrics": metrics,
            "skills": skills,
            "status": status,
            "tags": tags,
        }.items():
            if val is not None:
                body[key] = val
        r = await self._client.patch(f"/api/v1/projects/{project_id}", json=body)
        r.raise_for_status()
        return r.json()

    async def get_resume_bullet_set(self, bullet_set_id: str) -> dict:
        r = await self._client.get(f"/api/v1/resume-bullet-sets/{bullet_set_id}")
        r.raise_for_status()
        return r.json()

    async def list_resume_bullet_sets(
        self,
        project_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        params: dict = {"limit": limit, "offset": offset}
        r = await self._client.get(
            f"/api/v1/projects/{project_id}/resume-bullet-sets", params=params
        )
        r.raise_for_status()
        return r.json()

    async def save_resume_bullet_set(self, project_id: str, payload: dict) -> dict:
        r = await self._client.post(
            f"/api/v1/projects/{project_id}/resume-bullet-sets", json=payload
        )
        r.raise_for_status()
        return r.json()

    async def get_interview_story(self, story_id: str) -> dict:
        r = await self._client.get(f"/api/v1/interview-stories/{story_id}")
        r.raise_for_status()
        return r.json()

    async def list_interview_stories(
        self,
        project_id: str,
        question_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        params: dict = {"limit": limit, "offset": offset}
        if question_type:
            params["question_type"] = question_type
        r = await self._client.get(
            f"/api/v1/projects/{project_id}/interview-stories", params=params
        )
        r.raise_for_status()
        return r.json()

    async def save_interview_story(self, project_id: str, payload: dict) -> dict:
        r = await self._client.post(
            f"/api/v1/projects/{project_id}/interview-stories", json=payload
        )
        r.raise_for_status()
        return r.json()

    async def get_project_evidence(self, project_id: str, limit: int = 50) -> list[dict]:
        params: dict = {
            "direction": "incoming",
            "edge_types": ["belongs_to_project"],
            "limit": min(limit, 50),
        }
        r = await self._client.get(
            f"/api/v1/objects/{project_id}/related", params=params
        )
        r.raise_for_status()
        return r.json()

    async def delete_edge(self, edge_id: str) -> dict:
        r = await self._client.delete(f"/api/v1/edges/{edge_id}")
        r.raise_for_status()
        return r.json() if r.content else {}

    async def extract_project(
        self,
        source_id: str,
        create: bool = True,
        period_hint: list[str | None] | None = None,
    ) -> dict:
        body: dict = {"source_id": source_id, "create": create}
        if period_hint is not None:
            body["period_hint"] = period_hint
        r = await self._client.post("/api/v1/ai/extract-project", json=body)
        r.raise_for_status()
        return r.json()

    async def generate_resume_bullets(
        self,
        project_id: str,
        target_role: str | None = None,
        emphasis: str | None = None,
        count: int = 3,
        max_evidence_objects: int | None = None,
    ) -> dict:
        body: dict = {"project_id": project_id, "count": count}
        if target_role:
            body["target_role"] = target_role
        if emphasis:
            body["emphasis"] = emphasis
        if max_evidence_objects is not None:
            body["max_evidence_objects"] = max_evidence_objects
        r = await self._client.post("/api/v1/ai/generate-resume-bullets", json=body)
        r.raise_for_status()
        return r.json()

    async def generate_interview_story(
        self,
        project_id: str,
        question_type: str = "behavioral",
        target_role: str | None = None,
        max_words: int = 300,
        max_evidence_objects: int | None = None,
    ) -> dict:
        body: dict = {
            "project_id": project_id,
            "question_type": question_type,
            "max_words": max_words,
        }
        if target_role:
            body["target_role"] = target_role
        if max_evidence_objects is not None:
            body["max_evidence_objects"] = max_evidence_objects
        r = await self._client.post("/api/v1/ai/generate-interview-story", json=body)
        r.raise_for_status()
        return r.json()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> KosApiClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()
