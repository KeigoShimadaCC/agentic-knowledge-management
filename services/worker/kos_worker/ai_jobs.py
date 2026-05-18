import asyncio
import logging
import uuid as _uuid
from datetime import UTC, datetime

from app.db.session import AsyncSessionLocal
from app.models.object import KosObject
from app.services.ai_service import extract_claims, suggest_links, summarize_object
from app.services.settings_service import background_ai_settings

logger = logging.getLogger(__name__)


def process_object_ai(object_id: str, user_id: str) -> None:
    """RQ entry point. Runs all enabled AI tasks for one object."""
    obj_uuid = _uuid.UUID(object_id)
    user_uuid = _uuid.UUID(user_id)

    async def _settings():
        async with AsyncSessionLocal() as db:
            return await background_ai_settings(db, user_uuid)

    ai_settings = asyncio.run(_settings())
    if not ai_settings.enabled:
        return

    async def _load():
        async with AsyncSessionLocal() as db:
            return await db.get(KosObject, obj_uuid)

    obj = asyncio.run(_load())
    if obj is None or obj.deleted_at is not None:
        logger.info("process_object_ai: object %s not found or deleted, skipping", object_id)
        return

    if obj.metadata_ and obj.metadata_.get("ai_auto_process") is False:
        logger.info("process_object_ai: object %s opted out, skipping", object_id)
        return

    tasks_run: list[str] = []
    for task_name in ai_settings.tasks:
        try:
            if task_name == "summarize":
                _run_summarize(obj_uuid, user_uuid)
            elif task_name == "extract_claims":
                _run_extract_claims(obj_uuid, user_uuid)
            elif task_name == "suggest_links":
                _run_suggest_links(obj_uuid, user_uuid)
            else:
                logger.warning("process_object_ai: unknown task %s", task_name)
                continue
            tasks_run.append(task_name)
            logger.info("process_object_ai: %s completed for object %s", task_name, object_id)
        except Exception:
            logger.exception("process_object_ai: %s failed for object %s", task_name, object_id)

    iso_ts = datetime.now(UTC).isoformat()

    async def _write_processed_at():
        async with AsyncSessionLocal() as db:
            o = await db.get(KosObject, obj_uuid)
            if o:
                meta = dict(o.metadata_ or {})
                meta["ai_processed_at"] = iso_ts
                o.metadata_ = meta
                await db.commit()

    asyncio.run(_write_processed_at())

    if tasks_run:

        async def _create_notification():
            async with AsyncSessionLocal() as db:
                o = await db.get(KosObject, obj_uuid)
                title = o.title if o else str(obj_uuid)
                notif = KosObject(
                    user_id=user_uuid,
                    kind="ai_notification",
                    title=f"AI processed: {title}",
                    metadata_={
                        "source_object_id": object_id,
                        "tasks_run": tasks_run,
                        "ai_processed_at": iso_ts,
                    },
                )
                db.add(notif)
                await db.commit()

        asyncio.run(_create_notification())


def _run_summarize(object_id: _uuid.UUID, user_id: _uuid.UUID) -> None:
    async def _run():
        async with AsyncSessionLocal() as db:
            await summarize_object(db, user_id, object_id, force=False)

    asyncio.run(_run())


def _run_extract_claims(object_id: _uuid.UUID, user_id: _uuid.UUID) -> None:
    async def _run():
        async with AsyncSessionLocal() as db:
            await extract_claims(db, user_id, object_id)

    asyncio.run(_run())


def _run_suggest_links(object_id: _uuid.UUID, user_id: _uuid.UUID) -> None:
    async def _run():
        async with AsyncSessionLocal() as db:
            await suggest_links(db, user_id, object_id)

    asyncio.run(_run())
