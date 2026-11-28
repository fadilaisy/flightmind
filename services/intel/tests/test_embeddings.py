"""Event stories, embedders, embed_missing and similar-event search (SCRUM-35).

No test calls the Gemini API. The database tests need FLIGHTMIND_TEST_DSN (Postgres with
pgvector, see tests/realdb.py) and are skipped without it.
"""
import json
import math
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import jsonschema
import pytest
import yaml
from fastapi.testclient import TestClient

from embeddings import (
    DIMENSIONS, EmbeddingError, FakeEmbedder, GeminiEmbedder, UnknownEvent, build_story, embed_missing, from_env,
    l2_normalize, search_similar,
)
from embeddings.embedder import GEMINI_URL
from embeddings.job import vector_literal
from mock_api.app import app as mock_app
from realdb import create_database

SPEC = yaml.safe_load((Path(__file__).parents[3] / "contracts" / "openapi.yaml").read_text(encoding="utf-8"))
T0 = datetime(2026, 11, 14, 3, 12, tzinfo=timezone.utc)

GO_AROUND = {
    "type": "go_around", "icao24": "8a0f21", "callsign": "GIA123", "airport": "WIII", "severity": 2,
    "start_ts": T0, "end_ts": T0 + timedelta(minutes=2),
    "details": {"runway": "07L", "min_hat_ft": 400, "rebound_ft": 700, "max_vrate_fpm": 2200},
}
HOLDING = {
    "type": "holding", "icao24": "8A1C07", "callsign": "LNI456", "airport": "WIII", "severity": 1,
    "start_ts": T0, "end_ts": T0 + timedelta(minutes=8),
    "details": {"direction": "right", "circuits": 2, "duration_s": 480, "min_alt_ft": 4000, "max_alt_ft": 6000},
}
SQUAWK = {
    "type": "squawk_7700", "icao24": "76CD11", "callsign": None, "airport": None, "severity": 3,
    "start_ts": "2026-11-14T03:20:00Z", "end_ts": "2026-11-14T03:25:00Z",
    "details": {"code": "7700", "records_with_code": 12, "alt_ft": 35000, "alt_kind": "pressure"},
}


# ---------- story ----------

def test_go_around_story_has_the_key_facts():
    story = build_story(GO_AROUND)
    for part in ("Go-around at WIII", "GIA123 (icao24 8A0F21)", "runway 07L", "2026-11-14", "03:12 UTC",
                 "400 ft above the runway", "climbed 700 ft", "2,200 ft/min", "Severity 2."):
        assert part in story, part


def test_holding_story():
    story = build_story(HOLDING)
    assert "Holding pattern near WIII" in story
    assert "2 circuits" in story and "right-hand" in story and "8.0 min" in story
    assert "between 4,000 ft and 6,000 ft" in story


def test_squawk_story_with_iso_strings_and_no_callsign():
    story = build_story(SQUAWK)
    assert story.startswith("Emergency squawk 7700 (general emergency): aircraft 76CD11 transmitted 7700 on 2026-11-14 at 03:20 UTC.")
    assert "for 5.0 min" in story and "35,000 ft pressure altitude" in story and "12 records" in story


def test_story_skips_what_the_row_lacks_and_is_deterministic():
    bare = {"type": "go_around", "icao24": "abc123", "start_ts": T0, "end_ts": T0}
    story = build_story(bare)
    assert story == "Go-around: aircraft ABC123 broke off its approach on 2026-11-14 at 03:12 UTC."
    assert "None" not in story and build_story(bare) == story
    assert build_story({"type": "mystery"}) == "Mystery: an aircraft."


# ---------- embedders ----------

def test_l2_normalize_gives_unit_length_and_rejects_zero():
    v = l2_normalize([3.0, 4.0])
    assert v == [0.6, 0.8] and math.isclose(sum(x * x for x in v), 1.0)
    with pytest.raises(EmbeddingError):
        l2_normalize([0.0, 0.0])


def test_fake_embedder_is_deterministic_unit_length_and_orders_by_overlap():
    fake = FakeEmbedder()
    a, a2, b = fake.embed([build_story(GO_AROUND), build_story(GO_AROUND), build_story(HOLDING)])
    assert a == a2 and len(a) == DIMENSIONS
    assert math.isclose(sum(x * x for x in a), 1.0, rel_tol=1e-9)
    near = fake.embed(["Go-around at WIII runway 07L GIA123"])[0]
    cos = lambda x, y: sum(p * q for p, q in zip(x, y))  # noqa: E731
    assert cos(near, a) > cos(near, b)
    assert math.isclose(sum(x * x for x in fake.embed([""])[0]), 1.0)


