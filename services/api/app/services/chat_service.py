from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Chat
from app.models.object import KosObject
from app.services import chat_storage
from app.services.chat_parser import ChatParseError, ParsedChat, parse_chat_import


async def import_chats(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    content: bytes,
    provider: str,
    raw_format: str | None,
    title: str | None,
    source_filename: str | None,
) -> list[tuple[KosObject, Chat]]:
    try:
        parsed_chats = parse_chat_import(
            content,
            provider=provider,
            raw_format=raw_format,
            title=title,
        )
    except ChatParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    batch_raw_path: str | None = None
    if len(parsed_chats) > 1 and parsed_chats[0].provider == "chatgpt":
        batch_raw_path = chat_storage.store_batch_raw(content, provider="chatgpt")

    rows: list[tuple[KosObject, Chat]] = []
    for parsed in parsed_chats:
        rows.append(
            await _create_chat(
                db,
                user_id,
                parsed,
                source_filename=source_filename,
                batch_raw_path=batch_raw_path,
            )
        )
    return rows


async def _create_chat(
    db: AsyncSession,
    user_id: uuid.UUID,
    parsed: ParsedChat,
    *,
    source_filename: str | None,
    batch_raw_path: str | None,
) -> tuple[KosObject, Chat]:
    obj = KosObject(user_id=user_id, kind="chat", title=parsed.title)
    db.add(obj)
    await db.flush()

    raw_bytes = chat_storage.raw_payload_bytes(parsed.raw_payload, parsed.raw_format)
    metadata = {
        **parsed.metadata,
        "source_filename": source_filename,
        "batch_raw_storage_path": batch_raw_path,
    }
    raw_storage_path = chat_storage.store_chat_raw(
        chat_id=obj.id,
        provider=parsed.provider,
        raw_format=parsed.raw_format,
        content=raw_bytes,
        metadata=metadata,
    )
    chat = Chat(
        id=obj.id,
        provider=parsed.provider,
        external_chat_id=parsed.external_chat_id,
        source_filename=source_filename,
        raw_storage_path=raw_storage_path,
        raw_format=parsed.raw_format,
        turn_count=len(parsed.turns),
        started_at=parsed.started_at,
        ended_at=parsed.ended_at,
        parsed_turns=[turn.to_dict() for turn in parsed.turns],
        content_text=parsed.content_text,
        metadata_=metadata,
    )
    db.add(chat)
    await db.flush()
    return obj, chat


async def list_chats(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    provider: str | None = None,
    q: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[tuple[KosObject, Chat]]:
    stmt = (
        select(KosObject, Chat)
        .join(Chat, Chat.id == KosObject.id)
        .where(KosObject.user_id == user_id, KosObject.deleted_at.is_(None))
    )
    if provider:
        stmt = stmt.where(Chat.provider == provider)
    if q:
        needle = f"%{q}%"
        stmt = stmt.where((KosObject.title.ilike(needle)) | (Chat.content_text.ilike(needle)))
    stmt = stmt.order_by(Chat.imported_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


async def get_chat_or_404(
    db: AsyncSession, chat_id: uuid.UUID, user_id: uuid.UUID
) -> tuple[KosObject, Chat]:
    obj, chat = await _get_chat_row_or_404(db, chat_id, user_id)
    if obj.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return obj, chat


async def get_chat_for_restore_or_404(
    db: AsyncSession, chat_id: uuid.UUID, user_id: uuid.UUID
) -> tuple[KosObject, Chat]:
    return await _get_chat_row_or_404(db, chat_id, user_id)


async def soft_delete_chat(db: AsyncSession, obj: KosObject) -> KosObject:
    obj.deleted_at = datetime.now(UTC)
    obj.updated_at = datetime.now(UTC)
    await db.flush()
    return obj


async def restore_chat(db: AsyncSession, obj: KosObject) -> KosObject:
    obj.deleted_at = None
    obj.updated_at = datetime.now(UTC)
    await db.flush()
    return obj


def raw_file_response_info(chat: Chat) -> tuple[str, str]:
    path = chat_storage.resolve_library_path(chat.raw_storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Raw chat file not found")
    media_type = "application/json" if chat.raw_format == "json" else "text/plain"
    return str(path), media_type


async def _get_chat_row_or_404(
    db: AsyncSession, chat_id: uuid.UUID, user_id: uuid.UUID
) -> tuple[KosObject, Chat]:
    result = await db.execute(
        select(KosObject, Chat)
        .join(Chat, Chat.id == KosObject.id)
        .where(KosObject.id == chat_id, KosObject.user_id == user_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Chat not found")
    return row[0], row[1]


def raw_format_from_filename(filename: str | None) -> str | None:
    if not filename:
        return None
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix == "json":
        return "json"
    if suffix in {"md", "markdown"}:
        return "md"
    if suffix == "txt":
        return "txt"
    return None


def parsed_json_content(value: str) -> bytes:
    return json.dumps({"content": value}, ensure_ascii=False).encode("utf-8")
