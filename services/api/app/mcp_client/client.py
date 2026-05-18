"""On-demand MCP client session (spawn-call-kill per use)."""

import asyncio
import json
import os
from contextlib import AsyncExitStack, suppress

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client

from app.core.url_safety import UnsafeUrlError, validate_safe_http_url
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
        self._stack = None
        self._mcp_session = None

    async def __aenter__(self):
        if self._conn.transport in ("sse", "http"):
            try:
                validate_safe_http_url(self._conn.url)
            except UnsafeUrlError as exc:
                raise McpConnectionError(f"unsafe MCP URL: {exc}") from exc
            self._stack = AsyncExitStack()
            try:
                if self._conn.transport == "http":
                    read, write, _ = await self._stack.enter_async_context(
                        streamablehttp_client(url=self._conn.url)
                    )
                else:
                    read, write = await self._stack.enter_async_context(
                        sse_client(url=self._conn.url)
                    )
                self._mcp_session = await self._stack.enter_async_context(
                    ClientSession(read, write)
                )
                await self._mcp_session.initialize()
            except Exception:
                await self._stack.aclose()
                self._stack = None
                self._mcp_session = None
                raise
            return self

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
        if self._stack is not None:
            await self._stack.aclose()
            self._stack = None
            self._mcp_session = None
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
        if self._mcp_session is not None:
            tools_result = await self._mcp_session.list_tools()
            return [
                {"name": tool.name, "description": tool.description or ""}
                for tool in tools_result.tools
            ]

        req_id = self._next_id()
        await self._send({"jsonrpc": "2.0", "id": req_id, "method": "tools/list", "params": {}})
        resp = await self._recv()
        if "error" in resp:
            raise McpConnectionError(str(resp["error"]))
        return resp.get("result", {}).get("tools", [])

    async def call_tool(self, tool_name: str, args: dict) -> dict:
        if self._mcp_session is not None:
            result = await self._mcp_session.call_tool(tool_name, arguments=args)
            if hasattr(result, "model_dump"):
                return result.model_dump(by_alias=True, exclude_none=True)
            return {"content": [self._serialize_mcp_value(item) for item in result.content]}

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

    def _serialize_mcp_value(self, value):
        if hasattr(value, "model_dump"):
            return value.model_dump(by_alias=True, exclude_none=True)
        return value
