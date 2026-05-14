import logging
import uuid

from redis import Redis
from rq import Queue

from app.config import settings

logger = logging.getLogger(__name__)

SEARCH_QUEUE_NAME = "kos-ingest"


def enqueue_reindex_object(object_id: uuid.UUID | str) -> bool:
    object_id_str = str(object_id)
    try:
        queue = Queue(SEARCH_QUEUE_NAME, connection=Redis.from_url(settings.redis_url))
        queue.enqueue(
            "kos_worker.tasks.reindex_object",
            object_id_str,
            job_id=f"reindex-{object_id_str}",
        )
        return True
    except Exception:
        logger.warning(
            "Failed to enqueue search reindex for object %s",
            object_id_str,
            exc_info=True,
        )
        return False
