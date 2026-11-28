"""run_recording and run_pcap on the committed 500-packet fixture, with no database and no decoder.

The decoder and the database write are replaced by fakes: the decoder yields the decoded JSON
the real one produced earlier, and the write records its arguments and returns a byte count.
"""

import json
import struct
from pathlib import Path

import pytest

import flightmind_pipeline
from flightmind_pipeline import cleaning, cli
from flightmind_pipeline.compress import tolerance_note
from flightmind_pipeline.pcap_source import walk_pcap

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"
PCAP = FIXTURES / "adsb_sample_500.pcap"
JSONL = FIXTURES / "adsb_sample_500.decoded.jsonl"
FAKE_STORED_BYTES = 12345
REPORT_KEYS = {
    "raw_bytes",
    "raw_records",
    "decoded_points",
    "rows_stored",
    "stored_bytes",
    "max_h_err_m",
    "events_by_type",
    "steps",
    "tolerance_note",
    "dropped_no_position",
    "skipped_no_icao",
}


class _FakeConn:
    def __enter__(self) -> "_FakeConn":
        return self

    def __exit__(self, *exc: object) -> None:
        return None


@pytest.fixture
def writes(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    blocks = [json.loads(line) for line in JSONL.read_text(encoding="utf-8").splitlines() if line]
    calls: list[dict] = []

    def fake_write(conn, rec, kept, pinned, events, quarantine=()) -> int:
        calls.append(
            {
                "rec": rec,
                "kept": list(kept),
                "pinned": pinned,
                "events": events,
                "quarantine": list(quarantine),
            }
        )
        return FAKE_STORED_BYTES

    monkeypatch.setattr(cli, "decode_blocks", lambda path: iter(blocks))
    monkeypatch.setattr(cli, "write_recording", fake_write)
    monkeypatch.setattr(cli.psycopg, "connect", lambda dsn: _FakeConn())
    return calls


def test_run_recording_is_exported() -> None:
    assert flightmind_pipeline.run_recording is cli.run_recording


def test_run_recording_reports_and_stores(
    writes: list[dict], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Every aircraft in the 500-packet fixture has under 20 records, so the real fragment rule would
    # set all of them aside (see test_fixture_aircraft_are_all_fragments). Lower it to keep points.
    monkeypatch.setattr(cleaning, "MIN_TRACK_RECORDS", 1)
    progress: list[tuple[str, int, int]] = []
    before = set(tmp_path.iterdir())

    report = flightmind_pipeline.run_recording(
        PCAP, "upload42", "postgresql://fake", lambda *a: progress.append(a), None
    )

    total = len(list(walk_pcap(PCAP)))
    assert REPORT_KEYS <= report.keys()
    assert report["raw_records"] == total == 500
    assert report["stored_bytes"] == FAKE_STORED_BYTES

    assert len(writes) == 1
    rec = writes[0]["rec"]
    assert rec.id == "upload42"
    assert rec.uri == str(PCAP.resolve())
    assert Path(rec.uri).is_absolute()
    kept = writes[0]["kept"]
    assert kept and len(kept) == report["rows_stored"]
    assert all(p.raw_ref.startswith("upload42:") for p in kept)

    stages = [stage for stage, _, _ in progress]
    assert list(dict.fromkeys(stages)) == ["decoding", "filtering", "detecting", "storing"]
    assert stages == sorted(stages, key=["decoding", "filtering", "detecting", "storing"].index)
    decoding = [p for p in progress if p[0] == "decoding"]
    assert decoding[-1] == ("decoding", total, total)
    assert progress[-1] == ("storing", total, total)
    assert all(t == total for _, _, t in progress)

    assert set(tmp_path.iterdir()) == before


def test_run_recording_writes_no_report_file(
    writes: list[dict], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.chdir(tmp_path)
    flightmind_pipeline.run_recording(str(PCAP), "r1", "postgresql://fake")
    assert list(tmp_path.iterdir()) == []
    assert capsys.readouterr().out == ""


def test_run_recording_rejects_non_pcap(tmp_path: Path) -> None:
    bad = tmp_path / "zeros.bin"
    bad.write_bytes(bytes(16))
    with pytest.raises(ValueError, match="Only classic pcap"):
        flightmind_pipeline.run_recording(bad, "r1", "postgresql://fake")


def test_run_recording_works_without_progress_callback(writes: list[dict]) -> None:
    report = flightmind_pipeline.run_recording(PCAP, "r1", "postgresql://fake", None, None)
    assert report["raw_records"] == 500


def test_run_pcap_still_writes_its_report_file(
    writes: list[dict],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    monkeypatch.setenv("FLIGHTMIND_DSN", "postgresql://fake")
    report = cli.run_pcap(PCAP, tmp_path / "reports")

    report_file = tmp_path / "reports" / "adsb_sample_500.compression.json"
    assert json.loads(report_file.read_text(encoding="utf-8")) == report
    assert json.loads(capsys.readouterr().out) == report
    assert report["recording_id"] == "adsb_sample_500"
    assert writes[0]["rec"].id == "adsb_sample_500"


# ---------- cleaning in the report (SCRUM-67) ----------

STEP_CODES = [
    "no_address",
    "no_position",
    "duplicates",
    "position_jumps",
    "altitude_spikes",
    "fragments",
    "compression",
]


def _check_steps(report: dict, quarantine: list[tuple[str, str, str]], kept: int) -> None:
    steps = report["steps"]
    assert [s["code"] for s in steps] == STEP_CODES
    for before, after in zip(steps, steps[1:]):
        assert after["records_in"] == before["records_in"] - before["set_aside"]
    cleaning_steps = steps[:6]
    assert sum(s["set_aside"] for s in cleaning_steps) + kept == steps[0]["records_in"]
    assert sum(s["set_aside"] for s in cleaning_steps) == len(quarantine)
    last = steps[-1]
    assert (last["records_in"], last["records_in"] - last["set_aside"]) == (kept, report["rows_stored"])
    assert last["label"] == "Track reduction within tolerance"
    assert last["reason"] == (
        "Dropped points can be rebuilt from their neighbours within the tolerance; "
        "event windows are kept whole."
    )


def test_report_has_steps_tolerance_note_and_the_old_keys(
    writes: list[dict], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cleaning, "MIN_TRACK_RECORDS", 1)
    report = flightmind_pipeline.run_recording(PCAP, "r1", "postgresql://fake")
    quarantine = writes[0]["quarantine"]
    kept_before_compression = report["steps"][5]["records_in"] - report["steps"][5]["set_aside"]
    _check_steps(report, quarantine, kept_before_compression)
    assert report["steps"][0]["records_in"] == 500
    assert report["tolerance_note"] == tolerance_note()
    assert "92.6 m for NACp 8 or lower" in report["tolerance_note"]
    assert "25 ft" in report["tolerance_note"]
    assert report["dropped_no_position"] == 0  # compression no longer sees position-less points
    assert report["skipped_no_icao"] == report["steps"][0]["set_aside"] == 0
    assert report["decoded_points"] == 500


def test_fixture_aircraft_are_all_fragments(writes: list[dict]) -> None:
    # The real rules on the 500-packet fixture: no aircraft has 20 records, so nothing is stored.
    report = flightmind_pipeline.run_recording(PCAP, "r1", "postgresql://fake")
    quarantine = writes[0]["quarantine"]
    assert report["rows_stored"] == 0 and writes[0]["kept"] == []
    _check_steps(report, quarantine, 0)
    by_code = {s["code"]: s["set_aside"] for s in report["steps"]}
    assert by_code["fragments"] > 0
    assert {code for _, code, _ in quarantine} <= set(STEP_CODES[:6])
    assert all(ref.startswith("r1:") for ref, _, _ in quarantine)
    assert len({ref for ref, _, _ in quarantine}) == len(quarantine)


def test_no_address_is_skipped_no_icao_and_goes_to_quarantine(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    blocks = [json.loads(line) for line in JSONL.read_text(encoding="utf-8").splitlines() if line]
    for index in (3, 7):
        del blocks[index]["CAT021"]["I080"]
    calls: list[dict] = []
    monkeypatch.setattr(cleaning, "MIN_TRACK_RECORDS", 1)
    monkeypatch.setattr(cli, "decode_blocks", lambda path: iter(blocks))
    monkeypatch.setattr(
        cli,
        "write_recording",
        lambda conn, rec, kept, pinned, events, quarantine=(): calls.append(list(quarantine)) or 1,
    )
    monkeypatch.setattr(cli.psycopg, "connect", lambda dsn: _FakeConn())
    report = flightmind_pipeline.run_recording(PCAP, "r1", "postgresql://fake")
    assert report["skipped_no_icao"] == 2
    assert report["decoded_points"] == 498
    assert [(r, c) for r, c, _ in calls[0] if c == "no_address"] == [
        ("r1:4", "no_address"),
        ("r1:8", "no_address"),
    ]


# ---------- stream choice ----------

ETH_UDP_DST_PORT = 14 + 20 + 2  # offset of the UDP destination port in an Ethernet/IPv4/UDP frame
ETH_PAYLOAD_CAT = 14 + 20 + 8


def _two_stream_pcap(path: Path, n: int = 120) -> tuple[list[dict], tuple[str, str]]:
    """The first n fixture packets, each followed by a copy that is a CAT062-like stream.

    Returns the decoded blocks the fake decoder must emit (one per packet, in file order) and the
    endpoints of the CAT021 stream.
    """
    data = PCAP.read_bytes()
    fixture_blocks = [
        json.loads(line) for line in JSONL.read_text(encoding="utf-8").splitlines() if line
    ]
    out = bytearray(data[:24])
    blocks: list[dict] = []
    pos = 24
    for i in range(n):
        header = data[pos : pos + 16]
        cap = struct.unpack("<I", header[8:12])[0]
        packet = data[pos + 16 : pos + 16 + cap]
        pos += 16 + cap
        copy = bytearray(packet)
        copy[ETH_UDP_DST_PORT : ETH_UDP_DST_PORT + 2] = struct.pack(">H", 28702)
        copy[ETH_PAYLOAD_CAT] = 62
        out += header + packet + header + bytes(copy)
        blocks += [fixture_blocks[i], {"id": i, "cat": 62, "CAT062": {"I010": {"SAC": 1, "SIC": 2}}}]
    path.write_bytes(bytes(out))
    ip = packet[14:34]
    sport = struct.unpack(">H", packet[34:36])[0]
    dport = struct.unpack(">H", packet[36:38])[0]
    src = ".".join(str(b) for b in ip[12:16]) + f":{sport}"
    dst = ".".join(str(b) for b in ip[16:20]) + f":{dport}"
    return blocks, (src, dst)


@pytest.fixture
def two_streams(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict:
    pcap = tmp_path / "two.pcap"
    blocks, ends = _two_stream_pcap(pcap)
    calls: list[dict] = []

    def fake_write(conn, rec, kept, pinned, events, quarantine=()) -> int:
        calls.append({"rec": rec, "kept": list(kept), "quarantine": list(quarantine)})
        return 1

    monkeypatch.setattr(cleaning, "MIN_TRACK_RECORDS", 1)
    monkeypatch.setattr(cli, "decode_blocks", lambda path: iter(blocks))
    monkeypatch.setattr(cli, "write_recording", fake_write)
    monkeypatch.setattr(cli.psycopg, "connect", lambda dsn: _FakeConn())
    return {"pcap": pcap, "ends": ends, "calls": calls}


def test_only_the_chosen_stream_is_processed(two_streams: dict) -> None:
    report = flightmind_pipeline.run_recording(
        two_streams["pcap"], "two", "postgresql://fake", stream_ends=two_streams["ends"]
    )
    call = two_streams["calls"][0]
    assert report["raw_records"] == 240  # the whole file is still numbered
    assert report["steps"][0]["records_in"] == 120  # only the CAT021 stream is cleaned
    assert report["skipped_no_icao"] == 0
    assert call["rec"].record_count == 240
    refs = [p.raw_ref for p in call["kept"]]
    assert refs and all(int(r.split(":")[1]) % 2 == 1 for r in refs)  # odd packets: the CAT021 copies
    assert all(int(r.split(":")[1]) % 2 == 1 for r, _, _ in call["quarantine"])
    quarantined_or_kept = len(call["quarantine"]) + report["steps"][5]["records_in"] - report["steps"][5]["set_aside"]
    assert quarantined_or_kept == 120


def test_without_a_stream_every_packet_is_processed(two_streams: dict) -> None:
    report = flightmind_pipeline.run_recording(two_streams["pcap"], "two", "postgresql://fake")
    assert report["steps"][0]["records_in"] == 240
    assert report["skipped_no_icao"] == 120  # the CAT062 copies carry no CAT021 address


def test_empty_stream_endpoints_mean_every_packet(two_streams: dict) -> None:
    report = flightmind_pipeline.run_recording(
        two_streams["pcap"], "two", "postgresql://fake", stream_ends=("", "")
    )
    assert report["steps"][0]["records_in"] == 240


def test_a_stream_with_no_packets_stores_nothing(two_streams: dict) -> None:
    report = flightmind_pipeline.run_recording(
        two_streams["pcap"], "two", "postgresql://fake", stream_ends=("1.1.1.1:1", "2.2.2.2:2")
    )
    assert report["steps"][0]["records_in"] == 0
    assert report["rows_stored"] == 0 and two_streams["calls"][0]["quarantine"] == []


def test_udp_endpoints_of_the_fixture_frames() -> None:
    from flightmind_pipeline.pcap_source import udp_endpoints, walk_pcap_streams

    ends = {e for *_, e in walk_pcap_streams(PCAP)}
    assert ends == {("%s" % next(iter(ends))[0], "226.9.1.1:28701")}
    assert udp_endpoints(b"\x00" * 10, 1) is None  # too short
    assert udp_endpoints(bytes(60), 1) is None  # not IPv4
    assert udp_endpoints(bytes(60), 999) is None  # unknown link type
