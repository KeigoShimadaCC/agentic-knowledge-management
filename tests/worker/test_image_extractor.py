"""Unit tests for the image extractor — uses a real 100×60 PNG fixture."""
from __future__ import annotations

import pathlib

import pytest

from helpers import make_asset, make_db, make_source


def _run(source, db, tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.library_root", tmp_path)
    from kos_worker.extractors import image as extractor
    return extractor.extract(source, db)


def test_image_extracts_dimensions(sample_image, tmp_path, monkeypatch):
    # sample_image is at tmp_path/sample.png (fixture from conftest)
    source = make_source("src-img-1", asset_id="aid-img-1")
    asset = make_asset("sample.png")
    db = make_db(asset)

    result = _run(source, db, tmp_path, monkeypatch)

    assert result["ingestion_status"] == "ready"
    assert result["preview_data"]["width"] == 100
    assert result["preview_data"]["height"] == 60


def test_image_creates_thumbnail(sample_image, tmp_path, monkeypatch):
    source = make_source("src-img-2", asset_id="aid-img-2")
    asset = make_asset("sample.png")
    db = make_db(asset)

    result = _run(source, db, tmp_path, monkeypatch)

    assert result["ingestion_status"] == "ready"
    thumb_path = tmp_path / "sources" / "src-img-2" / "thumbnail.jpg"
    assert thumb_path.exists(), "thumbnail.jpg was not created"
    assert result["thumbnail_path"] == "sources/src-img-2/thumbnail.jpg"


def test_image_returns_error_when_no_asset_id(tmp_path, monkeypatch):
    source = make_source("src-img-3", asset_id=None)
    db = make_db(None)
    result = _run(source, db, tmp_path, monkeypatch)
    assert result["ingestion_status"] == "error"


def test_image_returns_error_when_file_missing(tmp_path, monkeypatch):
    source = make_source("src-img-4", asset_id="aid-img-4")
    asset = make_asset("does_not_exist.png")
    db = make_db(asset)
    result = _run(source, db, tmp_path, monkeypatch)
    assert result["ingestion_status"] == "error"
