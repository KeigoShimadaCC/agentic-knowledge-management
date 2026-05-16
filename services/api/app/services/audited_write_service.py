"""Transactional wrapper that enforces audit + revision discipline for every MCP write.

Usage pattern:

    result = await audited_write(
        db, redis,
        user_id=user.id,
        agent_id=agent_id_from_request(request),
        tool_name="create_page",
        args={"title": "...", "tags": [...]},
        fn=_do_create_page,
        mutating_object_id=None,   # set to object id when updating/archiving
    )
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import check_and_increment
from app.services import agent_run_service, revision_service

if TYPE_CHECKING:
    from redis.asyncio import Redis


async def audited_write(
    db: AsyncSession,
    redis: "Redis",
    *,
    user_id: uuid.UUID,
    agent_id: str,
    tool_name: str,
    args: dict[str, Any],
    fn: Callable[["AsyncSession"], Awaitable[Any]],
    mutating_object_id: uuid.UUID | None = None,
) -> Any:
    """Run *fn* inside a single transaction with full audit + revision logging.

    Rate-limit check happens BEFORE the transaction so a rejected call never
    touches the database.  If *mutating_object_id* is provided the state of
    that object is snapshotted before and after *fn* runs and an
    ``object_revisions`` row is created linking to the ``agent_runs`` row.

    Raises:
        RateLimitError: if either the per-minute or per-hour bucket is full.
        Any exception raised by *fn*: propagated after marking the run as
            failed.  The enclosing transaction is rolled back so no partial
            writes survive.
    """
    # Rate-limit check (no DB side-effects on rejection)
    await check_and_increment(agent_id, redis)

    # Work within the existing autobegun transaction on the session.
    # The session is opened by get_db; get_current_user autobegins it.
    # Do NOT call db.begin() here — that would raise InvalidRequestError.
    # The endpoint is responsible for calling await db.commit() on success.
    run = await agent_run_service.create_agent_run(
        db,
        user_id=user_id,
        agent_type=agent_id,
        input_payload=args,
    )

    before_snapshot: dict[str, Any] = {}
    if mutating_object_id is not None:
        before_snapshot = await revision_service.snapshot_object_state(db, mutating_object_id)

    try:
        result = await fn(db)

        if mutating_object_id is not None:
            after_snapshot = await revision_service.snapshot_object_state(db, mutating_object_id)
            await revision_service.create_revision(
                db,
                object_id=mutating_object_id,
                user_id=user_id,
                before_snapshot=before_snapshot,
                after_snapshot=after_snapshot,
                changed_by="agent",
                agent_run_id=run.id,
            )

        output = _summarise(result)
        await agent_run_service.complete(db, run, output=output)
        return result

    except Exception as exc:
        await agent_run_service.fail(db, run, error=str(exc))
        raise


def _summarise(result: Any) -> dict[str, Any]:
    """Build a compact, JSON-safe output dict from an ORM object or plain dict."""
    if result is None:
        return {}
    if isinstance(result, dict):
        return result
    # ORM objects: extract id, kind (or type), title if present
    summary: dict[str, Any] = {}
    for attr in ("id", "kind", "title", "status", "ingestion_status"):
        val = getattr(result, attr, None)
        if val is not None:
            summary[attr] = str(val) if not isinstance(val, (str, int, bool, float)) else val
    return summary
