"""FlightMind MCP server (SCRUM-34, extended in SCRUM-36): four tools over the HTTP API.

Tools: query_tracks, search_events, get_track and get_raw. Descriptions and schemas come from
agent/tools.py, so the agent and this server cannot drift apart.

Built on the low-level mcp Server (mcp>=1.2,<2), not FastMCP. FastMCP cannot take a
parameter named `from` at call time (`from` is a Python keyword); the low-level Server
passes the arguments dict through, so the tools keep the contract's names `from` and `to`.
A failed tool raises, and the client gets isError with the message.
get_track without max_points returns the API body unchanged (the thinning default of 60 is
for the agent only). stdout carries the protocol: log to stderr only.
"""
import logging
import sys
from typing import Any

import httpx
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from agent.api_client import ApiClient
from agent.tools import TOOL_SPECS, mcp_schema, run_tool

logging.basicConfig(stream=sys.stderr, level=logging.INFO)

server: Server = Server("flightmind")

# None in production. Tests set it to an in-process transport.
_transport: httpx.AsyncBaseTransport | None = None


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(name=spec.name, description=spec.description, inputSchema=mcp_schema(spec))
        for spec in TOOL_SPECS
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    api = ApiClient(transport=_transport)
    result = await run_tool(api, name, arguments or {}, for_agent=False)
    if result.is_error:
        data = result.data
        raise ValueError(data.get("error", "Tool failed.") if isinstance(data, dict) else "Tool failed.")
    return result.data


async def run_stdio() -> None:
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main() -> None:
    import anyio

    anyio.run(run_stdio)
