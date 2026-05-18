from __future__ import annotations

import asyncio
import fnmatch
import json
import re
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.ai import prompts
from app.ai.client import call_ai
from app.config import settings
from app.mcp_client.adapters import BraveSearchAdapter, Context7Adapter
from app.mcp_client.client import McpClientSession, McpConnectionError
from app.models.agent_run import AgentRun
from app.models.edge import Edge
from app.models.object import KosObject
from app.models.page import Page
from app.models.source import Source
from app.schemas.ai import (
    AnswerResponse,
    Citation,
    EnrichPageResponse,
    ExtractedItem,
    ExtractResponse,
    LinkSuggestion,
    SuggestLinksResponse,
    SummarizeResponse,
    TriageResponse,
    WebCitation,
)
from app.schemas.source import SourceCreate
from app.services import (
    edge_service,
    page_service,
    reindex_service,
    revision_service,
    source_service,
)
from app.services import (
    mcp_connection_service as _mcp_svc,
)
from app.services.search_service import hybrid_search, keyword_search


async def _load_object(db: AsyncSession, user_id: uuid.UUID, object_id: uuid.UUID) -> KosObject:
    result = await db.execute(
        select(KosObject).where(
            KosObject.id == object_id,
            KosObject.user_id == user_id,
            KosObject.deleted_at.is_(None),
        )
    )
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=404, detail="object_not_found")
    return obj


async def _get_content(db: AsyncSession, obj: KosObject) -> str:
    if obj.kind == "page":
        result = await db.execute(select(Page).where(Page.id == obj.id))
        page = result.scalar_one_or_none()
        return (page.content_text or "") if page else ""
    if obj.kind == "source":
        result = await db.execute(select(Source).where(Source.id == obj.id))
        source = result.scalar_one_or_none()
        return (source.extracted_text or "") if source else ""
    return f"{obj.title} {obj.description or ''}"


def _cached_tool_name(tool: dict | object) -> str:
    return tool["name"] if isinstance(tool, dict) else tool.name


def _first_matching_tool(tools: list[dict] | None, patterns: list[str]) -> str | None:
    return next(
        (
            tool_name
            for tool in (tools or [])
            if any(fnmatch.fnmatch(tool_name := _cached_tool_name(tool), p) for p in patterns)
        ),
        None,
    )


async def summarize_object(
    db: AsyncSession,
    user_id: uuid.UUID,
    object_id: uuid.UUID,
    force: bool = False,
) -> SummarizeResponse:
    obj = await _load_object(db, user_id, object_id)

    if not force and obj.metadata_.get("ai_summary"):
        cached_run_id = obj.metadata_.get("ai_summary_run_id", str(uuid.uuid4()))
        return SummarizeResponse(
            summary=obj.metadata_["ai_summary"],
            agent_run_id=uuid.UUID(cached_run_id),
            cached=True,
        )

    content = await _get_content(db, obj)
    if not content.strip():
        raise HTTPException(status_code=422, detail="no_content_to_summarize")

    template = prompts.SUMMARIZE_PAGE if obj.kind == "page" else prompts.SUMMARIZE_SOURCE
    messages = [{"role": "user", "content": template.format(content=content[:8000])}]
    summary_text, run = await call_ai(
        db,
        user_id=user_id,
        agent_type="summarize",
        messages=messages,
        input_context={"object_id": str(object_id)},
    )

    before = dict(obj.metadata_)
    obj.metadata_ = {
        **obj.metadata_,
        "ai_summary": summary_text,
        "ai_summary_model": run.model,
        "ai_summary_at": datetime.now(UTC).isoformat(),
        "ai_summary_run_id": str(run.id),
    }
    flag_modified(obj, "metadata_")

    await revision_service.create_revision(
        db,
        object_id=obj.id,
        user_id=user_id,
        changed_by="summarize",
        before_snapshot=before,
        after_snapshot=obj.metadata_,
        agent_run_id=run.id,
    )
    await db.commit()
    return SummarizeResponse(summary=summary_text, agent_run_id=run.id, cached=False)


async def extract_claims(
    db: AsyncSession, user_id: uuid.UUID, object_id: uuid.UUID
) -> ExtractResponse:
    return await _extract(db, user_id, object_id, "claim", "extract_claims", prompts.EXTRACT_CLAIMS)


async def extract_tasks(
    db: AsyncSession, user_id: uuid.UUID, object_id: uuid.UUID
) -> ExtractResponse:
    return await _extract(db, user_id, object_id, "task", "extract_tasks", prompts.EXTRACT_TASKS)


