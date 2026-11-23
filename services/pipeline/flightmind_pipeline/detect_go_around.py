"""Detect go-arounds (missed approaches) on one track, one runway box at a time.

Each point moves a small state machine through Idle, Approach and Climb. A descent inside a
runway box opens Approach. A climb that rebounds far enough above the lowest point emits one
event.
"""
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from flightmind_pipeline.events import (
    DetectedEvent,
    collect_raw_refs,
    event_callsign,
    nacp_range,
)
from flightmind_pipeline.geo import (
    RUNWAYS,
    WIII_REF,
    Runway,
    angle_diff_deg,
    distance_m,
    runway_frame,
)
from flightmind_pipeline.points import Point

AltSource = Literal["geo", "baro_qnh"]

# advisor 2026-11-16 (early go-arounds at WIII); decided
CAPTURE_CEILING_HAT_FT = 2500
MAX_MIN_HAT_FT = 2500  # same
# TDD v0.1 / advisor, unverified against PANS-OPS
DESCENT_VRATE_FPM = -300
CLIMB_VRATE_FPM = 500
CLIMB_HOLD_S = 4
REBOUND_FT = 150
# decided (single 60 kt gate)
MIN_GS_KT = 60
HEADING_TOL_DEG = 15
CORRIDOR_HALF_M = 200
BOX_BEFORE_M = 5556  # 3.0 NM before threshold
BOX_AFTER_M = 2778  # 1.5 NM past threshold
APPROACH_LOST_S = 30
CLIMB_TIMEOUT_S = 60
# Largest gap between two fixes that still counts as one climb (review 2026-11-23).
CLIMB_GAP_S = 60
# Rule A of the brief. The brief gives no source; it is not in its constant list.
APPROACH_RADIUS_M = 10000
QNH_HPA = 1010
STD_QNH_HPA = 1013.25
FT_PER_HPA = 27  # from memory, unverified
# EGM96 undulation at WIII not found (2026-11-16). None disables the geometric path.
GEOID_N_FT: int | None = None
THRESHOLDS_TAG = "advisor-2026-11-16-unverified"


def runway_match(point: Point) -> Runway | None:
    """Return the runway whose box the point is in, else None.

    When several boxes match, the runway with the smallest cross-track offset wins.
    """
    if point.lat is None or point.lon is None or point.track_deg is None:
        return None
    if point.gs_kt is None or point.gs_kt < MIN_GS_KT:
        return None
    if distance_m(point.lat, point.lon, *WIII_REF) > APPROACH_RADIUS_M:
        return None
    best: Runway | None = None
    best_cross = 0.0
    for rwy in RUNWAYS:
        along, cross = runway_frame(point.lat, point.lon, rwy)
        if not -BOX_BEFORE_M <= along <= BOX_AFTER_M or abs(cross) > CORRIDOR_HALF_M:
            continue
        if angle_diff_deg(point.track_deg, rwy.bearing_deg) > HEADING_TOL_DEG:
            continue
        if best is None or abs(cross) < best_cross:
            best, best_cross = rwy, abs(cross)
    return best


def hat_ft(point: Point, rwy: Runway, source: AltSource) -> float | None:
    """Return height above the threshold in feet, or None when the source has no value."""
    if source == "geo":
        if point.geo_alt_ft is None or GEOID_N_FT is None:
            return None
        return point.geo_alt_ft - GEOID_N_FT - rwy.elev_ft
    if point.baro_alt_ft is None:
        return None
    return point.baro_alt_ft + (QNH_HPA - STD_QNH_HPA) * FT_PER_HPA - rwy.elev_ft


@dataclass(slots=True)
class _Run:
    """An open Approach. Climb is the same run with climb_index set.

    Indexes point into the track, so the event window can be a slice by position.
    """

    runway: Runway
    source: AltSource
    start_index: int
    min_index: int
    min_hat: float
    last_in_box_ts: datetime
    climb_index: int | None = None


def detect_go_around(track: Sequence[Point]) -> list[DetectedEvent]:
    """Return one go_around event per climb that rebounds after an approach, in track order."""
    events: list[DetectedEvent] = []
    run: _Run | None = None
    for index, point in enumerate(track):
        if point.on_ground is True:
            run = None
        elif run is None:
            run = _arm(point, index)
        else:
            run, event = _step(track, run, index)
            if event is not None:
                events.append(event)
    return events


def _arm(point: Point, index: int) -> _Run | None:
    """Idle: open an Approach on a descent inside a box below the capture ceiling."""
    rwy = runway_match(point)
    if rwy is None or point.vrate_fpm is None or point.vrate_fpm > DESCENT_VRATE_FPM:
        return None
    source: AltSource = (
        "geo" if GEOID_N_FT is not None and point.geo_alt_ft is not None else "baro_qnh"
    )
    hat = hat_ft(point, rwy, source)
    if hat is None or hat > CAPTURE_CEILING_HAT_FT:
        return None
    return _Run(rwy, source, index, index, hat, point.ts)


