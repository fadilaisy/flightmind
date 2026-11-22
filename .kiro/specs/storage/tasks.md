# Tasks: storage (plan steps 0 and 7 to 11)

Setup: the same `$py` and `cd services\pipeline` as in the detectors tasks. Tasks 0, 8 and 11 are run by the lead (commands only, no code). Order: 0 → detectors 1 to 5 → compression 6 → 7.1 to 7.3 → 8 → 9 → 7.4 → 10 → 11.

- [ ] 0.1 Record environment facts in `KiroBrain\Toolchain Status.md` (step 0):
  - TimescaleDB `extversion`;
  - Python, psycopg, hypothesis and pytest versions;
  - telemetry count, expected `1017761|417`;
  - day-01 pcap count, expected 24;
  - free disk: C: ≥ 30 GB and E: ≥ 10 GB (estimate);
  - EGM96 N at -6.1201, 106.6567, with its URL, or "not found";
  - decoder start-up time (> 0.75 s counts as a risk).
  - Check: every item has a recorded value. Commands are in the plan, step 0.
- [ ] 7. Storage writer and CLI (step 7; depends on steps 1 to 6)
  - [ ] 7.1 Write `flightmind_pipeline/store.py` (`RecordingFile`, `write_recording`) and `tests/test_store.py` (marker `db`, recording `TEST_REC`).
    - The tests cover: writing twice gives the same counts and ids; an exception before commit leaves counts unchanged; cleanup afterwards.
    - Check: `$env:FLIGHTMIND_TEST_DSN=$env:FLIGHTMIND_DSN; & $py -m pytest -q` shows 0 failures, with the db tests run and not skipped.
    - _Requirements: 1_
  - [ ] 7.2 Write `flightmind_pipeline/cli.py` with the `run` subcommand and the report, as in design.md.
    - Check: run `& $py -m flightmind_pipeline.cli run E:\ataspace\playground\PCAP\adsb_5minute.pcap` twice. Pass: identical counts, `max_ratio ≤ 1.0`, `rows_stored < decoded_points`.
    - _Requirements: 2_
  - [ ] 7.3 Confirm that no event ref is missing from telemetry.
    - Check: `docker exec flightmind-db psql -U flightmind -d flightmind -tAc "SELECT count(*) FROM events e, unnest(e.raw_refs) r WHERE NOT EXISTS (SELECT 1 FROM telemetry t WHERE t.raw_ref = r)"` prints `0`.
    - _Requirements: 1.6_
  - [ ] 7.4 Run on hour 00, after 9.1 `prepare-postgres`: `& $py -m flightmind_pipeline.cli run E:\ataspace\playground\PCAP\01\ADSB_COMSOFT_20261001-00.pcap`.
    - Pass: detect + compress ≤ 120 s (estimate), and the 7.3 query prints 0.
    - If there are zero events, report that.
- [ ] 8.1 Load the rest of day 01 at full resolution (step 8, lead):
  - `Get-ChildItem E:\ataspace\playground\PCAP\01\ADSB_COMSOFT_20261001-*.pcap | Where-Object Name -ne 'ADSB_COMSOFT_20261001-00.pcap' | ForEach-Object { & $py E:\ataspace\playground\ingest-prototype\ingest_hour.py $_.FullName }`
  - Check: 23 JSON lines, each with `rows_loaded > 0`. Record the exact day count from `SELECT count(*) FROM telemetry WHERE ts >= '2026-10-01' AND ts < '2026-10-02'` (≈ 24M).
- [ ] 9. Benchmark, Postgres candidates (step 9)
  - [ ] 9.1 Write `bench/storage_bench.py` `prepare-postgres`. Use the version branch for the TimescaleDB found in 0.1.
    - Check: `& $py bench\storage_bench.py prepare-postgres` prints load times, conversion time and sizes for A and B.
  - [ ] 9.2 Write `run`, with `params.json`, all the queries, the stats and the results file.
    - Check:
      1. Run `& $py bench\storage_bench.py run --candidates row,col`.
      2. Run `docker restart flightmind-db` and wait until it is healthy.
      3. Run `& $py bench\storage_bench.py run --candidates row,col --first-only`.
      - Pass: `storage_results.json` has every query for both candidates, and pass/fail is recorded against the thresholds.
    - _Requirements: 3.1–3.3, 3.5_
- [ ] 10. DuckDB candidate (step 10; approved)
  - [ ] 10.1 Run `& $py -m pip install duckdb`. Add `prepare-duckdb` and the duckdb branch of `run` (`read_only=True`, `?` parameters, naive UTC datetimes).
    - Check: run `& $py bench\storage_bench.py prepare-duckdb` and then `& $py bench\storage_bench.py run --candidates row,col,duckdb`. The results include all three candidates, plus the DuckDB build time and size.
    - _Requirements: 3_
- [ ] 11.1 Record the results (step 11, lead) in `KiroBrain\Speed Priority.md` and `Toolchain Status.md`:
  - the results table and the winner under the decision rule;
  - the TimescaleDB version;
  - N with its source;
  - the decoder start-up time;
  - the hour-00 compression numbers.
  - Check: the numbers are copied from `storage_results.json` and the report JSON.
  - _Requirements: 3.4_
- [ ] 11.2 Final quality bar (all specs):
  - `& $py -m pytest -q` (with `FLIGHTMIND_TEST_DSN`) shows 0 failures and no db tests skipped;
  - `& $py -m compileall -q flightmind_pipeline bench` prints nothing;
  - `& $py -m mypy flightmind_pipeline` and `& $py -m ruff check .` report 0 errors;
  - the `Select-String` wall-clock check finds no matches;
  - `git -C e:\ataspace\playground\flightmind status --porcelain` lists only `services/pipeline/**` and `.kiro/specs/**`, with nothing under `contracts/`.

Not settled:
- **Track gap:** kept at 3,600 s until the advisor re-checks it (300 s is the alternative).
- **`record_index`:** 1-based, pending Role 3.
- **README:** the decoder and DuckDB need a mention in `README.md`, which is Role 1's file.
- **Fields I added:** `nacp_range` (event details) and `stabilized_below_1000_ft = min_hat_ft < 1000` are my definitions. The plan did not spell them out.
- **Delete bounds on re-run:** I chose the wider of the stored and new first/last timestamps. I did not open `ingest_hour.py` (the upsert pattern) this session.

