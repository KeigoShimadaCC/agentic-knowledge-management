import pytest
from httpx import AsyncClient


async def create_object(auth_client: AsyncClient, *, title: str) -> dict:
    resp = await auth_client.post(
        "/api/v1/objects",
        json={"kind": "note", "title": title},
    )
    assert resp.status_code == 201
    return resp.json()


async def create_edge(
    auth_client: AsyncClient,
    *,
    source_id: str,
    target_id: str,
    kind: str = "cites",
) -> dict:
    resp = await auth_client.post(
        "/api/v1/edges",
        json={"source_id": source_id, "target_id": target_id, "kind": kind},
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_create_edge(auth_client: AsyncClient):
    source = await create_object(auth_client, title="Source")
    target = await create_object(auth_client, title="Target")

    resp = await auth_client.post(
        "/api/v1/edges",
        json={"source_id": source["id"], "target_id": target["id"], "kind": "cites"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["source_id"] == source["id"]
    assert data["target_id"] == target["id"]
    assert data["kind"] == "cites"
    assert data["deleted_at"] is None


@pytest.mark.asyncio
async def test_list_edges(auth_client: AsyncClient):
    source = await create_object(auth_client, title="Source")
    target = await create_object(auth_client, title="Target")
    edge = await create_edge(auth_client, source_id=source["id"], target_id=target["id"])

    resp = await auth_client.get(f"/api/v1/edges?source_id={source['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == edge["id"]


@pytest.mark.asyncio
async def test_create_edge_duplicate_idempotent(auth_client: AsyncClient):
    source = await create_object(auth_client, title="Source")
    target = await create_object(auth_client, title="Target")
    body = {"source_id": source["id"], "target_id": target["id"], "kind": "cites"}

    first = await auth_client.post("/api/v1/edges", json=body)
    second = await auth_client.post("/api/v1/edges", json=body)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]


@pytest.mark.asyncio
async def test_delete_edge(auth_client: AsyncClient):
    source = await create_object(auth_client, title="Source")
    target = await create_object(auth_client, title="Target")
    edge = await create_edge(auth_client, source_id=source["id"], target_id=target["id"])

    resp = await auth_client.delete(f"/api/v1/edges/{edge['id']}")
    assert resp.status_code in {200, 204}
    if resp.status_code == 200:
        assert resp.json()["deleted_at"] is not None


@pytest.mark.asyncio
async def test_list_edges_by_kind(auth_client: AsyncClient):
    source = await create_object(auth_client, title="Source")
    target_one = await create_object(auth_client, title="Target One")
    target_two = await create_object(auth_client, title="Target Two")
    cites = await create_edge(
        auth_client,
        source_id=source["id"],
        target_id=target_one["id"],
        kind="cites",
    )
    await create_edge(
        auth_client,
        source_id=source["id"],
        target_id=target_two["id"],
        kind="derives_from",
    )

    resp = await auth_client.get("/api/v1/edges?kind=cites")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == cites["id"]
    assert data[0]["kind"] == "cites"
