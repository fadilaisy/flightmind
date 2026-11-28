"""scan_recording, preview and stream_id on the committed fixture and on small built files."""

import json
import struct
from pathlib import Path

import pytest

import flightmind_pipeline
from flightmind_pipeline import cleaning, cli, streams
from flightmind_pipeline.streams import Stream, preview, scan_recording

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"
PCAP = FIXTURES / "adsb_sample_500.pcap"
JSONL = FIXTURES / "adsb_sample_500.decoded.jsonl"
UDP_DST_PORT = 14 + 20 + 2
PAYLOAD_CAT = 14 + 20 + 8


def _fixture_blocks() -> list[dict]:
    return [json.loads(line) for line in JSONL.read_text(encoding="utf-8").splitlines() if line]


def _packets(n: int) -> tuple[bytes, list[tuple[bytes, bytes]]]:
    data = PCAP.read_bytes()
    pos, out = 24, []
    for _ in range(n):
        header = data[pos : pos + 16]
        cap = struct.unpack("<I", header[8:12])[0]
        out.append((header, data[pos + 16 : pos + 16 + cap]))
        pos += 16 + cap
    return data[:24], out


def _mixed_pcap(path: Path, n021: int = 30, n062: int = 10) -> None:
    """n021 fixture packets as the CAT021 stream and n062 copies of them on another port as CAT062."""
    head, packets = _packets(n021)
    out = bytearray(head)
    for header, packet in packets:
        out += header + packet
    for header, packet in packets[:n062]:
        copy = bytearray(packet)
        copy[UDP_DST_PORT : UDP_DST_PORT + 2] = struct.pack(">H", 28702)
        copy[PAYLOAD_CAT] = 62
        copy[PAYLOAD_CAT + 3] = 0x00  # no I010, so SAC/SIC are 0
        out += header + bytes(copy)
    path.write_bytes(bytes(out))


def test_scan_of_the_fixture() -> None:
    result = scan_recording(PCAP)
    assert len(result) == 1
    stream = result[0]
    assert isinstance(stream, Stream)
    assert stream.id == "s1" and stream.supported and stream.category == 21
    assert stream.dst == "226.9.1.1:28701"
    assert stream.frames == stream.records == 500
    assert (stream.sac, stream.sic) != (0, 0)  # read from I010 of the first record


def test_scan_gives_a_cat021_and_a_cat062_stream(tmp_path: Path) -> None:
    pcap = tmp_path / "mixed.pcap"
    _mixed_pcap(pcap)
    result = scan_recording(pcap)
    assert [(s.id, s.category, s.frames, s.records, s.supported) for s in result] == [
        ("s1", 21, 30, 30, True),
        ("s2", 62, 10, 0, False),
    ]
    assert result[0].dst == "226.9.1.1:28701" and result[1].dst == "226.9.1.1:28702"
    assert (result[1].sac, result[1].sic) == (0, 0)


def test_scan_of_a_raw_asterix_file_is_one_stream(tmp_path: Path) -> None:
    block = bytes([21, 0, 8, 0x80, 7, 9, 0, 0])  # CAT021, LEN 8, FSPEC with I010 only, SAC 7, SIC 9
    raw = tmp_path / "x.ast"
    raw.write_bytes(block * 3)
    result = scan_recording(raw)
    assert result == [Stream("raw", "", "", 21, 7, 9, 3, 3, True)]


def test_scan_keeps_what_was_read_when_the_file_is_cut_short(tmp_path: Path) -> None:
    pcap = tmp_path / "cut.pcap"
    pcap.write_bytes(PCAP.read_bytes()[:-10])
    assert scan_recording(pcap)[0].frames == 499


