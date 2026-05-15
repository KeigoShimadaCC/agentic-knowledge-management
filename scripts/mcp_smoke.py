#!/usr/bin/env python
"""Phase 7B MCP write-tools E2E smoke harness.

Usage:
    MCP_ENABLED=true MCP_ALLOW_WRITE_TOOLS=true uv run scripts/mcp_smoke.py

Requires the API to be running (default: http://localhost:8000) and Postgres
reachable (DATABASE_URL or default). Registers a throw-away smoke user, spawns
kos-mcp via stdio, exercises all 6 write tools, then queries Postgres directly
to verify agent_runs and object_revisions were created.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import asyncpg
import httpx

API_URL = os.getenv("MCP_API_BASE_URL", os.getenv("KOS_API_BASE_URL", "http://localhost:8000"))
DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://kos:kospass@localhost:5432/knowledgeos",
)
INTERNAL_TOKEN = os.getenv("MCP_INTERNAL_TOKEN", "smoke-test-secret")
LIBRARY_ROOT = Path(
    os.getenv("LIBRARY_ROOT", str(Path.home() / "KnowledgeOS" / "library"))
)

_SMOKE_EMAIL = "mcp-smoke@example.com"
_SMOKE_PASS = "smoke-pass-12345"


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

async def ensure_smoke_user() -> None:
    async with httpx.AsyncClient(base_url=API_URL, timeout=10) as client:
        r = await client.post(
            "/api/v1/auth/register",
            json={"email": _SMOKE_EMAIL, "password": _SMOKE_PASS, "display_name": "Smoke"},
        )
        if r.status_code in (200, 201):
            return
        if r.status_code == 400:
            # Already registered — that's fine
            return
        r.raise_for_status()


# ---------------------------------------------------------------------------
# MCP stdio helpers
# ---------------------------------------------------------------------------

async def _write(proc: asyncio.subprocess.Process, msg: dict) -> None:
    line = json.dumps(msg) + "\n"
    proc.stdin.write(line.encode())
    await proc.stdin.drain()


async def _read(proc: asyncio.subprocess.Process, timeout: float = 15.0) -> dict:
    raw = await asyncio.wait_for(proc.stdout.readline(), timeout=timeout)
    return json.loads(raw)


async def rpc(
    proc: asyncio.subprocess.Process,
    method: str,
    params: dict,
    req_id: int,
    timeout: float = 15.0,
) -> dict:
    await _write(proc, {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})
    return await _read(proc, timeout=timeout)


def _text(resp: dict) -> str:
    """Extract the first TextContent text from a tools/call response."""
    content = resp.get("result", {}).get("content", [])
    if content:
        return content[0].get("text", "")
    return ""


def _json(resp: dict) -> dict:
    try:
        return json.loads(_text(resp))
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

async def run() -> None:
    results: list[tuple[str, bool, str]] = []  # (label, ok, detail)

    def check(label: str, ok: bool, detail: str = "") -> None:
        results.append((label, ok, detail))
        mark = "✓" if ok else "✗"
        suffix = f"  ({detail})" if detail and not ok else ""
        print(f"  {mark}  {label}{suffix}")

    print("\nRegistering smoke user …")
    await ensure_smoke_user()

    env = {
        **os.environ,
        "MCP_ENABLED": "true",
        "MCP_ALLOW_WRITE_TOOLS": "true",
        "MCP_ALLOW_FILE_ACCESS": "true",
        "MCP_INTERNAL_TOKEN": INTERNAL_TOKEN,
        "MCP_API_BASE_URL": API_URL,
    }

    # Build kos-mcp command (works both inside the worktree and CI)
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    mcp_project = repo_root / "services" / "mcp"

    cmd = ["uv", "run", "--project", str(mcp_project), "kos-mcp"]

    print("Spawning kos-mcp …")
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        env=env,
    )

    req_id = 0

    try:
        # ── 1. Initialize handshake ──────────────────────────────────────────
        req_id += 1
        init_resp = await rpc(
            proc,
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "smoke", "version": "1.0"},
            },
            req_id=req_id,
        )
        initialized = "result" in init_resp
        check("initialize handshake", initialized, str(init_resp.get("error", "")))

        # Send initialized notification (no response expected)
        await _write(proc, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

        # ── 2. tools/list ────────────────────────────────────────────────────
        req_id += 1
        list_resp = await rpc(proc, "tools/list", {}, req_id=req_id)
        tool_names = [t["name"] for t in list_resp.get("result", {}).get("tools", [])]
        write_expected = {"create_page", "update_page", "create_edge", "archive_object", "ingest_url", "ingest_file"}
        found_write = write_expected & set(tool_names)
        check("tools/list ≥ 13 tools", len(tool_names) >= 13, f"got {len(tool_names)}")
        check("all 6 write tools listed", found_write == write_expected, f"missing: {write_expected - found_write}")

        # ── 3. create_page ───────────────────────────────────────────────────
        req_id += 1
        cp_resp = await rpc(
            proc,
            "tools/call",
            {"name": "create_page", "arguments": {"title": "Smoke Page A", "content_text": "Phase 7B smoke."}},
            req_id=req_id,
        )
        cp_data = _json(cp_resp)
        page_id = cp_data.get("id", "")
        check("create_page returns id", bool(page_id), _text(cp_resp)[:100])

        # ── 4. update_page ───────────────────────────────────────────────────
        req_id += 1
        up_resp = await rpc(
            proc,
            "tools/call",
            {"name": "update_page", "arguments": {"page_id": page_id, "title": "Smoke Page A (updated)"}},
            req_id=req_id,
        )
        up_data = _json(up_resp)
        check("update_page ok", "error" not in up_data and up_data.get("id"), _text(up_resp)[:100])

        # ── 5. create_page (second, for edge target) ─────────────────────────
        req_id += 1
        cp2_resp = await rpc(
            proc,
            "tools/call",
            {"name": "create_page", "arguments": {"title": "Smoke Page B"}},
            req_id=req_id,
        )
        page_id_b = _json(cp2_resp).get("id", page_id)

        # ── 6. create_edge ───────────────────────────────────────────────────
        req_id += 1
        ce_resp = await rpc(
            proc,
            "tools/call",
            {"name": "create_edge", "arguments": {"source_id": page_id, "target_id": page_id_b, "kind": "related_to"}},
            req_id=req_id,
        )
        ce_data = _json(ce_resp)
        check("create_edge ok", bool(ce_data.get("id")), _text(ce_resp)[:100])

        # ── 7. archive_object ────────────────────────────────────────────────
        req_id += 1
        ao_resp = await rpc(
            proc,
            "tools/call",
            {"name": "archive_object", "arguments": {"object_id": page_id_b, "reason": "smoke test"}},
            req_id=req_id,
        )
        ao_data = _json(ao_resp)
        check("archive_object ok", ao_data.get("is_archived") is True, _text(ao_resp)[:100])

        # ── 8. ingest_url ────────────────────────────────────────────────────
        req_id += 1
        iu_resp = await rpc(
            proc,
            "tools/call",
            {
                "name": "ingest_url",
                "arguments": {
                    "url": "https://en.wikipedia.org/wiki/Python_(programming_language)",
                    "source_type": "web",
                    "title": "Python Wikipedia",
                },
            },
            req_id=req_id,
        )
        iu_data = _json(iu_resp)
        check("ingest_url ok", bool(iu_data.get("id")), _text(iu_resp)[:100])

        # ── 9. ingest_file ───────────────────────────────────────────────────
        smoke_file = LIBRARY_ROOT / "smoke_test_input.csv"
        smoke_file.parent.mkdir(parents=True, exist_ok=True)
        smoke_file.write_text("col_a,col_b\nPhase,7B\nSmoke,Test\n")
        try:
            req_id += 1
            if_resp = await rpc(
                proc,
                "tools/call",
                {
                    "name": "ingest_file",
                    "arguments": {
                        "file_path": str(smoke_file),
                        "source_type": "csv",
                        "title": "Smoke CSV",
                    },
                },
                req_id=req_id,
            )
            if_data = _json(if_resp)
            check("ingest_file ok", bool(if_data.get("id")), _text(if_resp)[:100])
        finally:
            smoke_file.unlink(missing_ok=True)

    finally:
        proc.stdin.close()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5)
        except asyncio.TimeoutError:
            proc.kill()

    # ── 10. DB verification ──────────────────────────────────────────────────
    import hashlib

    print("\nVerifying Postgres audit rows …")
    # agent_type is derived from the internal token when no X-KOS-Agent-Id header is sent
    expected_agent_type = "shared:" + hashlib.sha256(INTERNAL_TOKEN.encode()).hexdigest()[:16]
    conn = await asyncpg.connect(DB_URL)
    try:
        run_count = await conn.fetchval(
            "SELECT count(*) FROM agent_runs WHERE agent_type = $1"
            " AND created_at > now() - interval '5 minutes'",
            expected_agent_type,
        )
        rev_count = await conn.fetchval(
            "SELECT count(*) FROM object_revisions WHERE agent_run_id IS NOT NULL"
            " AND created_at > now() - interval '5 minutes'"
        )
        check("agent_runs rows written", run_count >= 1, f"found {run_count}")
        check("object_revisions rows written", rev_count >= 1, f"found {rev_count}")
    finally:
        await conn.close()

    # ── Summary ──────────────────────────────────────────────────────────────
    width = 60
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print()
    print("=" * width)
    print(f"  Phase 7B MCP Write Tools — Smoke Test  ({passed}/{total})")
    print("=" * width)
    if passed == total:
        print("  ALL CHECKS PASSED")
        sys.exit(0)
    else:
        failed = [(lbl, det) for lbl, ok, det in results if not ok]
        for lbl, det in failed:
            print(f"  FAIL  {lbl}" + (f": {det}" if det else ""))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run())
