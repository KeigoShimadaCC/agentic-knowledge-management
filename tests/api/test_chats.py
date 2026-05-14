from pathlib import Path

import pytest
from app.services.chunk_service import chunk_object
from httpx import AsyncClient

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "chats"


@pytest.fixture(autouse=True)
def stub_reindex(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []
    monkeypatch.setattr(
        "app.services.reindex_service.enqueue_reindex_object",
        lambda object_id: calls.append(str(object_id)) or True,
    )
    return calls


async def _import_plain(auth_client: AsyncClient, title: str = "Plain chat") -> dict:
    resp = await auth_client.post(
        "/api/v1/chats/import",
        json={
            "title": title,
            "provider": "plain_text",
            "raw_format": "txt",
            "content": "User: hello searchablechatmarker\nAssistant: stored response",
        },
    )
    assert resp.status_code == 201
    return resp.json()["imported"][0]


@pytest.mark.asyncio
async def test_paste_plain_text_transcript_import(
    auth_client: AsyncClient, stub_reindex: list[str]
):
    chat = await _import_plain(auth_client)

    assert chat["kind"] == "chat"
    assert chat["provider"] == "plain_text"
    assert chat["turn_count"] == 2
    assert chat["raw_storage_path"].startswith("chats/plain_text/")
    assert stub_reindex == [chat["id"]]


@pytest.mark.asyncio
async def test_upload_markdown_transcript_import(auth_client: AsyncClient):
    resp = await auth_client.post(
        "/api/v1/chats/import",
        files={
            "file": (
                "claude_sample.md",
                FIXTURES.joinpath("claude_sample.md").read_bytes(),
                "text/markdown",
            )
        },
        data={"provider": "claude"},
    )

    assert resp.status_code == 201
    chat = resp.json()["imported"][0]
    assert chat["provider"] == "claude"
    assert chat["raw_format"] == "md"
    assert [turn["role"] for turn in chat["parsed_turns"]] == ["user", "assistant"]


@pytest.mark.asyncio
async def test_upload_chatgpt_multi_conversation_json(auth_client: AsyncClient):
    resp = await auth_client.post(
        "/api/v1/chats/import",
        files={
            "file": (
                "conversations.json",
                FIXTURES.joinpath("chatgpt_sample.json").read_bytes(),
                "application/json",
            )
        },
        data={"provider": "auto"},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["total"] == 2
    assert {chat["external_chat_id"] for chat in data["imported"]} == {"conv-alpha", "conv-beta"}
    assert all(chat["metadata"]["batch_raw_storage_path"] for chat in data["imported"])


@pytest.mark.asyncio
async def test_malformed_json_returns_422(auth_client: AsyncClient):
    resp = await auth_client.post(
        "/api/v1/chats/import",
        json={"content": "{bad json", "provider": "chatgpt", "raw_format": "json"},
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_chats(auth_client: AsyncClient):
    created = await _import_plain(auth_client, title="Listable chat")
    resp = await auth_client.get("/api/v1/chats")

    assert resp.status_code == 200
    assert created["id"] in {chat["id"] for chat in resp.json()}


@pytest.mark.asyncio
async def test_get_chat_detail(auth_client: AsyncClient):
    created = await _import_plain(auth_client, title="Detail chat")
    resp = await auth_client.get(f"/api/v1/chats/{created['id']}")

    assert resp.status_code == 200
    assert resp.json()["title"] == "Detail chat"


@pytest.mark.asyncio
async def test_get_raw_chat(auth_client: AsyncClient):
    created = await _import_plain(auth_client)
    resp = await auth_client.get(f"/api/v1/chats/{created['id']}/raw")

    assert resp.status_code == 200
    assert "searchablechatmarker" in resp.text


@pytest.mark.asyncio
async def test_soft_delete_chat(auth_client: AsyncClient):
    created = await _import_plain(auth_client)
    resp = await auth_client.delete(f"/api/v1/chats/{created['id']}")

    assert resp.status_code == 200
    assert resp.json()["deleted_at"] is not None
    get_resp = await auth_client.get(f"/api/v1/chats/{created['id']}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_restore_chat(auth_client: AsyncClient, stub_reindex: list[str]):
    created = await _import_plain(auth_client)
    await auth_client.delete(f"/api/v1/chats/{created['id']}")

    resp = await auth_client.post(f"/api/v1/chats/{created['id']}/restore")

    assert resp.status_code == 200
    assert resp.json()["deleted_at"] is None
    assert stub_reindex[-1] == created["id"]


@pytest.mark.asyncio
async def test_reindex_chat_endpoint(auth_client: AsyncClient, stub_reindex: list[str]):
    created = await _import_plain(auth_client)
    resp = await auth_client.post(f"/api/v1/chats/{created['id']}/reindex")

    assert resp.status_code == 200
    assert stub_reindex[-1] == created["id"]


@pytest.mark.asyncio
async def test_chunk_service_chunks_chat_content(auth_client: AsyncClient):
    created = await _import_plain(auth_client)

    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        chunks = await chunk_object(db, created["id"])

    assert chunks
    assert "searchablechatmarker" in chunks[0].content


@pytest.mark.asyncio
async def test_keyword_search_finds_imported_chat(auth_client: AsyncClient):
    created = await _import_plain(auth_client)
    resp = await auth_client.get(
        "/api/v1/search/keyword",
        params={"q": "searchablechatmarker", "kind": "chat"},
    )

    assert resp.status_code == 200
    assert created["id"] in {result["id"] for result in resp.json()["results"]}


@pytest.mark.asyncio
async def test_deleted_chat_excluded_from_search(auth_client: AsyncClient):
    created = await _import_plain(auth_client)
    await auth_client.delete(f"/api/v1/chats/{created['id']}")

    resp = await auth_client.get(
        "/api/v1/search/keyword",
        params={"q": "searchablechatmarker", "kind": "chat"},
    )

    assert resp.status_code == 200
    assert created["id"] not in {result["id"] for result in resp.json()["results"]}


@pytest.mark.asyncio
async def test_cross_user_chat_access_returns_404(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "one@test.com", "password": "password123", "display_name": "One"},
    )
    created = await _import_plain(client)
    await client.post("/api/v1/auth/logout")
    await client.post(
        "/api/v1/auth/register",
        json={"email": "two@test.com", "password": "password123", "display_name": "Two"},
    )

    resp = await client.get(f"/api/v1/chats/{created['id']}")

    assert resp.status_code == 404
