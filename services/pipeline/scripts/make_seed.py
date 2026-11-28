"""Regenerate fixtures/seed.sql from the committed 500-packet sample (SCRUM-22).

Usage (from the repo root):
    python services/pipeline/scripts/make_seed.py [--out fixtures/seed.sql]

It runs the same steps as the pipeline CLI (clean, split, detect, compress), but reads the
decoded blocks from fixtures/adsb_sample_500.decoded.jsonl instead of running the decoder, so it
needs no decoder binary and no database. The output is deterministic: running it twice gives the
same bytes. The file is one transaction of INSERT ... ON CONFLICT DO NOTHING statements.
"""

import argparse
import hashlib
import json
import sys
from collections.abc import Iterable, Sequence
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "services" / "pipeline"))

from flightmind_pipeline.cleaning import clean_records  # noqa: E402
from flightmind_pipeline.compress import compress_track  # noqa: E402
from flightmind_pipeline.detect_go_around import detect_go_around  # noqa: E402
from flightmind_pipeline.detect_holding import detect_holding  # noqa: E402
from flightmind_pipeline.detect_squawk import detect_squawk  # noqa: E402
from flightmind_pipeline.events import DetectedEvent, event_id  # noqa: E402
from flightmind_pipeline.pcap_source import walk_pcap  # noqa: E402
from flightmind_pipeline.points import Point, clean_input_of, point_from_block  # noqa: E402
from flightmind_pipeline.store import KEPT_FOR_EVENT_FLAG  # noqa: E402
from flightmind_pipeline.tracks import split_tracks  # noqa: E402

FIXTURES = REPO / "fixtures"
PCAP = FIXTURES / "adsb_sample_500.pcap"
JSONL = FIXTURES / "adsb_sample_500.decoded.jsonl"
DEFAULT_OUT = FIXTURES / "seed.sql"
RECORDING_ID = "adsb_sample_500"
# Repo-relative, so the seed does not depend on who generated it. The API opens it relative to
# the repo root; elsewhere, update recording_files.uri to where the pcap lives.
RECORDING_URI = "fixtures/adsb_sample_500.pcap"


