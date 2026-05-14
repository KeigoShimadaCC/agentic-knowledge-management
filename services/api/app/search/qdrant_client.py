from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.config import settings

if TYPE_CHECKING:
    from qdrant_client import AsyncQdrantClient

logger = logging.getLogger(__name__)

_client: "AsyncQdrantClient | None" = None
_available: bool = False


async def get_client() -> "AsyncQdrantClient":
    global _client
    if _client is None:
        from qdrant_client import AsyncQdrantClient

        _client = AsyncQdrantClient(url=settings.qdrant_url)
    return _client


async def create_collection_if_not_exists() -> bool:
    """Create the knowledgeos_chunks collection. Returns True if Qdrant is reachable."""
    global _available
    try:
        from qdrant_client.models import Distance, VectorParams

        client = await get_client()
        existing = await client.get_collections()
        names = [c.name for c in existing.collections]
        if settings.qdrant_collection not in names:
            await client.create_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=VectorParams(
                    size=settings.embedding_dimension,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("Created Qdrant collection %s", settings.qdrant_collection)
        else:
            logger.info("Qdrant collection %s already exists", settings.qdrant_collection)
        _available = True
        return True
    except Exception as exc:
        logger.warning("Qdrant unavailable at startup: %s - vector search disabled", exc)
        _available = False
        return False


def is_available() -> bool:
    return _available


async def upsert_points(points: list[dict]) -> None:
    """Upsert a list of dicts with keys: id (str UUID), vector (list[float]), payload (dict)."""
    from qdrant_client.models import PointStruct

    client = await get_client()
    structs = [PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"]) for p in points]
    await client.upsert(collection_name=settings.qdrant_collection, points=structs)


async def search_vectors(
    query_vector: list[float],
    limit: int = 20,
    score_threshold: float | None = None,
    filter_conditions: dict | None = None,
) -> list[dict]:
    """Returns list of {id, score, payload}."""
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    client = await get_client()

    qdrant_filter = None
    if filter_conditions:
        must = [
            FieldCondition(key=k, match=MatchValue(value=v)) for k, v in filter_conditions.items()
        ]
        qdrant_filter = Filter(must=must)

    kwargs: dict = {
        "collection_name": settings.qdrant_collection,
        "query_vector": query_vector,
        "limit": limit,
        "with_payload": True,
    }
    if score_threshold is not None:
        kwargs["score_threshold"] = score_threshold
    if qdrant_filter is not None:
        kwargs["query_filter"] = qdrant_filter

    results = await client.search(**kwargs)
    return [{"id": str(r.id), "score": r.score, "payload": r.payload} for r in results]


async def delete_by_object_id(object_id: str) -> None:
    """Delete all Qdrant points whose payload.object_id matches."""
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    client = await get_client()
    await client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=Filter(
            must=[FieldCondition(key="object_id", match=MatchValue(value=object_id))]
        ),
    )
