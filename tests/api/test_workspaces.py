"""Integration tests for Phase 8B workspace persistence API."""

from __future__ import annotations

import asyncio
from datetime import datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient


def _layout(*, first_id: str = "pane-1", second_id: str = "pane-2") -> dict:
    return {
        "version": 1,
        "split": "horizontal",
        "panes": [
            {"id": first_id, "size_pct": 50, "mode": "read"},
            {"id": second_id, "size_pct": 50, "mode": "read"},
        ],
        "active_pane_id": first_id,
    }


async def _create_workspace(
    client: AsyncClient, *, name: str = "Research", layout: dict | None = None
) -> dict:
    resp = await client.post(
        "/api/v1/workspaces",
        json={"name": name, "description": "Saved layout", "layout": layout or _layout()},
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_create_workspace_happy_path(auth_client: AsyncClient):
    data = await _create_workspace(auth_client)

    assert data["id"]
    assert data["name"] == "Research"
    assert data["description"] == "Saved layout"
    assert data["layout"]["version"] == 1
    assert len(data["layout"]["panes"]) == 2
    assert data["layout"]["active_pane_id"] == "pane-1"
    assert data["is_pinned"] is False
    assert data["deleted_at"] is None


@pytest.mark.asyncio
async def test_create_workspace_rejects_bad_size_sum(auth_client: AsyncClient):
    bad = _layout()
    bad["panes"][0]["size_pct"] = 35
    bad["panes"][1]["size_pct"] = 35

    resp = await auth_client.post("/api/v1/workspaces", json={"name": "Bad", "layout": bad})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_workspace_rejects_duplicate_pane_ids(auth_client: AsyncClient):
    resp = await auth_client.post(
        "/api/v1/workspaces",
        json={"name": "Bad", "layout": _layout(first_id="pane", second_id="pane")},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_workspace_rejects_five_panes(auth_client: AsyncClient):
    bad = {
        "version": 1,
        "split": "horizontal",
        "panes": [{"id": f"pane-{i}", "size_pct": 20} for i in range(5)],
        "active_pane_id": "pane-0",
    }

    resp = await auth_client.post("/api/v1/workspaces", json={"name": "Bad", "layout": bad})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_workspace_rejects_missing_active_pane(auth_client: AsyncClient):
    bad = _layout()
    bad["active_pane_id"] = "missing"

    resp = await auth_client.post("/api/v1/workspaces", json={"name": "Bad", "layout": bad})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_workspaces_returns_only_current_user_items(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "wa@test.com", "password": "password123", "display_name": "A"},
    )
    owned_by_a = await _create_workspace(client, name="A")

    await client.post(
        "/api/v1/auth/register",
        json={"email": "wb@test.com", "password": "password123", "display_name": "B"},
    )
    owned_by_b = await _create_workspace(client, name="B")

    resp = await client.get("/api/v1/workspaces")
    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()["items"]}
    assert owned_by_b["id"] in ids
    assert owned_by_a["id"] not in ids


