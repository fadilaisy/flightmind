"""Real API (SCRUM-37) against a Postgres filled by the pipeline from the committed fixture.

Every response is checked against contracts/openapi.yaml. Needs FLIGHTMIND_TEST_DSN and the
pipeline package (see tests/realdb.py); skipped otherwise.
"""
import uuid
from pathlib import Path

import jsonschema
import pytest
import yaml
from fastapi.testclient import TestClient

from realdb import FIXTURE_ID, create_database, decoded_blocks, seed_fixture

SPEC = yaml.safe_load((Path(__file__).parents[3] / "contracts" / "openapi.yaml").read_text(encoding="utf-8"))

pytestmark = pytest.mark.db


def inline(node):
    if isinstance(node, list):
        return [inline(n) for n in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        return inline(SPEC["components"]["schemas"][node["$ref"].split("/")[-1]])
    out = {k: inline(v) for k, v in node.items()}
    if out.pop("nullable", False):
        out = {**out, "type": [out["type"], "null"]} if "type" in out else {"anyOf": [out, {"type": "null"}]}
    return out


def check(body, path, method="get", code="200"):
    schema = SPEC["paths"][path][method]["responses"][code]["content"]["application/json"]["schema"]
    jsonschema.validate(body, inline(schema))


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    dsn, drop = create_database()
    reports = tmp_path_factory.mktemp("reports")
    report = seed_fixture(dsn, reports)
    import psycopg

    with psycopg.connect(dsn, autocommit=True) as conn:
        # The 500-packet fixture is too short for any detector, so add one event by hand on the
        # aircraft with the most stored points, citing its first three stored records.
        icao, = conn.execute(
            "SELECT icao24 FROM telemetry GROUP BY icao24 ORDER BY count(*) DESC, icao24 LIMIT 1"
        ).fetchone()
        rows = conn.execute(
            "SELECT ts, raw_ref FROM telemetry WHERE icao24 = %s ORDER BY ts LIMIT 3", (icao,)
        ).fetchall()
        event_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO events (id, type, icao24, callsign, start_ts, end_ts, airport, severity, raw_refs) "
            "VALUES (%s, 'holding', %s, NULL, %s, %s, 'WIII', 1, %s)",
            (event_id, icao, rows[0][0], rows[-1][0], [r[1] for r in rows]),
        )
    yield {"dsn": dsn, "reports": reports, "report": report, "icao": icao, "event_id": event_id,
           "event_refs": [r[1] for r in rows]}
    drop()


@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setenv("FLIGHTMIND_DSN", db["dsn"])
    monkeypatch.setenv("FLIGHTMIND_REPORT_DIR", str(db["reports"]))
    monkeypatch.delenv("FLIGHTMIND_DEFAULT_RECORDING", raising=False)
    from real_api.app import app

    return TestClient(app)


def ok(client, url, path, **params):
    r = client.get(url, params=params)
    assert r.status_code == 200, r.text
    check(r.json(), path)
    return r.json()


def test_meta_lists_the_fixture(client, db):
    body = ok(client, "/api/meta", "/api/meta")
    assert body["recordings"] == [FIXTURE_ID]
    assert body["mode"] == "replay"
    assert body["airports"] == ["WIII"]


def test_events_default_and_filtered(client, db):
    events = ok(client, "/api/events", "/api/events")
    assert [e["id"] for e in events] == [db["event_id"]]
    assert ok(client, "/api/events", "/api/events", recording=FIXTURE_ID) == events
    assert ok(client, "/api/events", "/api/events", recording="rnope000000") == []
    assert ok(client, "/api/events", "/api/events", type="go_around") == []
    assert ok(client, "/api/events", "/api/events", airport="WIII") == events


def test_event_detail_has_the_track(client, db):
    body = ok(client, f"/api/events/{db['event_id']}", "/api/events/{id}")
    assert body["track"]["icao24"] == db["icao"]
    assert len(body["track"]["points"]) >= 3
    assert client.get(f"/api/events/{uuid.uuid4()}").status_code == 404
    assert client.get("/api/events/not-a-uuid").status_code == 404


def test_track_points_carry_raw_refs_and_event_flags(client, db):
    body = ok(client, f"/api/tracks/{db['icao'].lower()}", "/api/tracks/{icao24}")
    points = body["points"]
    assert body["icao24"] == db["icao"]
    assert [p["ts"] for p in points] == sorted(p["ts"] for p in points)
    assert all(p["raw_ref"].startswith(FIXTURE_ID + ":") for p in points)
    flagged = {p["raw_ref"] for p in points if p["kept_for_event"]}
    assert flagged == set() or flagged <= set(db["event_refs"])  # flags come from the pipeline's own events

    narrow = ok(client, f"/api/tracks/{db['icao']}", "/api/tracks/{icao24}", **{"from": points[1]["ts"]})
    assert len(narrow["points"]) == len(points) - 1
    assert client.get("/api/tracks/ZZZZZZ").status_code == 404
    assert client.get(f"/api/tracks/{db['icao']}", params={"recording": "rnope000000"}).status_code == 404


def test_raw_reads_the_original_block_for_kept_and_dropped_records(client, db):
    blocks = decoded_blocks()
    kept = ok(client, f"/api/raw/{db['event_refs'][0]}", "/api/raw/{raw_ref}")
    index = kept["record_index"]
    assert kept["hex"].startswith("15")  # CAT021 block header
    assert kept["hex"].endswith(blocks[index - 1]["hexdata"])
    assert kept["decoded"]["icao24"] == db["icao"]

    import psycopg

    with psycopg.connect(db["dsn"]) as conn:
        stored = {r[0] for r in conn.execute("SELECT raw_ref FROM telemetry")}
    dropped = next(i for i in range(1, 501) if f"{FIXTURE_ID}:{i}" not in stored)
    body = ok(client, f"/api/raw/{FIXTURE_ID}:{dropped}", "/api/raw/{raw_ref}")
    assert body["decoded"]["stored"] is False
    assert body["hex"].endswith(blocks[dropped - 1]["hexdata"])

    for bad in (f"{FIXTURE_ID}:0", f"{FIXTURE_ID}:501", f"{FIXTURE_ID}:x", "nope:1", "noindex"):
        assert client.get(f"/api/raw/{bad}").status_code == 404, bad


def test_compression_from_the_pipeline_report(client, db):
    body = ok(client, f"/api/compression/{FIXTURE_ID}", "/api/compression/{recording_id}")
    report = db["report"]
    assert body["raw_bytes"] == report["raw_bytes"]
    assert body["stored_bytes"] == report["stored_bytes"]
    assert body["points_in"] == report["decoded_points"] == 500
    assert body["points_kept"] == report["rows_stored"]
    assert body["events_kept"] == body["events_total"]
    assert client.get("/api/compression/nope").status_code == 404


def test_stream_replays_positions(client, db):
    with client.stream("GET", "/api/stream") as r:
        text = r.read().decode()
    assert text.count("event: position") > 100
    assert text.count("event: event") == 1


def test_ask_without_a_key_says_the_agent_is_off(client):
    r = client.post("/api/ask", json={"question": "Any holding?", "recording_id": FIXTURE_ID})
    assert r.status_code == 200
    check(r.json(), "/api/ask", "post")
    assert r.json()["status"] == "not_enough_evidence"
