# Requirements: detectors

Source: Opus Plan - Detectors and Compression (2026-11-16), steps 1 to 5. Kool approved all 13 recommendations on 2026-11-16. Priority: lowest latency, then correctness, then simplicity.

This spec also covers step 1 (package, `Point`, decoder source) and step 2 (tracks and runway geometry). The compression and storage specs build on them.

## Scope
- May touch only these files under `services/pipeline/`: `pyproject.toml`, `flightmind_pipeline/__init__.py`, `points.py`, `pcap_source.py`, `tracks.py`, `geo.py`, `events.py`, `detect_squawk.py`, `detect_go_around.py`, `detect_holding.py`, `tests/synth.py`, `tests/test_points.py`, `tests/test_tracks.py`, `tests/test_geo.py`, `tests/test_detect_squawk.py`, `tests/test_detect_go_around.py`, `tests/test_detect_holding.py`.
- Must not change `contracts/`. Events must fit `contracts/schema.sql` table `events` as it is.

## Unverified values
These values come from the advisor or from memory. Each one is marked "not verified" in code comments and in `details.thresholds`:
- the runway table;
- every go-around and holding threshold;
- 27 ft/hPa;
- QNH 1010 hPa;
- the I140 sentinel value 204,793.75;
- the WIII geoid undulation (taken from step 0, or None).

### Requirement 1: decode CAT021 records into points
**User Story:** As an analyst, I want every CAT021 record in a recording turned into a typed point that carries its `raw_ref`, so that every later result can be traced back to the record behind it.

#### Acceptance Criteria
1. WHEN a pcap is not a little-endian classic pcap THEN `walk_pcap` SHALL raise `ValueError` naming the magic bytes it found.
2. WHEN the decoder exits non-zero THEN `decode_blocks` SHALL raise `RuntimeError` containing the first 500 characters of stderr.
3. WHEN a record is decoded THEN the system SHALL set `raw_ref` to `<recording_id>:<record_index>`, where `record_index` is 1-based. This is pending Role 3 confirmation, because `/api/raw` depends on it.
4. IF `TAddr` is not 6 hex characters THEN `point_from_block` SHALL return None.
5. IF I140 is absent, or `geometric_height >= 150000` (the "greater than" sentinel), THEN `geo_alt_ft` SHALL be None.
6. WHEN I155 `BVR` is present THEN `vrate_fpm` SHALL be round(BVR). Otherwise it SHALL be round(I157 `GVR`). Otherwise it SHALL be None.
7. WHEN I090 `NACp` is an int THEN `nacp` SHALL be that int. Otherwise it SHALL be None.
8. IF a required environment variable (`FLIGHTMIND_ASTERIX_DIR`, `FLIGHTMIND_CYGWIN_BIN`) is missing THEN the system SHALL raise an error naming that variable.

### Requirement 2: split points into tracks
**User Story:** As an analyst, I want each aircraft's points grouped into tracks, so that the detectors look at one continuous flight at a time.

#### Acceptance Criteria
1. WHEN points are split THEN the system SHALL group them by `icao24` and sort them by `(ts, record_index)`.
2. WHEN the gap between consecutive points is `>= TRACK_GAP_S` (3600 s) THEN the system SHALL start a new track.
3. WHEN the input is empty THEN the system SHALL return `[]`.
4. WHEN two points share a timestamp THEN the system SHALL keep both, in `record_index` order.
5. The system SHALL process one recording file at a time and SHALL NOT carry state across files. Tracks and events are cut at each hour boundary.

### Requirement 3: emergency squawk events
**User Story:** As an analyst, I want separate events for squawk 7500, 7600 and 7700, so that I find emergencies in the data instead of learning about them from ATC reports.

#### Acceptance Criteria
1. WHEN a point's squawk equals "7500", "7600" or "7700" (string equality) THEN the system SHALL open an event of type `squawk_<code>`.
2. WHILE an event is open, IF a point has squawk None THEN the system SHALL include its `raw_ref` and SHALL neither close nor extend the event.
3. WHEN a different non-null code arrives, or the track ends, THEN the system SHALL close the event at the last point that carried the code.
4. WHEN only one record carries the code THEN the system SHALL emit an event with `start_ts = end_ts`.
5. The system SHALL set severity to 3 for 7500 and 7700, and to 2 for 7600.

### Requirement 4: go-around events
**User Story:** As an analyst, I want go-arounds at WIII detected from height above threshold (HAT), so that I see missed approaches without reading ATC logs.

#### Acceptance Criteria
1. IF lat, lon, track or gs is missing, or the point is more than 10 km from `WIII_REF`, or `gs_kt < 60` THEN the point SHALL match no runway.
2. WHEN a point matches a runway box (along-track -5556 m to +2778 m, cross-track within 200 m, track within 15° of the runway bearing) AND `vrate <= -300` AND `HAT <= 2500 ft` THEN the detector SHALL arm.
3. WHEN, after arming, the climb holds `vrate >= 500` for at least 4 s AND the rebound is at least 150 ft above the minimum AND the minimum HAT is at most 2500 ft THEN the detector SHALL emit one `go_around` event with severity 2.
4. IF `on_ground` is True THEN the detector SHALL return to Idle.
5. IF the track ends while a state is open THEN the detector SHALL emit no event.
6. IF HAT or vrate is None THEN that point SHALL NOT cause a state change on its own.
7. The event SHALL record `stabilized_below_1000_ft` and the altitude source (`geo` or `baro_qnh`).

### Requirement 5: holding events
**User Story:** As an analyst, I want racetrack holdings detected, so that I can study delays. This is a must-have for the demo.

#### Acceptance Criteria
1. WHEN a run of legs alternates turn and straight, with at least 2 turns of the same direction (each 150° to 210°) and at least 1 straight (30 s to 120 s), and each straight is within 30° of antiparallel to the previous straight, THEN the system SHALL emit one `holding` event with severity 1.
2. WHEN two points are more than 30 s apart THEN the system SHALL break the run.
3. IF a point has no track, or `gs < 60`, or `on_ground` is True THEN the system SHALL end the current run.
4. WHEN the aircraft flies a 360° orbit with no straight, or S-turns, or straights longer than 120 s THEN the system SHALL emit no event.

### Requirement 6: properties shared by all detectors
**User Story:** As an analyst, I want every event to cite all the records behind it, so that every claim can be checked.

#### Acceptance Criteria
1. Each event's `raw_refs` SHALL contain every point in `[start_ts, end_ts]` of its track, including points with no position.
2. The event id SHALL be `uuid5(uuid5(NAMESPACE_URL, "flightmind/events"), f"{type}|{icao24}|{raw_refs[0]}")`.
3. WHEN a detector is called twice on the same track THEN it SHALL return identical results.
4. WHEN the track is empty or has one point THEN a detector SHALL return `[]`. The one exception is squawk: a single emergency-code point gives one event.
5. NACp SHALL appear only in event `details` (as `nacp_range`) and in the compression report. It SHALL NOT be added as a telemetry column.
6. No detector SHALL read wall-clock time (C6).

