"""Unit tests for the CSV extractor — uses real CSV fixtures."""

from __future__ import annotations

from helpers import make_asset, make_db, make_source, write_asset_file


def _run(source, db, tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.library_root", tmp_path)
    from kos_worker.extractors import csv_ex as extractor

    return extractor.extract(source, db)


def test_csv_extracts_preview(sample_csv, tmp_path, monkeypatch):
    storage_path = "assets/ab/sample.csv"
    write_asset_file(tmp_path, storage_path, sample_csv.read_bytes())

    source = make_source("src-csv-1", asset_id="aid-csv-1")
    asset = make_asset(storage_path)
    db = make_db(asset)

    result = _run(source, db, tmp_path, monkeypatch)

    assert result["ingestion_status"] == "ready"
    preview = result["preview_data"]
    assert preview["headers"] == ["name", "age", "city"]
    assert len(preview["rows"]) == 5
    assert preview["rows"][0]["name"] == "Person0"
    assert preview["rows"][4]["city"] == "Tokyo"


def test_csv_handles_utf8_bom(sample_csv_bom, tmp_path, monkeypatch):
    storage_path = "assets/ab/bom.csv"
    write_asset_file(tmp_path, storage_path, sample_csv_bom.read_bytes())

    source = make_source("src-csv-bom", asset_id="aid-csv-bom")
    asset = make_asset(storage_path)
    db = make_db(asset)

    result = _run(source, db, tmp_path, monkeypatch)

    assert result["ingestion_status"] == "ready"
    assert result["preview_data"]["headers"] == ["name", "score"]
    assert result["preview_data"]["rows"][0]["name"] == "Alice"


def test_csv_handles_quoted_fields(sample_csv_quoted, tmp_path, monkeypatch):
    storage_path = "assets/ab/quoted.csv"
    write_asset_file(tmp_path, storage_path, sample_csv_quoted.read_bytes())

    source = make_source("src-csv-quoted", asset_id="aid-csv-quoted")
    asset = make_asset(storage_path)
    db = make_db(asset)

    result = _run(source, db, tmp_path, monkeypatch)

    assert result["ingestion_status"] == "ready"
    assert result["preview_data"]["rows"][0]["name"] == "Smith, Jr."
    assert result["preview_data"]["rows"][0]["note"] == "hello"


def test_csv_handles_empty_file(sample_csv_empty, tmp_path, monkeypatch):
    storage_path = "assets/ab/empty.csv"
    write_asset_file(tmp_path, storage_path, sample_csv_empty.read_bytes())

    source = make_source("src-csv-empty", asset_id="aid-csv-empty")
    asset = make_asset(storage_path)
    db = make_db(asset)

    result = _run(source, db, tmp_path, monkeypatch)

    assert result["ingestion_status"] == "ready"
    assert result["preview_data"]["headers"] == []
    assert result["preview_data"]["rows"] == []


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
