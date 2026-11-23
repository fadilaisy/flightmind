# Design: detectors

## Data flow
`decode_blocks(pcap)` → `point_from_block` → `split_tracks` → for each track, `detect_squawk`, `detect_go_around` and `detect_holding` → `list[DetectedEvent]`. All three detectors run on full-resolution points, before compression.

## Interfaces (`services/pipeline/flightmind_pipeline/`)

**points.py**
- `@dataclass(frozen=True, slots=True) class Point`
  - Required fields: `ts: datetime` (UTC-aware), `record_index: int`, `raw_ref: str`, `raw_offset: int`, `icao24: str`.
  - Optional fields, default None: `callsign`, `lat`, `lon`, `geo_alt_ft`, `baro_alt_ft`, `gs_kt`, `track_deg`, `vrate_fpm`, `squawk`, `on_ground`, `nacp`, `sac`, `sic`.
- `point_from_block(block: dict, recording_id: str, record_index: int, raw_offset: int, ts: datetime) -> Point | None`
  - Ported from `ingest-prototype\ingest_hour.py`.
  - `gs_kt` = I160 ground speed in NM/s × 3600.

**pcap_source.py**
- `walk_pcap(path) -> Iterator[tuple[int, int, datetime]]` yields `(record_index, offset, ts)`, with `record_index` 1-based.
- `decode_blocks(path) -> Iterator[dict]` runs `asterix.exe -P -d config/asterix.ini -j -f <path>` through Cygwin bash, reading `FLIGHTMIND_ASTERIX_DIR` and `FLIGHTMIND_CYGWIN_BIN`. There is no `--limit` option.

**tracks.py**
- `TRACK_GAP_S = 3600`. Comment: Kool-confirmed. It never fires inside a one-hour file. The advisor is to re-check it (300 s was the alternative).
- `split_tracks(points: Iterable[Point]) -> list[list[Point]]`

**geo.py**
- `@dataclass(frozen=True) class Runway(name, lat, lon, bearing_deg, elev_ft)`
- `RUNWAYS`: six rows. Comment: "advisor 2026-11-16, not verified against AIP; true vs magnetic not confirmed".

| Runway | Lat | Lon | Bearing | Elevation |
|---|---|---|---|---|
| 07R | -6.14260 | 106.64400 | 068.3 | 34 ft |
| 25L | -6.13032 | 106.67400 | 248.3 | 27 ft |
| 07L | -6.12106 | 106.63900 | 068.3 | 29 ft |
| 25R | -6.10899 | 106.66900 | 248.3 | 21 ft |
| 06 | -6.11389 | 106.64459 | 068.3 | 24 ft |
| 24 | -6.10384 | 106.66977 | 248.3 | 24 ft |

- `WIII_REF` = mean of the six thresholds.
- `EARTH_R_M = 6_371_008.8`
- `runway_frame(lat, lon, rwy) -> tuple[float, float]` returns `(along_m, cross_m)`, equirectangular.
- `angle_diff_deg(a, b) -> float` in [0, 180].
- `wrap180(d) -> float`
- `distance_m(lat1, lon1, lat2, lon2)` uses equirectangular at the mean latitude.
- `airport_for(lat, lon) -> str | None` returns `"WIII"` within 40 NM of `WIII_REF`. The 40 NM radius is Opus's choice.

**events.py**
- `@dataclass(frozen=True) class DetectedEvent(type, icao24, callsign, start_ts, end_ts, airport, lat, lon, severity, details: dict, raw_refs: tuple[str, ...])`
- `event_id(e) -> uuid.UUID` (see requirement 6.2).
- `collect_raw_refs(window: Sequence[Point]) -> tuple[str, ...]` returns the raw_ref of each point in the window slice, in order. The window is a slice of the track by position, not by timestamp.
- `event_callsign(window: Sequence[Point], track: Sequence[Point]) -> str | None`: the last non-null callsign in the window, else the last in the track, else None.
- `nacp_range(window: Sequence[Point]) -> list[int] | None`: [min, max] of NACp in the window, or None. Goes in event details as `nacp_range` (decided 2026-11-16).
- `nacp_range(points) -> list[int] | None` returns `[min, max]` over non-None NACp values, or None if there are none. Every detector adds it to `details["nacp_range"]`.
- Severity docstring: 3 = 7500/7700; 2 = 7600 and go-around; 1 = holding.

## Squawk (`detect_squawk.py`)
- `EMERGENCY = {"7500", "7600", "7700"}`. The rule is in requirement 3.
- `lat`/`lon` come from the first positioned point in the event. Both are None if no point has a position.
- `details = {code, records_with_code, first_raw_ref, alt_ft, alt_kind, nacp_range}`.
  - `alt_ft` is the baro altitude if present, else the geo altitude.
  - `alt_kind` is `"pressure"` or `"geometric"`.

## Go-around (`detect_go_around.py`)
Every constant carries a source comment.

