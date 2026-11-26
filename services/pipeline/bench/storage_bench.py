"""Benchmark two Postgres layouts for telemetry.

A: bench.tel_row, a row-store hypertable.
B: bench.tel_col, a hypertable with TimescaleDB columnstore.

prepare-postgres   copy day 01 into schema bench and build the three bench tables.
run                time the query set against each candidate and write the results.
run --first-only   one run per query (cold check after a database restart).
prepare-duckdb     build data/bench/telemetry.duckdb (candidate duckdb) from the day 01 CSV.

The DSN comes from FLIGHTMIND_DSN. Times use time.perf_counter only.
"""

import argparse
import json
import os
import random
import statistics
import struct
import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path
from time import perf_counter
from typing import Any

import psycopg

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = REPO_ROOT / "data" / "bench"
PARAMS_PATH = OUT_DIR / "params.json"
CSV_PATH = OUT_DIR / "telemetry_d01.csv"

DAY_START = datetime(2026, 10, 1, tzinfo=UTC)
DAY_END = DAY_START + timedelta(days=1)
HOUR = timedelta(hours=1)
SEED = 42
AIRCRAFT_COUNT = 20
RAW_REF_COUNT = 20
MAX_RAW_REF_DRAWS = 10_000
EVENT_COUNT = 10_000
EVENT_REFS = 200
EVENT_TYPES = ("go_around", "holding", "squawk_7500", "squawk_7600", "squawk_7700")
# Q2 always reads Postgres bench.events. The name says so, so no DuckDB result is labelled Q2.
Q2_NAME = "Q2 (Postgres bench.events, shared)"
WIII_LAT = -6.1201
WIII_LON = 106.6567
PCAP_RECORD_HEADER = struct.Struct("<IIII")
CSV_BLOCK_BYTES = 1 << 20

CANDIDATES = {"row": "bench.tel_row", "col": "bench.tel_col", "duckdb": "telemetry"}
DUCKDB_PATH = OUT_DIR / "telemetry.duckdb"
DUCKDB_PREPARE_PATH = OUT_DIR / "duckdb_prepare.json"
# Same types as public.telemetry in contracts/schema.sql. ts is naive UTC; flags is kept as text.
TELEMETRY_COLUMNS = {
    "ts": "TIMESTAMP",
    "icao24": "VARCHAR",
    "callsign": "VARCHAR",
    "lat": "DOUBLE",
    "lon": "DOUBLE",
    "baro_alt_ft": "INTEGER",
    "geo_alt_ft": "INTEGER",
    "gs_kt": "REAL",
    "track_deg": "REAL",
    "vrate_fpm": "INTEGER",
    "squawk": "VARCHAR",
    "on_ground": "BOOLEAN",
    "sac": "SMALLINT",
    "sic": "SMALLINT",
    "track_number": "INTEGER",
    "raw_ref": "VARCHAR",
    "raw_offset": "BIGINT",
    "flags": "VARCHAR",
}

# Limits from the approved plan (KiroBrain "Opus Plan - Detectors and Compression", Step 11).
# A missed limit is reported as a failure. Do not change these to make a candidate pass.
P95_LIMIT_MS = 250.0
LOAD_MIN_ROWS_PER_S = 283.0


def dsn() -> str:
    value = os.environ.get("FLIGHTMIND_DSN")
    if value is None:
        raise KeyError("missing environment variable FLIGHTMIND_DSN")
    return value


def connect() -> psycopg.Connection[tuple[Any, ...]]:
    conn = psycopg.connect(dsn(), autocommit=True)
    # Exported timestamps then carry an explicit +00 offset.
    conn.execute("SET TIME ZONE 'UTC'")
    return conn


def one(conn: psycopg.Connection[tuple[Any, ...]], sql: str, args: Sequence[Any] = ()) -> tuple[Any, ...]:
    row = conn.execute(sql, args).fetchone()
    if row is None:
        raise LookupError(f"no row returned for: {sql}")
    return row


