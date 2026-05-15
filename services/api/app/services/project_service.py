from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.chat import Chat
from app.models.object import KosObject
from app.models.page import Page
from app.models.project import Project
from app.models.source import Source
from app.schemas.project import (
    ExtractedProjectDraft,
    ExtractProjectRequest,
    ExtractProjectResponse,
    ProjectCreate,
    ProjectUpdate,
    draft_metrics_from_parsed,
    normalize_skills_for_draft,
    parse_extract_project_json,
)
from app.services.agent_run_service import create_agent_run, finish_agent_run

_EXTRACT_SYSTEM = """You extract a single, well-structured PROJECT record from professional content.

A "project" is a bounded effort the person worked on with measurable scope:
problem solved, actions taken, results achieved, metrics where available,
skills exercised, and a time period.

Return JSON matching this schema (no prose, no markdown, no code fences):
{
  "title": string,
  "description": string | null,
  "period_start": string | null,
  "period_end": string | null,
  "role": string | null,
  "organization": string | null,
  "problem": string | null,
  "actions": string | null,
  "results": string | null,
  "metrics": object,
  "skills": string[],
  "confidence": number
}

Rules:
- If the source mentions multiple distinct projects, pick the one most prominent
  by space/specificity. Do not merge two projects.
- If the source is not about a project (e.g. a generic discussion), return
  confidence <= 0.2 and minimal fields.
- Do not invent dates, employers, or metrics. Use null/empty when unknown.
- Lowercase skills. Strip leading/trailing whitespace.
"""


def _parse_iso_date(s: Any) -> date | None:
    if s is None or s == "":
        return None
    if isinstance(s, date) and not isinstance(s, datetime):
        return s
    if isinstance(s, str):
        try:
            return date.fromisoformat(s[:10])
        except ValueError:
            return None
    return None


async def create_project(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: ProjectCreate,
    extracted_by_agent_run_id: uuid.UUID | None = None,
    confidence_override: str | None = None,
) -> tuple[KosObject, Project]:
    conf = confidence_override or payload.confidence
    obj = KosObject(
        user_id=user_id,
        kind="project",
        title=payload.title,
        description=payload.description,
        tags=list(payload.tags),
    )
    db.add(obj)
    await db.flush()

    proj = Project(
        id=obj.id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        role=payload.role,
        organization=payload.organization,
        problem=payload.problem,
        actions=payload.actions,
        results=payload.results,
        metrics=dict(payload.metrics),
        skills=list(payload.skills),
        status=payload.status,
        confidence=conf,
        extracted_from=payload.extracted_from,
        extracted_by_agent_run_id=extracted_by_agent_run_id,
    )
    db.add(proj)
    await db.flush()
    return obj, proj


async def get_project(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
) -> tuple[KosObject, Project] | None:
    stmt = (
        select(KosObject, Project)
        .join(Project, Project.id == KosObject.id)
        .where(
            KosObject.id == project_id,
            KosObject.user_id == user_id,
            KosObject.kind == "project",
            KosObject.deleted_at.is_(None),
        )
    )
    row = (await db.execute(stmt)).one_or_none()
    if not row:
        return None
    return row[0], row[1]


