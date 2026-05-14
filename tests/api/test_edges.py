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


@pytest.mark.asyncio
async def test_create_edge_rejects_unknown_kind(auth_client: AsyncClient):
    source = await create_object(auth_client, title="Source")
    target = await create_object(auth_client, title="Target")

    resp = await auth_client.post(
        "/api/v1/edges",
        json={"source_id": source["id"], "target_id": target["id"], "kind": "random"},
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_edge_rejects_cross_user_target(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "one@test.com", "password": "password123", "display_name": "One"},
    )
    first_user_object = await create_object(client, title="First user object")

    await client.post(
        "/api/v1/auth/register",
        json={"email": "two@test.com", "password": "password123", "display_name": "Two"},
    )
    second_user_object = await create_object(client, title="Second user object")

    resp = await client.post(
        "/api/v1/edges",
        json={
            "source_id": second_user_object["id"],
            "target_id": first_user_object["id"],
            "kind": "links_to",
        },
    )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_edge_rejects_deleted_target(auth_client: AsyncClient):
    source = await create_object(auth_client, title="Source")
    target = await create_object(auth_client, title="Target")
    delete_resp = await auth_client.delete(f"/api/v1/objects/{target['id']}")
    assert delete_resp.status_code == 200

    resp = await auth_client.post(
        "/api/v1/edges",
        json={"source_id": source["id"], "target_id": target["id"], "kind": "links_to"},
    )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_edge_restores_soft_deleted_duplicate(auth_client: AsyncClient):
    source = await create_object(auth_client, title="Source")
    target = await create_object(auth_client, title="Target")
    edge = await create_edge(
        auth_client,
        source_id=source["id"],
        target_id=target["id"],
        kind="links_to",
    )

    delete_resp = await auth_client.delete(f"/api/v1/edges/{edge['id']}")
    assert delete_resp.status_code == 200

    restore_resp = await auth_client.post(
        "/api/v1/edges",
        json={"source_id": source["id"], "target_id": target["id"], "kind": "links_to"},
    )

    assert restore_resp.status_code == 200
    assert restore_resp.json()["id"] == edge["id"]
    assert restore_resp.json()["deleted_at"] is None


@pytest.mark.asyncio
async def test_object_edges_include_direction_and_object_summaries(auth_client: AsyncClient):
    page = await create_object(auth_client, title="Page")
    source = await create_object(auth_client, title="Source")
    target = await create_object(auth_client, title="Target")
    incoming = await create_edge(
        auth_client,
        source_id=source["id"],
        target_id=page["id"],
        kind="cites",
    )
    outgoing = await create_edge(
        auth_client,
        source_id=page["id"],
        target_id=target["id"],
        kind="mentions",
    )

    resp = await auth_client.get(f"/api/v1/objects/{page['id']}/edges")

    assert resp.status_code == 200
    data = resp.json()
    by_id = {item["id"]: item for item in data}
    assert by_id[incoming["id"]]["direction"] == "incoming"
    assert by_id[incoming["id"]]["source"]["title"] == "Source"
    assert by_id[outgoing["id"]]["direction"] == "outgoing"
    assert by_id[outgoing["id"]]["target"]["title"] == "Target"


@pytest.mark.asyncio
async def test_backlinks_returns_incoming_edges(auth_client: AsyncClient):
    page = await create_object(auth_client, title="Literature Review")
    source = await create_object(auth_client, title="PDF Source")
    await create_edge(auth_client, source_id=page["id"], target_id=source["id"], kind="cites")

    resp = await auth_client.get(f"/api/v1/objects/{source['id']}/backlinks")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["kind"] == "cites"
    assert data[0]["direction"] == "incoming"
    assert data[0]["source"]["title"] == "Literature Review"


@pytest.mark.asyncio
async def test_related_objects_depth_one(auth_client: AsyncClient):
    seed = await create_object(auth_client, title="Seed")
    related = await create_object(auth_client, title="Related")
    unrelated = await create_object(auth_client, title="Unrelated")
    await create_edge(auth_client, source_id=seed["id"], target_id=related["id"], kind="related_to")

    resp = await auth_client.get(f"/api/v1/objects/{seed['id']}/related")

    assert resp.status_code == 200
    titles = [item["object"]["title"] for item in resp.json()]
    assert titles == ["Related"]
    assert unrelated["title"] not in titles


@pytest.mark.asyncio
async def test_related_objects_depth_two(auth_client: AsyncClient):
    seed = await create_object(auth_client, title="Seed")
    middle = await create_object(auth_client, title="Middle")
    second_hop = await create_object(auth_client, title="Second Hop")
    await create_edge(auth_client, source_id=seed["id"], target_id=middle["id"], kind="links_to")
    await create_edge(
        auth_client,
        source_id=middle["id"],
        target_id=second_hop["id"],
        kind="mentions",
    )

    resp = await auth_client.get(f"/api/v1/objects/{seed['id']}/related?depth=2")

    assert resp.status_code == 200
    by_title = {item["object"]["title"]: item for item in resp.json()}
    assert by_title["Middle"]["distance"] == 1
    assert by_title["Second Hop"]["distance"] == 2
