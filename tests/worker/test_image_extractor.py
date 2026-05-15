"""Unit tests for the image extractor — uses real Pillow fixtures."""

from __future__ import annotations

from helpers import make_asset, make_db, make_source, write_asset_file


def _run(source, db, tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.library_root", tmp_path)
    from kos_worker.extractors import image as extractor

    return extractor.extract(source, db)


def test_image_extracts_dimensions(sample_image, tmp_path, monkeypatch):
    source = make_source("src-img-1", asset_id="aid-img-1")
    asset = make_asset("sample.png")
    db = make_db(asset)

    result = _run(source, db, tmp_path, monkeypatch)

    assert result["ingestion_status"] == "ready"
    assert result["preview_data"]["width"] == 100
    assert result["preview_data"]["height"] == 60


def test_image_applies_exif_orientation_before_thumbnail(sample_exif_image, tmp_path, monkeypatch):
    storage_path = "assets/ab/exif.jpg"
    write_asset_file(tmp_path, storage_path, sample_exif_image.read_bytes())

    source = make_source("src-img-exif", asset_id="aid-exif")
    asset = make_asset(storage_path)
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


def test_image_returns_error_for_non_image_bytes(tmp_path, monkeypatch):
    storage_path = "assets/ab/not-image.bin"
    write_asset_file(tmp_path, storage_path, b"not an image at all")

    source = make_source("src-img-bad", asset_id="aid-bad")
    asset = make_asset(storage_path)
    db = make_db(asset)

    result = _run(source, db, tmp_path, monkeypatch)

    assert result["ingestion_status"] == "error"
    assert result["error_message"]


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
