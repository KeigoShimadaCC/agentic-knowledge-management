"""Unit tests for the CSV extractor — uses a real 5-row CSV fixture."""

from __future__ import annotations

from helpers import make_asset, make_db, make_source


def _run(source, db, tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.library_root", tmp_path)
    from kos_worker.extractors import csv_ex as extractor

    return extractor.extract(source, db)


def test_csv_extracts_preview(sample_csv, tmp_path, monkeypatch):
    source = make_source("src-csv-1", asset_id="aid-csv-1")
    asset = make_asset("sample.csv")
    db = make_db(asset)

    result = _run(source, db, tmp_path, monkeypatch)

    assert result["ingestion_status"] == "ready"
    preview = result["preview_data"]
    assert preview["headers"] == ["name", "age", "city"]
    assert len(preview["rows"]) == 5
    assert preview["rows"][0]["name"] == "Person0"
    assert preview["rows"][4]["city"] == "Tokyo"


def test_csv_returns_error_when_no_asset_id(tmp_path, monkeypatch):
    source = make_source("src-csv-2", asset_id=None)
    db = make_db(None)
    result = _run(source, db, tmp_path, monkeypatch)
    assert result["ingestion_status"] == "error"


def test_csv_returns_error_when_file_missing(tmp_path, monkeypatch):
    source = make_source("src-csv-3", asset_id="aid-csv-3")
    asset = make_asset("no_such_file.csv")
    db = make_db(asset)
    result = _run(source, db, tmp_path, monkeypatch)
    assert result["ingestion_status"] == "error"