@pytest.mark.asyncio
async def test_get_workspace_404_when_other_user_owns_it(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "wc@test.com", "password": "password123", "display_name": "C"},
    )
    workspace = await _create_workspace(client, name="Owned by C")

    await client.post(
        "/api/v1/auth/register",
        json={"email": "wd@test.com", "password": "password123", "display_name": "D"},
    )
    resp = await client.get(f"/api/v1/workspaces/{workspace['id']}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_workspace_updates_last_used_at(auth_client: AsyncClient):
    workspace = await _create_workspace(auth_client)
    assert workspace["last_used_at"] is None

    first = await auth_client.get(f"/api/v1/workspaces/{workspace['id']}")
    assert first.status_code == 200
    first_last_used = datetime.fromisoformat(first.json()["last_used_at"])

    await asyncio.sleep(0.02)
    second = await auth_client.get(f"/api/v1/workspaces/{workspace['id']}")
    assert second.status_code == 200
    second_last_used = datetime.fromisoformat(second.json()["last_used_at"])
    assert second_last_used > first_last_used


@pytest.mark.asyncio
async def test_patch_workspace_updates_name_without_touching_layout(auth_client: AsyncClient):
    workspace = await _create_workspace(auth_client, name="Before")
    original_layout = workspace["layout"]

    resp = await auth_client.patch(
        f"/api/v1/workspaces/{workspace['id']}",
        json={"name": "After"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "After"
    assert data["layout"] == original_layout


@pytest.mark.asyncio
async def test_patch_workspace_updates_layout_preserving_last_used(auth_client: AsyncClient):
    workspace = await _create_workspace(auth_client)
    viewed = await auth_client.get(f"/api/v1/workspaces/{workspace['id']}")
    assert viewed.status_code == 200
    last_used = viewed.json()["last_used_at"]

    new_layout = {
        "version": 1,
        "split": "vertical",
        "panes": [
            {"id": "pane-a", "object_kind": "page", "size_pct": 40},
            {"id": "pane-b", "object_kind": "source", "size_pct": 60},
        ],
        "active_pane_id": "pane-b",
    }
    patch = await auth_client.patch(
        f"/api/v1/workspaces/{workspace['id']}",
        json={"layout": new_layout, "is_pinned": True},
    )
    assert patch.status_code == 200
    data = patch.json()
    assert data["layout"]["split"] == "vertical"
    assert data["layout"]["active_pane_id"] == "pane-b"
    assert data["is_pinned"] is True
    assert data["last_used_at"] == last_used


@pytest.mark.asyncio
async def test_delete_workspace_soft_deletes_and_list_can_include_deleted(
    auth_client: AsyncClient,
):
    workspace = await _create_workspace(auth_client, name="Trash")
    delete = await auth_client.delete(f"/api/v1/workspaces/{workspace['id']}")
    assert delete.status_code == 204

    get_deleted = await auth_client.get(f"/api/v1/workspaces/{workspace['id']}")
    assert get_deleted.status_code == 404

    listed = await auth_client.get("/api/v1/workspaces?include_deleted=true")
    assert listed.status_code == 200
    row = next(item for item in listed.json()["items"] if item["id"] == workspace["id"])
    assert row["deleted_at"] is not None


@pytest.mark.asyncio
async def test_delete_workspace_is_idempotent(auth_client: AsyncClient):
    workspace = await _create_workspace(auth_client, name="Delete twice")

    first = await auth_client.delete(f"/api/v1/workspaces/{workspace['id']}")
    second = await auth_client.delete(f"/api/v1/workspaces/{workspace['id']}")
    assert first.status_code == 204
    assert second.status_code == 204


@pytest.mark.asyncio
async def test_restore_workspace_clears_deleted_at(auth_client: AsyncClient):
    workspace = await _create_workspace(auth_client, name="Restore")
    await auth_client.delete(f"/api/v1/workspaces/{workspace['id']}")

    restore = await auth_client.post(f"/api/v1/workspaces/{workspace['id']}/restore")
    assert restore.status_code == 200
    assert restore.json()["deleted_at"] is None

    get_restored = await auth_client.get(f"/api/v1/workspaces/{workspace['id']}")
    assert get_restored.status_code == 200
    assert get_restored.json()["name"] == "Restore"


@pytest.mark.asyncio
async def test_workspace_accepts_stale_object_reference(auth_client: AsyncClient):
    stale_id = str(uuid4())
    layout = _layout()
    layout["panes"][0]["object_id"] = stale_id
    layout["panes"][0]["object_kind"] = "page"

    resp = await auth_client.post(
        "/api/v1/workspaces",
        json={"name": "Stale ref", "layout": layout},
    )
    assert resp.status_code == 201
    assert resp.json()["layout"]["panes"][0]["object_id"] == stale_id
