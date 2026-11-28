"""Cleaning dry run, recipe, quarantine and field quality (SCRUM-68), without a database."""
import json
import struct

import pytest

from real_api import clean, uploads
from realdb import FIXTURE_JSONL, FIXTURE_PCAP


def jsonl():
    return [json.loads(line) for line in FIXTURE_JSONL.read_text(encoding="utf-8").splitlines() if line]


def has(entry, item):
    return item in entry["CAT021"]


def expected_counts():
    entries = jsonl()
    no_address = [e for e in entries if not has(e, "I080")]
    no_position = [e for e in entries if has(e, "I080") and not has(e, "I130")]
    seen, dups = set(), 0
    for e in entries:
        quarantined = not has(e, "I080") or not has(e, "I130")
        if e["hexdata"] in seen and not quarantined:
            dups += 1
        seen.add(e["hexdata"])
    return entries, no_address, no_position, dups


@pytest.fixture(scope="module")
def stream():
    streams = uploads.scan_streams(str(FIXTURE_PCAP))
    assert len(streams) == 1 and streams[0]["supported"]
    return streams[0]


@pytest.fixture(scope="module")
def dry(stream):
    return clean.dry_run(str(FIXTURE_PCAP), stream, "r1")


def test_dry_run_counts_match_the_decoder_output(dry):
    entries, no_address, no_position, dups = expected_counts()
    assert dry["records_total"] == 500
    assert dry["steps"] == {"no_address": len(no_address), "no_position": len(no_position), "duplicates": dups}
    # The committed fixture is clean (every record has I080 and I130), so the rules are exercised by
    # the synthetic files below; here the fixture must report nothing set aside.
    assert (len(no_address), len(no_position)) == (0, 0)
    wanted = [(f"r1:{e['id']}", "no_address" if not has(e, "I080") else "no_position")
              for e in entries if not has(e, "I080") or not has(e, "I130")]
    assert [(q["raw_ref"], q["step_code"]) for q in dry["quarantine"]] == wanted
    for q in dry["quarantine"]:
        assert q["reason"] == clean.REASONS[q["step_code"]]


def test_item_counts_and_sample(dry):
    entries = jsonl()
    for item in ("I130", "I131", "I080", "I140", "I145", "I170", "I090", "I040"):
        assert dry["item_counts"][item] == sum(has(e, item) for e in entries), item
    assert len(dry["sample"]) == 200
    first = dry["sample"][0]
    assert first["raw_ref"] == "r1:1" and first["record_index"] == 1
    record = bytes.fromhex(entries_hex(0))
    assert first["hex"] == (bytes([21]) + (len(record) + 3).to_bytes(2, "big") + record).hex().upper()
    assert (first["sac"], first["sic"]) == (50, 201)
    for s, e in zip(dry["sample"], jsonl()):
        assert set(s["items"]) == {k for k in e["CAT021"] if k.startswith("I") and len(k) == 4}


def entries_hex(i):
    return jsonl()[i]["hexdata"]


def test_raw_file_gives_the_same_numbers_with_the_same_numbering(tmp_path, stream, dry):
    data, payloads, pos = FIXTURE_PCAP.read_bytes(), [], 24
    while pos + 16 <= len(data):
        cap = struct.unpack("<I", data[pos + 8:pos + 12])[0]
        payloads.append(data[pos + 16 + 42:pos + 16 + cap])
        pos += 16 + cap
    path = tmp_path / "day.atx"
    path.write_bytes(b"".join(payloads))
    raw = clean.dry_run(str(path), {"id": "raw", "src": "", "dst": ""}, "r1")
    assert raw["records_total"] == 500
    assert raw["steps"] == dry["steps"] and raw["quarantine"] == dry["quarantine"]
    assert raw["sample"][0]["offset"] == 0


def block(record: bytes) -> bytes:
    return bytes([21]) + (len(record) + 3).to_bytes(2, "big") + record


