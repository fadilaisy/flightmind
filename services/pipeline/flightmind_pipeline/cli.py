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

from flightmind_pipeline.cleaning import CleanInput, clean_records
from flightmind_pipeline.compress import (
    VERTICAL_TOL_FT,
    compress_track,
    tolerance_m,
    tolerance_note,
)
from flightmind_pipeline.detect_go_around import detect_go_around
from flightmind_pipeline.detect_holding import detect_holding
from flightmind_pipeline.detect_squawk import detect_squawk
from flightmind_pipeline.events import DetectedEvent
from flightmind_pipeline.pcap_source import PCAP_LE_MAGIC, decode_blocks, walk_pcap_streams
from flightmind_pipeline.points import Point, clean_input_of, point_from_block
from flightmind_pipeline.store import RecordingFile, write_recording
from flightmind_pipeline.streams import stream_ends as stream_ends_of
from flightmind_pipeline.tracks import split_tracks

ProgressCallback = Callable[[str, int, int], None]
PROGRESS_EVERY = 1000
COMPRESSION_REASON = (
    "Dropped points can be rebuilt from their neighbours within the tolerance; "
    "event windows are kept whole."
)

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
    packets: Sequence[tuple[int, int, datetime, tuple[str, str] | None]],
    stream_ends: tuple[str, str] | None,
    on_progress: ProgressCallback | None = None,
) -> tuple[list[CleanInput], dict[str, Point]]:
    """Return one CleanInput per record of the chosen stream, and the Points by raw_ref.

    The decoder emits one block per packet, in packet order. Block i belongs to packet i, so
    a different count means the raw_refs would point at the wrong records. Raise then.
    The decoder runs on the whole file; with stream_ends only packets whose UDP source and
    destination match are kept, and the others are skipped. A block with no usable ICAO24 has
    no Point; its CleanInput has icao24 None, so cleaning counts it as "no address".
    """
    inputs: list[CleanInput] = []
    points: dict[str, Point] = {}
    decoded = 0
    for block in decode_blocks(pcap):
        if decoded >= len(packets):
            raise RuntimeError(
                f"{pcap}: decoder produced more blocks than the {len(packets)} packets. "
                "Nothing was written."
            )
        record_index, offset, ts, ends = packets[decoded]
        decoded += 1
        if stream_ends is None or ends == stream_ends:
            point = point_from_block(block, recording_id, record_index, offset, ts)
            inputs.append(clean_input_of(point, f"{recording_id}:{record_index}", ts))
            if point is not None:
                points[point.raw_ref] = point
        if on_progress is not None and decoded % PROGRESS_EVERY == 0 and decoded < len(packets):
            on_progress("decoding", decoded, len(packets))
    if decoded != len(packets):
        raise RuntimeError(
            f"{pcap}: decoder produced {decoded} blocks for {len(packets)} packets. "
            "Nothing was written."
        )
    if on_progress is not None:
        on_progress("decoding", decoded, len(packets))
    return inputs, points


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
    pcap: Path,
    recording_id: str,
    dsn: str,
    on_progress: ProgressCallback | None,
    stream_ends: tuple[str, str] | None = None,
) -> dict[str, Any]:
    """Decode, clean, detect, compress and store one pcap. Return its report.

    Detection runs before compression because compression pins the raw_refs of event points,
    so the work order is decode, clean, split, detect, compress, write. Progress stages map as:
    decode -> decoding, clean and split -> filtering, detect -> detecting, compress and write
    -> storing. With stream_ends (source and destination "ip:port") only that UDP stream is
    cleaned and stored; record numbers stay the packet numbers of the whole file.
    """
    stage_seconds: dict[str, float] = {}

    def progress(stage: str, done: int, total: int) -> None:
        if on_progress is not None:
            on_progress(stage, done, total)

    started = time.perf_counter()
    packets = list(walk_pcap_streams(pcap))
    total = len(packets)
    inputs, decoded_by_ref = _decode_points(pcap, recording_id, packets, stream_ends, on_progress)
    stage_seconds["decode"] = time.perf_counter() - started

    started = time.perf_counter()
    progress("filtering", 0, total)
    cleaned = clean_records(inputs)
    points = [decoded_by_ref[r.raw_ref] for r in cleaned.kept]
    tracks = split_tracks(points)
    progress("filtering", total, total)
    split_seconds = time.perf_counter() - started
    skipped_no_icao = cleaned.steps[0]["set_aside"]
    decoded_points = len(inputs) - skipped_no_icao
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
        first_ts=min((p[2] for p in packets), default=None),
        last_ts=max((p[2] for p in packets), default=None),
    )

    started = time.perf_counter()
    with psycopg.connect(dsn) as conn:
        stored_bytes = write_recording(conn, rec, kept, pinned, events, cleaned.set_aside)
    stage_seconds["write"] = time.perf_counter() - started
    progress("storing", total, total)

    steps = [
        *cleaned.steps,
        {
            "code": "compression",
            "label": "Track reduction within tolerance",
            "records_in": len(points),
            "set_aside": len(points) - len(kept),
            "reason": COMPRESSION_REASON,
        },
    ]
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
        "steps": steps,
        "tolerance_note": tolerance_note(),
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
    stream_ends: tuple[str, str] | None = None,
    stream_id: str | None = None,
) -> dict[str, Any]:
    """Process one uploaded recording and return its report; print and write nothing.

    Only little-endian classic pcap is supported. `recording_date` is ignored because a pcap
    carries its own timestamps. `stream_id` ("s1", ... as `scan_recording` lists them) picks the
    one CAT021 stream to process; an unknown or non-CAT021 id raises ValueError. `stream_ends`
    is the same choice as (source, destination), each "ip:port"; `stream_id` wins if both are
    given. Other streams and non-UDP packets are left out of cleaning and storage, and record
    numbers stay the packet numbers of the whole file, so /api/raw still finds the bytes. With
    neither, every packet is processed. Failures propagate to the caller.
    """
    pcap = Path(path)
    try:
        with pcap.open("rb") as f:
            magic = f.read(len(PCAP_LE_MAGIC))
    except OSError as exc:
        raise ValueError("The recording file could not be read.") from exc
    if magic != PCAP_LE_MAGIC:
        raise ValueError("Only classic pcap recordings can be processed on this server for now.")
    ends = (stream_ends[0], stream_ends[1]) if stream_ends and all(stream_ends) else None
    if stream_id:
        ends = stream_ends_of(pcap, stream_id)
    return _process_pcap(pcap, recording_id, dsn, on_progress, ends)


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
