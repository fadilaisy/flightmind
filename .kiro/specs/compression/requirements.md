# Requirements: compression

Source: Opus Plan, step 6. Approved picks:
- NACp gate (option b);
- NACp 1 to 7 capped at 92.6 m;
- vertical tolerance 25 ft;
- NACp stored only in the report and in event details.

## Scope
- May touch only these files under `services/pipeline/`: `flightmind_pipeline/compress.py` and `tests/test_compress.py`.
- Depends on the detectors spec for `Point`, `geo.distance_m` and event `raw_refs`.

## Unverified values
- NACp 8 = 92.6 m comes from the FAA §91.227 text.
- NACp 9, 10 and 11 = 30, 10 and 3 m come from the advisor and ForeFlight support pages. DO-260B was not opened.
- NACp 1 to 7 come from memory.
- Every accuracy claim is worded "within NACp n". The system never promises 3 ft.

### Requirement 1: keep every event record
**User Story:** As an analyst, I want every record of every detected event kept, so that citations never point to deleted data.

#### Acceptance Criteria
1. WHEN a point's `raw_ref` is in `pinned` THEN the compressor SHALL keep it, with reason `event`, even if it has no position.
2. The compressor SHALL keep the first and last positioned points of each track, with reason `endpoint`.

### Requirement 2: bound the error of every dropped point
**User Story:** As an analyst, I want every dropped point to be reconstructable within its own NACp bound, so that the compressed track is as trustworthy as the raw one.

#### Acceptance Criteria
1. WHEN a positioned point is dropped THEN its horizontal distance to the position interpolated (linearly in time) between its kept neighbours SHALL be ≤ `EPU_M[nacp]`.
2. WHEN a positioned point is dropped THEN, for each of `geo_alt_ft` and `baro_alt_ft` present on the point, the error SHALL be ≤ 25 ft.
3. IF NACp is None or 0 THEN the compressor SHALL keep the point, with reason `nacp_unknown`.
4. IF an altitude is present on the point but missing on either kept neighbour THEN the compressor SHALL treat the error as infinite and keep a point in that segment.
5. WHEN squawk, callsign or on_ground differs from the last non-null value THEN the compressor SHALL keep the point, with reason `attribute_change`.
6. IF a non-pinned point has no lat or lon THEN the compressor SHALL drop it and count it in `dropped_no_position`.

### Requirement 3: report the result
**User Story:** As an analyst, I want the before/after size and the achieved accuracy, so that I can trust the compression.

#### Acceptance Criteria
1. The compressor SHALL return `kept`, `kept_reason`, `max_h_err_m`, `max_v_err_ft`, `max_ratio`, `dropped_by_nacp` and `dropped_no_position`.
2. `max_ratio` SHALL be ≤ 1.0 for every track.
3. WHEN the same input is compressed twice THEN the output SHALL be identical.
4. WHEN the track is empty THEN 0 points SHALL be kept. WHEN it has one point THEN 1 point SHALL be kept.

