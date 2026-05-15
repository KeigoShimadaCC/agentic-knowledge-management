from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.search import HybridSearchResult, SearchResult, SearchSnippet

# Sentinels chosen to never appear in user content; used with ts_headline so
# we can parse highlight ranges without injecting HTML into API responses.
_SNIPPET_OPTS = f"MaxWords=30, MinWords=10, StartSel={chr(1)}, StopSel={chr(2)}"


def _parse_snippet(raw: str) -> SearchSnippet:
    """Convert sentinel-delimited ts_headline output to plain text + ranges."""
    text_parts: list[str] = []
    highlights: list[tuple[int, int]] = []
    pos = 0
    i = 0
    while i < len(raw):
        if raw[i] == "\x01":
            try:
                j = raw.index("\x02", i + 1)
            except ValueError:
                text_parts.append(raw[i + 1 :])
                break
            word = raw[i + 1 : j]
            highlights.append((pos, pos + len(word)))
            text_parts.append(word)
            pos += len(word)
            i = j + 1
        else:
            text_parts.append(raw[i])
            pos += 1
            i += 1
    return SearchSnippet(text="".join(text_parts), highlights=highlights)


async def keyword_search(
    db: AsyncSession,
    user_id: uuid.UUID,
    q: str,
    kind: str | None = None,
    source_type: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[SearchResult]:
    kinds = _resolve_kinds(kind)
    rows: list[SearchResult] = []

    if not kind or "page" in kinds:
        rows.extend(await _fts_pages(db, user_id, q, limit, offset))
    if not kind or "source" in kinds:
        rows.extend(await _fts_sources(db, user_id, q, source_type, limit, offset))
    if not kind or "chat" in kinds:
        rows.extend(await _fts_chats(db, user_id, q, limit, offset))
    if not kind or "asset" in kinds:
        rows.extend(await _fts_assets(db, user_id, q, limit, offset))

    generic_kinds = sorted(kinds.intersection({"claim", "task"}))
    if generic_kinds:
        rows.extend(await _fts_generic_objects(db, user_id, q, generic_kinds, limit, offset))

    rows.sort(key=lambda r: r.score, reverse=True)
    return rows[:limit]


async def vector_search(
    db: AsyncSession,
    user_id: uuid.UUID,
    q: str,
    kind: str | None = None,
    source_type: str | None = None,
    limit: int = 20,
    score_threshold: float | None = None,
) -> list[SearchResult]:
    from app.search import qdrant_client as qc
    from app.search.embedding import get_embedding_provider

    provider = get_embedding_provider()
    if not provider.is_enabled:
        return []

    vectors = await provider.embed([q])
    filter_conditions: dict = {}
    if kind:
        filter_conditions["object_kind"] = kind
    if source_type:
        filter_conditions["source_type"] = source_type

    hits = await qc.search_vectors(
        query_vector=vectors[0],
        limit=limit * 2,
        score_threshold=score_threshold,
        filter_conditions=filter_conditions or None,
    )

    if not hits:
        return []

    object_ids = list({h["payload"]["object_id"] for h in hits})
    obj_map = await _load_objects_by_ids(db, user_id, object_ids)
    source_map = await _load_sources_by_ids(
        db, [oid for oid in object_ids if obj_map.get(oid) and obj_map[oid].kind == "source"]
    )  # noqa: E501

    results: list[SearchResult] = []
    seen: set[str] = set()
    for hit in hits:
        oid = hit["payload"]["object_id"]
        if oid in seen:
            continue
        obj = obj_map.get(oid)
        if obj is None:
            continue
        seen.add(oid)
        source = source_map.get(oid)
        raw_content = hit["payload"].get("content", "")[:300]
        results.append(
            SearchResult(
                id=obj.id,
                kind=obj.kind,
                title=obj.title,
                snippet=SearchSnippet(text=raw_content, highlights=[]) if raw_content else None,
                tags=obj.tags or [],
                score=hit["score"],
                updated_at=obj.updated_at,
                source_type=source.source_type if source else None,
                ingestion_status=source.ingestion_status if source else None,
            )
        )
    return results[:limit]


async def hybrid_search(
    db: AsyncSession,
    user_id: uuid.UUID,
    q: str,
    kind: str | None = None,
    source_type: str | None = None,
    limit: int = 20,
) -> tuple[list[HybridSearchResult], bool]:
    """Returns (results, embeddings_used)."""
    from app.search.embedding import get_embedding_provider

    provider = get_embedding_provider()
    embeddings_enabled = provider.is_enabled
    kw_results = await keyword_search(db, user_id, q, kind, source_type, limit * 2)

    if embeddings_enabled:
        try:
            vec_results = await vector_search(db, user_id, q, kind, source_type, limit * 2)
        except Exception:
            vec_results = []
            embeddings_enabled = False
    else:
        vec_results = []

    merged = _merge_results(kw_results, vec_results, limit)
    return merged, embeddings_enabled


def _merge_results(
    kw: list[SearchResult],
    vec: list[SearchResult],
    limit: int,
) -> list[HybridSearchResult]:
    max_kw = max((r.score for r in kw), default=1.0) or 1.0
    max_vec = max((r.score for r in vec), default=1.0) or 1.0

    scores: dict[str, dict] = {}

    for r in kw:
        oid = str(r.id)
        scores.setdefault(oid, {"result": r, "kw": 0.0, "vec": 0.0})
        scores[oid]["kw"] = r.score / max_kw

    for r in vec:
        oid = str(r.id)
        scores.setdefault(oid, {"result": r, "kw": 0.0, "vec": 0.0})
        scores[oid]["vec"] = r.score / max_vec

    now = datetime.now(UTC)
    combined: list[HybridSearchResult] = []
    for oid, data in scores.items():
        r = data["result"]
        kw_score = data["kw"]
        vec_score = data["vec"]
        age = (
            (now - r.updated_at.replace(tzinfo=UTC)) if r.updated_at.tzinfo else timedelta(days=999)
        )  # noqa: E501
        recency = 1.0 if age < timedelta(days=7) else (0.5 if age < timedelta(days=30) else 0.0)
        final = 0.45 * kw_score + 0.45 * vec_score + 0.10 * recency
        combined.append(
            HybridSearchResult(
                id=r.id,
                kind=r.kind,
                title=r.title,
                snippet=r.snippet,
                tags=r.tags,
                score=final,
                updated_at=r.updated_at,
                source_type=r.source_type,
                ingestion_status=r.ingestion_status,
                keyword_score=kw_score,
                vector_score=vec_score,
                recency_boost=recency,
            )
        )

    combined.sort(key=lambda r: r.score, reverse=True)
    return combined[:limit]


async def _fts_pages(
    db: AsyncSession,
    user_id: uuid.UUID,
    q: str,
    limit: int,
    offset: int,
) -> list[SearchResult]:
    sql = text(
        """
        WITH matches AS (
            SELECT
                o.id,
                o.kind,
                o.title,
                o.tags,
                o.updated_at,
                p.content_text,
                to_tsvector(
                    'english', coalesce(o.title,'') || ' ' || coalesce(p.content_text,'')
                ) as vector,
                plainto_tsquery('english', :q) as query
            FROM objects o
            JOIN pages p ON p.id = o.id
            WHERE o.deleted_at IS NULL
              AND o.user_id = :user_id
        )
        SELECT
            id, kind, title, tags, updated_at,
            (
                coalesce(ts_rank_cd(vector, query), 0) +
                (CASE WHEN title ILIKE :q_like THEN 1.0 ELSE 0 END) +
                (CASE WHEN content_text ILIKE :q_like THEN 0.5 ELSE 0 END)
            ) AS score,
            ts_headline(
                'english',
                coalesce(content_text,''),
                query,
                :snippet_opts
            ) AS snippet,
            content_text
        FROM matches
        WHERE vector @@ query
           OR title ILIKE :q_like
           OR content_text ILIKE :q_like
        ORDER BY score DESC
        LIMIT :limit OFFSET :offset
        """
    )
    params = {
        "q": q,
        "q_like": f"%{q}%",
        "user_id": str(user_id),
        "limit": limit,
        "offset": offset,
        "snippet_opts": _SNIPPET_OPTS,
    }
    result = await db.execute(sql, params)
    rows = result.fetchall()
    return [
        SearchResult(
            id=row.id,
            kind=row.kind,
            title=row.title,
            tags=list(row.tags) if row.tags else [],
            score=float(row.score),
            updated_at=row.updated_at,
            snippet=_parse_snippet(row.snippet)
            if row.snippet
            else (
                SearchSnippet(text=row.content_text[:200], highlights=[])
                if row.content_text
                else None
            ),
        )
        for row in rows
    ]


async def _fts_sources(
    db: AsyncSession,
    user_id: uuid.UUID,
    q: str,
    source_type: str | None,
    limit: int,
    offset: int,
) -> list[SearchResult]:
    source_filter = "AND s.source_type = :source_type" if source_type else ""
    sql = text(
        f"""
        WITH matches AS (
            SELECT
                o.id,
                o.kind,
                o.title,
                o.tags,
                o.updated_at,
                s.source_type,
                s.ingestion_status,
                s.extracted_text,
                to_tsvector(
                    'english', coalesce(o.title,'') || ' ' || coalesce(s.extracted_text,'')
                ) as vector,
                plainto_tsquery('english', :q) as query
            FROM objects o
            JOIN sources s ON s.id = o.id
            WHERE o.deleted_at IS NULL
              AND o.user_id = :user_id
              {source_filter}
        )
        SELECT
            id, kind, title, tags, updated_at, source_type, ingestion_status,
            (
                coalesce(ts_rank_cd(vector, query), 0) +
                (CASE WHEN title ILIKE :q_like THEN 1.0 ELSE 0 END) +
                (CASE WHEN extracted_text ILIKE :q_like THEN 0.5 ELSE 0 END)
            ) AS score,
            ts_headline(
                'english',
                coalesce(extracted_text,''),
                query,
                :snippet_opts
            ) AS snippet,
            extracted_text
        FROM matches
        WHERE vector @@ query
           OR title ILIKE :q_like
           OR extracted_text ILIKE :q_like
        ORDER BY score DESC
        LIMIT :limit OFFSET :offset
        """
    )
    params: dict = {
        "q": q,
        "q_like": f"%{q}%",
        "user_id": str(user_id),
        "limit": limit,
        "offset": offset,
        "snippet_opts": _SNIPPET_OPTS,
    }
    if source_type:
        params["source_type"] = source_type
    result = await db.execute(sql, params)
    rows = result.fetchall()
    return [
        SearchResult(
            id=row.id,
            kind=row.kind,
            title=row.title,
            tags=list(row.tags) if row.tags else [],
            score=float(row.score),
            updated_at=row.updated_at,
            snippet=_parse_snippet(row.snippet)
            if row.snippet
            else (
                SearchSnippet(text=row.extracted_text[:200], highlights=[])
                if row.extracted_text
                else None
            ),
            source_type=row.source_type,
            ingestion_status=row.ingestion_status,
        )
        for row in rows
    ]


async def _fts_chats(
    db: AsyncSession,
    user_id: uuid.UUID,
    q: str,
    limit: int,
    offset: int,
) -> list[SearchResult]:
    sql = text(
        """
        WITH matches AS (
            SELECT
                o.id,
                o.kind,
                o.title,
                o.tags,
                o.updated_at,
                c.content_text,
                c.structured_summary,
                to_tsvector(
                    'english',
                    coalesce(o.title,'') || ' ' ||
                    coalesce(c.content_text,'') || ' ' ||
                    coalesce(c.structured_summary::text,'')
                ) as vector,
                plainto_tsquery('english', :q) as query
            FROM objects o
            JOIN chats c ON c.id = o.id
            WHERE o.deleted_at IS NULL
              AND o.user_id = :user_id
        )
        SELECT
            id, kind, title, tags, updated_at,
            (
                coalesce(ts_rank_cd(vector, query), 0) +
                (CASE WHEN title ILIKE :q_like THEN 1.0 ELSE 0 END) +
                (CASE WHEN content_text ILIKE :q_like THEN 0.5 ELSE 0 END) +
                (
                    CASE WHEN coalesce(structured_summary::text,'') ILIKE :q_like
                    THEN 0.5 ELSE 0 END
                )
            ) AS score,
            ts_headline(
                'english',
                coalesce(content_text,'') || ' ' || coalesce(structured_summary::text,''),
                query,
                :snippet_opts
            ) AS snippet,
            content_text
        FROM matches
        WHERE vector @@ query
           OR title ILIKE :q_like
           OR content_text ILIKE :q_like
           OR coalesce(structured_summary::text,'') ILIKE :q_like
        ORDER BY score DESC
        LIMIT :limit OFFSET :offset
        """
    )
    params = {
        "q": q,
        "q_like": f"%{q}%",
        "user_id": str(user_id),
        "limit": limit,
        "offset": offset,
        "snippet_opts": _SNIPPET_OPTS,
    }
    result = await db.execute(sql, params)
    rows = result.fetchall()
    return [
        SearchResult(
            id=row.id,
            kind=row.kind,
            title=row.title,
            tags=list(row.tags) if row.tags else [],
            score=float(row.score),
            updated_at=row.updated_at,
            snippet=_parse_snippet(row.snippet)
            if row.snippet
            else (
                SearchSnippet(text=row.content_text[:200], highlights=[])
                if row.content_text
                else None
            ),
        )
        for row in rows
    ]


async def _fts_assets(
    db: AsyncSession,
    user_id: uuid.UUID,
    q: str,
    limit: int,
    offset: int,
) -> list[SearchResult]:
    sql = text(
        """
        WITH matches AS (
            SELECT
                o.id,
                o.kind,
                o.title,
                o.description,
                o.tags,
                o.updated_at,
                to_tsvector(
                    'english', coalesce(o.title,'') || ' ' || coalesce(o.description,'')
                ) as vector,
                plainto_tsquery('english', :q) as query
            FROM objects o
            WHERE o.deleted_at IS NULL
              AND o.user_id = :user_id
              AND o.kind = 'asset'
        )
        SELECT
            id, kind, title, tags, updated_at,
            (
                coalesce(ts_rank_cd(vector, query), 0) +
                (CASE WHEN title ILIKE :q_like THEN 1.0 ELSE 0 END) +
                (CASE WHEN description ILIKE :q_like THEN 0.5 ELSE 0 END)
            ) AS score,
            ts_headline(
                'english',
                coalesce(description,''),
                query,
                :snippet_opts
            ) AS snippet,
            description
        FROM matches
        WHERE vector @@ query
           OR title ILIKE :q_like
           OR description ILIKE :q_like
        ORDER BY score DESC
        LIMIT :limit OFFSET :offset
        """
    )
    params = {
        "q": q,
        "q_like": f"%{q}%",
        "user_id": str(user_id),
        "limit": limit,
        "offset": offset,
        "snippet_opts": _SNIPPET_OPTS,
    }
    result = await db.execute(sql, params)
    rows = result.fetchall()
    return [
        SearchResult(
            id=row.id,
            kind=row.kind,
            title=row.title,
            tags=list(row.tags) if row.tags else [],
            score=float(row.score),
            updated_at=row.updated_at,
            snippet=_parse_snippet(row.snippet)
            if row.snippet
            else (
                SearchSnippet(text=row.description[:200], highlights=[])
                if row.description
                else None
            ),
        )
        for row in rows
    ]


async def _fts_generic_objects(
    db: AsyncSession,
    user_id: uuid.UUID,
    q: str,
    kinds: list[str],
    limit: int,
    offset: int,
) -> list[SearchResult]:
    sql = text(
        """
        WITH matches AS (
            SELECT
                o.id,
                o.kind,
                o.title,
                o.description,
                o.tags,
                o.updated_at,
                o.metadata,
                to_tsvector('english', 
                    coalesce(o.title,'') || ' ' || 
                    coalesce(o.description,'') || ' ' || 
                    coalesce(o.metadata::text,'')
                ) as vector,
                plainto_tsquery('english', :q) as query
            FROM objects o
            WHERE o.deleted_at IS NULL
              AND o.user_id = :user_id
              AND o.kind = ANY(:kinds)
        )
        SELECT
            id, kind, title, tags, updated_at,
            (
                coalesce(ts_rank_cd(vector, query), 0) +
                (CASE WHEN title ILIKE :q_like THEN 1.0 ELSE 0 END) +
                (CASE WHEN description ILIKE :q_like THEN 0.5 ELSE 0 END)
            ) AS score,
            ts_headline(
                'english',
                coalesce(description,'') || ' ' || coalesce(metadata::text,''),
                query,
                :snippet_opts
            ) AS snippet,
            description,
            metadata
        FROM matches
        WHERE vector @@ query
           OR title ILIKE :q_like
           OR description ILIKE :q_like
        ORDER BY score DESC
        LIMIT :limit OFFSET :offset
        """
    )
    params = {
        "q": q,
        "q_like": f"%{q}%",
        "user_id": str(user_id),
        "kinds": kinds,
        "limit": limit,
        "offset": offset,
        "snippet_opts": _SNIPPET_OPTS,
    }
    result = await db.execute(sql, params)
    rows = result.fetchall()
    return [
        SearchResult(
            id=row.id,
            kind=row.kind,
            title=row.title,
            tags=list(row.tags) if row.tags else [],
            score=float(row.score),
            updated_at=row.updated_at,
            snippet=_parse_snippet(row.snippet)
            if row.snippet
            else (
                SearchSnippet(text=row.description[:200], highlights=[])
                if row.description
                else None
            ),
        )
        for row in rows
    ]


async def _fts_generic_objects(
    db: AsyncSession,
    user_id: uuid.UUID,
    q: str,
    kinds: list[str],
    limit: int,
    offset: int,
) -> list[SearchResult]:
    sql = text(
        """
        SELECT
            o.id,
            o.kind,
            o.title,
            o.tags,
            o.updated_at,
            ts_rank_cd(
                to_tsvector(
                    'english',
                    coalesce(o.title,'') || ' ' ||
                    coalesce(o.description,'') || ' ' ||
                    coalesce(o.metadata::text,'')
                ),
                plainto_tsquery('english', :q)
            ) AS score,
            ts_headline(
                'english',
                coalesce(o.description,'') || ' ' || coalesce(o.metadata::text,''),
                plainto_tsquery('english', :q),
                :snippet_opts
            ) AS snippet
        FROM objects o
        WHERE o.deleted_at IS NULL
          AND o.user_id = :user_id
          AND o.kind = ANY(:kinds)
          AND to_tsvector(
                'english',
                coalesce(o.title,'') || ' ' ||
                coalesce(o.description,'') || ' ' ||
                coalesce(o.metadata::text,'')
              )
              @@ plainto_tsquery('english', :q)
        ORDER BY score DESC
        LIMIT :limit OFFSET :offset
        """
    )
    params = {
        "q": q,
        "user_id": str(user_id),
        "kinds": kinds,
        "limit": limit,
        "offset": offset,
        "snippet_opts": _SNIPPET_OPTS,
    }
    result = await db.execute(sql, params)
    rows = result.fetchall()
    return [
        SearchResult(
            id=row.id,
            kind=row.kind,
            title=row.title,
            tags=list(row.tags) if row.tags else [],
            score=float(row.score),
            updated_at=row.updated_at,
            snippet=_parse_snippet(row.snippet) if row.snippet else None,
        )
        for row in rows
    ]


async def _load_objects_by_ids(db: AsyncSession, user_id: uuid.UUID, ids: list[str]) -> dict:
    if not ids:
        return {}
    from sqlalchemy import select

    from app.models.object import KosObject

    result = await db.execute(
        select(KosObject).where(
            KosObject.id.in_([uuid.UUID(oid) for oid in ids]),
            KosObject.user_id == user_id,
            KosObject.deleted_at.is_(None),
        )
    )
    return {str(obj.id): obj for obj in result.scalars().all()}


async def _load_sources_by_ids(db: AsyncSession, ids: list[str]) -> dict:
    if not ids:
        return {}
    from sqlalchemy import select

    from app.models.source import Source

    result = await db.execute(select(Source).where(Source.id.in_([uuid.UUID(oid) for oid in ids])))
    return {str(s.id): s for s in result.scalars().all()}


def _resolve_kinds(kind: str | None) -> set[str]:
    if kind is None:
        return {"page", "source", "asset", "chat", "claim", "task"}
    return {kind}
