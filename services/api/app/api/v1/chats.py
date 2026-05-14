from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.config import settings
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.chat import Chat
from app.models.object import KosObject
from app.models.user import User
from app.schemas.chat import (
    ChatImportJson,
    ChatImportResponse,
    ChatOut,
    StructuredSummaryPreviewOut,
)
from app.services import chat_service, chat_structured_service, reindex_service

router = APIRouter(prefix="/chats", tags=["chats"])


def build_chat_out(obj: KosObject, chat: Chat) -> ChatOut:
    return ChatOut(
        id=obj.id,
        user_id=obj.user_id,
        kind=obj.kind,
        title=obj.title,
        description=obj.description,
        tags=obj.tags,
        is_pinned=obj.is_pinned,
        is_archived=obj.is_archived,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        deleted_at=obj.deleted_at,
        provider=chat.provider,
        external_chat_id=chat.external_chat_id,
        source_filename=chat.source_filename,
        raw_storage_path=chat.raw_storage_path,
        raw_format=chat.raw_format,
        turn_count=chat.turn_count,
        started_at=chat.started_at,
        ended_at=chat.ended_at,
        imported_at=chat.imported_at,
        parsed_turns=chat.parsed_turns,
        content_text=chat.content_text,
        metadata_=chat.metadata_,
        structured_summary=chat.structured_summary,
        structured_summary_status=chat.structured_summary_status,
        structured_summary_agent_run_id=chat.structured_summary_agent_run_id,
        structured_summary_updated_at=chat.structured_summary_updated_at,
    )


@router.post("/import", response_model=ChatImportResponse, status_code=201)
async def import_chat(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatImportResponse:
    content_type = request.headers.get("content-type", "")
    provider = "auto"
    raw_format: str | None = None
    title: str | None = None
    source_filename: str | None = None

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        file = form.get("file")
        if not isinstance(file, StarletteUploadFile):
            raise HTTPException(status_code=422, detail="file is required")
        content = await file.read()
        source_filename = file.filename
        provider = str(form.get("provider") or "auto")
        title_value = form.get("title")
        title = str(title_value) if title_value else None
        raw_format = chat_service.raw_format_from_filename(file.filename)
        if raw_format is None:
            raise HTTPException(
                status_code=422,
                detail="Unsupported upload type. Use .json, .md, .markdown, or .txt.",
            )
    else:
        body = ChatImportJson.model_validate(await request.json())
        content = body.content.encode("utf-8")
        provider = body.provider
        raw_format = body.raw_format
        title = body.title

    if len(content) > settings.chat_import_max_bytes:
        raise HTTPException(status_code=413, detail="Chat import exceeds configured size limit.")

    rows = await chat_service.import_chats(
        db,
        user.id,
        content=content,
        provider=provider,
        raw_format=raw_format,
        title=title,
        source_filename=source_filename,
    )
    await db.commit()

    imported: list[ChatOut] = []
    for obj, chat in rows:
        await db.refresh(obj)
        await db.refresh(chat)
        reindex_service.enqueue_reindex_object(obj.id)
        imported.append(build_chat_out(obj, chat))
    return ChatImportResponse(imported=imported, total=len(imported))


@router.get("", response_model=list[ChatOut])
async def list_chats(
    provider: str | None = None,
    q: str | None = None,
    skip: int = 0,
    limit: int = 100,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ChatOut]:
    rows = await chat_service.list_chats(
        db,
        user.id,
        provider=provider,
        q=q,
        skip=skip,
        limit=limit,
    )
    return [build_chat_out(obj, chat) for obj, chat in rows]


@router.get("/{chat_id}", response_model=ChatOut)
async def get_chat(
    chat_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatOut:
    obj, chat = await chat_service.get_chat_or_404(db, chat_id, user.id)
    return build_chat_out(obj, chat)


@router.get("/{chat_id}/raw")
async def get_raw_chat(
    chat_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    _, chat = await chat_service.get_chat_or_404(db, chat_id, user.id)
    path, media_type = chat_service.raw_file_response_info(chat)
    return FileResponse(path=path, media_type=media_type)


@router.delete("/{chat_id}", response_model=ChatOut)
async def delete_chat(
    chat_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatOut:
    obj, chat = await chat_service.get_chat_or_404(db, chat_id, user.id)
    obj = await chat_service.soft_delete_chat(db, obj)
    await db.commit()
    await db.refresh(obj)
    await db.refresh(chat)
    return build_chat_out(obj, chat)


@router.post("/{chat_id}/restore", response_model=ChatOut)
async def restore_chat(
    chat_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatOut:
    obj, chat = await chat_service.get_chat_for_restore_or_404(db, chat_id, user.id)
    obj = await chat_service.restore_chat(db, obj)
    await db.commit()
    await db.refresh(obj)
    await db.refresh(chat)
    reindex_service.enqueue_reindex_object(obj.id)
    return build_chat_out(obj, chat)


@router.post("/{chat_id}/reindex", response_model=ChatOut)
async def reindex_chat(
    chat_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatOut:
    obj, chat = await chat_service.get_chat_or_404(db, chat_id, user.id)
    reindex_service.enqueue_reindex_object(obj.id)
    return build_chat_out(obj, chat)


@router.post("/{chat_id}/structured-summary", response_model=StructuredSummaryPreviewOut)
async def generate_structured_summary(
    chat_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StructuredSummaryPreviewOut:
    obj, chat = await chat_service.get_chat_or_404(db, chat_id, user.id)
    summary = await chat_structured_service.generate_structured_summary_preview(
        db,
        obj=obj,
        chat=chat,
        user_id=user.id,
    )
    await db.commit()
    await db.refresh(chat)
    if chat.structured_summary_agent_run_id is None:
        raise HTTPException(status_code=500, detail="Structured summary agent run was not saved")
    return StructuredSummaryPreviewOut(
        structured_summary=summary,
        agent_run_id=chat.structured_summary_agent_run_id,
        status="previewed",
    )


@router.get("/{chat_id}/structured-summary", response_model=StructuredSummaryPreviewOut)
async def get_structured_summary(
    chat_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StructuredSummaryPreviewOut:
    _, chat = await chat_service.get_chat_or_404(db, chat_id, user.id)
    summary = chat_structured_service.get_existing_structured_summary(chat)
    if summary is None or chat.structured_summary_agent_run_id is None:
        raise HTTPException(status_code=404, detail="Structured summary not found")
    return StructuredSummaryPreviewOut(
        structured_summary=summary,
        agent_run_id=chat.structured_summary_agent_run_id,
        status=chat.structured_summary_status,
    )
