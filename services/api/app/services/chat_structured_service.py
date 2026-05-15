from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from string import Template
from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import call_ai
from app.models.agent_run import AgentRun
from app.models.chat import Chat
from app.models.edge import Edge
from app.models.object import KosObject
from app.schemas.chat import StructuredChatSummary, StructuredSummaryApplyIn
from app.schemas.object import ObjectOut
from app.services.agent_run_service import create_agent_run, finish_agent_run
from app.services.edge_service import create_edge
from app.services.reindex_service import enqueue_reindex_object
from app.services.revision_service import create_revision

STRUCTURED_CHAT_SUMMARY_SYSTEM_PROMPT = """You extract durable knowledge from imported chats.
Use only the provided chat turns. Do not invent facts. Preserve uncertainty.
Every decision, open question, action item, claim, and concept must include turn_refs
with zero-based turn indexes from the transcript. Avoid trivial or duplicate items.
Return strict JSON only. Do not wrap the JSON in Markdown."""

STRUCTURED_CHAT_SUMMARY_USER_TEMPLATE = """Analyze this chat and return JSON with this shape:

{
  "title": "short useful title",
  "summary": "concise grounded summary",
  "date_range": {"start": "ISO timestamp or null", "end": "ISO timestamp or null"},
  "topics": ["topic"],
  "key_decisions": [
    {
      "decision": "decision",
      "rationale": "why or null",
      "turn_refs": [0],
      "confidence": "low|medium|high"
    }
  ],
  "open_questions": [
    {"question": "question", "turn_refs": [1], "status": "open", "confidence": "low|medium|high"}
  ],
  "action_items": [
    {
      "task": "task",
      "owner": "owner or null",
      "due_at": "ISO timestamp or null",
      "turn_refs": [2],
      "confidence": "low|medium|high"
    }
  ],
  "claims": [
    {
      "claim": "claim",
      "type": "fact|hypothesis|preference|decision_context|unknown",
      "turn_refs": [3],
      "confidence": "low|medium|high"
    }
  ],
  "concepts": [
    {
      "name": "name",
      "type": "person|organization|product|technology|topic|project|unknown",
      "turn_refs": [4],
      "confidence": "low|medium|high"
    }
  ],
  "suggested_links": [
    {
      "target_object_id": null,
      "target_title": "title",
      "edge_kind": "related_to|mentions|supports|contradicts|belongs_to_project|created_from",
      "rationale": "why",
      "confidence": "low|medium|high"
    }
  ],
  "warnings": ["warning"]
}

If there is insufficient content, return empty arrays and a warning instead of guessing.

Chat metadata:
- object_id: $chat_id
- title: $title
- provider: $provider
- turn_count: $turn_count
- started_at: $started_at
- ended_at: $ended_at

Turns:
$turns
"""

MAX_STRUCTURED_PROMPT_CHARS = 60000


async def generate_structured_summary_preview(
    db: AsyncSession,
    *,
    obj: KosObject,
    chat: Chat,
    user_id: uuid.UUID,
) -> StructuredChatSummary:
    before = _chat_structured_snapshot(chat)
    messages = build_structured_summary_messages(obj, chat)
    raw_text, run = await call_ai(
        db,
        user_id=user_id,
        agent_type="chat_structured_summary_preview",
        messages=messages,
        input_context={"chat_id": str(chat.id)},
    )

    try:
        summary = parse_structured_summary_output(raw_text)
    except HTTPException:
        repair_messages = [
            {"role": "system", "content": "Return only valid JSON matching the requested schema."},
            {
                "role": "user",
                "content": (
                    "Repair this malformed structured chat summary JSON. "
                    "Do not add new facts.\n\n"
                    f"{raw_text}"
                ),
            },
        ]
        raw_text, run = await call_ai(
            db,
            user_id=user_id,
            agent_type="chat_structured_summary_repair",
            messages=repair_messages,
            input_context={"chat_id": str(chat.id), "previous_agent_run_id": str(run.id)},
        )
        try:
            summary = parse_structured_summary_output(raw_text)
        except HTTPException:
            chat.structured_summary_status = "failed"
            chat.structured_summary_agent_run_id = run.id
            chat.structured_summary_updated_at = datetime.now(UTC)
            obj.updated_at = datetime.now(UTC)
            await db.flush()
            await create_revision(
                db,
                object_id=obj.id,
                user_id=user_id,
                changed_by="ai",
                agent_run_id=run.id,
                before_snapshot=before,
                after_snapshot=_chat_structured_snapshot(chat),
            )
            raise

    chat.structured_summary = summary.model_dump(mode="json")
    chat.structured_summary_status = "previewed"
    chat.structured_summary_agent_run_id = run.id
    chat.structured_summary_updated_at = datetime.now(UTC)
    chat.structured_summary_hash = structured_summary_hash(summary)
    obj.updated_at = datetime.now(UTC)
    await db.flush()
    await create_revision(
        db,
        object_id=obj.id,
        user_id=user_id,
        changed_by="ai",
        agent_run_id=run.id,
        before_snapshot=before,
        after_snapshot=_chat_structured_snapshot(chat),
    )
    return summary


