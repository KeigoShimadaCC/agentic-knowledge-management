import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_object(auth_client: AsyncClient):
    resp = await auth_client.post(
        "/api/v1/objects",
        json={"kind": "note", "title": "Test Note"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test Note"
    assert data["kind"] == "note"


@pytest.mark.asyncio
async def test_get_object(auth_client: AsyncClient):
    create = await auth_client.post("/api/v1/objects", json={"kind": "note", "title": "Get Me"})
    obj_id = create.json()["id"]
    resp = await auth_client.get(f"/api/v1/objects/{obj_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == obj_id


@pytest.mark.asyncio
async def test_list_objects_pagination(auth_client: AsyncClient):
    for i in range(3):
        await auth_client.post("/api/v1/objects", json={"kind": "note", "title": f"Note {i}"})
    resp = await auth_client.get("/api/v1/objects?limit=2&page=1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] >= 3


@pytest.mark.asyncio
async def test_list_objects_filtered_by_kind(auth_client: AsyncClient):
    await auth_client.post("/api/v1/objects", json={"kind": "note", "title": "A Note"})
    await auth_client.post("/api/v1/objects", json={"kind": "bookmark", "title": "A Bookmark"})
    resp = await auth_client.get("/api/v1/objects?kind=note")
    data = resp.json()
    assert all(item["kind"] == "note" for item in data["items"])


@pytest.mark.asyncio
async def test_patch_object(auth_client: AsyncClient):
    create = await auth_client.post("/api/v1/objects", json={"kind": "note", "title": "Old Title"})
    obj_id = create.json()["id"]
    resp = await auth_client.patch(f"/api/v1/objects/{obj_id}", json={"title": "New Title"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "New Title"


@pytest.mark.asyncio
async def test_soft_delete_object(auth_client: AsyncClient):
    create = await auth_client.post("/api/v1/objects", json={"kind": "note", "title": "Delete Me"})
    obj_id = create.json()["id"]
    resp = await auth_client.delete(f"/api/v1/objects/{obj_id}")
    assert resp.status_code == 200
    assert resp.json()["deleted_at"] is not None


@pytest.mark.asyncio
async def test_deleted_not_in_list(auth_client: AsyncClient):
    create = await auth_client.post("/api/v1/objects", json={"kind": "note", "title": "Gone"})
    obj_id = create.json()["id"]
    await auth_client.delete(f"/api/v1/objects/{obj_id}")
    resp = await auth_client.get("/api/v1/objects")
    ids = [item["id"] for item in resp.json()["items"]]
    assert obj_id not in ids


@pytest.mark.asyncio
async def test_get_trash(auth_client: AsyncClient):
    create = await auth_client.post("/api/v1/objects", json={"kind": "note", "title": "In Trash"})
    obj_id = create.json()["id"]
    await auth_client.delete(f"/api/v1/objects/{obj_id}")
    resp = await auth_client.get("/api/v1/objects/trash")
    ids = [item["id"] for item in resp.json()["items"]]
    assert obj_id in ids


@pytest.mark.asyncio
async def test_restore_object(auth_client: AsyncClient):
    create = await auth_client.post("/api/v1/objects", json={"kind": "note", "title": "Restore Me"})
    obj_id = create.json()["id"]
    await auth_client.delete(f"/api/v1/objects/{obj_id}")
    resp = await auth_client.post(f"/api/v1/objects/{obj_id}/restore")
    assert resp.status_code == 200
    assert resp.json()["deleted_at"] is None
