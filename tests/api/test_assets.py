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
async def test_413_writes_no_asset_row_and_no_library_file(
    auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    """Belt-and-suspenders check: the 413 path must not create an Asset row,
    a KosObject row, or a file under the library root before bailing.
    """
    from sqlalchemy import func, select

    from app.config import settings
    from app.core.library import get_library_root
    from app.db.session import AsyncSessionLocal
    from app.models.asset import Asset

    monkeypatch.setattr(settings, "asset_upload_max_bytes", 1024)

    async with AsyncSessionLocal() as db:
        before_assets = (await db.execute(select(func.count(Asset.id)))).scalar_one()

    lib_root = get_library_root()
    files_before = sum(1 for _ in lib_root.rglob("*") if _.is_file())

    oversize = b"z" * 4096
    resp = await auth_client.post(
        "/api/v1/assets/upload",
        files={"file": ("nope.bin", oversize, "application/octet-stream")},
    )
    assert resp.status_code == 413

    async with AsyncSessionLocal() as db:
        after_assets = (await db.execute(select(func.count(Asset.id)))).scalar_one()
    files_after = sum(1 for _ in lib_root.rglob("*") if _.is_file())

    assert after_assets == before_assets, "413 must not create an Asset row"
    assert files_after == files_before, "413 must not write a file to the library"


@pytest.mark.asyncio
async def test_soft_deleted_asset_get_download_and_delete_return_404(
    auth_client: AsyncClient,
):
    """After soft-delete, GET /assets/{id}, /download, and DELETE all return 404.
    Defense-in-depth: asset_service.get_asset_or_404 already filtered deleted_at,
    but the DELETE handler reaches through object_service.get_object_or_404 which
    PHASE-FIX-04 S7 tightened.
    """
    up = await auth_client.post(
        "/api/v1/assets/upload",
        files={"file": ("doc.txt", b"hello", "text/plain")},
    )
    assert up.status_code == 201, up.text
    asset_id = up.json()["asset"]["id"]

    first_delete = await auth_client.delete(f"/api/v1/assets/{asset_id}")
    assert first_delete.status_code == 200, first_delete.text

    get_resp = await auth_client.get(f"/api/v1/assets/{asset_id}")
    assert get_resp.status_code == 404, get_resp.text

    dl_resp = await auth_client.get(f"/api/v1/assets/{asset_id}/download")
    assert dl_resp.status_code == 404, dl_resp.text

    second_delete = await auth_client.delete(f"/api/v1/assets/{asset_id}")
    assert second_delete.status_code == 404, second_delete.text


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
