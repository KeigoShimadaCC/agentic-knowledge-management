from __future__ import annotations

import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server

from .client import KosApiClient
from .config import McpSettings
from .tools import register_tools

settings = McpSettings()


def build_server() -> tuple[Server, KosApiClient]:
    server = Server("knowledgeos")
    client = KosApiClient(settings)
    register_tools(server, client, settings)
    return server, client


def run() -> None:
    """Entry point: kos-mcp CLI command."""
    if not settings.mcp_enabled:
        raise SystemExit(
            "MCP server is disabled. Set MCP_ENABLED=true to enable."
        )
    server, client = build_server()

    async def _run() -> None:
        async with client:
            async with stdio_server() as (read_stream, write_stream):
                await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(_run())
