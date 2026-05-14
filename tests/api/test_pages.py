import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_page_creates_object_and_page(auth_client: AsyncClient):
    resp = await auth_client.post("/api/v1/pages", json={"title": "My Page"})
    assert resp.status_code == 201
    data = resp.json()
    assert "object" in data
    assert "page" in data
    assert data["object"]["kind"] == "page"
    assert data["object"]["title"] == "My Page"


@pytest.mark.asyncio
async def test_get_page_returns_content(auth_client: AsyncClient):
    create = await auth_client.post("/api/v1/pages", json={"title": "Get Page"})
    page_id = create.json()["page"]["id"]
    resp = await auth_client.get(f"/api/v1/pages/{page_id}")
    assert resp.status_code == 200
    assert "content_json" in resp.json()
    assert "word_count" in resp.json()


@pytest.mark.asyncio
async def test_patch_page_updates_title(auth_client: AsyncClient):
    create = await auth_client.post("/api/v1/pages", json={"title": "Old Title"})
    page_id = create.json()["page"]["id"]
    resp = await auth_client.patch(f"/api/v1/pages/{page_id}", json={"title": "New Title"})
    assert resp.status_code == 200

    # Verify via object endpoint
    obj_id = create.json()["object"]["id"]
    obj = await auth_client.get(f"/api/v1/objects/{obj_id}")
    assert obj.json()["title"] == "New Title"


@pytest.mark.asyncio
async def test_put_page_replaces_content(auth_client: AsyncClient):
    create = await auth_client.post("/api/v1/pages", json={"title": "Replace Test"})
    page_id = create.json()["page"]["id"]
    new_content = {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "hello"}]}]}
    resp = await auth_client.put(
        f"/api/v1/pages/{page_id}",
        json={"content_json": new_content, "content_text": "hello"},
    )
    assert resp.status_code == 200
    assert resp.json()["content_json"] == new_content
