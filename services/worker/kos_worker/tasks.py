from datetime import UTC, datetime
from typing import Any

from app.models.ingestion_job import IngestionJob
from app.models.source import Source

from kos_worker.db import get_session
from kos_worker.extractors import run_extractor


def _now() -> datetime:
    return datetime.now(UTC)


def _apply_source_result(source: Source, result: dict[str, Any]) -> None:
    source_fields = set(Source.__mapper__.attrs.keys())
    for key, value in result.items():
        if key in source_fields:
            setattr(source, key, value)


def ingest_source(job_id: str) -> None:
    db = get_session()
    try:
        job = db.get(IngestionJob, job_id)
        if job is None:
            raise ValueError(f"Ingestion job not found: {job_id}")

        job.status = "running"
        job.started_at = _now()
        job.attempts = (job.attempts or 0) + 1

        source = db.get(Source, job.object_id)
        if source is None:
            raise ValueError(f"Source not found for ingestion job: {job_id}")

        source.ingestion_status = "running"
        db.commit()

        result = run_extractor(source, db)
        _apply_source_result(source, result)

        job.status = "success"
        job.result = result
        job.finished_at = _now()
        db.commit()
    except Exception as exc:
        db.rollback()
        message = str(exc)

        if "job" in locals() and job is not None:
            job.status = "failed"
            job.error = message
            job.finished_at = _now()

        if "source" in locals() and source is not None:
            source.ingestion_status = "error"
            source.error_message = message

        db.commit()
        raise
    finally:
        db.close()
