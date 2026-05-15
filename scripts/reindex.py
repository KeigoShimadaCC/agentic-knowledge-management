#!/usr/bin/env python3
"""Enqueue chunk/vector reindex jobs for one or more objects.

Usage:
    PYTHONPATH=services/api:services/worker uv run python scripts/reindex.py --all
    PYTHONPATH=services/api:services/worker uv run python scripts/reindex.py <uuid> [<uuid> ...]
"""
from __future__ import annotations

import sys
import uuid


def main() -> int:
    from kos_worker.tasks import enqueue_reindex_object, reindex_all_objects

    if len(sys.argv) == 1 or sys.argv[1] == "--all":
        result = reindex_all_objects()
        print(f"Enqueued {result['enqueued']} objects for reindex.")
        return 0

    for arg in sys.argv[1:]:
        try:
            oid = uuid.UUID(arg)
        except ValueError:
            print(f"Invalid UUID: {arg}", file=sys.stderr)
            return 1
        enqueue_reindex_object(str(oid))
        print(f"Enqueued {oid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
