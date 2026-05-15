"""Shared pytest fixtures for worker extractor unit tests.

All fixtures are fully in-memory or tmp_path based — no DB, no Redis, no network.
"""

from __future__ import annotations

import csv
import pathlib
import sys

import pytest
from PIL import Image

# Ensure helpers.py in this directory is importable as a plain module
sys.path.insert(0, str(pathlib.Path(__file__).parent))


@pytest.fixture()
def sample_image(tmp_path: pathlib.Path) -> pathlib.Path:
    """100×60 PNG written with Pillow."""
    img = Image.new("RGB", (100, 60), color=(255, 0, 0))
    p = tmp_path / "sample.png"
    img.save(p, "PNG")
    return p


@pytest.fixture()
def sample_exif_image(tmp_path: pathlib.Path) -> pathlib.Path:
    """Portrait pixels stored with EXIF orientation 6 (displayed as 100×60)."""
    img = Image.new("RGB", (60, 100), color=(0, 0, 255))
    exif = img.getexif()
    exif[274] = 6
    p = tmp_path / "exif-oriented.jpg"
    img.save(p, "JPEG", exif=exif)
    return p


@pytest.fixture()
def sample_csv(tmp_path: pathlib.Path) -> pathlib.Path:
    """5-row CSV with headers name, age, city."""
    p = tmp_path / "sample.csv"
    with open(p, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "age", "city"])
        writer.writeheader()
        for i in range(5):
            writer.writerow({"name": f"Person{i}", "age": str(20 + i), "city": "Tokyo"})
    return p


@pytest.fixture()
def sample_csv_bom(tmp_path: pathlib.Path) -> pathlib.Path:
    p = tmp_path / "bom.csv"
    p.write_text("\ufeffname,score\nAlice,99\n", encoding="utf-8")
    return p


@pytest.fixture()
def sample_csv_quoted(tmp_path: pathlib.Path) -> pathlib.Path:
    p = tmp_path / "quoted.csv"
    p.write_text('name,note\n"Smith, Jr.",hello\n', encoding="utf-8")
    return p


@pytest.fixture()
def sample_csv_empty(tmp_path: pathlib.Path) -> pathlib.Path:
    p = tmp_path / "empty.csv"
    p.write_bytes(b"")
    return p


@pytest.fixture()
def sample_pdf_reportlab(tmp_path: pathlib.Path) -> pathlib.Path:
    """Two-page PDF with known text (≤100KB) generated via reportlab."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    p = tmp_path / "report.pdf"
    pdf = canvas.Canvas(str(p), pagesize=letter)
    pdf.drawString(72, 720, "Page one text here.")
    pdf.showPage()
    pdf.drawString(72, 720, "Page two content.")
    pdf.showPage()
    pdf.save()
    return p


@pytest.fixture()
def corrupt_pdf(tmp_path: pathlib.Path) -> pathlib.Path:
    p = tmp_path / "corrupt.pdf"
    p.write_bytes(b"%PDF-1.4\n%%EOF\nnot-valid-structure")
    return p