def get_existing_structured_summary(chat: Chat) -> StructuredChatSummary | None:
    if not chat.structured_summary:
        return None
    return StructuredChatSummary.model_validate(chat.structured_summary)


async def apply_structured_summary(
    db: AsyncSession,
    *,
    obj: KosObject,
    chat: Chat,
    user_id: uuid.UUID,
    data: StructuredSummaryApplyIn,
) -> tuple[list[KosObject], list[KosObject], list[Edge], AgentRun]:
    summary = data.structured_summary or get_existing_structured_summary(chat)
    if summary is None:
        raise HTTPException(status_code=422, detail="No structured summary to apply")

    before = _chat_structured_snapshot(chat)
    summary_hash = structured_summary_hash(summary)
    apply_run = await create_agent_run(
        db,
        user_id=user_id,
        agent_type="chat_structured_summary_apply",
        input_payload={
            "chat_id": str(chat.id),
            "structured_summary_hash": summary_hash,
            "create_claims": data.create_claims,
            "create_tasks": data.create_tasks,
            "create_concepts": data.create_concepts,
            "link_existing_objects": data.link_existing_objects,
        },
    )

    chat.structured_summary = summary.model_dump(mode="json")
    chat.structured_summary_status = "applied"
    chat.structured_summary_agent_run_id = chat.structured_summary_agent_run_id or apply_run.id
    chat.structured_summary_updated_at = datetime.now(UTC)
    chat.structured_summary_hash = summary_hash
    obj.title = summary.title or obj.title
    obj.updated_at = datetime.now(UTC)
    await db.flush()

    created: list[KosObject] = []
    reused: list[KosObject] = []
    edges: list[Edge] = []
    if data.create_claims:
        for index, claim in enumerate(summary.claims):
            extracted, was_created = await _create_or_reuse_extracted_object(
                db,
                user_id=user_id,
                kind="claim",
                title=_short_title(claim.claim),
                description=claim.claim,
                extraction_key=_extraction_key("claim", chat.id, claim.claim, claim.turn_refs),
                metadata={
                    "ai_generated": True,
                    "source_chat_id": str(chat.id),
                    "turn_refs": claim.turn_refs,
                    "confidence": claim.confidence,
                    "claim_type": claim.type,
                    "agent_run_id": str(apply_run.id),
                    "summary_hash": summary_hash,
                    "item_index": index,
                },
            )
            (created if was_created else reused).append(extracted)
            edge = await create_edge(
                db,
                extracted.id,
                chat.id,
                "derives_from",
                user_id=user_id,
                metadata_={"turn_refs": claim.turn_refs, "agent_run_id": str(apply_run.id)},
            )
            edges.append(edge)
            enqueue_reindex_object(extracted.id)

    if data.create_tasks:
        for index, item in enumerate(summary.action_items):
            extracted, was_created = await _create_or_reuse_extracted_object(
                db,
                user_id=user_id,
                kind="task",
                title=_short_title(item.task),
                description=item.task,
                extraction_key=_extraction_key("task", chat.id, item.task, item.turn_refs),
                metadata={
                    "ai_generated": True,
                    "source_chat_id": str(chat.id),
                    "turn_refs": item.turn_refs,
                    "confidence": item.confidence,
                    "owner": item.owner,
                    "due_at": item.due_at,
                    "agent_run_id": str(apply_run.id),
                    "summary_hash": summary_hash,
                    "item_index": index,
                },
            )
            (created if was_created else reused).append(extracted)
            edge = await create_edge(
                db,
                extracted.id,
                chat.id,
                "created_from",
                user_id=user_id,
                metadata_={"turn_refs": item.turn_refs, "agent_run_id": str(apply_run.id)},
            )
            edges.append(edge)
            enqueue_reindex_object(extracted.id)

    if data.create_concepts:
        summary.warnings.append("Concept object creation is not available in this phase.")

    await create_revision(
        db,
        object_id=obj.id,
        user_id=user_id,
        changed_by="ai",
        agent_run_id=apply_run.id,
        before_snapshot=before,
        after_snapshot=_chat_structured_snapshot(chat),
    )
    await finish_agent_run(
        db,
        apply_run,
        status="success",
        output={
            "created_object_ids": [str(item.id) for item in created],
            "reused_object_ids": [str(item.id) for item in reused],
            "edge_ids": [str(edge.id) for edge in edges],
        },
        cost_usd=Decimal("0"),
    )
    enqueue_reindex_object(chat.id)
    return created, reused, edges, apply_run


