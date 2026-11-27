"""Mock recording upload flow (SCRUM-62), checked against contracts/openapi.yaml 1.2.0."""
import hashlib
import io
import json
import zipfile
from pathlib import Path

import jsonschema
import pytest
import yaml
from fastapi.testclient import TestClient

from mock_api import data, uploads
from mock_api.app import app

SPEC = yaml.safe_load((Path(__file__).parents[3] / "contracts" / "openapi.yaml").read_text(encoding="utf-8"))
client = TestClient(app)

PCAP = bytes.fromhex("d4c3b2a1") + b"\x02\x00\x04\x00" + bytes(200)  # little-endian pcap header, then filler
RAW_CAT021 = b"\x15\x00\x30" + bytes(45)  # one CAT021 block, 48 bytes long


def inline(node):
    """Resolve $refs and turn OpenAPI 3.0 `nullable` into JSON Schema."""
    if isinstance(node, list):
        return [inline(n) for n in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        return inline(SPEC["components"]["schemas"][node["$ref"].split("/")[-1]])
    out = {k: inline(v) for k, v in node.items()}
    if out.pop("nullable", False):
        if "type" in out:
            out["type"] = [out["type"], "null"]
        else:
            out = {"anyOf": [out, {"type": "null"}]}
    return out


def check(body, path, method="get", code="200"):
    schema = SPEC["paths"][path][method]["responses"][code]["content"]["application/json"]["schema"]
    jsonschema.validate(body, inline(schema))


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


PART = 128  # small parts for the tests (FLIGHTMIND_PART_SIZE_BYTES); PCAP is 208 bytes, so two parts


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    monkeypatch.setenv("FLIGHTMIND_PART_SIZE_BYTES", str(PART))
    uploads.reset()
    c = Clock()
    monkeypatch.setattr(uploads, "clock", c)
    yield c
    uploads.reset()


def create(filename="flight.pcap", size=len(PCAP), **extra):
    r = client.post("/api/recordings", json={"filename": filename, "size_bytes": size, **extra})
    assert r.status_code == 201, r.text
    check(r.json(), "/api/recordings", "post", "201")
    return r.json()


def send(rid, content):
    for n in range(-(-len(content) // PART)):
        r = client.put(f"/api/recordings/{rid}/parts/{n}", content=content[n * PART:(n + 1) * PART])
        assert r.status_code == 204, r.text


def upload(content, filename="flight.pcap", **extra):
    """Create, send the bytes in PART-sized parts, complete. Returns the complete response."""
    rec = create(filename, len(content), **extra)
    send(rec["id"], content)
    return client.post(f"/api/recordings/{rec['id']}/complete")


def scanned(clock, content=PCAP, **kw):
    r = upload(content, **kw)
    assert r.status_code == 202, r.text
    clock.advance(uploads.SCAN_S)
    return r.json()["id"]


def get(rid):
    r = client.get(f"/api/recordings/{rid}")
    assert r.status_code == 200, r.text
    check(r.json(), "/api/recordings/{id}")
    return r.json()


def test_full_flow_from_create_to_export(clock):
    rec = create()
    assert rec["status"] == "uploading" and rec["part_size_bytes"] == PART
    assert rec["id"].startswith("r") and len(rec["id"]) == 11
    assert rec["streams"] == [] and rec["progress"] is None

    send(rec["id"], PCAP)
    assert get(rec["id"])["bytes_received"] == len(PCAP)

    r = client.post(f"/api/recordings/{rec['id']}/complete")
    assert r.status_code == 202
    check(r.json(), "/api/recordings/{id}/complete", "post", "202")
    assert r.json()["status"] == "scanning"

    clock.advance(uploads.SCAN_S)
    now = get(rec["id"])
    assert now["status"] == "scanned"
    assert [(s["id"], s["category"], s["supported"]) for s in now["streams"]] == [("s1", 21, True), ("s2", 62, False)]

    r = client.post(f"/api/recordings/{rec['id']}/process", json={"stream_id": "s1"})
    assert r.status_code == 202
    check(r.json(), "/api/recordings/{id}/process", "post", "202")
    assert r.json()["status"] == "queued"

    seen = []
    for _ in range(12):
        clock.advance(1)
        seen.append(get(rec["id"])["status"])
    assert seen[-1] == "ready"
    assert [s for i, s in enumerate(seen) if i == 0 or s != seen[i - 1]] == [
        "decoding", "filtering", "detecting", "storing", "ready"
    ]
    ready = get(rec["id"])
    assert ready["record_count"] == uploads.MOCK_RECORDS and ready["event_count"] == len(data.EVENTS)
    assert ready["first_ts"] and ready["last_ts"]

    listed = client.get("/api/recordings").json()
    check(listed, "/api/recordings")
    assert [x["id"] for x in listed] == [rec["id"]]
    assert rec["id"] in client.get("/api/meta").json()["recordings"]


def test_progress_while_processing(clock):
    rid = scanned(clock)
    client.post(f"/api/recordings/{rid}/process", json={"stream_id": "s1"})
    clock.advance(2.5)  # 1 s queued, then 1.5 s into decoding
    now = get(rid)
    assert now["status"] == "decoding"
    assert 0 < now["progress"]["records_done"] < now["progress"]["records_total"]


def test_preview_recipe_and_quarantine_once_scanned(clock):
    rid = scanned(clock)

    r = client.get(f"/api/recordings/{rid}/preview", params={"stream": "s1", "limit": 5})
    assert r.status_code == 200
    check(r.json(), "/api/recordings/{id}/preview")
    assert len(r.json()["records"]) == 5
    for rec in r.json()["records"]:
        assert client.get(f"/api/raw/{rec['raw_ref']}").status_code == 200

    r = client.get(f"/api/recordings/{rid}/recipe")
    assert r.status_code == 200
    check(r.json(), "/api/recordings/{id}/recipe")
    recipe = r.json()
    assert recipe["input_sha256"] == hashlib.sha256(PCAP).hexdigest()
    assert recipe["raw_bytes"] == len(PCAP)
    assert recipe["stored_bytes"] is None and recipe["ratio"] is None  # only known after processing
    for a, b in zip(recipe["steps"], recipe["steps"][1:]):
        assert b["records_in"] == a["records_in"] - a["set_aside"]

    r = client.get(f"/api/recordings/{rid}/quarantine", params={"offset": 0, "limit": 3})
    check(r.json(), "/api/recordings/{id}/quarantine")
    assert r.json()["total"] == sum(s["set_aside"] for s in recipe["steps"])
    assert len(r.json()["items"]) == 3
    last = client.get(f"/api/recordings/{rid}/quarantine", params={"offset": uploads.QUARANTINE_TOTAL - 2}).json()
    assert len(last["items"]) == 2
    assert {i["step_code"] for i in last["items"]} == {"fragments"}


def test_export_zip_when_ready(clock):
    rid = scanned(clock, filename="Jakarta approach.pcap")
    assert client.get(f"/api/recordings/{rid}/export").status_code == 409
    client.post(f"/api/recordings/{rid}/process", json={"stream_id": "s1"})
    clock.advance(uploads.PROCESS_S)
    r = client.get(f"/api/recordings/{rid}/export")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    assert 'filename="Jakarta_approach-flightmind.zip"' in r.headers["content-disposition"]
    z = zipfile.ZipFile(io.BytesIO(r.content))
    assert sorted(z.namelist()) == ["cleaned.csv", "events.csv", "quarantine.csv", "recipe.json"]
    assert json.loads(z.read("recipe.json"))["input_sha256"] == hashlib.sha256(PCAP).hexdigest()
    assert z.read("events.csv").decode().count("\n") == len(data.EVENTS) + 1
    assert z.read("quarantine.csv").decode().count("\n") == uploads.QUARANTINE_TOTAL + 1


def test_ready_upload_serves_the_sample_through_the_recording_filter(clock):
    rid = scanned(clock)
    assert client.get("/api/events", params={"recording": rid}).json() == []
    assert client.get("/api/tracks/8A0F21", params={"recording": rid}).status_code == 404
    assert client.get(f"/api/compression/{rid}").status_code == 404

    client.post(f"/api/recordings/{rid}/process", json={"stream_id": "s1"})
    clock.advance(uploads.PROCESS_S)
    assert client.get("/api/events", params={"recording": rid}).json() == data.EVENTS
    assert client.get("/api/tracks/8A0F21", params={"recording": rid}).status_code == 200
    report = client.get(f"/api/compression/{rid}").json()
    assert report["recording_id"] == rid


def test_recording_filter_on_the_sample_and_unknown_ids():
    assert client.get("/api/events", params={"recording": data.RECORDING_ID}).json() == data.EVENTS
    assert client.get("/api/events").json() == data.EVENTS
    assert client.get("/api/events", params={"recording": "rnope000000"}).json() == []
    assert client.get("/api/tracks/8A0F21", params={"recording": "rnope000000"}).status_code == 404
    with client.stream("GET", "/api/stream", params={"recording": "rnope000000"}) as r:
        assert r.read() == b""
    r = client.post("/api/ask", json={"question": "Any squawk 7700?", "recording_id": "rnope000000"})
    assert r.json()["status"] == "not_enough_evidence"
    r = client.post("/api/ask", json={"question": "Any squawk 7700?", "recording_id": data.RECORDING_ID})
    assert r.json()["status"] == "ok"


@pytest.mark.parametrize("filename", ["notes.txt", "capture.pcap.zip", "noext"])
def test_create_refuses_other_extensions(filename):
    r = client.post("/api/recordings", json={"filename": filename, "size_bytes": 10})
    assert r.status_code == 415


def test_create_refuses_files_over_the_limit(monkeypatch):
    monkeypatch.setenv("FLIGHTMIND_MAX_UPLOAD_MB", "1")
    assert client.post("/api/recordings", json={"filename": "a.pcap", "size_bytes": 1024 * 1024}).status_code == 201
    r = client.post("/api/recordings", json={"filename": "a.pcap", "size_bytes": 1024 * 1024 + 1})
    assert r.status_code == 413
    assert client.post("/api/recordings", json={"filename": "a.pcap", "size_bytes": 0}).status_code == 422


def test_parts_must_come_in_order_and_fit_the_size():
    rid = create(size=2 * PART + 10)["id"]
    full = b"x" * PART
    assert client.put(f"/api/recordings/{rid}/parts/1", content=full).status_code == 409  # out of order
    assert client.put(f"/api/recordings/{rid}/parts/0", content=b"x" * 5).status_code == 409  # short, not last
    assert client.put(f"/api/recordings/{rid}/parts/0", content=b"").status_code == 409  # empty
    assert client.put(f"/api/recordings/{rid}/parts/0", content=b"x" * (PART + 1)).status_code == 413
    assert client.put(f"/api/recordings/{rid}/parts/0", content=full).status_code == 204
    assert client.put(f"/api/recordings/{rid}/parts/1", content=full).status_code == 204
    assert client.put(f"/api/recordings/{rid}/parts/2", content=b"x" * 11).status_code == 409  # past size_bytes
    assert client.put(f"/api/recordings/{rid}/parts/0", content=full).status_code == 409  # not the last part


def test_resending_the_last_part_is_a_no_op():
    rid = create(size=len(PCAP))["id"]
    assert client.put(f"/api/recordings/{rid}/parts/0", content=PCAP[:PART]).status_code == 204
    assert client.put(f"/api/recordings/{rid}/parts/0", content=PCAP[:PART]).status_code == 204  # lost response
    assert get(rid)["bytes_received"] == PART
    assert client.put(f"/api/recordings/{rid}/parts/1", content=PCAP[PART:]).status_code == 204
    assert client.put(f"/api/recordings/{rid}/parts/1", content=PCAP[PART:]).status_code == 204
    r = client.post(f"/api/recordings/{rid}/complete")
    assert r.status_code == 202
    assert client.get(f"/api/recordings/{rid}/recipe").status_code == 409  # still scanning
    assert r.json()["bytes_received"] == len(PCAP)


def test_complete_needs_every_byte():
    rid = create(size=len(PCAP))["id"]
    client.put(f"/api/recordings/{rid}/parts/0", content=PCAP[:PART])
    r = client.post(f"/api/recordings/{rid}/complete")
    assert r.status_code == 409
    assert f"{PART} of" in r.json()["detail"]


@pytest.mark.parametrize("content,filename", [(RAW_CAT021, "day1.pcap"), (PCAP, "capture.atx")])
def test_complete_refuses_content_that_does_not_match_the_extension(content, filename):
    r = upload(content, filename=filename)
    assert r.status_code == 415
    assert "name it" in r.json()["detail"]


def test_complete_refuses_bytes_that_are_not_a_capture():
    r = upload(b"PK\x03\x04" + bytes(100), filename="flight.pcap")
    assert r.status_code == 415


def test_raw_asterix_file_has_one_raw_stream(clock):
    rid = scanned(clock, content=RAW_CAT021, filename="day1.atx", recording_date="2026-11-14")
    rec = get(rid)
    assert rec["format"] == "asterix_raw"
    assert [s["id"] for s in rec["streams"]] == ["raw"]
    assert client.post(f"/api/recordings/{rid}/process", json={"stream_id": "raw"}).status_code == 202


def test_same_file_twice_returns_the_first_upload(clock):
    first = upload(PCAP).json()
    assert first["status"] == "scanning"
    second_created = create(size=len(PCAP))
    send(second_created["id"], PCAP)
    r = client.post(f"/api/recordings/{second_created['id']}/complete")
    assert r.status_code == 200
    check(r.json(), "/api/recordings/{id}/complete", "post", "200")
    assert r.json()["id"] == first["id"]
    assert client.get(f"/api/recordings/{second_created['id']}").status_code == 404
    assert [x["id"] for x in client.get("/api/recordings").json()] == [first["id"]]


def test_bad_pcap_fails_after_scanning(clock):
    rid = scanned(clock, filename="bad.pcap")
    rec = get(rid)
    assert rec["status"] == "failed"
    assert rec["error"] == "No CAT021 records found in bad.pcap."
    assert rec["streams"] == []
    assert client.get(f"/api/recordings/{rid}/recipe").status_code == 409
    assert client.post(f"/api/recordings/{rid}/process", json={"stream_id": "s1"}).status_code == 409


def test_process_and_preview_need_a_scanned_recording_and_a_supported_stream(clock):
    r = upload(PCAP)
    rid = r.json()["id"]
    assert client.post(f"/api/recordings/{rid}/process", json={"stream_id": "s1"}).status_code == 409  # scanning
    assert client.get(f"/api/recordings/{rid}/preview", params={"stream": "s1"}).status_code == 409
    assert client.get(f"/api/recordings/{rid}/quarantine").status_code == 409
    clock.advance(uploads.SCAN_S)
    assert client.post(f"/api/recordings/{rid}/process", json={"stream_id": "s2"}).status_code == 409  # CAT062
    assert client.get(f"/api/recordings/{rid}/preview", params={"stream": "s2"}).status_code == 409
    assert client.get(f"/api/recordings/{rid}/preview", params={"stream": "s1", "limit": 0}).status_code == 422
    assert client.get(f"/api/recordings/{rid}/preview", params={"stream": "s1", "limit": 201}).status_code == 422
    assert client.post(f"/api/recordings/{rid}/process", json={"stream_id": "s1"}).status_code == 202
    assert client.post(f"/api/recordings/{rid}/process", json={"stream_id": "s1"}).status_code == 409  # queued
    assert client.put(f"/api/recordings/{rid}/parts/2", content=b"x").status_code == 409  # not uploading


@pytest.mark.parametrize("method,path", [
    ("get", ""), ("put", "/parts/0"), ("post", "/complete"), ("post", "/process"),
    ("get", "/preview?stream=s1"), ("get", "/recipe"), ("get", "/quarantine"), ("get", "/export"),
])
def test_unknown_recording_is_404(method, path):
    kwargs = {"json": {"stream_id": "s1"}} if path == "/process" else {}
    if method == "put":
        kwargs = {"content": b"x"}
    r = getattr(client, method)(f"/api/recordings/rnope000000{path}", **kwargs)
    assert r.status_code == 404


def test_a_failed_upload_does_not_block_the_same_file(clock):
    bad = scanned(clock, filename="bad.pcap")
    assert get(bad)["status"] == "failed"
    r = upload(PCAP, filename="good.pcap")
    assert r.status_code == 202
    assert r.json()["id"] != bad and r.json()["filename"] == "good.pcap"


def test_recipe_sizes_are_set_once_ready(clock):
    rid = scanned(clock)
    client.post(f"/api/recordings/{rid}/process", json={"stream_id": "s1"})
    clock.advance(uploads.PROCESS_S)
    recipe = client.get(f"/api/recordings/{rid}/recipe").json()
    check(recipe, "/api/recordings/{id}/recipe")
    assert recipe["stored_bytes"] > 0
    assert recipe["ratio"] == pytest.approx(recipe["stored_bytes"] / recipe["raw_bytes"])