def _step(
    track: Sequence[Point], run: _Run, index: int
) -> tuple[_Run | None, DetectedEvent | None]:
    point = track[index]
    # The climb is over. This point is then judged as an Approach point.
    if run.climb_index is not None and point.vrate_fpm is not None and point.vrate_fpm < CLIMB_VRATE_FPM:
        run.climb_index = None
    if run.climb_index is not None:
        return _climb_step(track, run, run.climb_index, index)
    return _approach_step(track, run, index)


def _approach_step(
    track: Sequence[Point], run: _Run, index: int
) -> tuple[_Run | None, DetectedEvent | None]:
    point = track[index]
    hat = hat_ft(point, run.runway, run.source)
    if hat is None:
        return run, None
    climbing = point.vrate_fpm is not None and point.vrate_fpm >= CLIMB_VRATE_FPM
    matched = runway_match(point)
    in_box = matched is not None and matched.name == run.runway.name
    if in_box and hat <= CAPTURE_CEILING_HAT_FT:
        # Review 2026-11-22: a stale approach must not survive a coverage gap just because the next
        # fix lands back in the box. Drop it; the aircraft needs a new descent to re-arm.
        if (point.ts - run.last_in_box_ts).total_seconds() > APPROACH_LOST_S:
            return None, None
        # Option A (Kool 2026-11-17): a climb inside the box opens Climb at once. The box
        # update still runs first, so the minimum and last_in_box stay current.
        run.last_in_box_ts = point.ts
        if hat < run.min_hat:
            run.min_hat = hat
            run.min_index = index
        if climbing:
            run.climb_index = index
        return run, None
    # Gate review 2026-11-22: the lost-approach timeout must run before a climb outside the box,
    # so a climb after a long coverage gap cannot open Climb on a stale approach.
    if (point.ts - run.last_in_box_ts).total_seconds() > APPROACH_LOST_S:
        return None, None
    if climbing:
        run.climb_index = index
    return run, None


def _climb_step(
    track: Sequence[Point], run: _Run, climb_index: int, index: int
) -> tuple[_Run | None, DetectedEvent | None]:
    point = track[index]
    # Review 2026-11-23: a climb is confirmed only on fixes that follow each other closely. A gap over
    # CLIMB_GAP_S since the previous fix means coverage dropped during the climb; drop the run.
    if (point.ts - track[index - 1].ts).total_seconds() > CLIMB_GAP_S:
        return None, None
    hat = hat_ft(point, run.runway, run.source)
    if hat is None:
        return run, None
    elapsed = (point.ts - track[climb_index].ts).total_seconds()
    rebound = hat - run.min_hat
    if (
        elapsed >= CLIMB_HOLD_S
        and rebound >= REBOUND_FT
        and run.min_hat <= MAX_MIN_HAT_FT
        and elapsed <= CLIMB_TIMEOUT_S
    ):
        return None, _build_event(track, run, index, hat)
    if elapsed > CLIMB_TIMEOUT_S:
        return None, None
    return run, None


def _build_event(
    track: Sequence[Point], run: _Run, index: int, confirm_hat: float
) -> DetectedEvent:
    window = track[run.start_index : index + 1]
    start, minimum, confirm = track[run.start_index], track[run.min_index], track[index]
    vrates = [p.vrate_fpm for p in window if p.vrate_fpm is not None]
    if run.source == "baro_qnh":
        alt_msl_ft_at_min = minimum.baro_alt_ft
    else:
        alt_msl_ft_at_min = minimum.geo_alt_ft
    details: dict[str, object] = {
        "runway": run.runway.name,
        "min_hat_ft": run.min_hat,
        "min_raw_ref": minimum.raw_ref,
        "rebound_ft": confirm_hat - run.min_hat,
        "max_vrate_fpm": max(vrates) if vrates else None,
        "alt_source": run.source,
        "alt_msl_ft_at_min": alt_msl_ft_at_min,
        "min_hat_below_1000_ft": run.min_hat < 1000,
        "thresholds": THRESHOLDS_TAG,
        "nacp_range": nacp_range(window),
    }
    return DetectedEvent(
        type="go_around",
        icao24=start.icao24,
        callsign=event_callsign(window, track),
        start_ts=start.ts,
        end_ts=confirm.ts,
        airport="WIII",
        lat=minimum.lat,
        lon=minimum.lon,
        severity=2,
        details=details,
        raw_refs=collect_raw_refs(window),
    )




