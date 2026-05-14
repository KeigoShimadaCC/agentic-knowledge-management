from app.models.source import Source
from sqlalchemy.orm import Session


def run_extractor(source: Source, db: Session) -> dict:
    stype = source.source_type
    if stype == "pdf":
        from kos_worker.extractors import pdf as extractor
    elif stype == "image":
        from kos_worker.extractors import image as extractor
    elif stype == "csv":
        from kos_worker.extractors import csv_ex as extractor
    elif stype == "youtube":
        from kos_worker.extractors import youtube as extractor
    elif stype == "web":
        from kos_worker.extractors import web as extractor
    else:
        from kos_worker.extractors import file_ as extractor

    return extractor.extract(source, db)
