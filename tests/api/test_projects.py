"""Integration tests for Phase 9A project (career memory) API."""

from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_project_minimal(auth_client: AsyncClient):
    resp = await auth_client.post("/api/v1/projects", json={"title": "Minimal"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Minimal"
    assert data["confidence"] == "manual"
    assert data["id"]
    assert data["skills"] == []
    obj = await auth_client.get(f"/api/v1/objects/{data['id']}")
    assert obj.status_code == 200
    assert obj.json()["kind"] == "project"


@pytest.mark.asyncio
async def test_create_project_full(auth_client: AsyncClient):
    body = {
        "title": "Full Project",
        "description": "Desc",
        "period_start": "2020-01-15",
        "period_end": "2021-06-01",
        "role": "Lead",
        "organization": "Acme",
        "problem": "Scaling",
        "actions": "Built infra",
        "results": "99% uptime",
        "metrics": {"users": 100, "ok": True},
        "skills": ["rust", "postgres"],
        "status": "completed",
        "tags": ["work", "infra"],
    }
    resp = await auth_client.post("/api/v1/projects", json=body)
    assert resp.status_code == 201
    d = resp.json()
    assert d["title"] == body["title"]
    assert d["description"] == body["description"]
    assert d["period_start"] == body["period_start"]
    assert d["period_end"] == body["period_end"]
    assert d["role"] == body["role"]
    assert d["organization"] == body["organization"]
    assert d["problem"] == body["problem"]
    assert d["actions"] == body["actions"]
    assert d["results"] == body["results"]
    assert d["metrics"] == body["metrics"]
    assert d["skills"] == ["rust", "postgres"]
    assert d["status"] == "completed"
    assert set(d["tags"]) >= {"work", "infra"}


@pytest.mark.asyncio
async def test_create_project_period_validation(auth_client: AsyncClient):
    resp = await auth_client.post(
        "/api/v1/projects",
        json={
            "title": "Bad",
            "period_start": "2022-01-01",
            "period_end": "2021-01-01",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_project_skill_normalization(auth_client: AsyncClient):
    resp = await auth_client.post(
        "/api/v1/projects",
        json={"title": "Skills", "skills": ["Python", " python ", "FASTAPI", "python"]},
    )
    assert resp.status_code == 201
    assert resp.json()["skills"] == ["python", "fastapi"]


@pytest.mark.asyncio
async def test_get_project(auth_client: AsyncClient):
    created = await auth_client.post("/api/v1/projects", json={"title": "G1"})
    assert created.status_code == 201
    pid = created.json()["id"]
    resp = await auth_client.get(f"/api/v1/projects/{pid}")
    assert resp.status_code == 200
    d = resp.json()
    assert d["id"] == pid
    assert d["title"] == "G1"


@pytest.mark.asyncio
async def test_get_project_404_when_other_user_owns_it(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "pa@test.com", "password": "password123", "display_name": "A"},
    )
    r = await client.post("/api/v1/projects", json={"title": "Owned by A"})
    assert r.status_code == 201
    pid = r.json()["id"]

    await client.post(
        "/api/v1/auth/register",
        json={"email": "pb@test.com", "password": "password123", "display_name": "B"},
    )
    r2 = await client.get(f"/api/v1/projects/{pid}")
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_list_projects_pagination(auth_client: AsyncClient):
    for i in range(5):
        r = await auth_client.post("/api/v1/projects", json={"title": f"P{i}"})
        assert r.status_code == 201
    resp = await auth_client.get("/api/v1/projects?limit=2&offset=2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_projects_filter_by_status(auth_client: AsyncClient):
    await auth_client.post(
        "/api/v1/projects",
        json={"title": "Active1", "status": "active"},
    )
    r2 = await auth_client.post(
        "/api/v1/projects",
        json={"title": "Done1", "status": "completed"},
    )
    assert r2.status_code == 201
    resp = await auth_client.get("/api/v1/projects?status=completed")
    assert resp.status_code == 200
    titles = {x["title"] for x in resp.json()["items"]}
    assert "Done1" in titles
    assert all(x["status"] == "completed" for x in resp.json()["items"])


@pytest.mark.asyncio
async def test_list_projects_filter_by_skill(auth_client: AsyncClient):
    await auth_client.post(
        "/api/v1/projects",
        json={"title": "HasPy", "skills": ["python", "django"]},
    )
    await auth_client.post(
        "/api/v1/projects",
        json={"title": "NoPy", "skills": ["rust"]},
    )
    resp = await auth_client.get("/api/v1/projects?skill=python")
    assert resp.status_code == 200
    titles = {x["title"] for x in resp.json()["items"]}
    assert "HasPy" in titles
    assert "NoPy" not in titles


@pytest.mark.asyncio
async def test_update_project(auth_client: AsyncClient):
    r = await auth_client.post("/api/v1/projects", json={"title": "Before", "problem": "old"})
    assert r.status_code == 201
    pid = r.json()["id"]
    u0 = r.json()["updated_at"]
    await asyncio.sleep(0.02)
    patch = await auth_client.patch(
        f"/api/v1/projects/{pid}",
        json={"title": "After", "problem": None},
    )
    assert patch.status_code == 200
    d = patch.json()
    assert d["title"] == "After"
    assert d["problem"] is None
    assert d["updated_at"] != u0


@pytest.mark.asyncio
async def test_soft_delete_project(auth_client: AsyncClient):
    r = await auth_client.post("/api/v1/projects", json={"title": "DelMe"})
    assert r.status_code == 201
    pid = r.json()["id"]
    d1 = await auth_client.delete(f"/api/v1/projects/{pid}")
    assert d1.status_code == 204
    g = await auth_client.get(f"/api/v1/projects/{pid}")
    assert g.status_code == 404
    listed = await auth_client.get("/api/v1/projects?include_archived=true")
    assert listed.status_code == 200
    row = next(x for x in listed.json()["items"] if x["id"] == pid)
    assert row["deleted_at"] is not None


@pytest.mark.asyncio
async def test_restore_project_via_existing_objects_endpoint(auth_client: AsyncClient):
    r = await auth_client.post("/api/v1/projects", json={"title": "RestoreMe"})
    assert r.status_code == 201
    pid = r.json()["id"]
    await auth_client.delete(f"/api/v1/projects/{pid}")
    rest = await auth_client.post(f"/api/v1/objects/{pid}/restore")
    assert rest.status_code == 200
    g = await auth_client.get(f"/api/v1/projects/{pid}")
    assert g.status_code == 200
    assert g.json()["title"] == "RestoreMe"
