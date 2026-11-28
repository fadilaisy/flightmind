"""Write one recording's kept telemetry and detected events to Postgres, in one transaction.

Rows are matched to a recording by the prefix of their raw_ref, '<recording_id>:'. Re-running
the same recording replaces its rows, so the counts and event ids stay the same.
"""

from collections.abc import Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from datetime import datetime

import psycopg
from psycopg.types.json import Jsonb

from flightmind_pipeline.events import DetectedEvent, event_id
from flightmind_pipeline.points import Point

TELEMETRY_COLUMNS = (
    "ts",
    "icao24",
    "callsign",
    "lat",
    "lon",
    "baro_alt_ft",
    "geo_alt_ft",
    "gs_kt",
    "track_deg",
    "vrate_fpm",
    "squawk",
    "on_ground",
    "sac",
    "sic",
    "track_number",
    "raw_ref",
    "raw_offset",
    "flags",
)

KEPT_FOR_EVENT_FLAG = "kept_for_event"


@dataclass(frozen=True, slots=True)
class RecordingFile:
    id: str
    uri: str
    sha256: str
    size_bytes: int
    record_count: int
    first_ts: datetime | None
    last_ts: datetime | None


_UPSERT_RECORDING = """
INSERT INTO recording_files (id, uri, sha256, size_bytes, record_count, first_ts, last_ts)
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (id) DO UPDATE SET
  uri = EXCLUDED.uri,
  sha256 = EXCLUDED.sha256,
  size_bytes = EXCLUDED.size_bytes,
  record_count = EXCLUDED.record_count,
  first_ts = EXCLUDED.first_ts,
  last_ts = EXCLUDED.last_ts
"""

# The ts bound lets TimescaleDB skip chunks outside the recording's time range.
_SCOPE_IN_RANGE = "ts BETWEEN %s AND %s AND left(raw_ref, length(%s) + 1) = %s || ':'"
# Used when the recording has no packets, so there is no time range.
_SCOPE_ID_ONLY = "left(raw_ref, length(%s) + 1) = %s || ':'"

# Remove only this recording's events whose id this run no longer produces. Events that are still
# produced are upserted in place, so their event_embeddings rows survive (no ON DELETE CASCADE).
_DELETE_STALE_EVENTS = (
    "DELETE FROM events "
    "WHERE cardinality(raw_refs) > 0 AND left(raw_refs[1], length(%s) + 1) = %s || ':' "
    "AND NOT (id = ANY(%s::uuid[]))"
)

# Upsert on id (event_id is stable across runs). The AFTER INSERT trigger fires only for new rows,
# so events that were already stored are not announced again on re-run (review 2026-11-24).
_INSERT_EVENT = """
INSERT INTO events (id, type, icao24, callsign, start_ts, end_ts, airport, lat, lon,
                    severity, details, raw_refs)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (id) DO UPDATE SET
    type = EXCLUDED.type,
    icao24 = EXCLUDED.icao24,
    callsign = EXCLUDED.callsign,
    start_ts = EXCLUDED.start_ts,
    end_ts = EXCLUDED.end_ts,
    airport = EXCLUDED.airport,
    lat = EXCLUDED.lat,
    lon = EXCLUDED.lon,
    severity = EXCLUDED.severity,
    details = EXCLUDED.details,
    raw_refs = EXCLUDED.raw_refs
"""

_STORED_BYTES = "SELECT coalesce(sum(pg_column_size(t.*)), 0) FROM telemetry t WHERE {scope}"


