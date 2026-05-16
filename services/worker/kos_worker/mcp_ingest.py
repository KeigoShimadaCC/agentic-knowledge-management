"""RQ entry point for importing MCP tool results into KnowledgeOS."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from app.mcp_client.adapters import PageInput, SourceInput, get_adapter
from app.mcp_client.client import McpClientSession
from app.models.agent_run import AgentRun
from app.models.mcp_connection import McpConnection
from app.models.object import KosObject
from app.models.page import Page
from app.models.source import Source

from kos_worker.db import get_session
from kos_worker.tasks import reindex_object


def _now() -> datetime:
    return datetime.now(UTC)


def _write_agent_run(
    db,
    *,
    user_id: uuid.UUID,
    status: str,
    tool_name: str,
    input_payload: dict[str, Any],
    output: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    try:
        db.add(
            AgentRun(
                user_id=user_id,
                status=status,
                agent_type=f"mcp:{tool_name}"[:64],
                input=input_payload,
                output=output,
                error=error,
                model="mcp",
                started_at=_now(),
                finished_at=_now(),
            )
        )
        db.flush()
    except Exception:
        db.rollback()


def _page_doc(text: str) -> dict[str, Any]:
    return {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}] if text else [],
            }
        ],
    }


def _create_page(db, *, user_id: uuid.UUID, data: PageInput, tags: list[str]) -> KosObject:
    obj = KosObject(
        user_id=user_id,
        kind="page",
        title=data.title,
        tags=tags,
        metadata_={"mcp": data.metadata},
        ai_generated=True,
    )
    db.add(obj)
    db.flush()
    db.add(
        Page(
            id=obj.id,
            content_json=data.content_json or _page_doc(data.content_text),
            content_text=data.content_text,
            word_count=len(data.content_text.split()) if data.content_text.strip() else 0,
        )
    )
    db.flush()
    return obj


def _create_source(db, *, user_id: uuid.UUID, data: SourceInput, tags: list[str]) -> KosObject:
    obj = KosObject(
        user_id=user_id,
        kind="source",
        title=data.title,
        tags=tags,
        metadata_={"mcp": data.metadata or {}},
        ai_generated=True,
    )
    db.add(obj)
    db.flush()
    db.add(
        Source(
            id=obj.id,
            source_type=data.source_type,
            url=data.url,
            ingestion_status="success",
            extracted_text=data.extracted_text,
            preview_data=data.preview_data,
        )
    )
    db.flush()
    return obj


async def _call_mcp(conn: McpConnection, tool_name: str, tool_args: dict) -> dict:
    async with McpClientSession(conn, timeout=30) as session:
        return await session.call_tool(tool_name, tool_args)


def ingest_from_mcp(
    connection_id: str,
    tool_name: str,
    tool_args: dict,
    target_kind: str,
    tags: list[str],
    user_id: str,
) -> dict:
    db = get_session()
    input_payload = {
        "connection_id": connection_id,
        "tool_name": tool_name,
        "args": tool_args,
        "target_kind": target_kind,
        "tags": tags,
    }
    user_uuid = uuid.UUID(str(user_id))
    try:
        conn = db.get(McpConnection, uuid.UUID(str(connection_id)))
        if conn is None or conn.user_id != user_uuid or conn.deleted_at is not None:
            raise ValueError("MCP connection not found")

        result = asyncio.run(_call_mcp(conn, tool_name, tool_args or {}))
        adapter = get_adapter(tool_name)
        inputs = adapter.adapt(result, "page" if target_kind == "page" else "source")

        objects: list[KosObject] = []
        for item in inputs:
            if target_kind == "page" and isinstance(item, PageInput):
                objects.append(_create_page(db, user_id=user_uuid, data=item, tags=tags or []))
            elif isinstance(item, SourceInput):
                objects.append(_create_source(db, user_id=user_uuid, data=item, tags=tags or []))

        db.commit()
        object_ids = [str(obj.id) for obj in objects]
        titles = [obj.title for obj in objects]

        for object_id in object_ids:
            reindex_object(object_id)

        output = {"object_ids": object_ids, "kind": target_kind, "titles": titles}
        _write_agent_run(
            db,
            user_id=user_uuid,
            status="success",
            tool_name=tool_name,
            input_payload=input_payload,
            output=output,
        )
        db.commit()
        return output
    except Exception as exc:
        db.rollback()
        _write_agent_run(
            db,
            user_id=user_uuid,
            status="failed",
            tool_name=tool_name,
            input_payload=input_payload,
            error=str(exc),
        )
        db.commit()
        raise
    finally:
        db.close()