async def _extract(
    db: AsyncSession,
    user_id: uuid.UUID,
    object_id: uuid.UUID,
    kind: str,
    agent_type: str,
    prompt_template: str,
) -> ExtractResponse:
    obj = await _load_object(db, user_id, object_id)
    content = await _get_content(db, obj)
    if not content.strip():
        raise HTTPException(status_code=422, detail="no_content_to_extract")

    messages = [{"role": "user", "content": prompt_template.format(content=content[:8000])}]
    raw, run = await call_ai(
        db,
        user_id=user_id,
        agent_type=agent_type,
        messages=messages,
        temperature=0.1,
        input_context={"object_id": str(object_id)},
    )

    try:
        items = json.loads(raw)
        if not isinstance(items, list):
            items = []
    except json.JSONDecodeError:
        items = []

    created: list[ExtractedItem] = []
    for item in items[:10]:
        title = (item.get("text") or item.get("title") or "")[:200].strip()
        if not title:
            continue
        new_obj = KosObject(
            user_id=user_id,
            kind=kind,
            title=title,
            metadata_={
                "ai_generated": True,
                "source_object_id": str(object_id),
                "ai_run_id": str(run.id),
            },
            ai_generated=True,
        )
        db.add(new_obj)
        await db.flush()

        edge = Edge(
            user_id=user_id,
            source_id=object_id,
            target_id=new_obj.id,
            kind="mentions",
        )
        db.add(edge)
        created.append(ExtractedItem(id=new_obj.id, title=title))

    await db.commit()
    return ExtractResponse(items=created, agent_run_id=run.id)


async def suggest_links(
    db: AsyncSession,
    user_id: uuid.UUID,
    object_id: uuid.UUID,
    limit: int = 5,
) -> SuggestLinksResponse:
    obj = await _load_object(db, user_id, object_id)
    content = await _get_content(db, obj)
    query = f"{obj.title} {obj.description or ''} {content[:300]}".strip()

    kw_results = await keyword_search(db, user_id, query, limit=20)

    edges_result = await db.execute(
        select(Edge).where(
            or_(Edge.source_id == object_id, Edge.target_id == object_id),
            Edge.deleted_at.is_(None),
        )
    )
    linked_ids: set[str] = set()
    for edge in edges_result.scalars().all():
        linked_ids.add(str(edge.source_id))
        linked_ids.add(str(edge.target_id))

    candidates = [
        r for r in kw_results if str(r.id) != str(object_id) and str(r.id) not in linked_ids
    ][:15]

    if not candidates:
        noop_run = AgentRun(
            user_id=user_id,
            status="success",
            agent_type="suggest_links",
            input={},
            output={"text": "[]"},
            model="none",
            finished_at=datetime.now(UTC),
        )
        db.add(noop_run)
        await db.flush()
        await db.commit()
        return SuggestLinksResponse(suggestions=[], agent_run_id=noop_run.id)

    candidate_text = "\n".join(
        f"id={r.id} title={r.title} kind={r.kind} snippet={r.snippet or ''}" for r in candidates
    )
    messages = [
        {
            "role": "user",
            "content": prompts.SUGGEST_LINKS.format(
                title=obj.title,
                content=content[:500],
                candidates=candidate_text,
                limit=limit,
            ),
        }
    ]
    raw, run = await call_ai(
        db,
        user_id=user_id,
        agent_type="suggest_links",
        messages=messages,
        temperature=0.2,
        input_context={"object_id": str(object_id)},
    )

    try:
        raw_suggestions = json.loads(raw)
        if not isinstance(raw_suggestions, list):
            raw_suggestions = []
    except json.JSONDecodeError:
        raw_suggestions = []

    candidate_map = {str(r.id): r for r in candidates}
    suggestions: list[LinkSuggestion] = []
    for s in raw_suggestions[:limit]:
        tid = str(s.get("target_id", ""))
        cand = candidate_map.get(tid)
        if cand is None:
            continue
        suggestions.append(
            LinkSuggestion(
                target_id=cand.id,
                target_title=cand.title,
                target_kind=cand.kind,
                reason=str(s.get("reason", ""))[:300],
                confidence=min(1.0, max(0.0, float(s.get("confidence", 0.5)))),
            )
        )

    await db.commit()
    return SuggestLinksResponse(suggestions=suggestions, agent_run_id=run.id)


