from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
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
from app.models.page import Page
from app.models.project import Project
from app.models.source import Source
from app.schemas.career_ai import (
    GenerateInterviewStoryRequest,
    GenerateInterviewStoryResponse,
    GenerateResumeBulletsRequest,
    GenerateResumeBulletsResponse,
    StarStory,
)
from app.services.agent_run_service import finish_agent_run
from app.services.career_ai_prompts import PROMPT_VERSION
from app.services.settings_service import prompt_template

SNIPPET_LIMIT = 1500


@dataclass(frozen=True)
class EvidenceItem:
    object_id: uuid.UUID
    kind: str
    title: str
    snippet: str


async def _load_project(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
) -> tuple[KosObject, Project]:
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
    if row is None:
        raise HTTPException(status_code=404, detail="project_not_found")
    return row[0], row[1]


async def _load_evidence_object(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    object_id: uuid.UUID,
) -> KosObject | None:
    result = await db.execute(
        select(KosObject).where(
            KosObject.id == object_id,
            KosObject.user_id == user_id,
            KosObject.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def _snippet_for_object(db: AsyncSession, obj: KosObject) -> str:
    text = ""
    if obj.kind == "page":
        page = await db.get(Page, obj.id)
        text = page.content_text if page else ""
    elif obj.kind == "source":
        source = await db.get(Source, obj.id)
        text = source.extracted_text if source and source.extracted_text else ""
    elif obj.kind == "chat":
        chat = await db.get(Chat, obj.id)
        text = chat.content_text if chat else ""

    if not text:
        text = f"{obj.title}\n{obj.description or ''}".strip()
    return text[:SNIPPET_LIMIT]


async def _evidence_item_for_object(db: AsyncSession, obj: KosObject) -> EvidenceItem:
    return EvidenceItem(
        object_id=obj.id,
        kind=obj.kind,
        title=obj.title,
        snippet=await _snippet_for_object(db, obj),
    )


async def _gather_evidence(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    project: Project,
    max_evidence_objects: int,
) -> list[EvidenceItem]:
    objects: list[KosObject] = []
    seen: set[uuid.UUID] = set()

    if project.extracted_from is not None:
        extracted = await _load_evidence_object(
            db, user_id=user_id, object_id=project.extracted_from
        )
        if extracted is not None:
            objects.append(extracted)
            seen.add(extracted.id)

    remaining = max_evidence_objects - len(objects)
    if remaining > 0:
        stmt = (
            select(KosObject)
            .join(Edge, Edge.source_id == KosObject.id)
            .where(
                Edge.target_id == project.id,
                Edge.kind == "belongs_to_project",
                Edge.deleted_at.is_(None),
                KosObject.user_id == user_id,
                KosObject.deleted_at.is_(None),
            )
            .order_by(KosObject.is_pinned.desc(), KosObject.updated_at.desc())
            .limit(max_evidence_objects)
        )
        result = await db.execute(stmt)
        for obj in result.scalars().all():
            if obj.id in seen:
                continue
            objects.append(obj)
            seen.add(obj.id)
            if len(objects) >= max_evidence_objects:
                break

    return [await _evidence_item_for_object(db, obj) for obj in objects[:max_evidence_objects]]


def _project_payload(obj: KosObject, project: Project) -> dict[str, Any]:
    return {
        "id": str(project.id),
        "title": obj.title,
        "description": obj.description,
        "period_start": project.period_start.isoformat() if project.period_start else None,
        "period_end": project.period_end.isoformat() if project.period_end else None,
        "role": project.role,
        "organization": project.organization,
        "problem": project.problem,
        "actions": project.actions,
        "results": project.results,
        "metrics": project.metrics or {},
        "skills": project.skills or [],
        "status": project.status,
        "confidence": project.confidence,
    }


def _evidence_payload(evidence: list[EvidenceItem]) -> list[dict[str, str]]:
    return [
        {
            "object_id": str(item.object_id),
            "kind": item.kind,
            "title": item.title,
            "snippet": item.snippet,
        }
        for item in evidence
    ]


def _user_message(project_data: dict[str, Any], evidence: list[EvidenceItem]) -> str:
    return json.dumps(
        {"project": project_data, "evidence": _evidence_payload(evidence)},
        ensure_ascii=False,
    )


async def _mark_malformed(db: AsyncSession, run: AgentRun, raw: str, error: str) -> None:
    await finish_agent_run(
        db,
        run,
        status="failed",
        output={"text": raw},
        error=error,
        input_tokens=run.input_tokens,
        output_tokens=run.output_tokens,
        cost_usd=run.cost_usd,
    )
    await db.flush()
    await db.commit()


def _parse_json_object(raw: str) -> dict[str, Any]:
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("not_object")
    return parsed


async def generate_resume_bullets(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: GenerateResumeBulletsRequest,
) -> GenerateResumeBulletsResponse:
    obj, project = await _load_project(db, user_id=user_id, project_id=payload.project_id)
    evidence = await _gather_evidence(
        db,
        user_id=user_id,
        project=project,
        max_evidence_objects=payload.max_evidence_objects,
    )
    project_data = _project_payload(obj, project)
    system = (await prompt_template(db, user_id, "career.resume_bullets")).format(
        prompt_version=PROMPT_VERSION,
        count=payload.count,
        max_evidence_objects=payload.max_evidence_objects,
        target_role=payload.target_role or "not specified",
        emphasis=payload.emphasis or "not specified",
    )
    raw, run = await call_ai(
        db,
        user_id=user_id,
        agent_type="generate_resume_bullets",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": _user_message(project_data, evidence)},
        ],
        temperature=0.3,
        input_context={
            "project_id": str(payload.project_id),
            "target_role": payload.target_role,
            "emphasis": payload.emphasis,
            "count": payload.count,
            "evidence_object_count": len(evidence),
            "prompt_version": PROMPT_VERSION,
        },
        response_format={"type": "json_object"},
    )

    try:
        parsed = _parse_json_object(raw)
        response = GenerateResumeBulletsResponse(
            project_id=payload.project_id,
            bullets=parsed.get("bullets", []),
            agent_run_id=run.id,
            evidence_count=len(evidence),
        )
    except (json.JSONDecodeError, ValueError, TypeError, ValidationError) as exc:
        await _mark_malformed(db, run, raw, str(exc))
        raise HTTPException(status_code=502, detail="AI returned malformed JSON") from exc

    return response


async def generate_interview_story(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: GenerateInterviewStoryRequest,
) -> GenerateInterviewStoryResponse:
    obj, project = await _load_project(db, user_id=user_id, project_id=payload.project_id)
    evidence = await _gather_evidence(
        db,
        user_id=user_id,
        project=project,
        max_evidence_objects=payload.max_evidence_objects,
    )
    project_data = _project_payload(obj, project)
    system = (await prompt_template(db, user_id, "career.interview_story")).format(
        prompt_version=PROMPT_VERSION,
        max_evidence_objects=payload.max_evidence_objects,
        max_words=payload.max_words,
        question_type=payload.question_type,
        target_role=payload.target_role or "not specified",
    )
    raw, run = await call_ai(
        db,
        user_id=user_id,
        agent_type="generate_interview_story",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": _user_message(project_data, evidence)},
        ],
        temperature=0.3,
        input_context={
            "project_id": str(payload.project_id),
            "target_role": payload.target_role,
            "question_type": payload.question_type,
            "max_words": payload.max_words,
            "evidence_object_count": len(evidence),
            "prompt_version": PROMPT_VERSION,
        },
        response_format={"type": "json_object"},
    )

    try:
        parsed = _parse_json_object(raw)
        story = StarStory.model_validate(parsed)
        word_count = sum(
            len(part.split()) for part in (story.situation, story.task, story.action, story.result)
        )
        response = GenerateInterviewStoryResponse(
            project_id=payload.project_id,
            story=story,
            agent_run_id=run.id,
            word_count=word_count,
        )
    except (json.JSONDecodeError, ValueError, TypeError, ValidationError) as exc:
        await _mark_malformed(db, run, raw, str(exc))
        raise HTTPException(status_code=502, detail="AI returned malformed JSON") from exc

    return response
