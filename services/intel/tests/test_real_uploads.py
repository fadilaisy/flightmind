"""Real upload API and worker (SCRUM-64) against Postgres.

The pipeline job (run_recording) is SCRUM-63 and does not exist yet, so the worker gets a
stand-in with the same signature. It runs the pipeline's own CLI on the uploaded bytes (the
decoder output replayed from the committed jsonl), so the rows in the database are real
pipeline output. Swap in the real job once SCRUM-63 merges.
"""
import shutil
import struct
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from realdb import FIXTURE_PCAP, create_database, decoded_blocks, replay_decoder
from test_real_api import check


def pcap_offsets(path):
    from real_api import raw_file

    with open(path, "rb") as f:
        kind, order, _ = raw_file._format(f)
        yield from raw_file.iter_offsets(f, kind, order)

pytestmark = pytest.mark.db

PART = 25_000
FIXTURE = FIXTURE_PCAP.read_bytes()


def drop_first(k: int) -> bytes:
    """The fixture without its first k packets: still a valid pcap, with a different sha256."""
    pos = 24
    for _ in range(k):
        pos += 16 + struct.unpack("<I", FIXTURE[pos + 8:pos + 12])[0]
    return FIXTURE[:24] + FIXTURE[pos:]


@pytest.fixture(scope="module")
def db():
    dsn, drop = create_database()
    yield dsn
    drop()


