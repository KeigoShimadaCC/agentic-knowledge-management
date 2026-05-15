"""Shared pytest fixtures for worker extractor unit tests.

All fixtures are fully in-memory or tmp_path based — no DB, no Redis, no network.
"""
from __future__ import annotations

import csv
import pathlib
import sys
import uuid

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
def sample_csv(tmp_path: pathlib.Path) -> pathlib.Path:
    """5-row CSV with headers name, age, city."""
    p = tmp_path / "sample.csv"
    with open(p, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "age", "city"])
        writer.writeheader()
        for i in range(5):
            writer.writerow({"name": f"Person{i}", "age": str(20 + i), "city": "Tokyo"})
    return p