def test_duplicates_are_flagged_and_not_counted_when_already_set_aside(tmp_path):
    no_address = block(bytes([0x84, 0x32, 0xC9]) + bytes(6))  # FSPEC 0x84: I010 and I130
    no_position = block(bytes([0x81, 0x10, 0x32, 0xC9, 0x76, 0xCC, 0x67]))  # I010, then I080 (FRN 11)
    good = block(bytes([0x85, 0x10, 0x32, 0xC9]) + bytes(6) + bytes([0x76, 0xCC, 0x67]))  # I010, I130, I080
    path = tmp_path / "x.atx"
    path.write_bytes(no_address * 2 + no_position * 2 + good * 3)
    out = clean.dry_run(str(path), {"id": "raw", "src": "", "dst": ""}, "rx")
    assert out["records_total"] == 7
    # copies of a record that is already set aside are not counted twice; the two copies of `good` are
    assert out["steps"] == {"no_address": 2, "no_position": 2, "duplicates": 2}
    assert [(q["raw_ref"], q["step_code"]) for q in out["quarantine"]] == [
        ("rx:1", "no_address"), ("rx:2", "no_address"), ("rx:3", "no_position"), ("rx:4", "no_position")]


def test_field_quality_labels_order_and_percentages(dry):
    quality = clean.field_quality(dry)
    assert [(q["item"], q["label"]) for q in quality] == [
        ("I021/130", "Position (WGS-84)"),
        ("I021/131", "Position, high resolution"),
        ("I021/080", "Target address (ICAO 24-bit)"),
        ("I021/140", "Geometric height (WGS-84)"),
        ("I021/145", "Flight level (pressure, std 1013.25)"),
        ("I021/170", "Target identification"),
        ("I021/090", "Quality indicators (NACp)"),
        ("I021/040", "Target report descriptor"),
    ]
    entries = jsonl()
    for q, item in zip(quality, ("I130", "I131", "I080", "I140", "I145", "I170", "I090", "I040")):
        assert q["present_pct"] == round(100 * sum(has(e, item) for e in entries) / 500, 1)


def test_preview_records_follow_the_raw_record_shape(dry):
    records = clean.preview_records(dry, "r1", 3)
    assert [r["raw_ref"] for r in records] == ["r1:1", "r1:2", "r1:3"]
    first = records[0]
    assert first["recording_file_id"] == "r1" and first["record_index"] == 1
    assert first["decoded"] == {"items": dry["sample"][0]["items"]}
    assert set(first) == {"raw_ref", "recording_file_id", "record_index", "hex", "decoded", "sac", "sic"}


def test_sidecar_round_trip_and_removal(tmp_path, dry):
    upload = tmp_path / "r1.pcap"
    upload.write_bytes(b"x")
    side = clean.sidecar_path(str(upload), "r1")
    assert side == tmp_path / "r1.clean.json"
    clean.save(side, dry)
    assert clean.load(side) == dry
    assert set(json.loads(side.read_text())) >= {"records_total", "item_counts", "quarantine", "steps", "sample"}
    clean.remove_files(str(upload), "r1")
    assert not upload.exists() and not side.exists() and clean.load(side) is None


def fake_clean(total=1000, no_address=30, no_position=20, duplicates=7):
    quarantine = [{"raw_ref": f"r1:{i}", "step_code": "no_address", "reason": clean.REASONS["no_address"]}
                  for i in range(1, no_address + 1)]
    quarantine += [{"raw_ref": f"r1:{i}", "step_code": "no_position", "reason": clean.REASONS["no_position"]}
                   for i in range(100, 100 + no_position)]
    return {"records_total": total, "item_counts": {}, "quarantine": quarantine, "sample": [],
            "steps": {"no_address": no_address, "no_position": no_position, "duplicates": duplicates}}


def test_recipe_before_ready_chains_records_in_and_has_no_stored_size():
    body = clean.recipe(fake_clean(), "abc", 123_456)
    assert [(s["code"], s["records_in"], s["set_aside"]) for s in body["steps"]] == [
        ("no_address", 1000, 30), ("no_position", 970, 20), ("duplicates", 950, 0)]
    assert body["steps"][2]["label"] == "Duplicate records (flagged, kept)"
    assert "7 records are byte-for-byte copies" in body["steps"][2]["reason"] and "kept" in body["steps"][2]["reason"]
    assert (body["input_sha256"], body["raw_bytes"], body["stored_bytes"], body["ratio"]) == ("abc", 123_456, None, None)
    assert "92.6 m" in body["tolerance_note"] and "25 ft" in body["tolerance_note"]