@pytest.fixture
def env(db, tmp_path, monkeypatch):
    from real_api import uploads

    monkeypatch.setenv("FLIGHTMIND_DSN", db)
    monkeypatch.setenv("FLIGHTMIND_UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("FLIGHTMIND_PART_SIZE_BYTES", str(PART))
    monkeypatch.setenv("FLIGHTMIND_UPLOAD_WORKER", "off")
    monkeypatch.delenv("FLIGHTMIND_DEFAULT_RECORDING", raising=False)
    import psycopg

    with psycopg.connect(db, autocommit=True) as conn:  # every test starts with no uploads
        conn.execute("DELETE FROM uploads")
    calls = []

    def stand_in(path, recording_id, dsn, on_progress=None, recording_date=None):
        """Same signature as SCRUM-63's run_recording."""
        pytest.importorskip("flightmind_pipeline")
        from flightmind_pipeline import cli
        import psycopg

        calls.append((path, recording_id, recording_date))
        copy = tmp_path / f"{recording_id}.pcap"  # the CLI takes the recording id from the file stem
        shutil.copy(path, copy)
        packets = sum(1 for _ in pcap_offsets(copy))
        blocks = decoded_blocks()[500 - packets:]  # test files only drop packets from the start
        with pytest.MonkeyPatch.context() as mp:
            replay_decoder(mp, {str(copy): blocks})
            mp.setenv("FLIGHTMIND_DSN", dsn)
            report = cli.run_pcap(copy, tmp_path / "reports")
        with psycopg.connect(dsn, autocommit=True) as conn:
            conn.execute("UPDATE recording_files SET uri = %s WHERE id = %s", (str(path), recording_id))
        for stage in ("decoding", "filtering", "detecting", "storing"):
            on_progress(stage, 500, 500)
        return report

    monkeypatch.setattr(uploads, "runner", stand_in)
    from real_api.app import app

    yield {"client": TestClient(app), "uploads": uploads, "calls": calls, "dsn": db, "dir": tmp_path / "uploads"}


def create(client, filename="flight.pcap", size=len(FIXTURE), **extra):
    r = client.post("/api/recordings", json={"filename": filename, "size_bytes": size, **extra})
    assert r.status_code == 201, r.text
    check(r.json(), "/api/recordings", "post", "201")
    return r.json()


def send(client, rid, content, part=PART):
    for n in range(0, -(-len(content) // part)):
        r = client.put(f"/api/recordings/{rid}/parts/{n}", content=content[n * part:(n + 1) * part])
        assert r.status_code == 204, r.text


def upload(client, content=FIXTURE, filename="flight.pcap", **extra):
    rec = create(client, filename, len(content), **extra)
    send(client, rec["id"], content)
    return rec["id"], client.post(f"/api/recordings/{rec['id']}/complete")


def get(client, rid):
    r = client.get(f"/api/recordings/{rid}")
    assert r.status_code == 200, r.text
    check(r.json(), "/api/recordings/{id}")
    return r.json()


def test_upload_in_three_parts_then_process_to_ready(env):
    client, uploads = env["client"], env["uploads"]
    rid, r = upload(client)
    assert -(-len(FIXTURE) // PART) == 3
    assert r.status_code == 202
    check(r.json(), "/api/recordings/{id}/complete", "post", "202")
    assert r.json()["status"] == "scanning" and r.json()["part_size_bytes"] == PART

    assert uploads.run_pending_once()
    rec = get(client, rid)
    assert rec["status"] == "scanned"
    assert [(s["id"], s["category"], s["frames"], s["supported"]) for s in rec["streams"]] == [("s1", 21, 500, True)]
    assert rec["streams"][0]["dst"] == "226.9.1.1:28701"

    r = client.post(f"/api/recordings/{rid}/process", json={"stream_id": "s1"})
    assert r.status_code == 202
    check(r.json(), "/api/recordings/{id}/process", "post", "202")
    assert r.json()["status"] == "queued"

    assert uploads.run_pending_once()
    assert not uploads.run_pending_once()
    rec = get(client, rid)
    assert rec["status"] == "ready", rec
    assert rec["record_count"] == 500 and rec["progress"] == {"records_done": 500, "records_total": 500}
    assert rec["first_ts"] and rec["last_ts"]
    assert env["calls"][0][1] == rid and Path(env["calls"][0][0]).read_bytes() == FIXTURE

    assert rid in client.get("/api/meta").json()["recordings"]
    assert client.get("/api/events", params={"recording": rid}).status_code == 200
    import psycopg

    with psycopg.connect(env["dsn"]) as conn:
        icao, = conn.execute("SELECT icao24 FROM telemetry WHERE raw_ref LIKE %s LIMIT 1", (rid + ":%",)).fetchone()
    track = client.get(f"/api/tracks/{icao}", params={"recording": rid}).json()
    assert "points" in track, (icao, track)
    assert track["points"] and all(p["raw_ref"].startswith(rid + ":") for p in track["points"])
    comp = client.get(f"/api/compression/{rid}")
    assert comp.status_code == 200
    check(comp.json(), "/api/compression/{recording_id}")
    assert comp.json()["points_in"] == 500
    raw = client.get(f"/api/raw/{rid}:1").json()
    assert raw["hex"].endswith(decoded_blocks()[0]["hexdata"])
    listed = client.get("/api/recordings").json()
    check(listed, "/api/recordings")
    assert listed[0]["id"] == rid


def test_same_file_twice_returns_the_first_upload(env):
    client = env["client"]
    content = drop_first(1)  # each test uploads a different file, since the database is shared
    first, r = upload(client, content)
    assert r.status_code == 202
    second, r = upload(client, content)
    assert r.status_code == 200
    check(r.json(), "/api/recordings/{id}/complete", "post", "200")
    assert r.json()["id"] == first
    assert client.get(f"/api/recordings/{second}").status_code == 404
    assert not any(p.name.startswith(second) for p in env["dir"].iterdir())  # its file is deleted


def test_create_checks_extension_and_size(env, monkeypatch):
    client = env["client"]
    assert client.post("/api/recordings", json={"filename": "notes.txt", "size_bytes": 10}).status_code == 415
    monkeypatch.setenv("FLIGHTMIND_MAX_UPLOAD_MB", "1")
    assert client.post("/api/recordings", json={"filename": "a.pcap", "size_bytes": 1024 * 1024 + 1}).status_code == 413
    assert client.post("/api/recordings", json={"filename": "a.pcap", "size_bytes": 0}).status_code == 422
    rec = create(client, "..\\..\\evil.pcap", 10)
    assert rec["filename"] == "evil.pcap"


def test_parts_must_be_in_order_and_full_size(env):
    client = env["client"]
    rid = create(client, size=60_000)["id"]
    assert client.put(f"/api/recordings/{rid}/parts/1", content=b"x" * PART).status_code == 409
    assert client.put(f"/api/recordings/{rid}/parts/0", content=b"x" * 100).status_code == 409  # short, not last
    assert client.put(f"/api/recordings/{rid}/parts/0", content=b"x" * PART).status_code == 204
    assert client.put(f"/api/recordings/{rid}/parts/0", content=b"x" * PART).status_code == 204  # retry: no-op
    assert get(client, rid)["bytes_received"] == PART
    assert client.put(f"/api/recordings/{rid}/parts/0", content=b"x" * (PART + 1)).status_code == 413
    assert client.put(f"/api/recordings/{rid}/parts/-1", content=b"x").status_code == 422
    assert client.put(f"/api/recordings/{rid}/parts/1", content=b"x" * PART).status_code == 204
    assert client.put(f"/api/recordings/{rid}/parts/2", content=b"x" * 10_001).status_code == 409  # past size
    r = client.post(f"/api/recordings/{rid}/complete")
    assert r.status_code == 409 and "50000 of 60000" in r.json()["detail"]
    assert client.put(f"/api/recordings/{rid}/parts/2", content=b"x" * 10_000).status_code == 204
    assert client.post(f"/api/recordings/{rid}/complete").status_code == 415  # not a capture
    assert get(client, rid)["bytes_received"] == 60_000


def test_process_needs_a_scanned_recording_and_a_cat021_stream(env):
    client, uploads = env["client"], env["uploads"]
    content = drop_first(2)
    rid, _ = upload(client, content)
    assert client.post(f"/api/recordings/{rid}/process", json={"stream_id": "s1"}).status_code == 409
    uploads.run_pending_once()
    assert client.post(f"/api/recordings/{rid}/process", json={"stream_id": "s9"}).status_code == 409
    assert client.post(f"/api/recordings/{rid}/process", json={"stream_id": "s1"}).status_code == 202
    assert client.post(f"/api/recordings/{rid}/process", json={"stream_id": "s1"}).status_code == 409


def _without_cat021(data: bytes) -> bytes:
    """The fixture with every ASTERIX category byte changed from 21 to 62."""
    out, pos = bytearray(data), 24
    while pos + 16 <= len(out):
        cap = struct.unpack("<I", out[pos + 8:pos + 12])[0]
        out[pos + 16 + 14 + 20 + 8] = 62
        pos += 16 + cap
    return bytes(out)


def test_file_with_no_cat021_fails_at_scan(env):
    client, uploads = env["client"], env["uploads"]
    rid, r = upload(client, _without_cat021(FIXTURE), filename="other.pcap")
    assert r.status_code == 202
    uploads.run_pending_once()
    rec = get(client, rid)
    assert rec["status"] == "failed"
    assert rec["error"] == "No CAT021 records found in other.pcap."


def test_pipeline_error_fails_with_one_sentence(env, monkeypatch):
    client, uploads = env["client"], env["uploads"]

    def broken(path, recording_id, dsn, on_progress=None, recording_date=None):
        on_progress("decoding", 0, 500)
        raise RuntimeError("decoder produced 499 blocks for 500 packets\nNothing was written")

    monkeypatch.setattr(uploads, "runner", broken)
    rid, _ = upload(client, drop_first(3))
    uploads.run_pending_once()
    client.post(f"/api/recordings/{rid}/process", json={"stream_id": "s1"})
    uploads.run_pending_once()
    rec = get(client, rid)
    assert rec["status"] == "failed"
    assert rec["error"] == "decoder produced 499 blocks for 500 packets Nothing was written."


def test_raw_asterix_upload_has_one_raw_stream(env):
    client, uploads = env["client"], env["uploads"]
    payloads, pos = [], 24
    while pos + 16 <= len(FIXTURE):
        cap = struct.unpack("<I", FIXTURE[pos + 8:pos + 12])[0]
        payloads.append(FIXTURE[pos + 16 + 42:pos + 16 + cap])
        pos += 16 + cap
    rid, r = upload(client, b"".join(payloads), filename="day1.atx", recording_date="2026-11-14")
    assert r.status_code == 202 and r.json()["format"] == "asterix_raw"
    uploads.run_pending_once()
    rec = get(client, rid)
    assert [(s["id"], s["category"], s["records"]) for s in rec["streams"]] == [("raw", 21, 500)]


def test_restart_fails_mid_processing_and_drops_stale_uploads(env):
    client, uploads = env["client"], env["uploads"]
    import psycopg

    busy = create(client, size=10)["id"]
    stale = create(client, size=10)["id"]
    stale_path = env["dir"] / f"{stale}.pcap"
    assert stale_path.exists()
    with psycopg.connect(env["dsn"], autocommit=True) as conn:
        conn.execute("UPDATE uploads SET status = 'detecting' WHERE id = %s", (busy,))
        conn.execute("UPDATE uploads SET updated_at = now() - interval '2 hours' WHERE id = %s", (stale,))
    uploads.recover()
    rec = get(client, busy)
    assert rec["status"] == "failed" and rec["error"] == uploads.RESTART_ERROR
    assert client.get(f"/api/recordings/{stale}").status_code == 404
    assert not stale_path.exists()


def test_worker_thread_takes_an_upload_to_ready(env, monkeypatch):
    client, uploads = env["client"], env["uploads"]
    monkeypatch.setenv("FLIGHTMIND_UPLOAD_WORKER", "on")
    try:
        rid, _ = upload(client, drop_first(4))
        uploads.ensure_worker()
        deadline = time.time() + 30
        status = None
        while time.time() < deadline:
            status = get(client, rid)["status"]
            if status == "scanned":
                client.post(f"/api/recordings/{rid}/process", json={"stream_id": "s1"})
            if status in ("ready", "failed"):
                break
            time.sleep(0.2)
        assert status == "ready", get(client, rid)["error"]
    finally:
        uploads.stop_worker()


def to_scanned(env, content=None):
    client, uploads = env["client"], env["uploads"]
    rid, _ = upload(client, content or drop_first(5))
    uploads.run_pending_once()
    assert get(client, rid)["status"] == "scanned"
    return rid


def to_ready(env, content=None):
    rid = to_scanned(env, content)
    env["client"].post(f"/api/recordings/{rid}/process", json={"stream_id": "s1"})
    env["uploads"].run_pending_once()
    assert get(env["client"], rid)["status"] == "ready"
    return rid


@pytest.mark.parametrize("path", ["/preview?stream=s1", "/recipe", "/quarantine", "/export"])
def test_unknown_id_is_404_and_a_recording_not_yet_scanned_is_409(env, path):
    client = env["client"]
    assert client.get(f"/api/recordings/rnope000000{path}").status_code == 404
    rid = create(client, size=10)["id"]  # still uploading
    assert client.get(f"/api/recordings/{rid}{path}").status_code == 409


def test_failed_recording_is_409_and_its_sidecar_is_gone(env):
    client, uploads = env["client"], env["uploads"]
    rid, _ = upload(client, _without_cat021(FIXTURE), filename="other.pcap")
    uploads.run_pending_once()
    assert get(client, rid)["status"] == "failed"
    for path in ("/preview?stream=s1", "/recipe", "/quarantine", "/export"):
        assert client.get(f"/api/recordings/{rid}{path}").status_code == 409, path
    assert not list(env["dir"].glob(f"{rid}*"))


def test_scanned_recording_serves_preview_recipe_and_quarantine_from_the_dry_run(env):
    client = env["client"]
    rid = to_scanned(env)
    assert (env["dir"] / f"{rid}.clean.json").exists()

    r = client.get(f"/api/recordings/{rid}/preview", params={"stream": "s1", "limit": 3})
    assert r.status_code == 200, r.text
    check(r.json(), "/api/recordings/{id}/preview")
    body = r.json()
    assert [x["raw_ref"] for x in body["records"]] == [f"{rid}:{i}" for i in (1, 2, 3)]
    assert body["records"][0]["recording_file_id"] == rid and "items" in body["records"][0]["decoded"]
    assert "sample_size" not in body and len(body["field_quality"]) == 8
    assert client.get(f"/api/recordings/{rid}/preview", params={"stream": "s9"}).status_code == 409
    assert client.get(f"/api/recordings/{rid}/preview", params={"stream": "s1", "limit": 201}).status_code == 422

    r = client.get(f"/api/recordings/{rid}/recipe")
    assert r.status_code == 200
    check(r.json(), "/api/recordings/{id}/recipe")
    recipe = r.json()
    assert [s["code"] for s in recipe["steps"]] == ["no_address", "no_position", "duplicates"]
    assert recipe["stored_bytes"] is None and recipe["ratio"] is None
    assert recipe["raw_bytes"] == len(drop_first(5)) and recipe["input_sha256"]

    r = client.get(f"/api/recordings/{rid}/quarantine", params={"limit": 5})
    assert r.status_code == 200
    check(r.json(), "/api/recordings/{id}/quarantine")
    assert r.json()["total"] == sum(s["set_aside"] for s in recipe["steps"][:2])

    # an upload from before the sidecar existed gets one computed on demand
    (env["dir"] / f"{rid}.clean.json").unlink()
    assert client.get(f"/api/recordings/{rid}/recipe").json() == recipe
    assert (env["dir"] / f"{rid}.clean.json").exists()
    assert client.get(f"/api/recordings/{rid}/export").status_code == 409  # only ready


def test_ready_recording_adds_compression_and_exports_a_zip(env):
    import csv
    import io
    import json
    import tempfile
    import zipfile

    import psycopg

    client = env["client"]
    rid = to_ready(env, drop_first(6))
    recipe = client.get(f"/api/recordings/{rid}/recipe").json()
    check(recipe, "/api/recordings/{id}/recipe")
    assert recipe["steps"][-1]["code"] == "compression"
    assert recipe["stored_bytes"] and 0 < recipe["ratio"] < 1
    total = client.get(f"/api/recordings/{rid}/quarantine").json()["total"]

    preview = client.get(f"/api/recordings/{rid}/preview", params={"stream": "s1", "limit": 200}).json()
    check(preview, "/api/recordings/{id}/preview")
    assert any("ts" in r["decoded"] and "items" in r["decoded"] for r in preview["records"])

    r = client.get(f"/api/recordings/{rid}/export")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    assert r.headers["content-disposition"] == 'attachment; filename="flight-flightmind.zip"'
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        assert sorted(z.namelist()) == ["cleaned.csv", "events.csv", "quarantine.csv", "recipe.json"]
        assert json.loads(z.read("recipe.json")) == recipe
        quarantined = list(csv.DictReader(io.StringIO(z.read("quarantine.csv").decode())))
        cleaned = list(csv.DictReader(io.StringIO(z.read("cleaned.csv").decode())))
        events = list(csv.DictReader(io.StringIO(z.read("events.csv").decode())))
    assert len(quarantined) == total
    with psycopg.connect(env["dsn"]) as conn:
        stored = conn.execute("SELECT count(*) FROM telemetry WHERE raw_ref LIKE %s", (rid + ":%",)).fetchone()[0]
        n_events = conn.execute("SELECT count(*) FROM events WHERE raw_refs[1] LIKE %s", (rid + ":%",)).fetchone()[0]
    assert len(cleaned) == stored and len(events) == n_events
    assert {"raw_ref", "flags", "ts", "icao24"} <= set(cleaned[0])
    assert not list(Path(tempfile.gettempdir()).glob("flightmind-export-*"))  # the temp zip is deleted after sending
