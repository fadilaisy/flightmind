# Design: storage

## Data flow (cli.py)
1. `walk_pcap` produces the packets, indexed by `record_index − 1`.
2. `decode_blocks` produces the blocks. If the block count differs from the packet count, raise.
3. `point_from_block` turns blocks into points, then `split_tracks` groups them.
4. Each track goes through the three detectors.
5. `pinned` = the union of all event refs.
6. `compress_track` runs on each track.
7. `write_recording` writes everything.
8. The report is written and printed.

`recording_id` = the file stem.

## Interfaces
**store.py**
- `write_recording(conn: psycopg.Connection, rec: RecordingFile, rows: Sequence[Point], kept_for_event: AbstractSet[str], events: Sequence[DetectedEvent]) -> int` returns `stored_bytes`.
- `RecordingFile` (frozen dataclass): `id, uri, sha256, size_bytes, record_count, first_ts, last_ts`.

Transaction steps:
1. `SELECT pg_advisory_xact_lock(hashtext(%s))`
2. Upsert `recording_files` the way `ingest_hour.py` does.
3. `DELETE FROM telemetry WHERE ts BETWEEN lo AND hi AND left(raw_ref, length(%s)+1) = %s || ':'`. Here `lo`/`hi` is the wider of the stored and new `first_ts`/`last_ts`.
4. `DELETE FROM events WHERE left(raw_refs[1], length(%s)+1) = %s || ':'`
5. COPY the telemetry rows. `track_number` is written as NULL, because `Point` has no track number.
6. INSERT events with `id = event_id(e)` and `details` as `Jsonb`.
7. `SELECT sum(pg_column_size(t.*)) FROM telemetry t WHERE <same prefix and ts bound>`
8. Commit. The events trigger sends NOTIFY `events_new`, which re-sends on every re-run (memory).

**cli.py**
- `python -m flightmind_pipeline.cli run <pcap> [--report-dir DIR]`. The default report dir is `<repo>/data/reports/`.
- Report fields:
  - sizes: `raw_bytes, raw_records, decoded_points, skipped_no_icao, rows_stored, stored_bytes, ratio_rows, ratio_bytes`;
  - compression: `kept_by_reason, dropped_no_position, dropped_by_nacp, max_h_err_m, max_v_err_ft, max_ratio, accuracy_statement`;
  - run: `events_by_type, stage_seconds {decode, detect, compress, write}`.

**bench/storage_bench.py** (subcommands)
- `prepare-postgres`:
  - Create schema `bench`.
  - COPY day 01 to `data/bench/telemetry_d24.csv` (`ts` as UTC text).
  - Build **A** `bench.tel_row`: `LIKE public.telemetry INCLUDING ALL`, then `create_hypertable`, then COPY.
  - Build **B** `bench.tel_col`, using the same DDL, then:
    - On TimescaleDB ≥ 2.18: `enable_columnstore`, segmentby `icao24`, orderby `ts, raw_ref`, then `convert_to_columnstore` per chunk from `show_chunks`.
    - On older versions: `timescaledb.compress`, `compress_segmentby`, `compress_orderby`, `compress_chunk`.
    - Load time and conversion time are timed separately.
  - Build `bench.events`: `LIKE public.events INCLUDING ALL` with no trigger, filled with 10,000 synthetic rows of 200 refs each.
  - Sizes come from `hypertable_size`.
- `prepare-duckdb`:
  - Build `data/bench/telemetry.duckdb` with `CREATE TABLE … AS SELECT * FROM read_csv(...)`, explicit types, ts as naive UTC `TIMESTAMP`, flags as VARCHAR, `ORDER BY icao24, ts`.
  - Run `CREATE INDEX ON telemetry(raw_ref)`.
  - `duckdb` is imported only inside this subcommand and inside `run` for candidate C.
- `run --candidates row,col[,duckdb] [--first-only]`:
  - Inputs are fixed once in `data/bench/params.json`.
  - The query set is below.
  - Results go to `data/bench/storage_results.json`, and a table is printed.

## Queries
| Id | What | Runs |
|---|---|---|
| Q1a | busiest icao24, its busiest hour: `ts, lat, lon, geo_alt_ft, baro_alt_ft, raw_ref, flags ORDER BY ts` | 5 warm-up, 50 timed |
| Q1b | same aircraft, whole day | report only |
| Q1c | 20 aircraft from `Random(42).sample` over the sorted distinct list, window [first ts, +1 h) | 1 warm-up, 10 timed each |
| Q3 | `recording_files` lookup, then `raw_offset` by raw_ref with a ts bound, then seek and read the pcap record header and packet | 20 refs from `Random(42)`, redrawn if missing |
| Q3u | Q3 without the ts bound | same refs as Q3 |
| Q2 | `bench.events WHERE start_ts >= day_start ORDER BY start_ts LIMIT 200`, plus payload bytes | candidate-independent |

- p95 = `statistics.quantiles(n=20, method='inclusive')[18]`.
- Q3's recording lookup stays in Postgres for DuckDB.

## Decided constants
- Thresholds: 250 ms warm p95 per query (the API and network keep the remaining 750 ms of the 1 s target), and a load rate of 283 rows/s.
- Random seed 42.
- Tie window 10 ms.

## Decided boundaries
- Re-run: replaces the recording's rows, giving identical counts and ids.
- Concurrent runs of the same recording are serialized by the advisory lock.
- Cancelled halfway: rollback, nothing written.
- Empty pcap: only the recording row is written.
- A missing env var raises an error naming it.

## Rejected
- ClickHouse: it needs a new server in `infra/` (Role 3).
- pgvector for track pulls: it is built for nearest-neighbour search, not range pulls.

