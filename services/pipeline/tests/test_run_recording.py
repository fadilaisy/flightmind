"""run_recording and run_pcap on the committed 500-packet fixture, with no database and no decoder.

The decoder and the database write are replaced by fakes: the decoder yields the decoded JSON
the real one produced earlier, and the write records its arguments and returns a byte count.
"""

import json
from pathlib import Path

import pytest

import flightmind_pipeline
from flightmind_pipeline import cli
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

    def fake_write(conn, rec, kept, pinned, events) -> int:
        calls.append({"rec": rec, "kept": list(kept), "pinned": pinned, "events": events})
        return FAKE_STORED_BYTES

    monkeypatch.setattr(cli, "decode_blocks", lambda path: iter(blocks))
    monkeypatch.setattr(cli, "write_recording", fake_write)
    monkeypatch.setattr(cli.psycopg, "connect", lambda dsn: _FakeConn())
    return calls


def test_run_recording_is_exported() -> None:
    assert flightmind_pipeline.run_recording is cli.run_recording


def test_run_recording_reports_and_stores(writes: list[dict], tmp_path: Path) -> None:
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