def build_structured_summary_messages(obj: KosObject, chat: Chat) -> list[dict[str, str]]:
    turns = _format_turns(chat.parsed_turns)
    warning = ""
    if len(turns) > MAX_STRUCTURED_PROMPT_CHARS:
        turns = turns[:MAX_STRUCTURED_PROMPT_CHARS]
        warning = "\n\nThe transcript was truncated for context length; include this in warnings."

    user_prompt = Template(STRUCTURED_CHAT_SUMMARY_USER_TEMPLATE).substitute(
        chat_id=str(obj.id),
        title=obj.title,
        provider=chat.provider,
        turn_count=str(chat.turn_count),
        started_at=chat.started_at.isoformat() if chat.started_at else "None",
        ended_at=chat.ended_at.isoformat() if chat.ended_at else "None",
        turns=f"{turns}{warning}",
    )
    return [
        {"role": "system", "content": STRUCTURED_CHAT_SUMMARY_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def parse_structured_summary_output(raw_text: str) -> StructuredChatSummary:
    payload = _extract_json_object(raw_text)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail="AI returned malformed structured JSON",
        ) from exc

    try:
        return StructuredChatSummary.model_validate(data)
    except ValidationError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "AI structured summary failed schema validation",
                "errors": exc.errors(),
            },
        ) from exc


def structured_summary_hash(summary: StructuredChatSummary | dict[str, Any]) -> str:
    if isinstance(summary, StructuredChatSummary):
        payload = summary.model_dump(mode="json")
    else:
        payload = summary
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def structured_summary_search_text(summary: dict[str, Any] | None) -> str:
    if not summary:
        return ""
    parts: list[str] = []
    _collect_strings(summary, parts)
    return "\n".join(parts)


def _extract_json_object(raw_text: str) -> str:
    text = raw_text.strip()
    fence_match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    if text.startswith("{") and text.endswith("}"):
        return text
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    raise HTTPException(status_code=502, detail="AI response did not contain a JSON object")


def _format_turns(turns: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for idx, turn in enumerate(turns):
        turn_index = turn.get("turn_index", idx)
        role = turn.get("role") or "unknown"
        author = turn.get("author") or role
        created_at = turn.get("created_at")
        content = str(turn.get("content") or "").strip()
        if not content:
            continue
        header = f"[turn_index={turn_index} role={role} author={author}"
        if created_at:
            header += f" created_at={created_at}"
        header += "]"
        lines.append(f"{header}\n{content}")
    return "\n\n".join(lines)


def _collect_strings(value: Any, parts: list[str]) -> None:
    if isinstance(value, str):
        if value.strip():
            parts.append(value.strip())
    elif isinstance(value, dict):
        for child in value.values():
            _collect_strings(child, parts)
    elif isinstance(value, list):
        for child in value:
            _collect_strings(child, parts)


def _chat_structured_snapshot(chat: Chat) -> dict[str, Any]:
    return {
        "id": str(chat.id),
        "structured_summary": chat.structured_summary,
        "structured_summary_status": chat.structured_summary_status,
        "structured_summary_agent_run_id": (
            str(chat.structured_summary_agent_run_id)
            if chat.structured_summary_agent_run_id
            else None
        ),
        "structured_summary_updated_at": (
            chat.structured_summary_updated_at.isoformat()
            if chat.structured_summary_updated_at
            else None
        ),
        "structured_summary_hash": chat.structured_summary_hash,
    }


async def _create_or_reuse_extracted_object(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    kind: str,
    title: str,
    description: str,
    extraction_key: str,
    metadata: dict[str, Any],
) -> tuple[KosObject, bool]:
    result = await db.execute(
        select(KosObject).where(
            KosObject.user_id == user_id,
            KosObject.kind == kind,
            KosObject.deleted_at.is_(None),
            KosObject.metadata_["extraction_key"].astext == extraction_key,
        )
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing, False

    obj = KosObject(
        user_id=user_id,
        kind=kind,
        title=title,
        description=description,
        metadata_={**metadata, "extraction_key": extraction_key},
        ai_generated=True,
    )
    db.add(obj)
    await db.flush()
    return obj, True


def object_summary_dict(obj: KosObject) -> dict[str, Any]:
    return ObjectOut.model_validate(obj).model_dump(mode="json")


def edge_summary_dict(edge: Edge) -> dict[str, Any]:
    return {
        "id": str(edge.id),
        "source_id": str(edge.source_id),
        "target_id": str(edge.target_id),
        "kind": edge.kind,
        "metadata": edge.metadata_,
    }


def _extraction_key(kind: str, chat_id: uuid.UUID, text: str, turn_refs: list[int]) -> str:
    payload = json.dumps(
        {"kind": kind, "chat_id": str(chat_id), "text": text, "turn_refs": sorted(turn_refs)},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _short_title(value: str) -> str:
    cleaned = " ".join(value.split())
    if len(cleaned) <= 80:
        return cleaned
    return f"{cleaned[:77].rstrip()}..."
