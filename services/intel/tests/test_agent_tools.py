"""Tests for ApiClient and the four tools (SCRUM-36). Backend: the mock API, in process."""
import asyncio
import json

import httpx
import pytest

from agent import api_client as api_client_mod
from agent import tools
from agent.api_client import ApiClient, ApiError
from mock_api.app import app as mock_app

KNOWN = "8A0F21"


def api():
    return ApiClient(app=mock_app)


async def direct(path):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=mock_app), base_url="http://t") as c:
        r = await c.get(path)
        assert r.status_code == 200
        return r.json()


class Recorder:
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


def client_with(rec, base="http://api.test"):
    return ApiClient(base, transport=rec.transport())


# --- ApiClient -----------------------------------------------------------------------

@pytest.mark.anyio
async def test_client_in_process_matches_api_body():
    assert await api().track(KNOWN) == await direct(f"/api/tracks/{KNOWN}")
    assert await api().events() == await direct("/api/events")
    first = (await direct("/api/events"))[0]
    assert (await api().event(first["id"]))["id"] == first["id"]
    assert (await api().raw("rec01:0"))["raw_ref"] == "rec01:0"


@pytest.mark.anyio
async def test_client_paths_and_query_parameters():
    rec = Recorder(httpx.Response(200, json=[]))
    c = client_with(rec)
    await c.events(since="2026-11-14T03:00:00Z", type="holding", airport="WIII")
    await c.events()
    req = rec.requests[0]
    assert req.url.path == "/api/events"
    assert dict(req.url.params) == {"since": "2026-11-14T03:00:00Z", "type": "holding", "airport": "WIII"}
    assert rec.requests[1].url.query == b""

    rec = Recorder(httpx.Response(200, json={"points": []}))
    await client_with(rec).track(KNOWN, "2026-11-14T03:00:00Z", "2026-11-14T03:05:00Z")
    assert dict(rec.requests[0].url.params) == {"from": "2026-11-14T03:00:00Z", "to": "2026-11-14T03:05:00Z"}


@pytest.mark.anyio
async def test_client_encodes_path_values_as_one_segment():
    rec = Recorder(httpx.Response(200, json={}))
    c = client_with(rec)
    await c.track("../meta")
    await c.track("a/b")
    await c.raw("rec01:5")
    await c.event("x/y")
    paths = [r.url.raw_path.decode() for r in rec.requests]
    assert paths[0] == "/api/tracks/..%2Fmeta"
    assert paths[1] == "/api/tracks/a%2Fb"
    assert paths[2].startswith("/api/raw/rec01") and "/" not in paths[2][len("/api/raw/"):]
    assert paths[3] == "/api/events/x%2Fy"


@pytest.mark.anyio
async def test_client_error_messages():
    c404 = client_with(Recorder(httpx.Response(404, json={"detail": "Unknown"})))
    with pytest.raises(ApiError, match="No aircraft with icao24 'ZZZZZZ'"):
        await c404.track("ZZZZZZ")
    with pytest.raises(ApiError, match="No event with id 'abc'"):
        await c404.event("abc")
    with pytest.raises(ApiError, match="No raw record 'rec01:999'"):
        await c404.raw("rec01:999")

    down = client_with(Recorder(error=httpx.ConnectError("refused")), base="http://nowhere:9")
    with pytest.raises(ApiError, match="Cannot reach the FlightMind API at http://nowhere:9"):
        await down.events()
    in_proc = ApiClient(app=mock_app, transport=Recorder(error=httpx.ConnectError("x")).transport())
    with pytest.raises(ApiError, match="did not answer"):
        await in_proc.events()

    with pytest.raises(ApiError, match="500: boom"):
        await client_with(Recorder(httpx.Response(500, json={"detail": "boom"}))).events()
    with pytest.raises(ApiError, match="not valid JSON"):
        await client_with(Recorder(httpx.Response(200, text="not json"))).events()
    with pytest.raises(ApiError, match="icao24 is required"):
        await client_with(Recorder(httpx.Response(200, json={}))).track("  ")