| Constant | Value | Source |
|---|---|---|
| `CAPTURE_CEILING_HAT_FT` | 2500 | approved pick 5 |
| `MAX_MIN_HAT_FT` | 2500 | |
| `DESCENT_VRATE_FPM` | -300 | |
| `CLIMB_VRATE_FPM` | 500 | |
| `CLIMB_HOLD_S` | 4 | |
| `REBOUND_FT` | 150 | |
| `MIN_GS_KT` | 60 | approved pick 6: one gate, because CAT021 has no jet/turboprop field |
| `HEADING_TOL_DEG` | 15 | |
| `CORRIDOR_HALF_M` | 200 | |
| `BOX_BEFORE_M` | 5556 | |
| `BOX_AFTER_M` | 2778 | |
| `APPROACH_LOST_S` | 30 | |
| `CLIMB_TIMEOUT_S` | 60 | |
| `NEAR_WIII_M` | 10000 | |
| `MIN_HAT_BELOW_1000_FT` | 1000 | |
| `QNH_HPA` | 1010 | |
| `FT_PER_HPA` | 27 | memory |
| `GEOID_N_FT` | step 0 value, or None | |

**Functions**
- `runway_match(p) -> Runway | None`. When several runways match, the one with the smallest |cross| wins.
- `hat_ft(p, rwy, source)`:
  - `"geo"`: `geo_alt_ft − GEOID_N_FT − elev_ft`.
  - `"baro_qnh"`: `baro_alt_ft + (QNH_HPA − 1013.25)·FT_PER_HPA − elev_ft`.
  - None if the field is missing.

**State machine** (`Idle | Approach | Climb`), evaluated per point in order:
- **Any state:** `on_ground is True` → Idle.
- **Idle → Approach:** when the point matches runway r AND `vrate <= -300` AND HAT ≤ 2500.
  - Lock `source`: "geo" if `geo_alt_ft` is set and `GEOID_N_FT` is known, else "baro_qnh".
  - Record `start`, `min` and `last_in_box`.
- **Approach:**
  - If the point is in box r with HAT ≤ 2500: update `last_in_box` and `min`.
  - Else, if `ts − last_in_box > 30 s`: go to Idle.
  - If `vrate >= 500` and HAT is known: go to Climb with `climb_start = p`.
- **Climb:**
  - If `vrate < 500`: go back to Approach and re-evaluate the same point.
  - If the gap since the previous fix is over 60 s (`CLIMB_GAP_S`): drop the run and go to Idle, with no event. Coverage dropped during the climb.
  - If `ts − climb_start >= 4` AND `HAT − min_hat >= 150` AND `min_hat <= 2500` AND `ts − climb_start <= 60 s` (`CLIMB_TIMEOUT_S`): emit, then go to Idle. The 60 s cap is hard: a confirm later than that never emits.
  - Else, if `ts − climb_start > 60 s`: go to Idle.
  - Trade-off (review 2026-11-23): a go-around is missed if coverage returns mid-climb, because the run is dropped and nothing re-arms on the point that drops it. A new descent in the box is needed to arm again.
- **End of track:** drop any open state.

**Event**
- `type="go_around"`, `airport="WIII"`, `severity=2`.
- `start_ts` = the arm point's time; `end_ts` = the confirming point's time.
- `lat`/`lon` come from the minimum point.
- `details = {runway, min_hat_ft, min_raw_ref, rebound_ft, max_vrate_fpm, alt_source, alt_msl_ft_at_min, min_hat_below_1000_ft, nacp_range, thresholds: "advisor-2026-11-16-unverified"}`.
- `min_hat_below_1000_ft` = `min_hat_ft < 1000`.

## Holding (`detect_holding.py`)
**Constants**
- `RATE_LOOKAHEAD_S=5`
- `RATE_GAP_MAX_S=30`
- `TURN_RATE_MIN_DPS=1.0`
- `STRAIGHT_RATE_MAX_DPS=0.5`
- `MIN_LEG_S=10`
- `HALF_TURN_DEG=(150,210)`
- `STRAIGHT_S=(30,120)`
- `ANTIPARALLEL_TOL_DEG=30`
- `MIN_GS_KT=60`

**Algorithm**
1. Filter points as in requirement 5.3.
2. Turn rate at point i: j is the first point with `ts_j − ts_i >= 5`.
   - If that gap is > 30 s, label the point X.
   - Else rate = `wrap180(track_j − track_i)/dt`.
3. Label each point:
   - R if rate ≥ 1.0; L if rate ≤ −1.0; S if |rate| ≤ 0.5.
   - Otherwise keep the previous label. The first such point gets S.
4. Legs are runs of one label.
   - Duration = next leg start − this leg start. For the last leg, it is last ts − start ts.
   - Heading change = the sum of `wrap180` differences across the leg.
   - Straight track = circular mean.
5. A leg under 10 s takes the previous leg's label (the next leg's label if it is the first leg). Then merge adjacent equal labels. X legs never merge.
6. Find maximal alternating runs that qualify under requirement 5.1, then continue scanning after each run.

**Event**
- `start_ts` = first leg start; `end_ts` = last leg end.
- `lat`/`lon` = mean of the positioned points in the event.
- `airport` = `airport_for(lat, lon)`.
- `details = {direction, half_turns, circuits=max(1, half_turns//2), turn_leg_s, straight_leg_s, straight_tracks_deg, min_alt_ft, max_alt_ft, duration_s, nacp_range}`.

## Decided boundaries
- Empty or one-point track: `[]`, except a single emergency squawk point (one event).
- Duplicate timestamps: both points are kept, ordered by `record_index`. `dt = 0` never divides, because the rate lookahead requires a gap of at least 5 s.
- A detector called twice on the same track returns identical results.
- Very large input: everything is held in memory per file, about 600 MB per hour (estimate).
- Cancelled halfway: nothing is written, because the detectors are pure functions.

## Rejected
- Detecting in the database after a full load: it writes every row and then deletes most of them, so ingest is slower.