def print_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> None:
    cells = [list(headers)] + [[str(value) for value in row] for row in rows]
    widths = [max(len(line[i]) for line in cells) for i in range(len(headers))]
    for index, line in enumerate(cells):
        print("  ".join(cell.ljust(width) for cell, width in zip(line, widths)))
        if index == 0:
            print("  ".join("-" * width for width in widths))


def export_day(conn: psycopg.Connection[tuple[Any, ...]]) -> float:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    start = perf_counter()
    with (
        conn.cursor() as cur,
        open(CSV_PATH, "wb") as f,
        cur.copy(
            "COPY (SELECT * FROM public.telemetry WHERE ts >= %s AND ts < %s) "
            "TO STDOUT (FORMAT csv, HEADER)",
            (DAY_START, DAY_END),
        ) as copy,
    ):
        f.writelines(copy)
    return perf_counter() - start


def load_csv(conn: psycopg.Connection[tuple[Any, ...]], table: str) -> float:
    start = perf_counter()
    with (
        conn.cursor() as cur,
        open(CSV_PATH, "rb") as f,
        cur.copy(f"COPY {table} FROM STDIN (FORMAT csv, HEADER)") as copy,
    ):
        while block := f.read(CSV_BLOCK_BYTES):
            copy.write(block)
    return perf_counter() - start


def convert_chunks(conn: psycopg.Connection[tuple[Any, ...]], table: str) -> tuple[float, int]:
    chunks = [row[0] for row in conn.execute(f"SELECT show_chunks('{table}')").fetchall()]
    start = perf_counter()
    for chunk in chunks:
        conn.execute("CALL convert_to_columnstore(%s::regclass)", (chunk,))
    return perf_counter() - start, len(chunks)


def build_hypertable(
    conn: psycopg.Connection[tuple[Any, ...]], table: str, columnstore: bool
) -> dict[str, Any]:
    conn.execute(
        f"CREATE TABLE {table} (LIKE public.telemetry "
        "INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES)"
    )
    conn.execute(f"SELECT create_hypertable('{table}', 'ts')")
    if columnstore:
        conn.execute(
            f"ALTER TABLE {table} SET (timescaledb.enable_columnstore = true, "
            "timescaledb.segmentby = 'icao24', timescaledb.orderby = 'ts, raw_ref')"
        )
    load_s = load_csv(conn, table)
    result: dict[str, Any] = {"load_s": round(load_s, 3)}
    if columnstore:
        convert_s, chunk_count = convert_chunks(conn, table)
        result["convert_s"] = round(convert_s, 3)
        result["chunks_converted"] = chunk_count
    rows = int(one(conn, f"SELECT count(*) FROM {table}")[0])
    result["rows"] = rows
    result["rows_per_s_load"] = round(rows / load_s, 1)
    result["hypertable_bytes"] = int(one(conn, f"SELECT hypertable_size('{table}')")[0])
    result["load_meets_limit"] = rows / load_s >= LOAD_MIN_ROWS_PER_S
    return result


def public_day_reference(conn: psycopg.Connection[tuple[Any, ...]]) -> dict[str, Any]:
    # Overlap, not containment: show_chunks() returns only chunks entirely inside a range, and
    # the chunk that holds day 01 also holds later days. Its range is reported so the size is
    # read correctly.
    chunks = conn.execute(
        "SELECT chunk_schema || '.' || chunk_name, range_start, range_end "
        "FROM timescaledb_information.chunks "
        "WHERE hypertable_schema = 'public' AND hypertable_name = 'telemetry' "
        "AND range_start < %s AND range_end > %s ORDER BY range_start",
        (DAY_END, DAY_START),
    ).fetchall()
    ranges = []
    total = 0
    for name, range_start, range_end in chunks:
        size = int(one(conn, "SELECT pg_total_relation_size(%s::regclass)", (name,))[0])
        total += size
        ranges.append({"chunk": name, "start": range_start.isoformat(), "end": range_end.isoformat(), "bytes": size})
    return {"chunks": len(ranges), "bytes": total, "ranges": ranges}


