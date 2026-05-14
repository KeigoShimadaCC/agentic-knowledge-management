from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Chat
from app.models.chunk import Chunk
from app.models.object import KosObject
from app.models.page import Page
from app.models.source import Source
from app.search.chunker import chunk_text
from app.services.chat_structured_service import structured_summary_search_text


async def chunk_object(db: AsyncSession, object_id: uuid.UUID) -> list[Chunk]:
    result = await db.execute(select(KosObject).where(KosObject.id == object_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        return []

    text = await _extract_text(db, obj)
    await db.execute(delete(Chunk).where(Chunk.object_id == object_id))

    chunk_data = chunk_text(
        text,
        source_locator={"object_id": str(obj.id), "kind": obj.kind},
    )
    chunks = [
        Chunk(
            user_id=obj.user_id,
            object_id=obj.id,
            chunk_idx=data.chunk_idx,
            content=data.content,
            token_count=data.token_count,
            content_hash=data.content_hash,
            source_locator=data.source_locator,
        )
        for data in chunk_data
    ]

    db.add_all(chunks)
    await db.commit()
    return chunks


async def delete_chunks_for_object(db: AsyncSession, object_id: uuid.UUID) -> int:
    result = await db.execute(delete(Chunk).where(Chunk.object_id == object_id))
    await db.commit()
    return result.rowcount or 0


async def _extract_text(db: AsyncSession, obj: KosObject) -> str:
    if obj.kind == "page":
        result = await db.execute(select(Page).where(Page.id == obj.id))
        page = result.scalar_one_or_none()
        return page.content_text if page else ""

    if obj.kind == "source":
        result = await db.execute(select(Source).where(Source.id == obj.id))
        source = result.scalar_one_or_none()
        if source is None:
            return _join_text(obj.title, obj.description)

        body = source.extracted_text or _serialize_preview_data(source.preview_data)
        return _join_text(obj.title, body)

    if obj.kind == "chat":
        result = await db.execute(select(Chat).where(Chat.id == obj.id))
        chat = result.scalar_one_or_none()
        if chat is None:
            return _join_text(obj.title, obj.description)
        return _join_text(
            obj.title,
            chat.content_text,
            structured_summary_search_text(chat.structured_summary),
        )

    return _join_text(obj.title, obj.description)


def _serialize_preview_data(preview_data: dict[str, Any] | None) -> str:
    if not preview_data:
        return ""

    headers = preview_data.get("headers")
    rows = preview_data.get("rows")
    if headers or rows:
        lines: list[str] = []
        if headers:
            lines.append(_serialize_preview_value(headers))
        if rows:
            if isinstance(rows, list):
                lines.extend(_serialize_preview_value(row) for row in rows)
            else:
                lines.append(_serialize_preview_value(rows))
        return "\n".join(line for line in lines if line)

    return _serialize_preview_value(preview_data)


def _serialize_preview_value(value: Any) -> str:
    if isinstance(value, list):
        return "\t".join(_serialize_preview_value(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if value is None:
        return ""
    return str(value)


def _join_text(*parts: str | None) -> str:
    return "\n\n".join(part.strip() for part in parts if part and part.strip())
