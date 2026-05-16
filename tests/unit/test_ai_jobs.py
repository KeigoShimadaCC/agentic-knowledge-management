"""Unit tests for kos_worker.ai_jobs — process_object_ai dispatch logic.

All DB, service, and queue dependencies are mocked. No real Postgres or Redis.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _invoke(object_id: str | None = None, user_id: str | None = None) -> None:
    from kos_worker.ai_jobs import process_object_ai

    process_object_ai(
        object_id or str(uuid.uuid4()),
        user_id or str(uuid.uuid4()),
    )


def _mock_session(obj=None):
    """Return a context-manager mock that yields a session returning obj from .get()."""
    session = AsyncMock()
    session.get = AsyncMock(return_value=obj)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session


def _make_obj(metadata=None, deleted_at=None, title="Test Object"):
    from app.models.object import KosObject

    obj = MagicMock(spec=KosObject)
    obj.deleted_at = deleted_at
    obj.title = title
    obj.metadata_ = metadata if metadata is not None else {}
    obj.user_id = uuid.uuid4()
    return obj


# ── Test 1: disabled flag ─────────────────────────────────────────────────────


def test_returns_immediately_when_ai_auto_process_false(monkeypatch: pytest.MonkeyPatch):
    """ai_auto_process=False → returns without touching DB or services."""
    monkeypatch.setattr("app.config.settings.ai_auto_process", False)

    with patch("kos_worker.ai_jobs.AsyncSessionLocal") as mock_sl:
        _invoke()

    mock_sl.assert_not_called()


# ── Test 2: object not found ──────────────────────────────────────────────────


def test_returns_when_object_not_found(monkeypatch: pytest.MonkeyPatch):
    """Non-existent object → no AI service calls."""
    monkeypatch.setattr("app.config.settings.ai_auto_process", True)
    monkeypatch.setattr("app.config.settings.ai_auto_process_tasks", ["summarize"])

    session = _mock_session(obj=None)
    with (
        patch("kos_worker.ai_jobs.AsyncSessionLocal", return_value=session),
        patch("kos_worker.ai_jobs.summarize_object", new_callable=AsyncMock) as mock_sum,
    ):
        _invoke()

    mock_sum.assert_not_called()


# ── Test 3: soft-deleted object ───────────────────────────────────────────────


def test_returns_when_object_soft_deleted(monkeypatch: pytest.MonkeyPatch):
    """Deleted object → no AI service calls."""
    import datetime

    monkeypatch.setattr("app.config.settings.ai_auto_process", True)
    monkeypatch.setattr("app.config.settings.ai_auto_process_tasks", ["summarize"])

    obj = _make_obj(deleted_at=datetime.datetime.now())
    session = _mock_session(obj=obj)

    with (
        patch("kos_worker.ai_jobs.AsyncSessionLocal", return_value=session),
        patch("kos_worker.ai_jobs.summarize_object", new_callable=AsyncMock) as mock_sum,
    ):
        _invoke()

    mock_sum.assert_not_called()


# ── Test 4: opt-out metadata ──────────────────────────────────────────────────


def test_returns_when_object_opted_out(monkeypatch: pytest.MonkeyPatch):
    """metadata_['ai_auto_process']=False → no AI calls."""
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


# ── Test 5: task isolation on failure ─────────────────────────────────────────


def test_remaining_tasks_run_after_one_failure(monkeypatch: pytest.MonkeyPatch):
    """summarize raises → extract_claims still called."""
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
            side_effect=RuntimeError("fail"),
        ) as mock_sum,
        patch("kos_worker.ai_jobs.extract_claims", new_callable=AsyncMock) as mock_ext,
    ):
        _invoke()  # must not raise

    mock_sum.assert_called_once()
    mock_ext.assert_called_once()


# ── Test 6: all tasks succeed → commit called ─────────────────────────────────


def test_ai_processed_at_written_on_success(monkeypatch: pytest.MonkeyPatch):
    """All tasks succeed → session.commit() called to persist ai_processed_at."""
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


# ── Test 7: notification created on success ───────────────────────────────────


def test_notification_created_when_tasks_succeed(monkeypatch: pytest.MonkeyPatch):
    """At least one task succeeds → KosObject with kind='ai_notification' added."""
    monkeypatch.setattr("app.config.settings.ai_auto_process", True)
    monkeypatch.setattr("app.config.settings.ai_auto_process_tasks", ["summarize"])

    obj = _make_obj(title="My Doc")
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
    assert "My Doc" in notifs[0].title


# ── Test 8: no notification when all tasks fail ───────────────────────────────


def test_no_notification_when_all_tasks_fail(monkeypatch: pytest.MonkeyPatch):
    """All tasks fail → no notification object created."""
    monkeypatch.setattr("app.config.settings.ai_auto_process", True)
    monkeypatch.setattr("app.config.settings.ai_auto_process_tasks", ["summarize"])

    obj = _make_obj()
    added: list = []

    session = _mock_session(obj=obj)
    session.add = MagicMock(side_effect=added.append)

    with (
        patch("kos_worker.ai_jobs.AsyncSessionLocal", return_value=session),
        patch(
            "kos_worker.ai_jobs.summarize_object",
            new_callable=AsyncMock,
            side_effect=RuntimeError("fail"),
        ),
    ):
        _invoke()

    notifs = [o for o in added if getattr(o, "kind", None) == "ai_notification"]
    assert notifs == []
