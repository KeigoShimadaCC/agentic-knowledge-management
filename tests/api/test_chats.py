import json
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from app.models.edge import Edge
from app.models.object import KosObject
from app.models.revision import ObjectRevision
from app.services.agent_run_service import create_agent_run, finish_agent_run
from app.services.chunk_service import chunk_object
from httpx import AsyncClient
from sqlalchemy import select

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


STRUCTURED_SUMMARY = {
    "title": "Structured planning chat",
    "summary": "The chat decides to ship a structured import flow.",
    "date_range": {"start": None, "end": None},
    "topics": ["structured import"],
    "key_decisions": [
        {
            "decision": "Use explicit apply before creating objects.",
            "rationale": "AI writes must be auditable.",
            "turn_refs": [1],
            "confidence": "high",
        }
    ],
    "open_questions": [
        {
            "question": "Should concepts become objects?",
            "turn_refs": [0],
            "status": "open",
            "confidence": "medium",
        }
    ],
    "action_items": [
        {
            "task": "Add mocked AI tests",
            "owner": "Keigo",
            "due_at": None,
            "turn_refs": [0],
            "confidence": "high",
        }
    ],
    "claims": [
        {
            "claim": "Keyword search works without embeddings.",
            "type": "fact",
            "turn_refs": [1],
            "confidence": "high",
        }
    ],
    "concepts": [
        {"name": "KnowledgeOS", "type": "product", "turn_refs": [0], "confidence": "high"}
    ],
    "suggested_links": [],
    "warnings": [],
}


def stub_structured_ai(monkeypatch: pytest.MonkeyPatch, payload: str | None = None) -> None:
    async def fake_call_ai(
        db,
        *,
        user_id,
        agent_type,
        messages,
        model=None,
        temperature=0.2,
        input_context=None,
    ):
        run = await create_agent_run(
            db,
            user_id=user_id,
            agent_type=agent_type,
            input_payload={"messages": messages, "context": input_context or {}},
            model=model,
        )
        await finish_agent_run(
            db,
            run,
            status="success",
            output={"text": payload or json.dumps(STRUCTURED_SUMMARY)},
        )
        return payload or json.dumps(STRUCTURED_SUMMARY), run

    monkeypatch.setattr("app.services.chat_structured_service.call_ai", fake_call_ai)


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


@pytest.mark.asyncio
async def test_structured_summary_preview_requires_auth(client: AsyncClient):
    resp = await client.post(f"/api/v1/chats/{uuid.uuid4()}/structured-summary")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_structured_summary_preview_returns_schema(
    auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    stub_structured_ai(monkeypatch)
    created = await _import_plain(auth_client)

    resp = await auth_client.post(f"/api/v1/chats/{created['id']}/structured-summary")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "previewed"
    assert data["structured_summary"]["claims"][0]["turn_refs"] == [1]


@pytest.mark.asyncio
async def test_structured_summary_ai_disabled_returns_clear_error(auth_client: AsyncClient):
    import app.ai.client as client_module

    created = await _import_plain(auth_client)

    fake_settings = SimpleNamespace(
        openai_api_key="",
        openai_chat_model="gpt-4o-mini",
        openai_max_tokens=2000,
    )
    with patch.object(client_module, "settings", fake_settings):
        resp = await auth_client.post(f"/api/v1/chats/{created['id']}/structured-summary")

    assert resp.status_code == 503
    assert resp.json()["detail"] == "ai_disabled"


@pytest.mark.asyncio
async def test_structured_summary_malformed_ai_json_returns_502(
    auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    stub_structured_ai(monkeypatch, payload="{not json")
    created = await _import_plain(auth_client)

    resp = await auth_client.post(f"/api/v1/chats/{created['id']}/structured-summary")

    assert resp.status_code == 502


@pytest.mark.asyncio
async def test_apply_structured_summary_creates_claim_task_edges_and_revision(
    auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch, stub_reindex: list[str]
):
    stub_structured_ai(monkeypatch)
    created = await _import_plain(auth_client)
    preview = await auth_client.post(f"/api/v1/chats/{created['id']}/structured-summary")
    assert preview.status_code == 200

    apply = await auth_client.post(
        f"/api/v1/chats/{created['id']}/structured-summary/apply",
        json={},
    )

    assert apply.status_code == 200
    data = apply.json()
    assert data["chat"]["structured_summary_status"] == "applied"
    kinds = {obj["kind"] for obj in data["created_objects"]}
    assert kinds == {"claim", "task"}
    assert len(data["edges"]) == 2
    assert created["id"] in stub_reindex

    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        objects = (
            (await db.execute(select(KosObject).where(KosObject.kind.in_(["claim", "task"]))))
            .scalars()
            .all()
        )
        edges = (await db.execute(select(Edge))).scalars().all()
        revisions = (
            (
                await db.execute(
                    select(ObjectRevision).where(ObjectRevision.object_id == created["id"])
                )
            )
            .scalars()
            .all()
        )

    assert {obj.metadata_["turn_refs"][0] for obj in objects} == {0, 1}
    assert {edge.kind for edge in edges} >= {"derives_from", "created_from"}
    assert revisions


@pytest.mark.asyncio
async def test_duplicate_apply_reuses_extracted_objects(
    auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    stub_structured_ai(monkeypatch)
    created = await _import_plain(auth_client)
    await auth_client.post(f"/api/v1/chats/{created['id']}/structured-summary")
    first = await auth_client.post(
        f"/api/v1/chats/{created['id']}/structured-summary/apply",
        json={},
    )
    second = await auth_client.post(
        f"/api/v1/chats/{created['id']}/structured-summary/apply",
        json={},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(second.json()["created_objects"]) == 0
    assert len(second.json()["reused_objects"]) == 2


@pytest.mark.asyncio
async def test_user_cannot_summarize_another_users_chat(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    stub_structured_ai(monkeypatch)
    await client.post(
        "/api/v1/auth/register",
        json={"email": "one-summary@test.com", "password": "password123", "display_name": "One"},
    )
    created = await _import_plain(client)
    await client.post("/api/v1/auth/logout")
    await client.post(
        "/api/v1/auth/register",
        json={"email": "two-summary@test.com", "password": "password123", "display_name": "Two"},
    )

    resp = await client.post(f"/api/v1/chats/{created['id']}/structured-summary")

    assert resp.status_code == 404
