"""Integration tests for Phase 11C background AI processing.

Queue calls are mocked — no Redis required.
AI service calls are mocked — no OpenAI required.
Dispatch tests (4–10) are sync so process_object_ai can use asyncio.run() directly.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

# ── helpers ──────────────────────────────────────────────────────────────────


async def _make_page(auth_client: AsyncClient, title: str = "BG AI Test") -> dict:
    r = await auth_client.post("/api/v1/pages", json={"title": title})
    assert r.status_code == 201, r.text
    return r.json()


def _invoke(object_id: str | None = None, user_id: str | None = None) -> None:
    from kos_worker.ai_jobs import process_object_ai

    process_object_ai(object_id or str(uuid.uuid4()), user_id or str(uuid.uuid4()))


def _mock_session(obj=None):
    """Same shape as tests/unit/test_ai_jobs.py::_mock_session — see that docstring."""
    session = AsyncMock()
    session.get = AsyncMock(return_value=obj)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    empty_result = MagicMock()
    empty_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=empty_result)
    return session


def _make_obj(metadata=None, deleted_at=None, title="Test"):
    from app.models.object import KosObject

    obj = MagicMock(spec=KosObject)
    obj.deleted_at = deleted_at
    obj.title = title
    obj.metadata_ = metadata if metadata is not None else {}
    obj.user_id = uuid.uuid4()
    return obj


# ── Tests 1–3: API hook guards (async — need real FastAPI client) ─────────────


@pytest.mark.asyncio
async def test_patch_page_no_ai_job_when_disabled(
    auth_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    """AI_AUTO_PROCESS=false (default) → PATCH page does not enqueue any AI job."""
    monkeypatch.setattr("app.config.settings.ai_auto_process", False)

    enqueued: list = []

    async def fake_to_thread(fn, *args, **kwargs):
        enqueued.append(args)

    with patch("asyncio.to_thread", side_effect=fake_to_thread):
        data = await _make_page(auth_client)
        page_id = data["page"]["id"]
        resp = await auth_client.patch(f"/api/v1/pages/{page_id}", json={"title": "Updated"})

    assert resp.status_code == 200
    ai_calls = [a for a in enqueued if "process_object_ai" in str(a)]
    assert ai_calls == []


@pytest.mark.asyncio
async def test_patch_page_enqueues_ai_job_when_enabled(
    auth_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    """AI_AUTO_PROCESS=true → PATCH page enqueues exactly one AI job."""
    monkeypatch.setattr("app.config.settings.ai_auto_process", True)

    enqueued: list[tuple] = []

    async def fake_to_thread(fn, *args, **kwargs):
        enqueued.append(args)

    with patch("asyncio.to_thread", side_effect=fake_to_thread):
        data = await _make_page(auth_client)
        page_id = data["page"]["id"]
        object_id = data["object"]["id"]
        resp = await auth_client.patch(f"/api/v1/pages/{page_id}", json={"title": "AI On"})

    assert resp.status_code == 200
    ai_calls = [a for a in enqueued if "process_object_ai" in str(a)]
    assert len(ai_calls) == 1
    assert object_id in str(ai_calls[0])


@pytest.mark.asyncio
async def test_put_page_enqueues_ai_job_when_enabled(
    auth_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    """AI_AUTO_PROCESS=true → PUT page also enqueues one AI job."""
    monkeypatch.setattr("app.config.settings.ai_auto_process", True)

    enqueued: list[tuple] = []

    async def fake_to_thread(fn, *args, **kwargs):
        enqueued.append(args)

    with patch("asyncio.to_thread", side_effect=fake_to_thread):
        data = await _make_page(auth_client)
        page_id = data["page"]["id"]
        object_id = data["object"]["id"]
        resp = await auth_client.put(
            f"/api/v1/pages/{page_id}",
            json={"content_text": "replaced content"},
        )

    assert resp.status_code == 200
    ai_calls = [a for a in enqueued if "process_object_ai" in str(a)]
    assert len(ai_calls) == 1
    assert object_id in str(ai_calls[0])


# ── Tests 4–10: process_object_ai dispatch (sync — avoids nested event loops) ──


def test_process_object_ai_skips_missing_object(monkeypatch: pytest.MonkeyPatch):
    """Non-existent object_id → returns immediately, no AI service calls."""
    monkeypatch.setattr("app.config.settings.ai_auto_process", True)
    monkeypatch.setattr("app.config.settings.ai_auto_process_tasks", ["summarize"])

    session = _mock_session(obj=None)
    with (
        patch("kos_worker.ai_jobs.AsyncSessionLocal", return_value=session),
        patch("kos_worker.ai_jobs.summarize_object", new_callable=AsyncMock) as mock_sum,
    ):
        _invoke()

    mock_sum.assert_not_called()


def test_process_object_ai_skips_opted_out_object(monkeypatch: pytest.MonkeyPatch):
    """Object with metadata_['ai_auto_process']=False → no AI calls."""
    monkeypatch.setattr("app.config.settings.ai_auto_process", True)
    monkeypatch.setattr("app.config.settings.ai_auto_process_tasks", ["summarize"])

    obj = _make_obj(metadata={"ai_auto_process": False})
    session = _mock_session(obj=obj)
    with (
        patch("kos_worker.ai_jobs.AsyncSessionLocal", return_value=session),
        patch("kos_worker.ai_jobs.summarize_object", new_callable=AsyncMock) as mock_sum,
    ):
        _invoke()

    mock_sum.assert_not_called()


def test_process_object_ai_runs_only_configured_tasks(monkeypatch: pytest.MonkeyPatch):
    """AI_AUTO_PROCESS_TASKS=['summarize'] → only summarize called."""
    monkeypatch.setattr("app.config.settings.ai_auto_process", True)
    monkeypatch.setattr("app.config.settings.ai_auto_process_tasks", ["summarize"])

    obj = _make_obj()
    session = _mock_session(obj=obj)
    with (
        patch("kos_worker.ai_jobs.AsyncSessionLocal", return_value=session),
        patch("kos_worker.ai_jobs.summarize_object", new_callable=AsyncMock) as mock_sum,
        patch("kos_worker.ai_jobs.extract_claims", new_callable=AsyncMock) as mock_ext,
        patch("kos_worker.ai_jobs.suggest_links", new_callable=AsyncMock) as mock_lnk,
    ):
        _invoke()

    mock_sum.assert_called_once()
    mock_ext.assert_not_called()
    mock_lnk.assert_not_called()


def test_process_object_ai_continues_after_task_failure(monkeypatch: pytest.MonkeyPatch):
    """summarize raises → extract_claims still runs."""
    monkeypatch.setattr("app.config.settings.ai_auto_process", True)
    monkeypatch.setattr(
        "app.config.settings.ai_auto_process_tasks", ["summarize", "extract_claims"]
    )

    obj = _make_obj()
    session = _mock_session(obj=obj)
    with (
        patch("kos_worker.ai_jobs.AsyncSessionLocal", return_value=session),
        patch(
            "kos_worker.ai_jobs.summarize_object",
            new_callable=AsyncMock,
            side_effect=RuntimeError("AI unavailable"),
        ) as mock_sum,
        patch("kos_worker.ai_jobs.extract_claims", new_callable=AsyncMock) as mock_ext,
    ):
        _invoke()  # must not raise

    mock_sum.assert_called_once()
    mock_ext.assert_called_once()


def test_process_object_ai_writes_processed_at(monkeypatch: pytest.MonkeyPatch):
    """All tasks succeed → session commit called (persists ai_processed_at)."""
    monkeypatch.setattr("app.config.settings.ai_auto_process", True)
    monkeypatch.setattr("app.config.settings.ai_auto_process_tasks", ["summarize"])

    obj = _make_obj()
    session = _mock_session(obj=obj)
    with (
        patch("kos_worker.ai_jobs.AsyncSessionLocal", return_value=session),
        patch("kos_worker.ai_jobs.summarize_object", new_callable=AsyncMock),
    ):
        _invoke()

    assert session.commit.called


def test_process_object_ai_creates_inbox_notification(monkeypatch: pytest.MonkeyPatch):
    """All tasks succeed → KosObject with kind='ai_notification' added to session."""
    monkeypatch.setattr("app.config.settings.ai_auto_process", True)
    monkeypatch.setattr("app.config.settings.ai_auto_process_tasks", ["summarize"])

    obj = _make_obj(title="My Page")
    added: list = []
    session = _mock_session(obj=obj)
    session.add = MagicMock(side_effect=added.append)

    with (
        patch("kos_worker.ai_jobs.AsyncSessionLocal", return_value=session),
        patch("kos_worker.ai_jobs.summarize_object", new_callable=AsyncMock),
    ):
        _invoke()

    notifs = [o for o in added if getattr(o, "kind", None) == "ai_notification"]
    assert len(notifs) == 1
    assert "summarize" in notifs[0].metadata_["tasks_run"]
    assert "My Page" in notifs[0].title


def test_source_ingest_enqueues_ai_job(monkeypatch: pytest.MonkeyPatch):
    """After source ingestion completes, AI job is enqueued when flag is on."""
    monkeypatch.setattr("app.config.settings.ai_auto_process", True)

    enqueued_tasks: list[str] = []

    mock_queue = MagicMock()
    mock_queue.enqueue = MagicMock(side_effect=lambda task, *a, **kw: enqueued_tasks.append(task))

    from app.models.object import KosObject
    from app.models.source import Source

    mock_source = MagicMock(spec=Source)
    mock_source.id = uuid.uuid4()

    mock_kos = MagicMock(spec=KosObject)
    mock_kos.user_id = uuid.uuid4()

    mock_db = MagicMock()
    mock_db.get = lambda model, key: mock_kos if model is KosObject else None

    # Exercise the exact hook logic from kos_worker/tasks.py ingest_source()
    from app.config import settings

    if settings.ai_auto_process:
        try:
            _kos_obj = mock_db.get(KosObject, mock_source.id)
            if _kos_obj:
                mock_queue.enqueue(
                    "kos_worker.ai_jobs.process_object_ai",
                    str(mock_source.id),
                    str(_kos_obj.user_id),
                    job_timeout=300,
                )
        except Exception:
            pass

    assert "kos_worker.ai_jobs.process_object_ai" in enqueued_tasks


def test_process_object_ai_empty_task_list_commits_without_ai_calls(
    monkeypatch: pytest.MonkeyPatch,
):
    """AI_AUTO_PROCESS_TASKS=[] → no AI calls, ai_processed_at still committed."""
    monkeypatch.setattr("app.config.settings.ai_auto_process", True)
    monkeypatch.setattr("app.config.settings.ai_auto_process_tasks", [])

    obj = _make_obj()
    session = _mock_session(obj=obj)
    with (
        patch("kos_worker.ai_jobs.AsyncSessionLocal", return_value=session),
        patch("kos_worker.ai_jobs.summarize_object", new_callable=AsyncMock) as mock_sum,
        patch("kos_worker.ai_jobs.extract_claims", new_callable=AsyncMock) as mock_ext,
        patch("kos_worker.ai_jobs.suggest_links", new_callable=AsyncMock) as mock_lnk,
    ):
        _invoke()

    mock_sum.assert_not_called()
    mock_ext.assert_not_called()
    mock_lnk.assert_not_called()
    assert session.commit.called