async def list_projects(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    skill: str | None = None,
    include_archived: bool = False,
) -> tuple[list[tuple[KosObject, Project]], int]:
    conditions = [
        KosObject.user_id == user_id,
        KosObject.kind == "project",
    ]
    if not include_archived:
        conditions.append(KosObject.deleted_at.is_(None))
    if status:
        conditions.append(Project.status == status)
    if skill:
        needle = skill.strip().lower()
        if needle:
            conditions.append(Project.skills.contains([needle]))

    count_stmt = (
        select(func.count())
        .select_from(KosObject)
        .join(Project, Project.id == KosObject.id)
        .where(*conditions)
    )
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = (
        select(KosObject, Project)
        .join(Project, Project.id == KosObject.id)
        .where(*conditions)
        .order_by(KosObject.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    return [(r[0], r[1]) for r in rows], int(total)


async def update_project(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: ProjectUpdate,
) -> tuple[KosObject, Project] | None:
    row = await get_project(db, project_id=project_id, user_id=user_id)
    if not row:
        return None
    obj, proj = row
    now = datetime.now(UTC)

    if payload.title is not None:
        obj.title = payload.title
    if payload.description is not None:
        obj.description = payload.description
    if payload.tags is not None:
        obj.tags = list(payload.tags)

    if payload.period_start is not None:
        proj.period_start = payload.period_start
    if payload.period_end is not None:
        proj.period_end = payload.period_end
    if payload.role is not None:
        proj.role = payload.role
    if payload.organization is not None:
        proj.organization = payload.organization
    if payload.problem is not None:
        proj.problem = payload.problem
    if payload.actions is not None:
        proj.actions = payload.actions
    if payload.results is not None:
        proj.results = payload.results
    if payload.metrics is not None:
        proj.metrics = dict(payload.metrics)
    if payload.skills is not None:
        proj.skills = list(payload.skills)
    if payload.status is not None:
        proj.status = payload.status
    if payload.confidence is not None:
        proj.confidence = payload.confidence

    obj.updated_at = now
    proj.updated_at = now
    await db.flush()
    return obj, proj


async def soft_delete_project(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    row = await get_project(db, project_id=project_id, user_id=user_id)
    if not row:
        return False
    obj, _proj = row
    obj.deleted_at = datetime.now(UTC)
    await db.flush()
    return True


async def _load_source_object(
    db: AsyncSession, user_id: uuid.UUID, source_id: uuid.UUID
) -> KosObject:
    stmt = select(KosObject).where(
        KosObject.id == source_id,
        KosObject.user_id == user_id,
        KosObject.deleted_at.is_(None),
    )
    obj = (await db.execute(stmt)).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Source object not found")
    if obj.kind not in ("page", "chat", "source"):
        raise HTTPException(
            status_code=400,
            detail="extract-project source must be a page, chat, or source object",
        )
    return obj


async def _source_text_for_extraction(db: AsyncSession, obj: KosObject) -> str:
    if obj.kind == "page":
        r = await db.execute(select(Page).where(Page.id == obj.id))
        page = r.scalar_one_or_none()
        if not page:
            return ""
        return page.content_text or ""
    if obj.kind == "chat":
        r = await db.execute(select(Chat).where(Chat.id == obj.id))
        chat = r.scalar_one_or_none()
        if not chat:
            return ""
        text = (chat.content_text or "").strip()
        if text:
            return text
        turns = chat.parsed_turns or []
        parts: list[str] = []
        for t in turns[:500]:
            if isinstance(t, dict):
                role = t.get("role", "")
                content = t.get("content", "")
                parts.append(f"{role}: {content}")
        joined = "\n".join(parts)
        return joined[:12000]
    if obj.kind == "source":
        r = await db.execute(select(Source).where(Source.id == obj.id))
        source = r.scalar_one_or_none()
        if not source:
            return ""
        return (source.extracted_text or "").strip()
    return ""


async def extract_project(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: ExtractProjectRequest,
) -> ExtractProjectResponse:
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="AI features disabled — set OPENAI_API_KEY",
        )

    obj = await _load_source_object(db, user_id, payload.source_id)
    source_text = (await _source_text_for_extraction(db, obj))[:12000]

    hint = payload.period_hint
    hint_str = "null"
    if hint is not None:
        hint_str = f"{hint[0]!s}, {hint[1]!s}"

    user_msg = f"""Title hint (may be empty): {obj.title}
Period hint (may be null): {hint_str}

Source content (truncated to 12k chars):
---
{source_text}
---
"""

    run = await create_agent_run(
        db,
        user_id=user_id,
        agent_type="extract-project",
        input_payload={
            "source_id": str(payload.source_id),
            "create": payload.create,
            "period_hint": list(hint) if hint is not None else None,
        },
        model=settings.openai_chat_model,
    )
    await db.flush()

    raw_text: str = "{}"
    input_tokens: int | None = None
    output_tokens: int | None = None
    try:
        import openai

        client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=[
                {"role": "system", "content": _EXTRACT_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=settings.openai_max_tokens,
            response_format={"type": "json_object"},
        )
        raw_text = response.choices[0].message.content or "{}"
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", None) if usage else None
        output_tokens = getattr(usage, "completion_tokens", None) if usage else None
    except Exception as exc:
        await finish_agent_run(db, run, status="error", error=str(exc))
        await db.flush()
        raise

    try:
        data = parse_extract_project_json(raw_text)
    except json.JSONDecodeError:
        await finish_agent_run(
            db,
            run,
            status="failed",
            output={"text": raw_text},
            error="malformed_json",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=Decimal("0"),
        )
        await db.flush()
        raise HTTPException(status_code=502, detail="AI returned malformed JSON") from None

    if not isinstance(data, dict):
        await finish_agent_run(
            db,
            run,
            status="failed",
            output={"text": raw_text},
            error="not_object",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=Decimal("0"),
        )
        await db.flush()
        raise HTTPException(status_code=502, detail="AI returned malformed JSON")

    try:
        skills_raw = data.get("skills") or []
        if not isinstance(skills_raw, list):
            skills_raw = []
        skills = normalize_skills_for_draft([str(s) for s in skills_raw])
        conf = float(data.get("confidence", 0))
        conf = max(0.0, min(1.0, conf))
        draft = ExtractedProjectDraft(
            title=str(data.get("title") or "Untitled project")[:255],
            description=(str(data["description"])[:280] if data.get("description") else None),
            period_start=_parse_iso_date(data.get("period_start")),
            period_end=_parse_iso_date(data.get("period_end")),
            role=str(data["role"]) if data.get("role") else None,
            organization=str(data["organization"]) if data.get("organization") else None,
            problem=str(data["problem"]) if data.get("problem") else None,
            actions=str(data["actions"]) if data.get("actions") else None,
            results=str(data["results"]) if data.get("results") else None,
            metrics=draft_metrics_from_parsed(data),
            skills=skills,
            confidence=conf,
        )
    except (TypeError, ValueError) as exc:
        await finish_agent_run(
            db,
            run,
            status="failed",
            output={"text": raw_text},
            error=str(exc),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=Decimal("0"),
        )
        await db.flush()
        raise HTTPException(status_code=502, detail="AI returned malformed JSON") from exc

    await finish_agent_run(
        db,
        run,
        status="success",
        output={"text": raw_text},
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=Decimal("0"),
    )
    await db.flush()

    project_id: uuid.UUID | None = None
    if payload.create:
        try:
            create_payload = ProjectCreate(
                title=draft.title[:255],
                description=draft.description,
                period_start=draft.period_start,
                period_end=draft.period_end,
                role=draft.role,
                organization=draft.organization,
                problem=draft.problem,
                actions=draft.actions,
                results=draft.results,
                metrics=draft.metrics,
                skills=draft.skills,
                status="active",
                tags=[],
                extracted_from=payload.source_id,
                confidence="ai_extracted",
            )
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
        _obj, proj = await create_project(
            db,
            user_id=user_id,
            payload=create_payload,
            extracted_by_agent_run_id=run.id,
            confidence_override="ai_extracted",
        )
        project_id = proj.id

    return ExtractProjectResponse(
        draft=draft,
        project_id=project_id,
        agent_run_id=run.id,
        source_id=payload.source_id,
    )
