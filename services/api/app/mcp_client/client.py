"""On-demand MCP client session (spawn-call-kill per use)."""

import asyncio
import json
import os
from contextlib import suppress

from app.mcp_client.crypto import decrypt_env_vars


class McpConnectionError(Exception):
    pass


class McpClientSession:
    """
    Usage:
        async with McpClientSession(conn, timeout=30) as session:
            tools = await session.list_tools()
            result = await session.call_tool("brave_search", {"query": "..."})
    """

    def __init__(self, conn, timeout: int = 30):
        self._conn = conn
        self._timeout = timeout
        self._proc = None
        self._req_id = 0

    async def __aenter__(self):
        if self._conn.transport == "sse":
            raise McpConnectionError("SSE transport not yet supported")
        decrypted = decrypt_env_vars(self._conn.env_vars or {})
        env = {
            key: value
            for key in ("PATH", "HOME", "TMPDIR", "TEMP", "TMP")
            if (value := os.environ.get(key))
        }
        env.update(decrypted)
        self._proc = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                self._conn.command,
                *(self._conn.args or []),
                env=env,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            ),
            timeout=self._timeout,
        )
        await self._handshake()
        return self

    async def __aexit__(self, *_):
        if self._proc is not None and self._proc.returncode is None:
            with suppress(ProcessLookupError):
                self._proc.kill()
            await self._proc.wait()

    async def _send(self, msg: dict) -> None:
        data = json.dumps(msg).encode() + b"\n"
        self._proc.stdin.write(data)
        await self._proc.stdin.drain()

    async def _recv(self) -> dict:
        line = await asyncio.wait_for(self._proc.stdout.readline(), timeout=self._timeout)
        return json.loads(line)

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    async def _handshake(self) -> None:
        req_id = self._next_id()
        await self._send(
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "kos-mcp-client", "version": "1.0"},
                },
            }
        )
        resp = await self._recv()
        if "error" in resp:
            raise McpConnectionError(str(resp["error"]))
        await self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    async def list_tools(self) -> list[dict]:
        req_id = self._next_id()
        await self._send({"jsonrpc": "2.0", "id": req_id, "method": "tools/list", "params": {}})
        resp = await self._recv()
        if "error" in resp:
            raise McpConnectionError(str(resp["error"]))
        return resp.get("result", {}).get("tools", [])

    async def call_tool(self, tool_name: str, args: dict) -> dict:
        req_id = self._next_id()
        await self._send(
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": args},
            }
        )
        resp = await self._recv()
        if "error" in resp:
            raise McpConnectionError(str(resp["error"]))
        return resp.get("result", {})
