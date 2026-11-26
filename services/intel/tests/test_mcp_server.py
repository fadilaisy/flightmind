"""Tests for the SCRUM-34 MCP server (get_track). Backend: the mock API, in process."""
import json
from pathlib import Path

import httpx
import jsonschema
import pytest
import yaml
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_server import client as client_mod
from mcp_server import server as server_mod
from mcp_server.client import DEFAULT_BASE, TrackError, api_base, fetch_track
from mock_api.app import app as mock_app

SPEC = yaml.safe_load((Path(__file__).parents[3] / "contracts" / "openapi.yaml").read_text(encoding="utf-8"))
KNOWN = "8A0F21"


@pytest.fixture
def anyio_backend():
    return "asyncio"


def inline(node):
    """Resolve $refs and turn OpenAPI 3.0 `nullable` into JSON Schema."""
    if isinstance(node, list):
        return [inline(n) for n in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        return inline(SPEC["components"]["schemas"][node["$ref"].split("/")[-1]])
    out = {k: inline(v) for k, v in node.items()}
    if out.pop("nullable", False) and "type" in out:
        out["type"] = [out["type"], "null"]
    return out


def track_schema():
    return inline(SPEC["paths"]["/api/tracks/{icao24}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"])


def mock_transport():
    return httpx.ASGITransport(app=mock_app)


class Recorder:
    """MockTransport handler that records requests and answers with a fixed response."""

    def __init__(self, response=None, error=None):
        self.requests = []
        self.response = response
        self.error = error

    def __call__(self, request):
        self.requests.append(request)
        if self.error:
            raise self.error
        return self.response

    def transport(self):
        return httpx.MockTransport(self)


async def call(tool_args, transport):
    """Call get_track through a real in-memory MCP client session."""
    server_mod._transport = transport
    try:
        async with create_connected_server_and_client_session(server_mod.server) as session:
            return await session.call_tool("get_track", tool_args)
    finally:
        server_mod._transport = None


def text_of(result):
    return result.content[0].text


async def direct_track(icao24=KNOWN, query=""):
    async with httpx.AsyncClient(transport=mock_transport(), base_url="http://test") as c:
        r = await c.get(f"/api/tracks/{icao24}{query}")
        assert r.status_code == 200
        return r.json()


# --- tool list, success, raw_ref ----------------------------------------------------

@pytest.mark.anyio
async def test_tool_list_is_exactly_get_track():
    async with create_connected_server_and_client_session(server_mod.server) as session:
        tools = (await session.list_tools()).tools
    assert [t.name for t in tools] == ["query_tracks", "search_events", "get_track", "get_raw"]
    schema = next(t for t in tools if t.name == "get_track").inputSchema
    assert schema["required"] == ["icao24"]
    assert set(schema["properties"]) == {"icao24", "from", "to", "max_points"}


@pytest.mark.anyio
async def test_result_validates_against_track_schema():
    result = await call({"icao24": KNOWN}, mock_transport())
    assert not result.isError
    body = json.loads(text_of(result))
    jsonschema.validate(body, track_schema())
    assert body["points"]


@pytest.mark.anyio
async def test_raw_refs_equal_api_in_same_order():
    result = await call({"icao24": KNOWN}, mock_transport())
    got = [p["raw_ref"] for p in json.loads(text_of(result))["points"]]
    want = [p["raw_ref"] for p in (await direct_track())["points"]]
    assert got == want and len(got) > 0


@pytest.mark.anyio
async def test_body_is_unchanged():
    result = await call({"icao24": KNOWN}, mock_transport())
    assert json.loads(text_of(result)) == await direct_track()


# --- from / to -----------------------------------------------------------------------

@pytest.mark.anyio
async def test_from_and_to_sent_as_query_and_narrow_points():
    full = await direct_track()
    start, end = full["points"][10]["ts"], full["points"][20]["ts"]
    result = await call({"icao24": KNOWN, "from": start, "to": end}, mock_transport())
    narrowed = json.loads(text_of(result))
    assert 0 < len(narrowed["points"]) < len(full["points"])
    assert narrowed == await direct_track(query=f"?from={start}&to={end}")

    rec = Recorder(response=httpx.Response(200, json={"icao24": KNOWN, "points": []}))
    await call({"icao24": KNOWN, "from": start, "to": end}, rec.transport())
    params = dict(rec.requests[0].url.params)
    assert params == {"from": start, "to": end}


@pytest.mark.anyio
async def test_no_times_means_no_query_string():
    rec = Recorder(response=httpx.Response(200, json={"icao24": KNOWN, "points": []}))
    await call({"icao24": KNOWN}, rec.transport())
    assert rec.requests[0].url.query == b""


# --- base URL --------------------------------------------------------------------------

def test_api_base_default_when_unset_or_empty(monkeypatch):
    monkeypatch.delenv("FLIGHTMIND_API_BASE", raising=False)
    assert api_base() == DEFAULT_BASE == "http://localhost:8000"
    monkeypatch.setenv("FLIGHTMIND_API_BASE", "")
    assert api_base() == DEFAULT_BASE


def test_api_base_override_strips_trailing_slash(monkeypatch):
    monkeypatch.setenv("FLIGHTMIND_API_BASE", "http://api.example:9000/")
    assert api_base() == "http://api.example:9000"


@pytest.mark.anyio
async def test_requests_go_to_configured_base(monkeypatch):
    monkeypatch.setenv("FLIGHTMIND_API_BASE", "http://api.example:9000")
    rec = Recorder(response=httpx.Response(200, json={"icao24": KNOWN, "points": []}))
    await call({"icao24": KNOWN}, rec.transport())
    assert str(rec.requests[0].url).startswith("http://api.example:9000/api/tracks/")


# --- errors ------------------------------------------------------------------------------

@pytest.mark.anyio
async def test_unknown_icao24_is_error_naming_it():
    result = await call({"icao24": "ZZZZZZ"}, mock_transport())
    assert result.isError
    assert "ZZZZZZ" in text_of(result)


@pytest.mark.anyio
@pytest.mark.parametrize("error", [httpx.ConnectError("refused"), httpx.ReadTimeout("slow")])
async def test_unreachable_is_error_with_base_url(error, monkeypatch):
    monkeypatch.setenv("FLIGHTMIND_API_BASE", "http://api.example:9000")
    result = await call({"icao24": KNOWN}, Recorder(error=error).transport())
    assert result.isError
    assert "http://api.example:9000" in text_of(result)
    assert "FLIGHTMIND_API_BASE" in text_of(result)


@pytest.mark.anyio
@pytest.mark.parametrize("status,body,expect", [
    (422, {"detail": "bad date"}, "bad date"),
    (500, {"detail": "boom"}, "boom"),
    (500, None, "500"),
])
async def test_other_statuses_are_errors_with_code(status, body, expect):
    response = httpx.Response(status, json=body) if body else httpx.Response(status, text="oops")
    result = await call({"icao24": KNOWN}, Recorder(response=response).transport())
    assert result.isError
    assert str(status) in text_of(result) and expect in text_of(result)


@pytest.mark.anyio
async def test_non_json_200_is_error():
    rec = Recorder(response=httpx.Response(200, text="not json"))
    result = await call({"icao24": KNOWN}, rec.transport())
    assert result.isError
    assert "not valid JSON" in text_of(result)


@pytest.mark.anyio
async def test_server_keeps_working_after_an_error():
    async with create_connected_server_and_client_session(server_mod.server) as session:
        server_mod._transport = mock_transport()
        try:
            bad = await session.call_tool("get_track", {"icao24": "ZZZZZZ"})
            good = await session.call_tool("get_track", {"icao24": KNOWN})
        finally:
            server_mod._transport = None
    assert bad.isError and not good.isError


@pytest.mark.anyio
async def test_timeout_is_ten_seconds(monkeypatch):
    seen = {}
    real = httpx.AsyncClient

    def spy(*a, **kw):
        seen.update(kw)
        return real(*a, **kw)

    monkeypatch.setattr(client_mod.httpx, "AsyncClient", spy)
    rec = Recorder(response=httpx.Response(200, json={"icao24": KNOWN, "points": []}))
    await fetch_track(KNOWN, transport=rec.transport())
    assert seen["timeout"] == 10.0


# --- input safety ------------------------------------------------------------------------

@pytest.mark.anyio
@pytest.mark.parametrize("value,encoded", [("../meta", b"..%2Fmeta"), ("a/b", b"a%2Fb")])
async def test_icao24_stays_one_path_segment(value, encoded):
    rec = Recorder(response=httpx.Response(404, json={"detail": "Unknown icao24"}))
    result = await call({"icao24": value}, rec.transport())
    assert result.isError
    assert len(rec.requests) == 1
    assert rec.requests[0].url.raw_path == b"/api/tracks/" + encoded


@pytest.mark.anyio
@pytest.mark.parametrize("value", ["", "   "])
async def test_empty_icao24_makes_no_request(value):
    rec = Recorder(response=httpx.Response(200, json={}))
    result = await call({"icao24": value}, rec.transport())
    assert result.isError
    assert rec.requests == []


@pytest.mark.anyio
async def test_fetch_track_raises_track_error_directly():
    with pytest.raises(TrackError):
        await fetch_track("")
