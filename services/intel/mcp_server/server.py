"""FlightMind MCP server (SCRUM-34): one tool, get_track.

Built on the low-level mcp Server (mcp>=1.2,<2), not FastMCP. FastMCP cannot take a
parameter named `from` at call time (`from` is a Python keyword); the low-level Server
passes the arguments dict through, so the tool keeps the contract's names `from` and `to`.
A TrackError raised in the handler comes back to the client as isError with its message.
stdout carries the protocol: log to stderr only.
"""
import logging
import sys
from typing import Any

import httpx
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from mcp_server.client import fetch_track

logging.basicConfig(stream=sys.stderr, level=logging.INFO)

server: Server = Server("flightmind")

# None in production. Tests set it to an in-process transport.
_transport: httpx.AsyncBaseTransport | None = None

DESCRIPTION = (
    "Get the 4D track (time, latitude, longitude, altitude in feet) of one aircraft from the "
    "FlightMind API. icao24 is the 6-character hex Mode S address, for example 8A0F21. "
    "from and to are optional ISO 8601 date-times, for example 2026-11-12T08:00:00Z. "
    "Every point has a raw_ref (<recording_file_id>:<record_index>); cite it for any claim "
    "made from that point."
)

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "icao24": {"type": "string", "description": "6-character hex aircraft address, e.g. 8A0F21"},
        "from": {"type": "string", "description": "Optional ISO 8601 start time"},
        "to": {"type": "string", "description": "Optional ISO 8601 end time"},
    },
    "required": ["icao24"],
}


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [types.Tool(name="get_track", description=DESCRIPTION, inputSchema=INPUT_SCHEMA)]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    if name != "get_track":
        raise ValueError(f"Unknown tool '{name}'. This server only has get_track.")
    args = arguments or {}
    return await fetch_track(
        args.get("icao24", ""), args.get("from"), args.get("to"), transport=_transport
    )


async def run_stdio() -> None:
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main() -> None:
    import anyio

    anyio.run(run_stdio)
