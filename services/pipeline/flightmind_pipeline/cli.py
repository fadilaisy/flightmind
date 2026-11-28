"""Command-line runner: one CAT021 pcap in, compressed telemetry and events out, plus a report.

Usage: python -m flightmind_pipeline.cli run <pcap> [--report-dir DIR]

The recording id is the file stem. The database connection comes from FLIGHTMIND_DSN.

`run_recording` is the same job as a callable for the upload worker: it takes the recording id
and the DSN as arguments, reports progress through a callback, returns the report and neither
prints nor writes a report file.
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import time
from collections import Counter
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg

from flightmind_pipeline.compress import VERTICAL_TOL_FT, compress_track, tolerance_m
from flightmind_pipeline.detect_go_around import detect_go_around
from flightmind_pipeline.detect_holding import detect_holding
from flightmind_pipeline.detect_squawk import detect_squawk
from flightmind_pipeline.events import DetectedEvent
from flightmind_pipeline.pcap_source import PCAP_LE_MAGIC, decode_blocks, walk_pcap
from flightmind_pipeline.points import Point, point_from_block
from flightmind_pipeline.store import RecordingFile, write_recording
from flightmind_pipeline.tracks import split_tracks

ProgressCallback = Callable[[str, int, int], None]
PROGRESS_EVERY = 1000

# services/pipeline/flightmind_pipeline/cli.py -> repo root is parents[3]
DEFAULT_REPORT_DIR = Path(__file__).resolve().parents[3] / "data" / "reports"


def _dsn() -> str:
    try:
        return os.environ["FLIGHTMIND_DSN"]
    except KeyError:
        raise KeyError("FLIGHTMIND_DSN is not set; it must hold the Postgres connection string") from None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _decode_points(
    pcap: Path,
    recording_id: str,
    packets: Sequence[tuple[int, int, datetime]],
    on_progress: ProgressCallback | None = None,
) -> tuple[list[Point], int]:
    """Return the points built from the decoded blocks, and the count of blocks with no ICAO24.

    The decoder emits one block per packet, in packet order. Block i belongs to packet i, so
    a different count means the raw_refs would point at the wrong records. Raise then.
    """
    points: list[Point] = []
    skipped_no_icao = 0
    decoded = 0
    for block in decode_blocks(pcap):
        if decoded >= len(packets):
            raise RuntimeError(
                f"{pcap}: decoder produced more blocks than the {len(packets)} packets. "
                "Nothing was written."
            )
        record_index, offset, ts = packets[decoded]
        decoded += 1
        point = point_from_block(block, recording_id, record_index, offset, ts)
        if point is None:
            skipped_no_icao += 1
        else:
            points.append(point)
        if on_progress is not None and decoded % PROGRESS_EVERY == 0 and decoded < len(packets):
            on_progress("decoding", decoded, len(packets))
    if decoded != len(packets):
        raise RuntimeError(
            f"{pcap}: decoder produced {decoded} blocks for {len(packets)} packets. "
            "Nothing was written."
        )
    if on_progress is not None:
        on_progress("decoding", decoded, len(packets))
    return points, skipped_no_icao


def _accuracy_statement(dropped_by_nacp: Counter[int]) -> str:
    """Return the requirement 2.5 sentence: each NACp bound with its dropped count, then vertical."""
    leading = "Every dropped point is within its NACp bound: "
    if not dropped_by_nacp:
        bounds = "no points dropped"
    else:
        parts = []
        for nacp in sorted(dropped_by_nacp):
            tol = tolerance_m(nacp)
            assert tol is not None, f"dropped points always have a known NACp, got {nacp}"
            parts.append(f"NACp {nacp} (<{tol:g} m): {dropped_by_nacp[nacp]} points")
        bounds = "; ".join(parts)
    return f"{leading}{bounds}; vertical within {VERTICAL_TOL_FT} ft"


def _ratio(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def _process_pcap(
    pcap: Path, recording_id: str, dsn: str, on_progress: ProgressCallback | None
) -> dict[str, Any]:
    """Decode, detect, compress and store one pcap. Return its report.

    Detection runs before compression because compression pins the raw_refs of event points,
    so the work order is decode, split, detect, compress, write. Progress stages map as:
    decode -> decoding, split -> filtering, detect -> detecting, compress and write -> storing.
    """
    stage_seconds: dict[str, float] = {}

    def progress(stage: str, done: int, total: int) -> None:
        if on_progress is not None:
            on_progress(stage, done, total)

    started = time.perf_counter()
    packets = list(walk_pcap(pcap))
    total = len(packets)
    points, skipped_no_icao = _decode_points(pcap, recording_id, packets, on_progress)
    stage_seconds["decode"] = time.perf_counter() - started

    started = time.perf_counter()
    progress("filtering", 0, total)
    tracks = split_tracks(points)
    progress("filtering", total, total)
    split_seconds = time.perf_counter() - started

    started = time.perf_counter()
    progress("detecting", 0, total)
    events: list[DetectedEvent] = []
    for track in tracks:
        events.extend(detect_squawk(track))
        events.extend(detect_go_around(track))
        events.extend(detect_holding(track))
    pinned = {ref for event in events for ref in event.raw_refs}
    progress("detecting", total, total)
    stage_seconds["detect"] = split_seconds + time.perf_counter() - started

    started = time.perf_counter()
    progress("storing", 0, total)
    kept: list[Point] = []
    kept_by_reason: Counter[str] = Counter()
    dropped_by_nacp: Counter[int] = Counter()
    dropped_no_position = 0
    max_h_err_m = 0.0
    max_v_err_ft = 0.0
    max_ratio = 0.0
    for track in tracks:
        result = compress_track(track, pinned)
        kept.extend(result.kept)
        kept_by_reason.update(result.kept_reason.values())
        dropped_by_nacp.update(result.dropped_by_nacp)
        dropped_no_position += result.dropped_no_position
        max_h_err_m = max(max_h_err_m, result.max_h_err_m)
        max_v_err_ft = max(max_v_err_ft, result.max_v_err_ft)
        max_ratio = max(max_ratio, result.max_ratio)
    stage_seconds["compress"] = time.perf_counter() - started

    raw_bytes = pcap.stat().st_size
    rec = RecordingFile(
        id=recording_id,
        uri=str(pcap.resolve()),
        sha256=_sha256(pcap),
        size_bytes=raw_bytes,
        record_count=len(packets),
        first_ts=min((ts for _, _, ts in packets), default=None),
        last_ts=max((ts for _, _, ts in packets), default=None),
    )

    started = time.perf_counter()
    with psycopg.connect(dsn) as conn:
        stored_bytes = write_recording(conn, rec, kept, pinned, events)
    stage_seconds["write"] = time.perf_counter() - started
    progress("storing", total, total)

    decoded_points = len(points)
    return {
        "recording_id": recording_id,
        "raw_bytes": raw_bytes,
        "raw_records": len(packets),
        "decoded_points": decoded_points,
        "skipped_no_icao": skipped_no_icao,
        "rows_stored": len(kept),
        "stored_bytes": stored_bytes,
        "ratio_rows": _ratio(len(kept), decoded_points),
        "ratio_bytes": _ratio(stored_bytes, raw_bytes),
        "kept_by_reason": dict(kept_by_reason),
        "dropped_no_position": dropped_no_position,
        "dropped_by_nacp": {str(k): v for k, v in sorted(dropped_by_nacp.items())},
        "max_h_err_m": max_h_err_m,
        "max_v_err_ft": max_v_err_ft,
        "max_ratio": max_ratio,
        "accuracy_statement": _accuracy_statement(dropped_by_nacp),
        "events_by_type": dict(Counter(e.type for e in events)),
        "stage_seconds": {k: round(v, 3) for k, v in stage_seconds.items()},
    }


def run_pcap(pcap: Path, report_dir: Path) -> dict[str, Any]:
    """Decode, detect, compress and store one pcap. Write and return its report."""
    dsn = _dsn()
    recording_id = pcap.stem
    report = _process_pcap(pcap, recording_id, dsn, None)

    report_dir.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, indent=2)
    (report_dir / f"{recording_id}.compression.json").write_text(text + "\n", encoding="utf-8")
    print(text)
    return report


def run_recording(
    path: str | os.PathLike[str],
    recording_id: str,
    dsn: str,
    on_progress: ProgressCallback | None = None,
    recording_date: dt.date | None = None,
) -> dict[str, Any]:
    """Process one uploaded recording and return its report; print and write nothing.

    Only little-endian classic pcap is supported. `recording_date` is ignored because a pcap
    carries its own timestamps. Failures propagate to the caller.
    """
    pcap = Path(path)
    try:
        with pcap.open("rb") as f:
            magic = f.read(len(PCAP_LE_MAGIC))
    except OSError as exc:
        raise ValueError("The recording file could not be read.") from exc
    if magic != PCAP_LE_MAGIC:
        raise ValueError("Only classic pcap recordings can be processed on this server for now.")
    return _process_pcap(pcap, recording_id, dsn, on_progress)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m flightmind_pipeline.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="decode, detect, compress and store one pcap")
    run.add_argument("pcap", type=Path)
    run.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    args = parser.parse_args(argv)
    run_pcap(args.pcap, args.report_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