def build_events(conn: psycopg.Connection[tuple[Any, ...]]) -> dict[str, Any]:
    rng = random.Random(SEED)
    icao24s = [row[0] for row in conn.execute("SELECT DISTINCT icao24 FROM public.telemetry WHERE ts >= %s AND ts < %s ORDER BY icao24", (DAY_START, DAY_END)).fetchall()]
    needed = EVENT_COUNT * EVENT_REFS
    refs = [
        row[0]
        for row in conn.execute(
            "SELECT raw_ref FROM bench.tel_row ORDER BY ts, raw_ref LIMIT %s", (needed,)
        ).fetchall()
    ]
    if len(refs) < needed:
        raise RuntimeError(f"bench.tel_row gave {len(refs)} raw_refs, need {needed}")
    rows = []
    for index in range(EVENT_COUNT):
        start = DAY_START + timedelta(seconds=rng.randrange(86_400))
        end = start + timedelta(seconds=rng.randrange(60, 1800))
        rows.append(
            (
                uuid.UUID(int=rng.getrandbits(128), version=4),
                rng.choice(EVENT_TYPES),
                rng.choice(icao24s),
                None,
                start,
                end,
                "WIII",
                WIII_LAT + rng.uniform(-0.2, 0.2),
                WIII_LON + rng.uniform(-0.2, 0.2),
                rng.randint(1, 3),
                refs[index * EVENT_REFS : (index + 1) * EVENT_REFS],
            )
        )
    # LIKE copies no triggers, so inserts here do not send NOTIFY events_new.
    conn.execute("CREATE TABLE bench.events (LIKE public.events INCLUDING ALL)")
    start_s = perf_counter()
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO bench.events (id, type, icao24, callsign, start_ts, end_ts, airport, "
            "lat, lon, severity, raw_refs) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            rows,
        )
    insert_s = perf_counter() - start_s
    return {
        "rows": EVENT_COUNT,
        "refs_per_event": EVENT_REFS,
        "insert_s": round(insert_s, 3),
        "bytes": int(one(conn, "SELECT pg_total_relation_size('bench.events')")[0]),
    }


def prepare_postgres() -> None:
    report: dict[str, Any] = {}
    with connect() as conn:
        conn.execute("CREATE SCHEMA IF NOT EXISTS bench")
        for table in ("tel_row", "tel_col", "events"):
            conn.execute(f"DROP TABLE IF EXISTS bench.{table}")
        report["export_s"] = round(export_day(conn), 3)
        report["csv_bytes"] = CSV_PATH.stat().st_size
        report["public_day01_reference"] = public_day_reference(conn)
        report["row"] = build_hypertable(conn, "bench.tel_row", columnstore=False)
        report["col"] = build_hypertable(conn, "bench.tel_col", columnstore=True)
        report["events"] = build_events(conn)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "prepare_results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print_table(
        ["candidate", "rows", "load_s", "rows/s", "convert_s", "hypertable_MB", "load>=283/s"],
        [
            [
                name,
                report[name]["rows"],
                report[name]["load_s"],
                report[name]["rows_per_s_load"],
                report[name].get("convert_s", "-"),
                round(report[name]["hypertable_bytes"] / 1e6, 1),
                report[name]["load_meets_limit"],
            ]
            for name in ("row", "col")
        ],
    )
    ref = report["public_day01_reference"]
    for chunk in ref["ranges"]:
        print(f"public.telemetry chunk {chunk['chunk']} {chunk['start']} to {chunk['end']}: {round(chunk['bytes'] / 1e6, 1)} MB")
    print(f"export_s={report['export_s']} csv_MB={round(report['csv_bytes'] / 1e6, 1)}")
    print(f"bench.events: {report['events']}")