def _gemini_transport(seen, dims=DIMENSIONS, status=200):
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append((request, body))
        values = [[2.0] * dims for _ in body["requests"]]
        return httpx.Response(status, json={"embeddings": [{"values": v} for v in values]})
    return httpx.MockTransport(handler)


def test_gemini_embedder_request_shape_and_normalization():
    seen = []
    out = GeminiEmbedder("secret-key", transport=_gemini_transport(seen)).embed(["one", "two"])
    request, body = seen[0]
    assert str(request.url) == GEMINI_URL and request.headers["x-goog-api-key"] == "secret-key"
    assert "secret-key" not in str(request.url)
    assert [r["outputDimensionality"] for r in body["requests"]] == [1024, 1024]
    assert all(r["model"] == "models/gemini-embedding-001" for r in body["requests"])
    assert [r["content"]["parts"][0]["text"] for r in body["requests"]] == ["one", "two"]
    assert len(out) == 2 and all(math.isclose(sum(x * x for x in v), 1.0) for v in out)


def test_gemini_embedder_batches_and_fails_without_leaking_the_key():
    seen = []
    assert len(GeminiEmbedder("k", transport=_gemini_transport(seen)).embed(["t"] * 250)) == 250
    assert [len(b["requests"]) for _, b in seen] == [100, 100, 50]
    with pytest.raises(EmbeddingError) as err:
        GeminiEmbedder("secret-key", transport=_gemini_transport([], status=429)).embed(["x"])
    assert "429" in str(err.value) and "secret-key" not in str(err.value)
    with pytest.raises(EmbeddingError):
        GeminiEmbedder("k", transport=_gemini_transport([], dims=768)).embed(["x"])


def test_from_env_reads_either_key_and_is_none_without(monkeypatch):
    assert from_env() is None
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    assert from_env()._key == "g"
    monkeypatch.setenv("GOOGLE_API_KEY", "google")
    assert from_env()._key == "google"


# ---------- database: embed_missing and search_similar ----------

@pytest.fixture
def conn():
    psycopg = pytest.importorskip("psycopg")
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb

    dsn, drop = create_database()
    connection = psycopg.connect(dsn, autocommit=True, row_factory=dict_row)
    ids = {}
    for name, ev, offset in (("g1", GO_AROUND, 0), ("g2", GO_AROUND, 60), ("h1", HOLDING, 120), ("s1", SQUAWK, 180)):
        ids[name] = str(uuid.uuid4())
        start = ev["start_ts"] if isinstance(ev["start_ts"], datetime) else T0
        start = start + timedelta(minutes=offset)
        connection.execute(
            "INSERT INTO events (id, type, icao24, callsign, start_ts, end_ts, airport, severity, details, raw_refs) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (ids[name], ev["type"], ev["icao24"], ev["callsign"], start, start + timedelta(minutes=3),
             ev["airport"], ev["severity"], Jsonb(ev["details"]), [f"rec01:{offset + 1}"]),
        )
    connection.ids = ids
    yield connection
    connection.close()
    drop()


@pytest.mark.db
def test_embed_missing_writes_every_row_once_and_is_idempotent(conn):
    assert embed_missing(conn, FakeEmbedder()) == 4
    rows = conn.execute("SELECT event_id, story, model, vector_dims(embedding) AS d FROM event_embeddings").fetchall()
    assert len(rows) == 4 and {r["d"] for r in rows} == {1024} and {r["model"] for r in rows} == {"fake-embedder"}
    assert all(r["story"] for r in rows)
    assert embed_missing(conn, FakeEmbedder()) == 0
    conn.execute("DELETE FROM event_embeddings WHERE event_id = %s", (conn.ids["h1"],))
    assert embed_missing(conn, FakeEmbedder()) == 1


@pytest.mark.db
def test_embed_missing_without_a_key_does_nothing(conn):
    assert embed_missing(conn) == 0
    assert conn.execute("SELECT count(*) AS n FROM event_embeddings").fetchone()["n"] == 0