def lit(value: object) -> str:
    """Return value as a SQL literal."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, datetime):
        return f"'{value.isoformat()}'"
    if isinstance(value, int | float):
        return repr(value)
    return "'" + str(value).replace("'", "''") + "'"


def text_array(values: Iterable[str]) -> str:
    items = ", ".join(lit(v) for v in values)
    return f"ARRAY[{items}]::text[]" if items else "'{}'::text[]"


def _insert(table: str, columns: Sequence[str], values: Sequence[str]) -> str:
    return (
        f"INSERT INTO {table} ({', '.join(columns)})\n"
        f"VALUES ({', '.join(values)})\nON CONFLICT DO NOTHING;"
    )


TELEMETRY_COLS = (
    "ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, "
    "squawk, on_ground, sac, sic, track_number, raw_ref, raw_offset, flags"
).split(", ")
EVENT_COLS = (
    "id, type, icao24, callsign, start_ts, end_ts, airport, lat, lon, severity, details, raw_refs"
).split(", ")


def build_seed() -> str:
    packets = list(walk_pcap(PCAP))
    blocks = [json.loads(line) for line in JSONL.read_text(encoding="utf-8").splitlines() if line]
    if len(blocks) != len(packets):
        raise RuntimeError(f"{len(blocks)} decoded blocks for {len(packets)} packets")

    inputs = []
    by_ref: dict[str, Point] = {}
    for (record_index, offset, ts), block in zip(packets, blocks, strict=True):
        point = point_from_block(block, RECORDING_ID, record_index, offset, ts)
        inputs.append(clean_input_of(point, f"{RECORDING_ID}:{record_index}", ts))
        if point is not None:
            by_ref[point.raw_ref] = point

    cleaned = clean_records(inputs)
    # The fragments rule (fewer than 20 records per address) would set aside every record of this
    # 1.7 s sample, leaving no telemetry. The seed skips that one step; steps 1 to 5 still apply.
    set_aside = [row for row in cleaned.set_aside if row[1] != "fragments"]
    dropped = {row[0] for row in set_aside}
    tracks = split_tracks(
        [by_ref[i.raw_ref] for i in inputs if i.raw_ref in by_ref and i.raw_ref not in dropped]
    )
    events: list[DetectedEvent] = []
    for track in tracks:
        events.extend(detect_squawk(track))
        events.extend(detect_go_around(track))
        events.extend(detect_holding(track))
    pinned = {ref for e in events for ref in e.raw_refs}
    kept: list[Point] = []
    for track in tracks:
        kept.extend(compress_track(track, pinned).kept)
    kept.sort(key=lambda p: (p.ts, p.icao24, p.raw_ref))
    events.sort(key=lambda e: (e.start_ts, e.type, e.icao24))

    kept_refs = {p.raw_ref for p in kept}
    missing = pinned - kept_refs
    if missing:
        raise RuntimeError(f"event records missing from telemetry: {sorted(missing)[:3]}")

    first_ts = min(p[2] for p in packets)
    last_ts = max(p[2] for p in packets)
    sha = hashlib.sha256(PCAP.read_bytes()).hexdigest()

    out = [
        "-- FlightMind fixture seed.",
        "-- Owner: Role 2 (Koolkar), SCRUM-22. GENERATED: do not edit by hand. Regenerate with",
        "--   python services/pipeline/scripts/make_seed.py",
        "-- Source: fixtures/adsb_sample_500.pcap, decoded blocks from",
        "-- fixtures/adsb_sample_500.decoded.jsonl, run through the pipeline's cleaning, track",
        "-- split, detectors and compression. The local stack (SCRUM-31) loads this file as the",
        "-- last init step (infra/docker-compose.yml, 02_seed.sql).",
        "--",
        "-- Cleaning: steps 1 to 5 only. The fragments step (fewer than 20 records per address)"
        " is skipped,",
        "-- because on this 1.7 s sample it would set aside all 500 records and leave no telemetry.",
        "--",
        "-- Rows match contracts/schema.sql (v1.2): recording_files, telemetry, events, quarantine.",
        "-- event_embeddings is left empty (needs the embedding API, Role 3). Every telemetry row",
        "-- that an event's raw_refs points at is present. The whole file is one transaction and",
        "-- every INSERT is ON CONFLICT DO NOTHING, so loading it twice changes nothing.",
        "--",
        f"-- Counts: {len(packets)} packets, {len(inputs) - cleaned.steps[0]['set_aside']} decoded"
        f" points, {len(kept)} telemetry rows, {len(set_aside)} quarantine rows,"
        f" {len(events)} events.",
    ]
    if not events:
        out.append(
            "-- The detectors found no events on this 500-packet sample, so the events table gets"
            " no rows."
        )
    out += ["", "BEGIN;", ""]

    out.append(
        _insert(
            "recording_files",
            ["id", "uri", "sha256", "size_bytes", "record_count", "first_ts", "last_ts"],
            [
                lit(RECORDING_ID),
                lit(RECORDING_URI),
                lit(sha),
                lit(PCAP.stat().st_size),
                lit(len(packets)),
                lit(first_ts),
                lit(last_ts),
            ],
        )
    )
    out.append("")

    for p in kept:
        flags = text_array([KEPT_FOR_EVENT_FLAG] if p.raw_ref in pinned else [])
        values = [
            lit(p.ts), lit(p.icao24), lit(p.callsign), lit(p.lat), lit(p.lon),
            lit(p.baro_alt_ft), lit(p.geo_alt_ft), lit(p.gs_kt), lit(p.track_deg),
            lit(p.vrate_fpm), lit(p.squawk), lit(p.on_ground), lit(p.sac), lit(p.sic),
            "NULL", lit(p.raw_ref), lit(p.raw_offset), flags,
        ]  # fmt: skip
        out.append(_insert("telemetry", TELEMETRY_COLS, values))
    out.append("")

    for raw_ref, step_code, reason in sorted(set_aside):
        out.append(
            _insert(
                "quarantine",
                ["recording_id", "raw_ref", "step_code", "reason"],
                [lit(RECORDING_ID), lit(raw_ref), lit(step_code), lit(reason)],
            )
        )
    out.append("")

    for e in events:
        values = [
            lit(str(event_id(e))), lit(e.type), lit(e.icao24), lit(e.callsign),
            lit(e.start_ts), lit(e.end_ts), lit(e.airport), lit(e.lat), lit(e.lon),
            lit(e.severity), lit(json.dumps(e.details, sort_keys=True)) + "::jsonb",
            text_array(e.raw_refs),
        ]  # fmt: skip
        out.append(_insert("events", EVENT_COLS, values))
    if events:
        out.append("")

    out += ["COMMIT;", ""]
    return "\n".join(out)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Regenerate fixtures/seed.sql")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    args.out.write_text(build_seed(), encoding="utf-8", newline="\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