def choose_params(conn: psycopg.Connection[tuple[Any, ...]]) -> dict[str, Any]:
    per_aircraft = conn.execute(
        "SELECT icao24, min(ts), count(*) FROM public.telemetry "
        "WHERE ts >= %s AND ts < %s GROUP BY icao24 ORDER BY icao24",
        (DAY_START, DAY_END),
    ).fetchall()
    busiest_icao24, first_ts_busiest, busiest_rows = min(per_aircraft, key=lambda r: (-r[2], r[0]))
    hour_start, hour_rows = one(
        conn,
        "SELECT date_trunc('hour', ts), count(*) FROM public.telemetry "
        "WHERE icao24 = %s AND ts >= %s AND ts < %s GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 1",
        (busiest_icao24, DAY_START, DAY_END),
    )

    first_ts = {icao24: ts for icao24, ts, _ in per_aircraft}
    all_icao24 = sorted(first_ts)
    sampled = random.Random(SEED).sample(all_icao24, AIRCRAFT_COUNT)
    aircraft = [
        {
            "icao24": icao24,
            "start": first_ts[icao24].isoformat(),
            "end": (first_ts[icao24] + HOUR).isoformat(),
        }
        for icao24 in sampled
    ]

    recordings = conn.execute(
        "SELECT id, record_count FROM recording_files "
        "WHERE first_ts < %s AND last_ts >= %s AND record_count > 0 ORDER BY id",
        (DAY_END, DAY_START),
    ).fetchall()
    raw_refs = draw_raw_refs(conn, recordings)

    return {
        "seed": SEED,
        "busiest_aircraft": {
            "icao24": busiest_icao24,
            "day01_rows": busiest_rows,
            "day01_first_ts": first_ts_busiest.isoformat(),
        },
        "busiest_hour": {
            "start": hour_start.isoformat(),
            "end": (hour_start + HOUR).isoformat(),
            "rows": hour_rows,
        },
        "day01": {"start": DAY_START.isoformat(), "end": DAY_END.isoformat()},
        "aircraft": aircraft,
        "raw_refs": raw_refs,
    }


def draw_raw_refs(
    conn: psycopg.Connection[tuple[Any, ...]], recordings: Sequence[tuple[str, int]]
) -> list[str]:
    rng = random.Random(SEED)
    picked: list[str] = []
    for _ in range(MAX_RAW_REF_DRAWS):
        recording_id, record_count = recordings[rng.randrange(len(recordings))]
        ref = f"{recording_id}:{rng.randint(1, record_count)}"
        if ref in picked:
            continue
        found = conn.execute(
            "SELECT 1 FROM public.telemetry WHERE raw_ref = %s AND ts >= %s AND ts < %s LIMIT 1",
            (ref, DAY_START, DAY_END),
        ).fetchone()
        if found is None:
            continue
        picked.append(ref)
        if len(picked) == RAW_REF_COUNT:
            return picked
    raise RuntimeError(f"found {len(picked)} raw_refs in {MAX_RAW_REF_DRAWS} draws")


def load_or_choose_params(conn: psycopg.Connection[tuple[Any, ...]]) -> dict[str, Any]:
    # Inputs are chosen once. Later runs reuse the saved file so every run measures the same queries.
    if PARAMS_PATH.exists():
        return json.loads(PARAMS_PATH.read_text(encoding="utf-8"))
    params = choose_params(conn)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PARAMS_PATH.write_text(json.dumps(params, indent=2), encoding="utf-8")
    return params


def measure(call: Callable[[], None], warmup: int, repeats: int) -> list[float]:
    for _ in range(warmup):
        call()
    timings: list[float] = []
    for _ in range(repeats):
        start = perf_counter()
        call()
        timings.append((perf_counter() - start) * 1000.0)
    return timings