def test_recipe_ready_adds_compression_and_uses_the_report():
    report = {"decoded_points": 950, "skipped_no_icao": 30, "dropped_no_position": 20, "rows_stored": 140,
              "stored_bytes": 12_345, "ratio_bytes": 0.1}
    body = clean.recipe(fake_clean(), "abc", 123_450, report)
    last = body["steps"][-1]
    assert (last["code"], last["label"]) == ("compression", "Track reduction within tolerance")
    assert (last["records_in"], last["set_aside"]) == (930, 790)
    assert last["reason"].startswith("Dropped points can be rebuilt from their neighbours within the tolerance")
    assert (body["stored_bytes"], body["ratio"]) == (12_345, 0.1)


def test_recipe_prefers_the_report_and_quarantine_drops_records_the_pipeline_kept():
    data = fake_clean()
    kept = {"r1:100", "r1:101"}  # an event pinned these two no_position records, so they were stored
    report = {"decoded_points": 950, "skipped_no_icao": 30, "dropped_no_position": 18, "rows_stored": 140,
              "stored_bytes": 10, "ratio_bytes": 0.5}
    items = clean.quarantine_items(data, kept)
    assert len(items) == 48 and not kept & {q["raw_ref"] for q in items}
    body = clean.recipe(data, "abc", 20, report, kept)
    assert [s["set_aside"] for s in body["steps"][:2]] == [30, 18]
    assert body["steps"][1]["records_in"] == 970
    assert sum(s["set_aside"] for s in body["steps"][:2]) == len(items)
    # a report count above what the dry run can list says so
    body = clean.recipe(data, "abc", 20, {**report, "skipped_no_icao": 35})
    assert body["steps"][0]["set_aside"] == 35 and "30 of them can be listed" in body["steps"][0]["reason"]


def test_quarantine_paging():
    items = clean.quarantine_items(fake_clean())
    assert clean.page(items, 0, 50)["total"] == 50
    assert [i["raw_ref"] for i in clean.page(items, 28, 4)["items"]] == ["r1:29", "r1:30", "r1:100", "r1:101"]
    assert clean.page(items, 50, 10) == {"total": 50, "items": []}


# ---------- the four endpoints against a stand-in for the database ----------

class FakeCursor:
    def __init__(self, rows):
        self.rows, self.itersize = rows, 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.sql = sql

    def __iter__(self):
        return iter(self.rows(self.sql))


class FakeConn:
    """Answers only the queries the four endpoints make. `row` is the uploads row."""

    def __init__(self, row, telemetry, events):
        self.row, self.telemetry, self.events = row, telemetry, events

    def execute(self, sql, params=()):
        class Result:
            def __init__(self, rows):
                self.rows = rows

            def fetchone(self):
                return self.rows[0] if self.rows else None

            def fetchall(self):
                return self.rows

            def __iter__(self):
                return iter(self.rows)

        if "FROM uploads" in sql:
            return Result([self.row] if params and params[0] == self.row["id"] else [])
        if "FROM telemetry WHERE raw_ref = ANY" in sql:
            return Result([{"raw_ref": r["raw_ref"]} for r in self.telemetry if r["raw_ref"] in params[0]])
        raise AssertionError(sql)

    def transaction(self):
        import contextlib

        return contextlib.nullcontext()

    def cursor(self, name=None):
        assert name
        return FakeCursor(lambda sql: self.telemetry if "FROM telemetry" in sql else self.events)