@pytest.mark.db
def test_search_similar_by_event_ranks_same_type_first_and_filters(conn):
    embed_missing(conn, FakeEmbedder())
    found = search_similar(conn, event_id=conn.ids["g1"], k=3)
    assert str(found[0]["id"]) == conn.ids["g2"] and conn.ids["g1"] not in {str(r["id"]) for r in found}
    sims = [r["similarity"] for r in found]
    assert sims == sorted(sims, reverse=True) and sims[0] > sims[-1]
    assert [str(r["id"]) for r in search_similar(conn, event_id=conn.ids["g1"], type="holding")] == [conn.ids["h1"]]
    assert len(search_similar(conn, event_id=conn.ids["g1"], k=1)) == 1
    late = search_similar(conn, event_id=conn.ids["g1"], since=T0 + timedelta(minutes=100))
    assert {str(r["id"]) for r in late} == {conn.ids["h1"], conn.ids["s1"]}
    early = search_similar(conn, event_id=conn.ids["g1"], until=T0 + timedelta(minutes=100))
    assert [str(r["id"]) for r in early] == [conn.ids["g2"]]


@pytest.mark.db
def test_search_similar_by_text_unknown_event_and_missing_embedding(conn):
    embed_missing(conn, FakeEmbedder())
    top = search_similar(conn, text="emergency squawk 7700 general emergency", embedder=FakeEmbedder())
    assert str(top[0]["id"]) == conn.ids["s1"]
    with pytest.raises(UnknownEvent):
        search_similar(conn, event_id=str(uuid.uuid4()))
    with pytest.raises(UnknownEvent):
        search_similar(conn, event_id="not-a-uuid")
    with pytest.raises(ValueError):
        search_similar(conn)
    conn.execute("DELETE FROM event_embeddings WHERE event_id = %s", (conn.ids["g1"],))
    assert search_similar(conn, event_id=conn.ids["g1"]) == []  # no stored vector, no embedder
    on_the_fly = search_similar(conn, event_id=conn.ids["g1"], embedder=FakeEmbedder())
    assert str(on_the_fly[0]["id"]) == conn.ids["g2"]


def test_vector_literal_is_pgvector_text():
    assert vector_literal([0.5, -1.0]) == "[0.5,-1.0]"


# ---------- mock endpoint and contract ----------

client = TestClient(mock_app)


def _inline(node):
    if isinstance(node, list):
        return [_inline(n) for n in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        return _inline(SPEC["components"]["schemas"][node["$ref"].split("/")[-1]])
    out = {k: _inline(v) for k, v in node.items()}
    if out.pop("nullable", False) and "type" in out:
        out["type"] = [out["type"], "null"]
    return out


def test_openapi_has_the_similar_path_and_minor_version():
    assert SPEC["info"]["version"] == "1.3.0"
    op = SPEC["paths"]["/api/events/{id}/similar"]["get"]
    assert {p["name"] for p in op["parameters"]} == {"id", "k", "type", "since", "until"}
    assert "404" in op["responses"]
    assert SPEC["components"]["schemas"]["SimilarEvent"]["allOf"][0] == {"$ref": "#/components/schemas/Event"}


def test_mock_similar_returns_nearby_events_of_the_same_type():
    goes = client.get("/api/events?type=go_around").json()
    r = client.get(f"/api/events/{goes[0]['id']}/similar")
    assert r.status_code == 200
    schema = SPEC["paths"]["/api/events/{id}/similar"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    jsonschema.validate(r.json(), _inline(schema))
    assert [e["id"] for e in r.json()] == [goes[1]["id"]]
    assert client.get(f"/api/events/{goes[0]['id']}/similar?type=holding").json() == []
    assert client.get(f"/api/events/{goes[0]['id']}/similar?since=2030-01-01T00:00:00Z").json() == []
    holding = client.get("/api/events?type=holding").json()[0]
    assert client.get(f"/api/events/{holding['id']}/similar").json() == []  # the only holding


def test_mock_similar_unknown_event_and_bad_k():
    assert client.get(f"/api/events/{uuid.uuid4()}/similar").status_code == 404
    goes = client.get("/api/events?type=go_around").json()
    assert client.get(f"/api/events/{goes[0]['id']}/similar?k=0").status_code == 422