@pytest.mark.anyio
async def test_client_timeout_is_ten_seconds(monkeypatch):
    seen = {}
    real = httpx.AsyncClient

    def spy(*args, **kwargs):
        seen.update(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr(api_client_mod.httpx, "AsyncClient", spy)
    await api().events()
    assert seen["timeout"] == 10.0


@pytest.mark.anyio
async def test_client_default_base_from_environment(monkeypatch):
    assert ApiClient().base == "http://localhost:8000"
    monkeypatch.setenv("FLIGHTMIND_API_BASE", "http://example.test:9/")
    assert ApiClient().base == "http://example.test:9"


# --- search_events -------------------------------------------------------------------

@pytest.mark.anyio
async def test_search_events_cut_down_shape():
    result = await tools.search_events(api(), type="go_around")
    full = [e for e in await direct("/api/events") if e["type"] == "go_around"]
    assert result.result_count == len(full) == 2
    row = result.data["events"][0]
    assert set(row) == {
        "id", "type", "icao24", "callsign", "start_ts", "end_ts", "airport", "severity",
        "raw_ref_count", "first_raw_ref", "last_raw_ref",
    }
    assert "raw_refs" not in row
    src = next(e for e in full if e["id"] == row["id"])
    assert row["raw_ref_count"] == len(src["raw_refs"])
    assert row["first_raw_ref"] == src["raw_refs"][0] and row["last_raw_ref"] == src["raw_refs"][-1]
    assert set(result.event_ids) == {e["id"] for e in full}
    assert set(result.raw_refs) == {r for e in full for r in (e["raw_refs"][0], e["raw_refs"][-1])}
    assert all(label.startswith("go_around ") for label in result.event_labels.values())


@pytest.mark.anyio
async def test_search_events_filters_and_empty():
    assert (await tools.search_events(api(), type="holding")).result_count == 1
    assert (await tools.search_events(api(), airport="WIII")).result_count == 3
    empty = await tools.search_events(api(), type="nonsense")
    assert empty.result_count == 0 and not empty.is_error and empty.event_ids == []


# --- get_track -----------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_track_without_max_points_is_unchanged():
    result = await tools.get_track(api(), KNOWN)
    assert result.data == await direct(f"/api/tracks/{KNOWN}")
    assert result.raw_refs == [p["raw_ref"] for p in result.data["points"]]


@pytest.mark.anyio
async def test_get_track_window_and_unknown_aircraft():
    full = await direct(f"/api/tracks/{KNOWN}")
    start, end = full["points"][10]["ts"], full["points"][20]["ts"]
    result = await tools.get_track(api(), KNOWN, from_=start, to=end)
    assert 0 < len(result.data["points"]) < len(full["points"])
    bad = await tools.get_track(api(), "ZZZZZZ")
    assert bad.is_error and "ZZZZZZ" in bad.data["error"]


def _synthetic(n, event_idx=()):
    return [
        {"ts": f"t{i}", "lat": 0.0, "lon": 0.0, "alt_ft": i, "raw_ref": f"r:{i}", "kept_for_event": i in event_idx}
        for i in range(n)
    ]


def _track_client(points):
    rec = Recorder(httpx.Response(200, json={"icao24": "AAAAAA", "callsign": "TST1", "points": points}))
    return client_with(rec)


@pytest.mark.anyio
async def test_thinning_keeps_first_last_and_event_points():
    event_idx = set(range(100, 110))
    points = _synthetic(300, event_idx)
    result = await tools.get_track(_track_client(points), "AAAAAA", max_points=50)
    kept = result.data["points"]
    refs = [p["raw_ref"] for p in kept]
    assert len(kept) == 50
    assert refs[0] == "r:0" and refs[-1] == "r:299"
    assert {f"r:{i}" for i in event_idx} <= set(refs)
    assert refs == sorted(refs, key=lambda r: int(r.split(":")[1]))
    assert result.data["total_points"] == 300 and result.data["returned_points"] == 50
    assert result.data["thinned"] is True
    assert result.raw_refs == refs
    assert all(p == points[int(p["raw_ref"].split(":")[1])] for p in kept)  # fields unchanged


@pytest.mark.anyio
async def test_thinning_cap_is_200_and_minimum_is_2():
    points = _synthetic(500)
    assert len((await tools.get_track(_track_client(points), "AAAAAA", max_points=5000)).data["points"]) == 200
    two = (await tools.get_track(_track_client(points), "AAAAAA", max_points=1)).data["points"]
    assert [p["raw_ref"] for p in two] == ["r:0", "r:499"]


@pytest.mark.anyio
async def test_thinning_when_event_points_exceed_the_cap():
    points = _synthetic(100, set(range(10, 90)))
    kept = (await tools.get_track(_track_client(points), "AAAAAA", max_points=10)).data["points"]
    refs = [p["raw_ref"] for p in kept]
    assert len(kept) == 10 and refs[0] == "r:0" and refs[-1] == "r:99"
    assert all(p["kept_for_event"] for p in kept[1:-1])


@pytest.mark.anyio
async def test_short_track_is_not_thinned():
    result = await tools.get_track(api(), KNOWN, max_points=200)
    assert result.data["thinned"] is False
    assert result.data["returned_points"] == result.data["total_points"] == 60


# --- query_tracks --------------------------------------------------------------------

@pytest.mark.anyio
async def test_query_tracks_summary_for_holding_aircraft():
    result = await tools.query_tracks(api(), callsign="lni456")
    (row,) = result.data["aircraft"]
    full = await direct("/api/tracks/8A1C07")
    pts = full["points"]
    assert row == {
        "icao24": "8A1C07", "callsign": "LNI456", "points_in_window": len(pts),
        "first_ts": pts[0]["ts"], "last_ts": pts[-1]["ts"],
        "min_alt_ft": min(p["alt_ft"] for p in pts), "max_alt_ft": max(p["alt_ft"] for p in pts),
        "first_raw_ref": pts[0]["raw_ref"], "last_raw_ref": pts[-1]["raw_ref"],
        "min_alt_raw_ref": pts[0]["raw_ref"], "max_alt_raw_ref": pts[0]["raw_ref"],  # constant altitude
    }
    assert result.raw_refs == [pts[0]["raw_ref"], pts[-1]["raw_ref"]]


@pytest.mark.anyio
async def test_query_tracks_filters_and_window():
    assert (await tools.query_tracks(api())).result_count == 4
    assert (await tools.query_tracks(api(), icao24="8a0f21")).result_count == 1
    assert (await tools.query_tracks(api(), callsign="nobody")).result_count == 0
    # A window before the recording starts leaves every aircraft out.
    early = await tools.query_tracks(api(), from_="2020-01-01T00:00:00Z", to="2020-01-02T00:00:00Z")
    assert early.data["aircraft"] == [] and early.result_count == 0


@pytest.mark.anyio
async def test_query_tracks_ignores_null_altitude_and_only_searches_aircraft_with_events():
    events = [{"icao24": "AAAAAA", "callsign": "TST1", "id": "e1", "type": "holding", "raw_refs": ["r:0"]}]
    points = [
        {"ts": "t0", "lat": 0, "lon": 0, "alt_ft": None, "raw_ref": "r:0", "kept_for_event": True},
        {"ts": "t1", "lat": 0, "lon": 0, "alt_ft": 4000, "raw_ref": "r:1", "kept_for_event": False},
        {"ts": "t2", "lat": 0, "lon": 0, "alt_ft": 6000, "raw_ref": "r:2", "kept_for_event": False},
    ]

    def handler(request):
        if request.url.path == "/api/events":
            return httpx.Response(200, json=events)
        return httpx.Response(200, json={"icao24": "AAAAAA", "callsign": "TST1", "points": points})

    seen = []

    def spy(request):
        seen.append(request.url.path)
        return handler(request)

    c = ApiClient("http://api.test", transport=httpx.MockTransport(spy))
    result = await tools.query_tracks(c)
    (row,) = result.data["aircraft"]
    assert row["min_alt_ft"] == 4000 and row["max_alt_ft"] == 6000
    assert seen == ["/api/events", "/api/tracks/AAAAAA"]  # no other aircraft is looked up
    assert "only aircraft that have at least one detected event" in tools.SPECS_BY_NAME["query_tracks"].description.lower()


# --- get_raw -------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_raw_returns_decoded_and_hex():
    result = await tools.get_raw(api(), "rec01:0")
    assert result.data["decoded"]["icao24"] and result.data["hex"]
    assert result.raw_refs == ["rec01:0"]


@pytest.mark.anyio
async def test_unknown_ids_are_tool_errors_not_exceptions():
    for name, args in (
        ("get_raw", {"raw_ref": "rec01:99999"}),
        ("get_track", {"icao24": "ZZZZZZ"}),
    ):
        result = await tools.run_tool(api(), name, args)
        assert result.is_error and "error" in result.data
    down = ApiClient("http://nowhere:9", transport=Recorder(error=httpx.ConnectError("x")).transport())
    assert (await tools.run_tool(down, "search_events", {})).is_error


# --- dispatcher and schemas ----------------------------------------------------------

@pytest.mark.anyio
async def test_dispatcher_validates_arguments():
    for name, args in (
        ("get_track", {}),
        ("get_track", {"icao24": 5}),
        ("get_track", {"icao24": KNOWN, "extra": 1}),
        ("get_track", {"icao24": KNOWN, "max_points": "10"}),
        ("get_raw", {"raw_ref": ""}),
        ("nope", {}),
    ):
        result = await tools.run_tool(api(), name, args)
        assert result.is_error, (name, args)
    assert (await tools.run_tool(api(), "get_track", "not a dict")).is_error


@pytest.mark.anyio
async def test_dispatcher_maps_from_to_and_fills_agent_max_points():
    long_points = _synthetic(150)
    rec = Recorder(httpx.Response(200, json={"icao24": "AAAAAA", "callsign": "T", "points": long_points}))
    c = client_with(rec)
    await tools.run_tool(c, "get_track", {"icao24": "AAAAAA", "from": "2026-11-14T03:00:00Z"}, for_agent=True)
    assert dict(rec.requests[0].url.params) == {"from": "2026-11-14T03:00:00Z"}
    agent = await tools.run_tool(c, "get_track", {"icao24": "AAAAAA", "max_points": None}, for_agent=True)
    assert agent.data["returned_points"] == 60
    mcp = await tools.run_tool(c, "get_track", {"icao24": "AAAAAA"})
    assert len(mcp.data["points"]) == 150


def test_model_tool_definitions_are_strict_and_stable():
    assert [t["name"] for t in tools.TOOLS_FOR_MODEL] == ["query_tracks", "search_events", "get_track", "get_raw"]
    forbidden = {"minimum", "maximum", "multipleOf", "minLength", "maxLength", "$ref"}
    for t in tools.TOOLS_FOR_MODEL:
        schema = t["input_schema"]
        assert t["strict"] is True
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == set(schema["properties"])
        assert not forbidden & set(json.dumps(schema).replace('"', " ").split())
    get_track = next(t for t in tools.TOOLS_FOR_MODEL if t["name"] == "get_track")
    assert set(get_track["input_schema"]["properties"]) == {"icao24", "from", "to", "max_points"}
    assert get_track["input_schema"]["properties"]["from"]["anyOf"] == [{"type": "string"}, {"type": "null"}]
    assert get_track["input_schema"]["properties"]["icao24"]["type"] == "string"


# --- review fixes (PR #22) -----------------------------------------------------------

@pytest.mark.anyio
async def test_query_tracks_altitude_extremes_have_citable_refs():
    result = await tools.query_tracks(api(), icao24=KNOWN)
    summary = result.data["aircraft"][0]
    for key, alt in (("min_alt_raw_ref", summary["min_alt_ft"]), ("max_alt_raw_ref", summary["max_alt_ft"])):
        ref = summary[key]
        assert ref in result.raw_refs
        raw = await api().raw(ref)
        assert raw["decoded"]["baro_alt_ft"] == alt
    assert summary["min_alt_ft"] < summary["max_alt_ft"]


@pytest.mark.anyio
async def test_query_tracks_altitude_refs_null_without_altitudes():
    class Fake:
        async def events(self, **kw):
            return [{"icao24": "AAAAAA", "callsign": "X1"}]

        async def track(self, icao24, from_=None, to=None):
            return {"icao24": icao24, "callsign": "X1", "points": [
                {"ts": "t1", "alt_ft": None, "raw_ref": "r:1"},
                {"ts": "t2", "alt_ft": None, "raw_ref": "r:2"}]}

    result = await tools.query_tracks(Fake())
    s = result.data["aircraft"][0]
    assert s["min_alt_raw_ref"] is None and s["max_alt_raw_ref"] is None
    assert s["min_alt_ft"] is None


@pytest.mark.anyio
async def test_query_tracks_caps_candidates_and_fan_out():
    state = {"now": 0, "peak": 0, "calls": 0}

    class Fake:
        async def events(self, **kw):
            return [{"icao24": f"{i:06X}", "callsign": f"C{i}"} for i in range(30)]

        async def track(self, icao24, from_=None, to=None):
            state["calls"] += 1
            state["now"] += 1
            state["peak"] = max(state["peak"], state["now"])
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            state["now"] -= 1
            return {"icao24": icao24, "points": [{"ts": "t", "alt_ft": 100, "raw_ref": f"r:{icao24}"}]}

    result = await tools.query_tracks(Fake())
    assert tools.MAX_CANDIDATES == 20 and tools.MAX_IN_FLIGHT == 5
    assert len(result.data["aircraft"]) == 20 and state["calls"] == 20
    assert result.data["truncated"] is True and result.data["candidates_total"] == 30
    assert state["peak"] == 5


@pytest.mark.anyio
async def test_query_tracks_not_truncated_when_few():
    result = await tools.query_tracks(api())
    assert "truncated" not in result.data


def test_descriptions_name_the_new_fields_and_all_types():
    specs = tools.SPECS_BY_NAME
    q = specs["query_tracks"].description
    assert "min_alt_raw_ref" in q and "max_alt_raw_ref" in q and "truncated" in q and "icao24" in q
    s = specs["search_events"].description
    for t in ("go_around", "holding", "squawk_7500", "squawk_7600", "squawk_7700"):
        assert t in s
