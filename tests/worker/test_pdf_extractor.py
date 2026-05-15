"""Unit tests for the PDF extractor — fully mocked, no real PDF file needed."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from helpers import make_asset, make_db, make_source


def _run(source, db, tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.library_root", tmp_path)
    from kos_worker.extractors import pdf as extractor

    return extractor.extract(source, db)


def _mock_reader(pages_text: list[str], has_image: bool = False) -> MagicMock:
    mock_pages = []
    for i, text in enumerate(pages_text):
        page = MagicMock()
        page.extract_text.return_value = text
        if i == 0 and has_image:
            img_data = MagicMock()
            img_data.data = b"\x89PNG\r\n\x1a\n"  # PNG magic bytes placeholder
            page.images = [img_data]
        else:
            page.images = []
        mock_pages.append(page)
    reader = MagicMock()
    reader.pages = mock_pages
    return reader


def test_pdf_extracts_text_and_page_count(tmp_path, monkeypatch):
    sid = "src-pdf-1"
    aid = "asset-pdf-1"
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n%%EOF")  # dummy bytes — pypdf is mocked

    source = make_source(sid, asset_id=aid)
    asset = make_asset("test.pdf")
    db = make_db(asset)

    mock_reader = _mock_reader(["Page one text here.", "Page two content."])

    with patch("pypdf.PdfReader", return_value=mock_reader):
        result = _run(source, db, tmp_path, monkeypatch)

    assert result["ingestion_status"] == "ready"
    assert result["page_count"] == 2
    assert "Page one text here." in result["extracted_text"]
    assert "Page two content." in result["extracted_text"]


def test_pdf_handles_empty_pages(tmp_path, monkeypatch):
    sid = "src-pdf-2"
    pdf_file = tmp_path / "empty.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n%%EOF")

    source = make_source(sid, asset_id="aid-2")
    asset = make_asset("empty.pdf")
    db = make_db(asset)

    mock_reader = _mock_reader(["", ""])

    with patch("pypdf.PdfReader", return_value=mock_reader):
        result = _run(source, db, tmp_path, monkeypatch)

    assert result["ingestion_status"] == "ready"
    assert result.get("extracted_text") is None


def test_pdf_returns_error_when_no_asset_id(tmp_path, monkeypatch):
    source = make_source("src-pdf-noasset", asset_id=None)
    db = make_db(None)
    result = _run(source, db, tmp_path, monkeypatch)
    assert result["ingestion_status"] == "error"
    assert "asset_id" in result["error_message"]


def test_pdf_returns_error_when_asset_missing(tmp_path, monkeypatch):
    source = make_source("src-pdf-3", asset_id="gone")
    db = make_db(None)  # db.get returns None
    result = _run(source, db, tmp_path, monkeypatch)
    assert result["ingestion_status"] == "error"


def test_pdf_returns_error_when_file_not_found(tmp_path, monkeypatch):
    source = make_source("src-pdf-4", asset_id="aid-4")
    asset = make_asset("nonexistent.pdf")
    db = make_db(asset)
    result = _run(source, db, tmp_path, monkeypatch)
    assert result["ingestion_status"] == "error"
    assert "not found" in result["error_message"].lower()