async def answer_question(
    db: AsyncSession,
    user_id: uuid.UUID,
    q: str,
    kind: str | None = None,
    limit: int = 8,
    object_ids: list[uuid.UUID] | None = None,
    use_web_search: bool = False,
) -> AnswerResponse:
    results, _ = await hybrid_search(db, user_id, q, kind=kind, limit=limit)
    if not results:
        results_kw = await keyword_search(db, user_id, q, kind=kind, limit=limit)
        results = results_kw  # type: ignore[assignment]

    if object_ids:
        id_set = {str(oid) for oid in object_ids}
        results = [r for r in results if str(r.id) in id_set]

    web_citations: list[dict] = []
    warning: str | None = None

    if use_web_search:
        max_score = max((r.score for r in results), default=0.0)
        if max_score < settings.mcp_web_search_threshold:
            brave_patterns = getattr(
                BraveSearchAdapter, "mcp_name_patterns", BraveSearchAdapter.patterns
            )
            preferred = settings.mcp_web_search_connection_name
            web_conn = await _mcp_svc.find_connection_for_patterns(
                db, user_id, brave_patterns, preferred_name=preferred
            )
            if web_conn is not None:
                matched_tool = _first_matching_tool(web_conn.capabilities, brave_patterns)
                if matched_tool:
                    try:
                        async with McpClientSession(web_conn, timeout=20) as session:
                            raw = await session.call_tool(matched_tool, {"query": q})
                        adapter = BraveSearchAdapter()
                        inputs = adapter.adapt(raw, "source")
                        for item in inputs:
                            if hasattr(item, "url") and item.url:
                                web_citations.append(
                                    {
                                        "title": item.title or item.url,
                                        "url": item.url,
                                        "snippet": (item.extracted_text or "")[:200] or None,
                                    }
                                )
                    except (McpConnectionError, asyncio.TimeoutError):
                        warning = "web_search_unavailable"
            else:
                warning = "web_search_unavailable"

    context_parts = [f"[{r.id}] {r.title}\n{r.snippet or ''}" for r in results[:limit]]

    if web_citations:
        web_ctx = "\n\n".join(
            f"{c['title']}\n{c.get('snippet') or ''}\nURL: {c['url']}" for c in web_citations
        )
        prompt = prompts.ANSWER_QUESTION_WITH_WEB.format(
            question=q,
            kb_context="\n\n".join(context_parts),
            web_context=web_ctx,
        )
    else:
        prompt = prompts.ANSWER_QUESTION.format(question=q, context="\n\n".join(context_parts))

    messages = [
        {
            "role": "user",
            "content": prompt,
        }
    ]
    answer_text, run = await call_ai(
        db,
        user_id=user_id,
        agent_type="answer",
        messages=messages,
        temperature=0.2,
        input_context={"q": q},
    )

    result_map = {str(r.id): r for r in results}
    citations: list[Citation] = []
    source_match = re.search(r"Sources:\s*\[([^\]]+)\]", answer_text)
    if source_match:
        for sid in re.split(r"[,\s]+", source_match.group(1)):
            sid = sid.strip()
            r = result_map.get(sid)
            if r:
                citations.append(
                    Citation(
                        object_id=r.id,
                        title=r.title,
                        kind=r.kind,
                        snippet=r.snippet.text if r.snippet else None,
                    )
                )

    await db.commit()
    return AnswerResponse(
        answer=answer_text,
        citations=citations,
        agent_run_id=run.id,
        context_count=len(results),
        web_citations=[WebCitation(**c) for c in web_citations],
        warning=warning,
    )


async def triage_object(
    db: AsyncSession,
    user_id: uuid.UUID,
    object_id: uuid.UUID,
) -> TriageResponse:
    obj = await _load_object(db, user_id, object_id)
    content = await _get_content(db, obj)

    messages = [
        {
            "role": "user",
            "content": prompts.TRIAGE_OBJECT.format(title=obj.title, content=content[:4000]),
        }
    ]
    raw, run = await call_ai(
        db,
        user_id=user_id,
        agent_type="triage",
        messages=messages,
        temperature=0.2,
        input_context={"object_id": str(object_id)},
    )

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {}

    await db.commit()
    return TriageResponse(
        suggested_tags=parsed.get("suggested_tags", [])[:5],
        suggested_title=parsed.get("suggested_title"),
        summary=parsed.get("summary", ""),
        agent_run_id=run.id,
    )


