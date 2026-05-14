from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import call_ai
from app.models.chat import Chat
from app.models.object import KosObject
from app.schemas.chat import StructuredChatSummary
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
- object_id: {chat_id}
- title: {title}
- provider: {provider}
- turn_count: {turn_count}
- started_at: {started_at}
- ended_at: {ended_at}

Turns:
{turns}
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


def build_structured_summary_messages(obj: KosObject, chat: Chat) -> list[dict[str, str]]:
    turns = _format_turns(chat.parsed_turns)
    warning = ""
    if len(turns) > MAX_STRUCTURED_PROMPT_CHARS:
        turns = turns[:MAX_STRUCTURED_PROMPT_CHARS]
        warning = "\n\nThe transcript was truncated for context length; include this in warnings."

    user_prompt = STRUCTURED_CHAT_SUMMARY_USER_TEMPLATE.format(
        chat_id=obj.id,
        title=obj.title,
        provider=chat.provider,
        turn_count=chat.turn_count,
        started_at=chat.started_at.isoformat() if chat.started_at else None,
        ended_at=chat.ended_at.isoformat() if chat.ended_at else None,
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
