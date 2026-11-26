"""The four MCP tools (SCRUM-36), through a real in-memory MCP session against the mock API."""
import json

import httpx
import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_server import server as server_mod
from mock_api.app import app as mock_app


async def call(name, args):
    server_mod._transport = httpx.ASGITransport(app=mock_app)
    try:
        async with create_connected_server_and_client_session(server_mod.server) as session:
            return await session.call_tool(name, args)
    finally:
        server_mod._transport = None


def body(result):
    return json.loads(result.content[0].text)


@pytest.mark.anyio
async def test_lists_exactly_four_tools_with_from_and_to():
    async with create_connected_server_and_client_session(server_mod.server) as session:
        tools = {t.name: t for t in (await session.list_tools()).tools}
    assert list(tools) == ["query_tracks", "search_events", "get_track", "get_raw"]
    assert {"from", "to"} <= set(tools["query_tracks"].inputSchema["properties"])
    assert tools["get_raw"].inputSchema["required"] == ["raw_ref"]
    assert "at least one" in tools["query_tracks"].description


@pytest.mark.anyio
async def test_search_events_runs():
    result = await call("search_events", {"type": "go_around"})
    assert not result.isError
    assert body(result)["count"] == 2


@pytest.mark.anyio
async def test_query_tracks_runs():
    result = await call("query_tracks", {"callsign": "LNI456"})
    assert not result.isError
    assert body(result)["aircraft"][0]["points_in_window"] > 0


@pytest.mark.anyio
async def test_get_track_unchanged_without_max_points_and_thinned_with_it():
    full = body(await call("get_track", {"icao24": "8A1C07"}))
    assert len(full["points"]) == 90 and "thinned" not in full
    thin = body(await call("get_track", {"icao24": "8A1C07", "max_points": 20}))
    assert thin["returned_points"] == 20 and thin["total_points"] == 90


@pytest.mark.anyio
async def test_get_raw_runs_and_unknown_is_error():
    ok = await call("get_raw", {"raw_ref": "rec01:0"})
    assert not ok.isError and body(ok)["raw_ref"] == "rec01:0"
    bad = await call("get_raw", {"raw_ref": "nope"})
    assert bad.isError