def _extract_context7_library_id(raw: dict) -> str | None:
    """Extract the first Context7-compatible library ID from a resolve-library-id response."""
    for part in raw.get("content") or []:
        text = part.get("text", "") if isinstance(part, dict) else str(part)
        m = re.search(r"Context7-compatible library ID:\s*(\S+)", text)
        if m:
            return m.group(1)
    return None


async def enrich_page_with_context7(
    db: AsyncSession,
    user_id: uuid.UUID,
    page_id: uuid.UUID,
    query: str,
) -> EnrichPageResponse:
    page_obj = await page_service.get_page_or_404(db, page_id, user_id)

    ctx7_patterns = getattr(Context7Adapter, "mcp_name_patterns", Context7Adapter.patterns)
    ctx7_conn = await _mcp_svc.find_connection_for_patterns(db, user_id, ctx7_patterns)
    if ctx7_conn is None:
        raise HTTPException(
            status_code=422,
            detail="no_context7_connection: Configure a Context7 MCP connection first.",
        )

    resolve_patterns = ["resolve-library*", "resolve_library*"]
    query_patterns = ["query-docs*", "get_library_docs*", "context7*"]
    resolve_tool = _first_matching_tool(ctx7_conn.capabilities, resolve_patterns)
    query_tool = _first_matching_tool(ctx7_conn.capabilities, query_patterns)
    if resolve_tool is None and query_tool is None:
        raise HTTPException(
            status_code=422,
            detail="no_context7_connection: No matching tool found.",
        )

    started_at = datetime.now(UTC)
    sources_created: list[uuid.UUID] = []
    edges_created: list[uuid.UUID] = []

    try:
        lib_id: str | None = None
        async with McpClientSession(ctx7_conn, timeout=60) as session:
            if resolve_tool and query_tool:
                resolve_raw = await session.call_tool(
                    resolve_tool, {"libraryName": query, "query": query}
                )
                lib_id = _extract_context7_library_id(resolve_raw)
                effective_lib_id = lib_id or query
                raw = await session.call_tool(
                    query_tool,
                    {
                        "context7CompatibleLibraryID": effective_lib_id,
                        "query": query,
                        "tokens": 3000,
                    },
                )
            elif query_tool:
                raw = await session.call_tool(query_tool, {"query": query, "tokens": 3000})
            else:
                raw = await session.call_tool(resolve_tool, {"libraryName": query, "query": query})

        ctx7_base_url = (
            f"https://context7.com{lib_id}" if lib_id and lib_id.startswith("/") else None
        )

        adapter = Context7Adapter()
        inputs = adapter.adapt(raw, "source")

        for item in inputs:
            title = (
                item.title
                if item.title and not item.title.startswith("MCP result ")
                else f"Context7 docs: {query}"
            )
            sc = SourceCreate(
                source_type="web",
                title=title,
                description=None,
                tags=[],
                url=item.url or ctx7_base_url or f"https://context7.com/search?q={query}",
            )
            kos_obj, _source, _job = await source_service.create_source(db, user_id, sc)
            sources_created.append(kos_obj.id)

            edge = await edge_service.create_edge(
                db,
                source_id=page_obj.id,
                target_id=kos_obj.id,
                kind="cites",
                user_id=user_id,
            )
            edges_created.append(edge.id)

        await db.flush()

        run = AgentRun(
            user_id=user_id,
            status="success",
            agent_type="mcp:enrich_page_context7",
            input={"page_id": str(page_id), "query": query, "connection_id": str(ctx7_conn.id)},
            output={"sources_created": [str(s) for s in sources_created]},
            error=None,
            model="mcp",
            started_at=started_at,
            finished_at=datetime.now(UTC),
        )
        db.add(run)
        await db.flush()
        await db.commit()

        for oid in sources_created:
            reindex_service.enqueue_reindex_object(oid)

        return EnrichPageResponse(
            sources_created=sources_created,
            edges_created=edges_created,
            agent_run_id=run.id,
        )

    except (McpConnectionError, asyncio.TimeoutError) as exc:
        run = AgentRun(
            user_id=user_id,
            status="failed",
            agent_type="mcp:enrich_page_context7",
            input={"page_id": str(page_id), "query": query},
            output=None,
            error=str(exc),
            model="mcp",
            started_at=started_at,
            finished_at=datetime.now(UTC),
        )
        db.add(run)
        await db.commit()
        raise HTTPException(status_code=422, detail=f"MCP call failed: {exc}") from exc