def endpoint_client(monkeypatch, tmp_path, status, report=None, telemetry=(), events=()):
    import contextlib
    from datetime import datetime, timezone

    from fastapi.testclient import TestClient

    from real_api.app import app

    path = tmp_path / "r1.pcap"
    path.write_bytes(FIXTURE_PCAP.read_bytes())
    stream = uploads.scan_streams(str(path))[0]
    row = {"id": "r1", "filename": "My flight (1).pcap", "size_bytes": path.stat().st_size, "sha256": "ab" * 32,
           "status": status, "streams": [stream], "path": str(path), "report": report}
    cols = ("ts", "icao24", "callsign", "lat", "lon", "baro_alt_ft", "geo_alt_ft", "gs_kt", "track_deg",
            "vrate_fpm", "squawk", "on_ground", "sac", "sic", "track_number", "raw_ref", "raw_offset", "flags")
    rows = [dict.fromkeys(cols) | {"ts": datetime(2026, 1, 1, 0, 0, i, tzinfo=timezone.utc), "icao24": "76cc67",
                                    "raw_ref": ref, "flags": ["kept_for_event"]} for i, ref in enumerate(telemetry)]
    ev = [{"id": "e1", "type": "holding", "icao24": "76cc67", "callsign": None, "start_ts": rows[0]["ts"],
           "end_ts": rows[0]["ts"], "airport": None, "severity": None, "raw_refs": list(telemetry)}] if events else []
    conn = FakeConn(row, rows, ev)

    @contextlib.contextmanager
    def connect():
        yield conn

    monkeypatch.setattr(uploads, "connect", connect)
    return TestClient(app), row


def test_scanned_endpoints_without_a_database(monkeypatch, tmp_path):
    client, row = endpoint_client(monkeypatch, tmp_path, "scanned")
    r = client.get("/api/recordings/r1/preview", params={"stream": "s1", "limit": 2})
    assert r.status_code == 200 and len(r.json()["records"]) == 2
    assert client.get("/api/recordings/r1/preview", params={"stream": "nope"}).status_code == 409
    assert client.get("/api/recordings/nope/recipe").status_code == 404
    recipe = client.get("/api/recordings/r1/recipe").json()
    assert recipe["steps"][0]["records_in"] == 500 and recipe["stored_bytes"] is None
    assert client.get("/api/recordings/r1/quarantine").json() == {"total": 0, "items": []}
    assert (tmp_path / "r1.clean.json").exists()  # computed on demand, saved once
    assert client.get("/api/recordings/r1/export").status_code == 409


@pytest.mark.parametrize("status", ["uploading", "scanning", "failed"])
def test_not_scanned_or_failed_is_409(monkeypatch, tmp_path, status):
    client, _ = endpoint_client(monkeypatch, tmp_path, status)
    for path in ("/preview?stream=s1", "/recipe", "/quarantine", "/export"):
        assert client.get(f"/api/recordings/r1{path}").status_code == 409, path


def test_export_zip_without_a_database(monkeypatch, tmp_path):
    import csv
    import io
    import tempfile
    import zipfile
    from pathlib import Path

    report = {"decoded_points": 500, "skipped_no_icao": 0, "dropped_no_position": 0, "rows_stored": 2,
              "stored_bytes": 900, "ratio_bytes": 0.02, "raw_records": 500}
    refs = ["r1:1", "r1:2"]
    before = set(Path(tempfile.gettempdir()).glob("flightmind-export-*"))
    client, _ = endpoint_client(monkeypatch, tmp_path, "ready", report, refs, events=True)
    r = client.get("/api/recordings/r1/export")
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    assert r.headers["content-disposition"] == 'attachment; filename="My_flight__1_-flightmind.zip"'
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        assert sorted(z.namelist()) == ["cleaned.csv", "events.csv", "quarantine.csv", "recipe.json"]
        assert json.loads(z.read("recipe.json")) == client.get("/api/recordings/r1/recipe").json()
        cleaned = list(csv.DictReader(io.StringIO(z.read("cleaned.csv").decode())))
        events = list(csv.DictReader(io.StringIO(z.read("events.csv").decode())))
        quarantined = list(csv.DictReader(io.StringIO(z.read("quarantine.csv").decode())))
    assert [c["raw_ref"] for c in cleaned] == refs and cleaned[0]["flags"] == "kept_for_event"
    assert cleaned[0]["ts"] == "2026-01-01T00:00:00Z" and cleaned[0]["lat"] == ""
    assert events[0]["raw_refs"] == "r1:1 r1:2"
    assert len(quarantined) == client.get("/api/recordings/r1/quarantine").json()["total"] == 0
    assert set(Path(tempfile.gettempdir()).glob("flightmind-export-*")) == before  # temp file removed after sending
    recipe = client.get("/api/recordings/r1/recipe").json()
    assert recipe["steps"][-1]["code"] == "compression" and recipe["stored_bytes"] == 900 and recipe["ratio"] == 0.02
