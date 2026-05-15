"""Shared helper factories for worker extractor unit tests."""
from __future__ import annotations

from unittest.mock import MagicMock


def make_source(source_id: str, asset_id: str | None = None, url: str | None = None) -> MagicMock:
    src = MagicMock()
    src.id = source_id
    src.asset_id = asset_id
    src.url = url
    return src


def make_asset(storage_path: str) -> MagicMock:
    asset = MagicMock()
    asset.storage_path = storage_path
    asset.width = None
    asset.height = None
    return asset


def make_db(asset: MagicMock | None) -> MagicMock:
    db = MagicMock()
    db.get.return_value = asset
    return db