def test_stream_ends_rejects_unknown_and_unsupported(tmp_path: Path) -> None:
    pcap = tmp_path / "mixed.pcap"
    _mixed_pcap(pcap)
    assert streams.stream_ends(pcap, "s1") == ("%s" % scan_recording(pcap)[0].src, "226.9.1.1:28701")
    with pytest.raises(ValueError, match="not CAT021"):
        streams.stream_ends(pcap, "s2")
    with pytest.raises(ValueError, match="not in this recording"):
        streams.stream_ends(pcap, "s9")


def test_preview_returns_records_and_field_quality_without_a_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    blocks = _fixture_blocks()
    monkeypatch.setattr(streams, "decode_blocks", lambda path: iter(blocks))
    records, quality = preview(PCAP, "s1", limit=5)
    assert len(records) == 5 and records[0]["record_index"] == 1
    assert quality["sample_size"] == 500
    pct = quality["present_pct"]
    assert list(pct) == ["I021/130", "I021/140", "I021/145", "I021/170", "I021/040"]
    expected = 100.0 * sum("I130" in b["CAT021"] for b in blocks) / 500
    assert pct["I021/130"] == round(expected, 1)
    assert all(0.0 <= v <= 100.0 for v in pct.values())


def test_preview_reads_at_most_100000_records(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(streams, "PREVIEW_SAMPLE_LIMIT", 120)
    blocks = _fixture_blocks()
    monkeypatch.setattr(streams, "decode_blocks", lambda path: iter(blocks))
    records, quality = preview(PCAP, "s1")
    assert len(records) == 8
    assert quality["sample_size"] == 120


def test_preview_sample_limit_is_100000() -> None:
    assert streams.PREVIEW_SAMPLE_LIMIT == 100_000


def test_preview_skips_the_other_stream_and_keeps_packet_numbers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pcap = tmp_path / "mixed.pcap"
    _mixed_pcap(pcap, n021=30, n062=10)
    fixture = _fixture_blocks()
    blocks = fixture[:30] + [{"CAT062": {"I010": {"SAC": 1, "SIC": 2}}}] * 10
    monkeypatch.setattr(streams, "decode_blocks", lambda path: iter(blocks))
    records, quality = preview(pcap, "s1", limit=100)
    assert quality["sample_size"] == 30
    assert [r["record_index"] for r in records] == list(range(1, 31))


# ---------- run_recording with stream_id ----------


class _FakeConn:
    def __enter__(self) -> "_FakeConn":
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def test_run_recording_stream_id_processes_only_that_stream(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pcap = tmp_path / "mixed.pcap"
    _mixed_pcap(pcap, n021=30, n062=10)
    blocks = _fixture_blocks()[:30] + [{"CAT062": {}}] * 10
    calls: list[dict] = []

    def fake_write(conn, rec, kept, pinned, events, quarantine=()) -> int:
        calls.append({"kept": list(kept), "quarantine": list(quarantine)})
        return 1

    monkeypatch.setattr(cleaning, "MIN_TRACK_RECORDS", 1)
    monkeypatch.setattr(cli, "decode_blocks", lambda path: iter(blocks))
    monkeypatch.setattr(cli, "write_recording", fake_write)
    monkeypatch.setattr(cli.psycopg, "connect", lambda dsn: _FakeConn())

    report = flightmind_pipeline.run_recording(pcap, "mixed", "postgresql://fake", stream_id="s1")
    assert report["raw_records"] == 40
    assert report["steps"][0]["records_in"] == 30
    assert all(int(p.raw_ref.split(":")[1]) <= 30 for p in calls[0]["kept"])
    # every record of the first step is either kept or set aside
    last_clean = report["steps"][5]
    kept = last_clean["records_in"] - last_clean["set_aside"]
    assert sum(s["set_aside"] for s in report["steps"][:6]) + kept == report["steps"][0]["records_in"]
    assert sum(s["set_aside"] for s in report["steps"][:6]) == len(calls[0]["quarantine"])

    with pytest.raises(ValueError, match="not CAT021"):
        flightmind_pipeline.run_recording(pcap, "mixed", "postgresql://fake", stream_id="s2")