def summarise(name: str, timings: list[float], limit_ms: float | None) -> dict[str, Any]:
    # With one sample there is no quantile; the single value stands for p95.
    p95 = statistics.quantiles(timings, n=20, method="inclusive")[18] if len(timings) > 1 else timings[0]
    return {
        "query": name,
        "samples": len(timings),
        "p50_ms": round(statistics.median(timings), 3),
        "p95_ms": round(p95, 3),
        "max_ms": round(max(timings), 3),
        "limit_p95_ms": limit_ms,
        "pass": None if limit_ms is None else p95 <= limit_ms,
        "timings_ms": [round(t, 3) for t in timings],
    }


def q1_fetch(conn: psycopg.Connection[tuple[Any, ...]], table: str, icao24: str, start: datetime, end: datetime) -> None:
    conn.execute(
        f"SELECT ts, lat, lon, geo_alt_ft, baro_alt_ft, raw_ref, flags FROM {table} "
        "WHERE icao24 = %s AND ts >= %s AND ts < %s ORDER BY ts",
        (icao24, start, end),
    ).fetchall()


def q2_fetch(conn: psycopg.Connection[tuple[Any, ...]]) -> None:
    conn.execute(
        "SELECT * FROM bench.events WHERE start_ts >= %s ORDER BY start_ts LIMIT 200",
        (DAY_START,),
    ).fetchall()


def q3_fetch(conn: psycopg.Connection[tuple[Any, ...]], table: str, raw_ref: str, bounded: bool) -> None:
    """Look up a record and read its bytes from the pcap file."""
    recording_id = raw_ref.rsplit(":", 1)[0]
    uri, first_ts, last_ts = one(
        conn,
        "SELECT uri, first_ts, last_ts FROM public.recording_files WHERE id = %s",
        (recording_id,),
    )
    if bounded:
        row = one(
            conn,
            f"SELECT raw_offset FROM {table} WHERE raw_ref = %s AND ts BETWEEN %s AND %s",
            (raw_ref, first_ts, last_ts),
        )
    else:
        row = one(conn, f"SELECT raw_offset FROM {table} WHERE raw_ref = %s", (raw_ref,))
    offset = row[0]
    if offset is None:
        raise LookupError(f"raw_ref {raw_ref} has no raw_offset in {table}")
    read_record(uri, offset)


def read_record(uri: str, offset: int) -> None:
    """Read one pcap record header and its packet bytes at offset."""
    with open(uri, "rb") as f:
        f.seek(offset)
        header = f.read(PCAP_RECORD_HEADER.size)
        _ts_sec, _ts_usec, captured_len, _orig_len = PCAP_RECORD_HEADER.unpack(header)
        packet = f.read(captured_len)
    if len(packet) != captured_len:
        raise OSError(f"{uri}: expected {captured_len} packet bytes at {offset}, got {len(packet)}")
def naive_utc(value: datetime) -> datetime:
    # DuckDB TIMESTAMP is naive. The stored values are UTC, so the offset is dropped after conversion.
    return value.astimezone(UTC).replace(tzinfo=None)
