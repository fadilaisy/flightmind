# Tasks: detectors (plan steps 1 to 5)

Setup (PowerShell):
```
$py = "E:\ataspace\playground\.venv-flightmind\Scripts\python.exe"
cd e:\ataspace\playground\flightmind\services\pipeline
```

Step 0 (storage spec, task 0.1) must be done first. It supplies `GEOID_N_FT` and the installed versions.

- [ ] 1. Package, Point, decoder source (step 1)
  - [ ] 1.1 Create `pyproject.toml`:
    - name `flightmind-pipeline`, `requires-python >=3.12`;
    - the only dependency is psycopg;
    - pytest settings: `testpaths=["tests"]`, `pythonpath=["."]`, marker `db`;
    - install mypy and ruff into the venv with default settings (approved pick 10).
    - Check: `& $py -m pip install mypy ruff` succeeds, and `& $py -c "import flightmind_pipeline"` exits 0.
    - _Requirements: 1_
  - [ ] 1.2 Write `flightmind_pipeline/points.py` (`Point`, `point_from_block`) and `pcap_source.py` (`walk_pcap`, `decode_blocks`).
    - _Requirements: 1.1–1.8_
  - [ ] 1.3 Write `tests/test_points.py` covering:
    - sample line 1: icao `8a09f6`, nacp 8, geo 34100, baro 31950, gs ≈ 415.28 kt, vrate -1150, squawk `0110`;
    - sample line 3: vrate 0 from GVR, squawk None;
    - sentinel 204793.75 → geo None;
    - missing TAddr → None;
    - bad pcap magic → ValueError.
    - Check: `& $py -m pytest -q tests/test_points.py` shows 0 failures.
- [ ] 2. Tracks and runway geometry (step 2)
  - [ ] 2.1 Write `flightmind_pipeline/tracks.py` and `geo.py`.
    - _Requirements: 2_
  - [ ] 2.2 Write `tests/test_tracks.py` and `tests/test_geo.py` covering:
    - a 3599 s gap → one track; a 3600 s gap → two tracks;
    - two icao24 → two tracks; empty → `[]`;
    - 25L in the 07R frame: along ≈ 3,590 m ± 20 and |cross| < 45 m (advisor coordinates give 42.4 m; AIP not checked, decided 2026-11-16);
    - 06 in the 07L frame: |cross| between 450 and 550 m.
    - Check: `& $py -m pytest -q tests/test_tracks.py tests/test_geo.py` shows 0 failures.
- [ ] 3. Event type and squawk detector (step 3)
  - [ ] 3.1 Write `flightmind_pipeline/events.py` (with `nacp_range`), `detect_squawk.py`, and `tests/synth.py` (1 Hz Points from a profile, with NACp and `SYN:<n>` refs).
    - _Requirements: 3, 6_
  - [ ] 3.2 Write `tests/test_detect_squawk.py` covering:
    - 10×7700 then 2000 → one event, 10 refs, severity 3;
    - 7700→7600→7700 → three events;
    - interleaved None-squawk refs are included;
    - 7701 → no event;
    - a single 7500 → start = end;
    - empty and one-point tracks;
    - two calls give identical results.
    - Check: `& $py -m pytest -q tests/test_detect_squawk.py` shows 0 failures.
- [ ] 4. Go-around detector (step 4; depends on 2 and 3)
  - [ ] 4.1 Write `flightmind_pipeline/detect_go_around.py` with the constants and state machine from design.md. Set `GEOID_N_FT` from Toolchain Status step 0.6, or None if it was not found.
    - _Requirements: 4, 6_
  - [ ] 4.2 Write `tests/test_detect_go_around.py`. The base case is a synthetic 1 Hz track at 140 kt on 07L: 3 NM out at 1,000 ft HAT, -700 fpm, minimum 400 ft, then +1,500 fpm for 20 s. Expected results:
    - base → one event, runway 07L, min_hat 400 ± 10, refs from the arm point to the confirm point, `stabilized_below_1000_ft` true;
    - on_ground at the minimum → none;
    - 3 s climb → none;
    - 100 ft rebound → none;
    - 300 m cross offset → none;
    - 20° off bearing → none;
    - the same profile on 06 → runway 06;
    - reversed on 25R → 25R;
    - empty, one-point, and repeated calls give identical results.
    - Check: `& $py -m pytest -q tests/test_detect_go_around.py` shows 0 failures.
- [ ] 5. Holding detector (step 5; depends on 2 and 3)
  - [ ] 5.1 Write `flightmind_pipeline/detect_holding.py` as in design.md.
    - _Requirements: 5, 6_
  - [ ] 5.2 Write `tests/test_detect_holding.py` covering:
    - 3°/s turns of 60 s with 60 s straights at 220 kt, two circuits → one event, right, half_turns 4;
    - the same with ±1° noise from `Random(0)` → one event;
    - a 360° orbit → none;
    - S-turns → none;
    - 200 s straights → none;
    - a single half turn → none;
    - a 40 s gap splits the run;
    - empty, one-point, and repeated calls give identical results.
    - Check: `& $py -m pytest -q tests/test_detect_holding.py` shows 0 failures.
- [ ] 5.3 Run the spec-level checks:
  - `& $py -m mypy flightmind_pipeline` and `& $py -m ruff check .` report 0 errors;
  - `Select-String -Path flightmind_pipeline\*.py -Pattern 'datetime\.now|utcnow|time\.time\(|date\.today'` finds no matches.