def _scope(
    rec: RecordingFile, stored: tuple[datetime | None, datetime | None] | None
) -> tuple[str, tuple[object, ...]]:
    """Return the SQL condition and parameters that select this recording's telemetry rows.
    The time range is the wider of the stored range and the new one, so rows left over from an
    earlier, longer write are selected too. With no stored row, or any missing bound, the scope
    is the id prefix alone.
    """
    if stored is None:
        return _SCOPE_ID_ONLY, (rec.id, rec.id)
    old_first, old_last = stored
    firsts = [rec.first_ts, old_first]
    lasts = [rec.last_ts, old_last]
    if any(v is None for v in (*firsts, *lasts)):
        return _SCOPE_ID_ONLY, (rec.id, rec.id)
    lo = min(v for v in firsts if v is not None)
    hi = max(v for v in lasts if v is not None)
    return _SCOPE_IN_RANGE, (lo, hi, rec.id, rec.id)


def _flags(raw_ref: str, kept_for_event: AbstractSet[str]) -> str:
    # Array literal for the text[] column; written as text in COPY, as ingest_hour.py does.
    return "{" + KEPT_FOR_EVENT_FLAG + "}" if raw_ref in kept_for_event else "{}"


def write_recording(
    conn: psycopg.Connection,
    rec: RecordingFile,
    rows: Sequence[Point],
    kept_for_event: AbstractSet[str],
    events: Sequence[DetectedEvent],
) -> int:
    """Replace this recording's telemetry and events, and return the bytes they now take.

    Runs in one transaction on conn, which must not have an open transaction. Any exception
    rolls the transaction back, so the previous state stays in place. The return value is
    the sum of pg_column_size over the recording's telemetry rows.
    """
    prefix = f"{rec.id}:"
    for point in rows:
        if not point.raw_ref.startswith(prefix):
            raise ValueError(f"telemetry raw_ref {point.raw_ref!r} is not in recording {rec.id!r}")
    for event in events:
        if not event.raw_refs or not event.raw_refs[0].startswith(prefix):
            raise ValueError(f"event {event.type} for {event.icao24} is not in recording {rec.id!r}")

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (rec.id,))
            cur.execute("SELECT first_ts, last_ts FROM recording_files WHERE id = %s", (rec.id,))
            stored_row = cur.fetchone()
            scope_sql, scope_args = _scope(rec, None if stored_row is None else tuple(stored_row))
            cur.execute(
                _UPSERT_RECORDING,
                (
                    rec.id,
                    rec.uri,
                    rec.sha256,
                    rec.size_bytes,
                    rec.record_count,
                    rec.first_ts,
                    rec.last_ts,
                ),
            )
            cur.execute(f"DELETE FROM telemetry WHERE {scope_sql}", scope_args)
            produced_ids = [str(event_id(e)) for e in events]
            cur.execute(_DELETE_STALE_EVENTS, (rec.id, rec.id, produced_ids))

            copy_sql = f"COPY telemetry ({', '.join(TELEMETRY_COLUMNS)}) FROM STDIN"
            with cur.copy(copy_sql) as copy:
                for p in rows:
                    copy.write_row(
                        (
                            p.ts,
                            p.icao24,
                            p.callsign,
                            p.lat,
                            p.lon,
                            p.baro_alt_ft,
                            p.geo_alt_ft,
                            p.gs_kt,
                            p.track_deg,
                            p.vrate_fpm,
                            p.squawk,
                            p.on_ground,
                            p.sac,
                            p.sic,
                            None,  # track_number: not decoded yet
                            p.raw_ref,
                            p.raw_offset,
                            _flags(p.raw_ref, kept_for_event),
                        )
                    )

            cur.executemany(
                _INSERT_EVENT,
                [
                    (
                        event_id(e),
                        e.type,
                        e.icao24,
                        e.callsign,
                        e.start_ts,
                        e.end_ts,
                        e.airport,
                        e.lat,
                        e.lon,
                        e.severity,
                        Jsonb(e.details),
                        list(e.raw_refs),
                    )
                    for e in events
                ],
            )

            cur.execute(_STORED_BYTES.format(scope=scope_sql), scope_args)
            row = cur.fetchone()
            stored_bytes = int(row[0]) if row is not None else 0
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    return stored_bytes
