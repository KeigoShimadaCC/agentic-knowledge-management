from __future__ import annotations

import uuid

import pytest
from app.db.session import AsyncSessionLocal
from app.models.agent_run import AgentRun
from app.models.chunk import Chunk
from app.models.edge import Edge
from app.models.object import KosObject
from app.services.chunk_service import chunk_object
from httpx import AsyncClient
from sqlalchemy import select


@pytest.fixture(autouse=True)
def stub_rate_limit_and_reindex(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    async def _allow(*args, **kwargs) -> bool:
        return True

    calls: list[str] = []
    monkeypatch.setattr("app.services.audited_write_service.check_and_increment", _allow)
    monkeypatch.setattr(
        "app.services.reindex_service.enqueue_reindex_object",
        lambda object_id: calls.append(str(object_id)) or True,
    )
    return calls


async def _create_project(auth_client: AsyncClient, title: str = "Career Project") -> dict:
    resp = await auth_client.post(
        "/api/v1/projects",
        json={
            "title": title,
            "problem": "Search was fragmented",
            "actions": "Built a retrieval workflow",
            "results": "Reduced lookup time",
            "skills": ["python"],
            "metrics": {"lookup_time_reduction": "40%"},
        },
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_evidence(auth_client: AsyncClient, title: str = "Evidence") -> dict:
    resp = await auth_client.post(
        "/api/v1/pages",
        json={"title": title, "content_text": f"{title} body"},
    )
    assert resp.status_code == 201
    return resp.json()["object"]


def _bullet_payload(evidence_ids: list[str] | None = None) -> dict:
    return {
        "target_role": "Staff Engineer",
        "emphasis": "search infrastructure",
        "count": 1,
        "bullets": [
            {
                "text": "Built a search workflow that reduced lookup time by 40%.",
                "evidence_object_ids": evidence_ids or [],
                "confidence": "high",
                "metrics_cited": ["40%"],
            }
        ],
        "prompt_version": "9b.1",
    }


def _story_payload(
    evidence_ids: list[str] | None = None, question_type: str = "behavioral"
) -> dict:
    return {
        "question_type": question_type,
        "target_role": "Staff Engineer",
        "max_words": 400,
        "word_count": 38,
        "story": {
            "situation": "Knowledge was split across tools.",
            "task": "Make the material searchable.",
            "action": "Built ingestion, chunking, and retrieval.",
            "result": "The team found project evidence faster.",
            "evidence_object_ids": evidence_ids or [],
        },
        "prompt_version": "9b.1",
    }


async def _edge_count(kind: str, source_id: str | None = None, target_id: str | None = None) -> int:
    async with AsyncSessionLocal() as db:
        stmt = select(Edge).where(Edge.kind == kind, Edge.deleted_at.is_(None))
        if source_id:
            stmt = stmt.where(Edge.source_id == uuid.UUID(source_id))
        if target_id:
            stmt = stmt.where(Edge.target_id == uuid.UUID(target_id))
        return len((await db.execute(stmt)).scalars().all())


async def _agent_run_count() -> int:
    async with AsyncSessionLocal() as db:
        return len((await db.execute(select(AgentRun))).scalars().all())


@pytest.mark.asyncio
async def test_save_resume_bullet_set_201(auth_client: AsyncClient):
    project = await _create_project(auth_client)
    evidence = await _create_evidence(auth_client)

    resp = await auth_client.post(
        f"/api/v1/projects/{project['id']}/resume-bullet-sets",
        json=_bullet_payload([evidence["id"]]),
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["project_id"] == project["id"]
    assert data["bullets"][0]["text"].startswith("Built a search workflow")
    assert await _agent_run_count() == 1
    assert (
        await _edge_count("belongs_to_project", source_id=data["id"], target_id=project["id"]) == 1
    )
    assert await _edge_count("cites", source_id=data["id"], target_id=evidence["id"]) == 1


@pytest.mark.asyncio
async def test_save_bullet_set_empty_evidence(auth_client: AsyncClient):
    project = await _create_project(auth_client)

    resp = await auth_client.post(
        f"/api/v1/projects/{project['id']}/resume-bullet-sets",
        json=_bullet_payload([]),
    )

    assert resp.status_code == 201
    assert await _edge_count("cites", source_id=resp.json()["id"]) == 0


@pytest.mark.asyncio
async def test_save_bullet_set_wrong_user_project(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "owner@test.com", "password": "password123", "display_name": "Owner"},
    )
    project = await _create_project(client)
    await client.post(
        "/api/v1/auth/register",
        json={"email": "other@test.com", "password": "password123", "display_name": "Other"},
    )

    resp = await client.post(
        f"/api/v1/projects/{project['id']}/resume-bullet-sets",
        json=_bullet_payload(),
    )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_save_bullet_set_deleted_project(auth_client: AsyncClient):
    project = await _create_project(auth_client)
    assert (await auth_client.delete(f"/api/v1/projects/{project['id']}")).status_code == 204

    resp = await auth_client.post(
        f"/api/v1/projects/{project['id']}/resume-bullet-sets",
        json=_bullet_payload(),
    )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_bullet_sets_paginated(auth_client: AsyncClient):
    project = await _create_project(auth_client)
    for i in range(3):
        payload = _bullet_payload()
        payload["emphasis"] = f"variant {i}"
        assert (
            await auth_client.post(
                f"/api/v1/projects/{project['id']}/resume-bullet-sets",
                json=payload,
            )
        ).status_code == 201

    resp = await auth_client.get(f"/api/v1/projects/{project['id']}/resume-bullet-sets?limit=2")

    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_get_bullet_set_ownership(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "a@test.com", "password": "password123", "display_name": "A"},
    )
    project = await _create_project(client)
    created = await client.post(
        f"/api/v1/projects/{project['id']}/resume-bullet-sets",
        json=_bullet_payload(),
    )
    assert created.status_code == 201
    await client.post(
        "/api/v1/auth/register",
        json={"email": "b@test.com", "password": "password123", "display_name": "B"},
    )

    resp = await client.get(f"/api/v1/resume-bullet-sets/{created.json()['id']}")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_bullet_set_soft(auth_client: AsyncClient):
    project = await _create_project(auth_client)
    created = await auth_client.post(
        f"/api/v1/projects/{project['id']}/resume-bullet-sets",
        json=_bullet_payload(),
    )
    bullet_set_id = created.json()["id"]

    resp = await auth_client.delete(f"/api/v1/resume-bullet-sets/{bullet_set_id}")
    get_resp = await auth_client.get(f"/api/v1/resume-bullet-sets/{bullet_set_id}")

    assert resp.status_code == 204
    assert get_resp.status_code == 404
    async with AsyncSessionLocal() as db:
        obj = await db.get(KosObject, uuid.UUID(bullet_set_id))
        assert obj is not None
        assert obj.deleted_at is not None


@pytest.mark.asyncio
async def test_restore_bullet_set(auth_client: AsyncClient):
    project = await _create_project(auth_client)
    created = await auth_client.post(
        f"/api/v1/projects/{project['id']}/resume-bullet-sets",
        json=_bullet_payload(),
    )
    bullet_set_id = created.json()["id"]
    assert (
        await auth_client.delete(f"/api/v1/resume-bullet-sets/{bullet_set_id}")
    ).status_code == 204

    restored = await auth_client.post(f"/api/v1/objects/{bullet_set_id}/restore")
    fetched = await auth_client.get(f"/api/v1/resume-bullet-sets/{bullet_set_id}")

    assert restored.status_code == 200
    assert fetched.status_code == 200


@pytest.mark.asyncio
async def test_save_interview_story_201(auth_client: AsyncClient):
    project = await _create_project(auth_client)
    evidence = await _create_evidence(auth_client)

    resp = await auth_client.post(
        f"/api/v1/projects/{project['id']}/interview-stories",
        json=_story_payload([evidence["id"]]),
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["project_id"] == project["id"]
    assert data["story"]["situation"].startswith("Knowledge")
    assert await _agent_run_count() == 1
    assert (
        await _edge_count("belongs_to_project", source_id=data["id"], target_id=project["id"]) == 1
    )
    assert await _edge_count("cites", source_id=data["id"], target_id=evidence["id"]) == 1


@pytest.mark.asyncio
async def test_list_stories_filter_question_type(auth_client: AsyncClient):
    project = await _create_project(auth_client)
    for question_type in ("behavioral", "behavioral", "technical"):
        assert (
            await auth_client.post(
                f"/api/v1/projects/{project['id']}/interview-stories",
                json=_story_payload(question_type=question_type),
            )
        ).status_code == 201

    resp = await auth_client.get(
        f"/api/v1/projects/{project['id']}/interview-stories?question_type=technical"
    )

    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["question_type"] == "technical"


@pytest.mark.asyncio
async def test_delete_interview_story_soft(auth_client: AsyncClient):
    project = await _create_project(auth_client)
    created = await auth_client.post(
        f"/api/v1/projects/{project['id']}/interview-stories",
        json=_story_payload(),
    )
    story_id = created.json()["id"]

    resp = await auth_client.delete(f"/api/v1/interview-stories/{story_id}")
    get_resp = await auth_client.get(f"/api/v1/interview-stories/{story_id}")

    assert resp.status_code == 204
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_bullet_set_appears_in_object_list(auth_client: AsyncClient):
    project = await _create_project(auth_client)
    created = await auth_client.post(
        f"/api/v1/projects/{project['id']}/resume-bullet-sets",
        json=_bullet_payload(),
    )

    resp = await auth_client.get("/api/v1/objects?kind=resume_bullet_set")

    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()["items"]}
    assert created.json()["id"] in ids


@pytest.mark.asyncio
async def test_bullet_set_chunks_created(auth_client: AsyncClient):
    project = await _create_project(auth_client)
    created = await auth_client.post(
        f"/api/v1/projects/{project['id']}/resume-bullet-sets",
        json=_bullet_payload(),
    )
    bullet_set_id = uuid.UUID(created.json()["id"])

    async with AsyncSessionLocal() as db:
        chunks = await chunk_object(db, bullet_set_id)
        stored = (
            (await db.execute(select(Chunk).where(Chunk.object_id == bullet_set_id)))
            .scalars()
            .all()
        )

    assert chunks
    assert stored
    assert "reduced lookup time" in stored[0].content


@pytest.mark.asyncio
async def test_story_chunks_created(auth_client: AsyncClient):
    project = await _create_project(auth_client)
    created = await auth_client.post(
        f"/api/v1/projects/{project['id']}/interview-stories",
        json=_story_payload(),
    )
    story_id = uuid.UUID(created.json()["id"])

    async with AsyncSessionLocal() as db:
        chunks = await chunk_object(db, story_id)
        stored = (
            (await db.execute(select(Chunk).where(Chunk.object_id == story_id))).scalars().all()
        )

    assert chunks
    assert stored
    assert "ingestion, chunking, and retrieval" in stored[0].content
