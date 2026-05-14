#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== Python API tests ==="
PYTHONPATH=services/api uv run pytest tests/api -v

echo ""
echo "=== All checks passed ==="
