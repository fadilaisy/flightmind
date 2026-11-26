"""Checks the mock API against contracts/openapi.yaml, not against itself."""
from pathlib import Path

import jsonschema
import pytest
import yaml
from fastapi.testclient import TestClient

from mock_api import data
from mock_api.app import app

SPEC = yaml.safe_load((Path(__file__).parents[3] / "contracts" / "openapi.yaml").read_text(encoding="utf-8"))
client = TestClient(app)


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


def check(body, path, method="get", code="200"):
    schema = SPEC["paths"][path][method]["responses"][code]["content"]["application/json"]["schema"]
    jsonschema.validate(body, inline(schema))


def get_ok(url):
    r = client.get(url)
    assert r.status_code == 200, r.text
    return r.json()


def test_meta():
    check(get_ok("/api/meta"), "/api/meta")


def test_events_list_and_filters():
    events = get_ok("/api/events")
    check(events, "/api/events")
    assert {e["type"] for e in events} == {"go_around", "holding", "squawk_7700"}
    assert all(e["type"] == "go_around" for e in get_ok("/api/events?type=go_around"))
    assert get_ok("/api/events?type=squawk_7500") == []
    assert all(e["airport"] == "WIII" for e in get_ok("/api/events?airport=WIII"))
    assert get_ok("/api/events?since=2030-01-01T00:00:00Z") == []


def test_event_detail_has_track_and_similar():
    events = get_ok("/api/events?type=go_around")
    detail = get_ok(f"/api/events/{events[0]['id']}")
    check(detail, "/api/events/{id}")
    assert detail["track"]["points"]
    assert [e["id"] for e in detail["similar"]] == [events[1]["id"]]


def test_event_unknown_is_404():
    assert client.get("/api/events/00000000-0000-0000-0000-000000000000").status_code == 404


def test_track_and_time_filter():
    track = get_ok("/api/tracks/8A0F21")
    check(track, "/api/tracks/{icao24}")
    pts = track["points"]
    assert len(pts) == 60
    mid = pts[30]["ts"]
    sliced = get_ok(f"/api/tracks/8A0F21?from={mid}")["points"]
    assert sliced[0]["ts"] == mid and len(sliced) == 30
    assert get_ok("/api/tracks/8a0f21")["icao24"] == "8A0F21"
    assert client.get("/api/tracks/FFFFFF").status_code == 404


def test_raw_known_and_unknown():
    ref = get_ok("/api/tracks/8A0F21")["points"][0]["raw_ref"]
    raw = get_ok(f"/api/raw/{ref}")
    check(raw, "/api/raw/{raw_ref}")
    assert raw["raw_ref"] == ref
    assert client.get("/api/raw/rec01:999999").status_code == 404


def test_compression_report_matches_contract_and_events():
    report = get_ok("/api/compression/rec01")
    check(report, "/api/compression/{recording_id}")
    events = get_ok("/api/events")
    assert report["recording_id"] == "rec01"
    assert report["events_kept"] == report["events_total"] == len(events)


def test_compression_counts_are_consistent():
    report = get_ok("/api/compression/rec01")
    events = get_ok("/api/events")
    total_points = sum(len(get_ok(f"/api/tracks/{icao}")["points"]) for icao in data.TRACKS)
    assert report["points_in"] == total_points
    assert 0 < report["points_kept"] < report["points_in"]
    assert report["stored_bytes"] < report["raw_bytes"]
    assert report["ratio"] == pytest.approx(report["stored_bytes"] / report["raw_bytes"], abs=1e-3)
    assert report["points_kept"] >= len({ref for e in events for ref in e["raw_refs"]})


def test_compression_for_recording_listed_in_meta():
    for rec in get_ok("/api/meta")["recordings"]:
        assert get_ok(f"/api/compression/{rec}")["recording_id"] == rec


def test_compression_unknown_recording_is_404():
    assert client.get("/api/compression/nope").status_code == 404


def test_compression_empty_recording_is_404(monkeypatch):
    empty = {**data.COMPRESSION["rec01"], "recording_id": "empty", "raw_bytes": 0, "stored_bytes": 0, "ratio": 0}
    monkeypatch.setitem(data.COMPRESSION, "empty", empty)
    r = client.get("/api/compression/empty")
    assert r.status_code == 404
    assert r.json()["detail"] == "Recording 'empty' has no data yet."


def test_every_citation_resolves():
    """Every event raw_ref and every track raw_ref must open via /api/raw (the UI relies on it)."""
    for e in get_ok("/api/events"):
        for ref in e["raw_refs"]:
            assert client.get(f"/api/raw/{ref}").status_code == 200
    for p in get_ok("/api/tracks/76CD11")["points"]:
        assert client.get(f"/api/raw/{p['raw_ref']}").status_code == 200


def test_kept_for_event_matches_event_refs():
    for e in get_ok("/api/events"):
        kept = {p["raw_ref"] for p in get_ok(f"/api/tracks/{e['icao24']}")["points"] if p["kept_for_event"]}
        assert set(e["raw_refs"]) <= kept


def test_ask_ok_has_citations_that_resolve():
    r = client.post("/api/ask", json={"question": "Any emergency squawk 7700?"})
    assert r.status_code == 200
    body = r.json()
    check(body, "/api/ask", method="post")
    assert body["status"] == "ok" and body["citations"]
    for c in body["citations"]:
        url = f"/api/raw/{c['id']}" if c["kind"] == "cat021_record" else f"/api/events/{c['id']}"
        assert client.get(url).status_code == 200


def test_ask_without_evidence():
    body = client.post("/api/ask", json={"question": "What is the weather in Paris?"}).json()
    check(body, "/api/ask", method="post")
    assert body["status"] == "not_enough_evidence" and body["citations"] == []


def test_ask_requires_question():
    assert client.post("/api/ask", json={}).status_code == 422


def test_stream_emits_positions_and_events(monkeypatch):
    monkeypatch.setenv("MOCK_STREAM_DELAY", "0")
    with client.stream("GET", "/api/stream") as r:
        assert r.headers["content-type"].startswith("text/event-stream")
        text = "".join(r.iter_text())
    assert text.count("event: position") == 270
    assert text.count("event: event") == 4