def prepare_duckdb() -> None:
    import duckdb

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # The file is ours and is rebuilt from the CSV each time, so it is replaced.
    DUCKDB_PATH.unlink(missing_ok=True)
    column_spec = ", ".join(f"'{name}': '{kind}'" for name, kind in TELEMETRY_COLUMNS.items())
    csv_literal = CSV_PATH.as_posix().replace("'", "''")
    with connect() as pg:
        expected_rows = int(one(pg, "SELECT count(*) FROM bench.tel_row")[0])
    con = duckdb.connect(str(DUCKDB_PATH))
    try:
        start = perf_counter()
        con.execute(
            f"CREATE TABLE telemetry AS SELECT * FROM read_csv('{csv_literal}', header=true, "
            f"columns={{{column_spec}}}) ORDER BY icao24, ts"
        )
        table_s = perf_counter() - start
        start = perf_counter()
        con.execute("CREATE INDEX telemetry_raw_ref_idx ON telemetry (raw_ref)")
        index_s = perf_counter() - start
        build_s = table_s + index_s
        telemetry_rows = int(con.execute("SELECT count(*) FROM telemetry").fetchall()[0][0])
        if telemetry_rows != expected_rows:
            raise RuntimeError(f"duckdb telemetry has {telemetry_rows} rows, Postgres bench.tel_row has {expected_rows}")
        con.execute("CHECKPOINT")
    finally:
        con.close()
    size = DUCKDB_PATH.stat().st_size
    report = {
        "duckdb_version": duckdb.__version__,
        "telemetry_rows": telemetry_rows,
        "postgres_rows": expected_rows,
        "table_s": round(table_s, 3),
        "index_s": round(index_s, 3),
        "build_s": round(build_s, 3),
        "rows_per_s_build": round(telemetry_rows / build_s, 1),
        "load_meets_limit": telemetry_rows / build_s >= LOAD_MIN_ROWS_PER_S,
        "file_bytes": size,
    }
    DUCKDB_PREPARE_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print_table(
        ["candidate", "rows", "build_s", "rows/s (build)", "file_MB", "load>=283/s"],
        [["duckdb", telemetry_rows, report["build_s"], report["rows_per_s_build"], round(size / 1e6, 1), report["load_meets_limit"]]],
    )
    print(f"duckdb_version={report['duckdb_version']} table_s={report['table_s']} index_s={report['index_s']}")
    print(f"telemetry rows={telemetry_rows} (Postgres bench.tel_row {expected_rows})")
def q1_duckdb(con: Any, icao24: str, start: datetime, end: datetime) -> None:
    con.execute(
        "SELECT ts, lat, lon, geo_alt_ft, baro_alt_ft, raw_ref, flags FROM telemetry "
        "WHERE icao24 = ? AND ts >= ? AND ts < ? ORDER BY ts",
        [icao24, start, end],
    ).fetchall()
def q3_duckdb(pg: psycopg.Connection[tuple[Any, ...]], con: Any, raw_ref: str, bounded: bool) -> None:
    """Postgres recording lookup, duckdb raw_offset lookup, then the pcap read."""
    recording_id = raw_ref.rsplit(":", 1)[0]
    uri, first_ts, last_ts = one(
        pg,
        "SELECT uri, first_ts, last_ts FROM public.recording_files WHERE id = %s",
        (recording_id,),
    )
    if bounded:
        row = con.execute(
            "SELECT raw_offset FROM telemetry WHERE raw_ref = ? AND ts BETWEEN ? AND ?",
            [raw_ref, naive_utc(first_ts), naive_utc(last_ts)],
        ).fetchone()
    else:
        row = con.execute("SELECT raw_offset FROM telemetry WHERE raw_ref = ?", [raw_ref]).fetchone()
    if row is None:
        raise LookupError(f"raw_ref {raw_ref} not in duckdb telemetry")
    offset = row[0]
    if offset is None:
        raise LookupError(f"raw_ref {raw_ref} has no raw_offset in duckdb telemetry")
    read_record(uri, offset)
