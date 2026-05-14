import uuid

import pytest
from httpx import AsyncClient


class NoopQueue:
    def __init__(self, *args, **kwargs):
        pass

    def enqueue(self, *args, **kwargs):
        return None


def stub_ingestion_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.source_service.Queue", NoopQueue)


async def create_source(
    auth_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    *,
    source_type: str = "web",
    url: str | None = "https://example.com",
    title: str = "",
) -> dict:
    stub_ingestion_queue(monkeypatch)
    body = {"source_type": source_type, "title": title}
    if url is not None:
        body["url"] = url
    resp = await auth_client.post("/api/v1/sources", json=body)
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_create_source_from_url(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    stub_ingestion_queue(monkeypatch)
    resp = await auth_client.post(
        "/api/v1/sources",
        json={"source_type": "web", "url": "https://example.com"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["source_type"] == "web"
    assert data["url"] == "https://example.com"
    assert data["ingestion_status"] == "pending"


@pytest.mark.asyncio
async def test_create_source_youtube(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    stub_ingestion_queue(monkeypatch)
    resp = await auth_client.post(
        "/api/v1/sources",
        json={"source_type": "youtube", "url": "https://youtu.be/dQw4w9WgXcQ"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["source_type"] == "youtube"
    assert data["url"] == "https://youtu.be/dQw4w9WgXcQ"


@pytest.mark.asyncio
async def test_create_source_file_requires_asset_id(auth_client: AsyncClient):
    resp = await auth_client.post("/api/v1/sources", json={"source_type": "pdf"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_source_url_requires_url(auth_client: AsyncClient):
    resp = await auth_client.post("/api/v1/sources", json={"source_type": "web"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_sources_empty(auth_client: AsyncClient):
    resp = await auth_client.get("/api/v1/sources")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_sources(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    await create_source(auth_client, monkeypatch, url="https://example.com/one")
    await create_source(auth_client, monkeypatch, url="https://example.com/two")
    resp = await auth_client.get("/api/v1/sources")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_list_sources_filter_by_type(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    await create_source(auth_client, monkeypatch, source_type="web", url="https://example.com")
    await create_source(
        auth_client,
        monkeypatch,
        source_type="youtube",
        url="https://youtu.be/dQw4w9WgXcQ",
    )
    resp = await auth_client.get("/api/v1/sources?source_type=web")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["source_type"] == "web"


@pytest.mark.asyncio
async def test_get_source(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    created = await create_source(
        auth_client,
        monkeypatch,
        url="https://example.com/source",
        title="Example Source",
    )
    resp = await auth_client.get(f"/api/v1/sources/{created['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == created["id"]
    assert data["user_id"] == created["user_id"]
    assert data["kind"] == "source"
    assert data["title"] == "Example Source"
    assert data["source_type"] == "web"
    assert data["url"] == "https://example.com/source"
    assert data["asset_id"] is None
    assert data["ingestion_status"] == "pending"
    assert data["deleted_at"] is None


@pytest.mark.asyncio
async def test_get_source_not_found(auth_client: AsyncClient):
    resp = await auth_client.get(f"/api/v1/sources/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_source(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    created = await create_source(auth_client, monkeypatch, title="Old Title")
    resp = await auth_client.patch(
        f"/api/v1/sources/{created['id']}",
        json={"title": "New Title"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New Title"


@pytest.mark.asyncio
async def test_delete_source(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    created = await create_source(auth_client, monkeypatch)
    resp = await auth_client.delete(f"/api/v1/sources/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["deleted_at"] is not None


@pytest.mark.asyncio
async def test_restore_source(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    created = await create_source(auth_client, monkeypatch)
    delete_resp = await auth_client.delete(f"/api/v1/sources/{created['id']}")
    assert delete_resp.status_code == 200

    resp = await auth_client.post(f"/api/v1/sources/{created['id']}/restore")
    assert resp.status_code == 200
    assert resp.json()["deleted_at"] is None


@pytest.mark.asyncio
async def test_get_deleted_source_404(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    created = await create_source(auth_client, monkeypatch)
    delete_resp = await auth_client.delete(f"/api/v1/sources/{created['id']}")
    assert delete_resp.status_code == 200

    resp = await auth_client.get(f"/api/v1/sources/{created['id']}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_source_text_not_found(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    created = await create_source(auth_client, monkeypatch)
    resp = await auth_client.get(f"/api/v1/sources/{created['id']}/text")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_source_thumbnail_not_found(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    created = await create_source(auth_client, monkeypatch)
    resp = await auth_client.get(f"/api/v1/sources/{created['id']}/thumbnail")
    assert resp.status_code == 404
