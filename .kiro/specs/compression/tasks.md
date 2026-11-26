# Tasks: compression (plan step 6)

Setup: the same `$py` and `cd services\pipeline` as in the detectors tasks. This step depends on detectors tasks 1 to 3 (`Point`, `geo.distance_m`, `tests/synth.py`).

- [x] 6. Compression (step 6)
  - [x] 6.1 Write `flightmind_pipeline/compress.py`: `EPU_M`, `VERTICAL_TOL_FT`, `TrackCompression` and `compress_track`, as in design.md.
    - _Requirements: 1, 2, 3_
  - [x] 6.2 Write the Hypothesis property tests in `tests/test_compress.py`.
    - Inputs:
      - tracks of 0 to 300 points near WIII;
      - some equal timestamps;
      - NACp drawn from {None, 0, 5, 8, 9, 10, 11};
      - random pinned subsets.
    - Properties:
      - pinned points are kept;
      - endpoints are kept;
      - every dropped positioned point is within tolerance, recomputed from `kept` with slack 1e-6;
      - NACp None and 0 points are kept;
      - two runs give identical output;
      - `max_ratio ≤ 1.0`.
    - _Requirements: 1.1, 1.2, 2.1–2.3, 3.2, 3.3_
  - [x] 6.3 Write unit tests:
    - a 1,000-point constant-velocity line at NACp 8 keeps 2 points;
    - empty → 0; one point → 1;
    - an altitude missing on an anchor keeps an interior point;
    - a squawk change is kept as `attribute_change`.
    - _Requirements: 2.4, 2.5, 3.4_
  - [x] 6.4 Check: `& $py -m pytest -q tests/test_compress.py` shows 0 failures. `& $py -m mypy flightmind_pipeline` and `& $py -m ruff check .` report 0 errors.