def run_duckdb_candidate(label: str, params: dict[str, Any], first_only: bool) -> dict[str, Any]:
    import duckdb

    # Same warm-up and repeat counts as run_candidate.
    def counts(warmup: int, repeats: int) -> tuple[int, int]:
        return (0, 1) if first_only else (warmup, repeats)

    busiest = params["busiest_aircraft"]["icao24"]
    hour_start = naive_utc(datetime.fromisoformat(params["busiest_hour"]["start"]))
    hour_end = naive_utc(datetime.fromisoformat(params["busiest_hour"]["end"]))
    day_start = naive_utc(datetime.fromisoformat(params["day01"]["start"]))
    day_end = naive_utc(datetime.fromisoformat(params["day01"]["end"]))
    aircraft = params["aircraft"]
    raw_refs = params["raw_refs"]
    queries: list[dict[str, Any]] = []
    with connect() as pg, duckdb.connect(str(DUCKDB_PATH), read_only=True) as con:
        warmup, repeats = counts(5, 50)
        timings = measure(lambda: q1_duckdb(con, busiest, hour_start, hour_end), warmup, repeats)
        queries.append(summarise("Q1a", timings, P95_LIMIT_MS))
        print(f"{label} Q1a done", flush=True)
        warmup, repeats = counts(5, 20)
        timings = measure(lambda: q1_duckdb(con, busiest, day_start, day_end), warmup, repeats)
        queries.append(summarise("Q1b", timings, None))
        warmup, repeats = counts(1, 10)
        timings = []
        for entry in aircraft:
            start = naive_utc(datetime.fromisoformat(entry["start"]))
            end = naive_utc(datetime.fromisoformat(entry["end"]))
            timings += measure(partial(q1_duckdb, con, entry["icao24"], start, end), warmup, repeats)
        queries.append(summarise("Q1c", timings, P95_LIMIT_MS))
        print(f"{label} Q1c done", flush=True)
        # Q3 and Q3u: each of the raw_refs gets its own warm-up and timed runs.
        warmup, repeats = counts(1, 5)
        timings = []
        for raw_ref in raw_refs:
            timings += measure(partial(q3_duckdb, pg, con, raw_ref, True), warmup, repeats)
        queries.append(summarise("Q3", timings, P95_LIMIT_MS))
        timings = []
        for raw_ref in raw_refs:
            timings += measure(partial(q3_duckdb, pg, con, raw_ref, False), warmup, repeats)
        queries.append(summarise("Q3u", timings, None))
        # Q2 reads Postgres bench.events, the same query as the Postgres candidates.
        warmup, repeats = counts(5, 50)
        timings = measure(lambda: q2_fetch(pg), warmup, repeats)
        queries.append(summarise(Q2_NAME, timings, P95_LIMIT_MS))
    return {"table": "telemetry", "file": str(DUCKDB_PATH), "queries": queries}
def run_candidate(label: str, table: str, params: dict[str, Any], first_only: bool) -> dict[str, Any]:
    # First-only: no warm-up and one run per query. Warm: the counts from the brief.
    def counts(warmup: int, repeats: int) -> tuple[int, int]:
        return (0, 1) if first_only else (warmup, repeats)

    busiest = params["busiest_aircraft"]["icao24"]
    hour = params["busiest_hour"]
    day = params["day01"]
    aircraft = params["aircraft"]
    raw_refs = params["raw_refs"]
    queries: list[dict[str, Any]] = []

    with connect() as conn:
        hour_start, hour_end = datetime.fromisoformat(hour["start"]), datetime.fromisoformat(hour["end"])
        day_start, day_end = datetime.fromisoformat(day["start"]), datetime.fromisoformat(day["end"])

        warmup, repeats = counts(5, 50)
        timings = measure(lambda: q1_fetch(conn, table, busiest, hour_start, hour_end), warmup, repeats)
        queries.append(summarise("Q1a", timings, P95_LIMIT_MS))
        print(f"{label} Q1a done", flush=True)

        warmup, repeats = counts(5, 20)
        timings = measure(lambda: q1_fetch(conn, table, busiest, day_start, day_end), warmup, repeats)
        queries.append(summarise("Q1b", timings, None))

        warmup, repeats = counts(1, 10)
        timings = []
        for entry in aircraft:
            start, end = datetime.fromisoformat(entry["start"]), datetime.fromisoformat(entry["end"])
            call = partial(q1_fetch, conn, table, entry["icao24"], start, end)
            timings += measure(call, warmup, repeats)
        queries.append(summarise("Q1c", timings, P95_LIMIT_MS))
        print(f"{label} Q1c done", flush=True)

        # Q3 and Q3u: each of the raw_refs gets its own warm-up and timed runs.
        warmup, repeats = counts(1, 5)
        timings = []
        for raw_ref in raw_refs:
            timings += measure(partial(q3_fetch, conn, table, raw_ref, True), warmup, repeats)
        queries.append(summarise("Q3", timings, P95_LIMIT_MS))

        timings = []
        for raw_ref in raw_refs:
            timings += measure(partial(q3_fetch, conn, table, raw_ref, False), warmup, repeats)
        queries.append(summarise("Q3u", timings, None))

        warmup, repeats = counts(5, 50)
        timings = measure(lambda: q2_fetch(conn), warmup, repeats)
        queries.append(summarise(Q2_NAME, timings, P95_LIMIT_MS))

    return {"table": table, "queries": queries}


