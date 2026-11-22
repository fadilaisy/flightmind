# Requirements: storage

Source: Opus Plan, steps 0 and 7 to 11. Approved picks:
- the "vectorized DB" reading is columnar storage, measured here; pgvector stays on C4 only;
- DuckDB is the third candidate;
- specs are generated first.

## Scope
- May touch only these files under `services/pipeline/`: `flightmind_pipeline/store.py`, `flightmind_pipeline/cli.py`, `tests/test_store.py`, `bench/storage_bench.py`.
- Runtime output goes to the gitignored `data/` folder (`data/reports/`, `data/bench/`).
- Benchmark tables go only in the database schema `bench`.
- Must not change `contracts/`, `infra/`, `README.md`, `KIRO.md` or `ingest-prototype\`.
- Writes only to the existing tables `recording_files`, `telemetry` and `events`.

## Unverified
- `record_index` is 1-based. This is pending Role 3 confirmation, because `/api/raw` depends on it.
- That NOTIFY fires at commit (from memory).
- The TimescaleDB columnstore syntax and the 2.18 cutover (from Tiger Data docs; the installed version is unknown until step 0).
- DuckDB index and timestamp behaviour (from memory).
- The 120 s detect + compress threshold (estimate).

### Requirement 1: write one recording atomically and repeatably
**User Story:** As an analyst, I want re-running a recording to give the same database state, so that results are reproducible.

#### Acceptance Criteria
1. WHEN `write_recording` runs THEN it SHALL do everything in one transaction, holding `pg_advisory_xact_lock(hashtext(rec.id))`.
2. WHEN a recording is written again THEN its telemetry and events SHALL be replaced, and row counts and event ids SHALL be identical.
3. IF an exception occurs before commit THEN the transaction SHALL roll back, leaving counts unchanged.
4. The system SHALL match a recording's rows by the prefix `left(raw_ref, length(id)+1) = id || ':'`. It SHALL NOT use LIKE, because `_` is a wildcard there.
5. WHEN a row's `raw_ref` is in any event THEN the system SHALL store `flags = ['kept_for_event']`. Otherwise it SHALL store `[]`.
6. Every event `raw_ref` SHALL exist in `telemetry`.
7. IF `FLIGHTMIND_DSN` is missing THEN the CLI SHALL raise an error naming it. No password SHALL appear in code.

### Requirement 2: CLI run and size report
**User Story:** As an analyst, I want a before/after size report for each recording, so that I see what compression saved and at what accuracy.

#### Acceptance Criteria
1. WHEN `python -m flightmind_pipeline.cli run <pcap>` runs THEN the system SHALL decode, split, detect, compress and write. It SHALL then write `<repo>/data/reports/<recording_id>.compression.json` and print it.
2. IF the decoded block count differs from the pcap packet count THEN the system SHALL raise before any write.
3. WHEN a divisor is 0 THEN the matching ratio field SHALL be null.
4. WHEN the pcap is empty THEN the system SHALL write only the `recording_files` row.
5. The report SHALL contain the accuracy statement in the form "Every dropped point is within its NACp bound: NACp n (<x m): k points; …; vertical within 25 ft".
6. Stage times SHALL use `time.perf_counter`. Nothing SHALL read wall-clock time (C6).

### Requirement 3: measured storage choice
**User Story:** As Kool, I want three storage engines compared on the same inputs, so that the storage choice rests on measurement.

#### Acceptance Criteria
1. The benchmark SHALL compare the TimescaleDB rowstore (A), the TimescaleDB columnstore (B) and DuckDB (C) on the same full day, using the same `params.json`.
2. The benchmark SHALL report p50, p95 and max in ms for Q1a, Q1b, Q1c, Q2, Q3 and Q3u, timed through `fetchall`.
3. A candidate SHALL pass only if all of these hold:
   - warm p95 ≤ 250 ms for Q1a, Q1c, Q2 and Q3;
   - load rate ≥ 283 rows/s.
4. The winner SHALL be the passing candidate with the lowest Q1a p95. Candidates within 10 ms of each other are ranked A, then B, then C. Adoption is Kool's decision.
5. The benchmark SHALL NOT alter `public.telemetry`.

