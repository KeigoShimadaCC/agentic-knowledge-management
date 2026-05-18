import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_rejects_oversize_with_413(
    auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    from app.config import settings

    monkeypatch.setattr(settings, "asset_upload_max_bytes", 1024)
    oversize = b"x" * 2048
    resp = await auth_client.post(
        "/api/v1/assets/upload",
        files={"file": ("big.bin", oversize, "application/octet-stream")},
    )
    assert resp.status_code == 413
    assert "maximum size" in resp.text


@pytest.mark.asyncio
async def test_upload_at_limit_still_succeeds(
    auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    from app.config import settings

    monkeypatch.setattr(settings, "asset_upload_max_bytes", 1024)
    payload = b"y" * 1024
    resp = await auth_client.post(
        "/api/v1/assets/upload",
        files={"file": ("ok.bin", payload, "application/octet-stream")},
    )
    assert resp.status_code == 201, resp.text


@pytest.mark.asyncio
async def test_upload_asset_returns_sha256(auth_client: AsyncClient):
    content = b"hello world test file content"
    resp = await auth_client.post(
        "/api/v1/assets/upload",
        files={"file": ("test.txt", content, "text/plain")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "asset" in data
    assert "sha256" in data["asset"]
    assert len(data["asset"]["sha256"]) == 64


@pytest.mark.asyncio
async def test_upload_same_file_twice_returns_same_sha256(auth_client: AsyncClient):
    content = b"deduplicated file content xyz"
    resp1 = await auth_client.post(
        "/api/v1/assets/upload",
        files={"file": ("file1.txt", content, "text/plain")},
    )
    resp2 = await auth_client.post(
        "/api/v1/assets/upload",
        files={"file": ("file2.txt", content, "text/plain")},
    )
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert resp1.json()["asset"]["sha256"] == resp2.json()["asset"]["sha256"]


@pytest.mark.asyncio
async def test_download_asset_returns_bytes(auth_client: AsyncClient):
    content = b"downloadable content"
    upload = await auth_client.post(
        "/api/v1/assets/upload",
        files={"file": ("dl.txt", content, "text/plain")},
    )
    asset_id = upload.json()["asset"]["id"]
    resp = await auth_client.get(f"/api/v1/assets/{asset_id}/download")
    assert resp.status_code == 200
    assert resp.content == content