def run_benchmark(candidates: list[str], first_only: bool) -> None:
    with connect() as conn:
        params = load_or_choose_params(conn)
        payload_rows, payload_bytes = one(
            conn,
            "SELECT count(*), coalesce(sum(octet_length(e::text)), 0) FROM "
            "(SELECT * FROM bench.events WHERE start_ts >= %s ORDER BY start_ts LIMIT 200) e",
            (DAY_START,),
        )

    results: dict[str, Any] = {
        "mode": "first-only" if first_only else "warm",
        "params_file": str(PARAMS_PATH),
        "limits": {"p95_ms": P95_LIMIT_MS, "source": "Opus Plan Step 11"},
        "q2_payload": {"rows": int(payload_rows), "bytes": int(payload_bytes)},
        "candidates": {},
    }
    if "duckdb" in candidates and not DUCKDB_PATH.exists():
        raise SystemExit(f"{DUCKDB_PATH} is missing; run prepare-duckdb first")
    for label in candidates:
        if label == "duckdb":
            results["candidates"][label] = run_duckdb_candidate(label, params, first_only)
        else:
            results["candidates"][label] = run_candidate(label, CANDIDATES[label], params, first_only)

    out_name = "storage_results_first_only.json" if first_only else "storage_results.json"
    out_path = write_results(results, out_name)

    rows = []
    for label in candidates:
        for query in results["candidates"][label]["queries"]:
            rows.append(
                [
                    label,
                    query["query"],
                    query["samples"],
                    query["p50_ms"],
                    query["p95_ms"],
                    query["max_ms"],
                    query["limit_p95_ms"] if query["limit_p95_ms"] is not None else "-",
                    "-" if query["pass"] is None else ("PASS" if query["pass"] else "FAIL"),
                ]
            )
    print_table(["cand", "query", "n", "p50_ms", "p95_ms", "max_ms", "limit_ms", "result"], rows)
    print(f"Q2 payload: {payload_rows} rows, {payload_bytes} bytes")
    print(f"wrote {out_path} (complete: {', '.join(candidates)})")


def write_results(results: dict[str, Any], out_name: str) -> Path:
    """Replace out_name with this run. The file holds every candidate measured in this run, and nothing else."""
    out_path = OUT_DIR / out_name
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return out_path
def parse_candidates(text: str) -> list[str]:
    names = [name.strip() for name in text.split(",") if name.strip()]
    unknown = [name for name in names if name not in CANDIDATES]
    if unknown:
        raise SystemExit(f"unknown candidate(s) {unknown}; this script supports {sorted(CANDIDATES)}")
    return names


def main() -> None:
    parser = argparse.ArgumentParser(prog="storage_bench")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("prepare-postgres", help="build bench tables from day 01")
    commands.add_parser("prepare-duckdb", help="build data/bench/telemetry.duckdb from the day 01 CSV")
    run = commands.add_parser("run", help="time the query set against the candidates")
    run.add_argument("--candidates", default="row,col", help="comma list of: row, col, duckdb")
    run.add_argument("--first-only", action="store_true", help="one run per query, no warm-up")
    args = parser.parse_args()

    if args.command == "prepare-postgres":
        prepare_postgres()
    elif args.command == "prepare-duckdb":
        prepare_duckdb()
    else:
        run_benchmark(parse_candidates(args.candidates), args.first_only)


if __name__ == "__main__":
    main()
