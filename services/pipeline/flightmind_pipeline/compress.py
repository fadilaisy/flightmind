"""Keep the points of one track that describe its shape and drop the rest.

compress_track keeps every point that is pinned, is an endpoint, changes squawk, callsign or
on_ground, or has an unknown NACp. Between two kept points it runs Douglas-Peucker on the
positioned points. A point is dropped only when its horizontal and vertical error from the
straight line between its neighbours is within tolerance.

Contract: between kept neighbours, lat, lon and altitude are linearly interpolated in time.
Antimeridian crossings are not handled (WIII only).
"""

import itertools
import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from flightmind_pipeline.geo import distance_m
from flightmind_pipeline.points import Point

# plan step 6, Opus 2026-11-16
EPU_M = {8: 92.6, 9: 30.0, 10: 10.0, 11: 3.0}  # advisor values, not checked against DO-260B
VERTICAL_TOL_FT = 25


@dataclass(frozen=True)
class TrackCompression:
    kept: list[Point]
    kept_reason: dict[str, str]
    max_h_err_m: float
    max_v_err_ft: float
    max_ratio: float
    dropped_by_nacp: Counter[int]
    dropped_no_position: int


@dataclass(frozen=True, slots=True)
class _Error:
    h_err_m: float
    v_err_ft: float
    ratio: float
    nacp: int


def tolerance_m(nacp: int | None) -> float | None:
    """Return the horizontal tolerance in metres for a NACp value, or None when it is unknown."""
    if nacp is None:
        return None
    if 1 <= nacp <= 7:
        return EPU_M[8]
    return EPU_M.get(nacp)


def compress_track(track: Sequence[Point], pinned: set[str]) -> TrackCompression:
    """Return the kept points of track in track order, with the reason each one was kept.

    track must be in time order. pinned holds raw_refs that are always kept.
    """
    kept_reason: dict[str, str] = {}
    kept_idx: set[int] = set()
    dropped_no_position = 0
    positioned: list[int] = []
    for index, point in enumerate(track):
        if _has_position(point):
            positioned.append(index)
        elif point.raw_ref in pinned:
            kept_idx.add(index)
            kept_reason[point.raw_ref] = "event"
        else:
            dropped_no_position += 1

    fixes = [track[index] for index in positioned]
    reasons = _anchor_reasons(fixes, pinned)
    dropped = _douglas_peucker(fixes, reasons)

    for k, reason in enumerate(reasons):
        if reason is not None:
            kept_idx.add(positioned[k])
            kept_reason[fixes[k].raw_ref] = reason

    return TrackCompression(
        kept=[track[index] for index in sorted(kept_idx)],
        kept_reason=kept_reason,
        max_h_err_m=max((e.h_err_m for e in dropped), default=0.0),
        max_v_err_ft=max((e.v_err_ft for e in dropped), default=0.0),
        max_ratio=max((e.ratio for e in dropped), default=0.0),
        dropped_by_nacp=Counter(e.nacp for e in dropped),
        dropped_no_position=dropped_no_position,
    )


def _has_position(point: Point) -> bool:
    return point.lat is not None and point.lon is not None


def _differs(previous: object, value: object) -> bool:
    """True when both values exist and differ. A null on either side is never a change."""
    return previous is not None and value is not None and previous != value


def _anchor_reasons(fixes: Sequence[Point], pinned: set[str]) -> list[str | None]:
    """Return the anchor reason for each positioned point, or None when it may be dropped.

    An attribute change compares with the last non-null value seen on a positioned point
    before this one.
    """
    reasons: list[str | None] = []
    last_squawk: str | None = None
    last_callsign: str | None = None
    last_on_ground: bool | None = None
    final = len(fixes) - 1
    for k, point in enumerate(fixes):
        changed = (
            _differs(last_squawk, point.squawk)
            or _differs(last_callsign, point.callsign)
            or _differs(last_on_ground, point.on_ground)
        )
        if point.squawk is not None:
            last_squawk = point.squawk
        if point.callsign is not None:
            last_callsign = point.callsign
        if point.on_ground is not None:
            last_on_ground = point.on_ground

        reason: str | None = None
        if point.raw_ref in pinned:
            reason = "event"
        elif k in (0, final):
            reason = "endpoint"
        elif changed:
            reason = "attribute_change"
        elif tolerance_m(point.nacp) is None:
            reason = "nacp_unknown"
        reasons.append(reason)
    return reasons


def _douglas_peucker(fixes: Sequence[Point], reasons: list[str | None]) -> list[_Error]:
    """Mark split points with reason 'shape' in reasons, and return the errors of dropped points.

    Works on an explicit stack of (lo, hi) index pairs. Each pair is a stretch between two
    neighbouring kept points. A stretch splits at its worst point when that point is outside
    tolerance, and drops all its interior points otherwise.
    """
    anchors = [k for k, reason in enumerate(reasons) if reason is not None]
    stack = list(itertools.pairwise(anchors))
    dropped: list[_Error] = []
    while stack:
        lo, hi = stack.pop()
        if hi - lo < 2:
            continue
        split = _first_infinite(fixes, lo, hi)
        if split is None:
            errors = [_error(fixes[lo], fixes[hi], fixes[k]) for k in range(lo + 1, hi)]
            worst = 0
            for j, error in enumerate(errors):
                if error.ratio > errors[worst].ratio:
                    worst = j
            if errors[worst].ratio <= 1:
                dropped.extend(errors)
                continue
            split = lo + 1 + worst
        reasons[split] = "shape"
        stack.append((lo, split))
        stack.append((split, hi))
    return dropped


def _first_infinite(fixes: Sequence[Point], lo: int, hi: int) -> int | None:
    """Return the first interior index whose altitude error is infinite, or None.

    An infinite ratio beats every finite one, and ties keep the first point, so this index is the
    split the full scan would choose. Finding it first skips the full error scan on each split when
    an anchor has no altitude field. That scan ran once per point of the stretch, so the total cost
    grew with the square of the stretch length. Measured 2026-11-22 on the full hour 00 (1,017,761
    points, 417 tracks) with a comparison script: old 531.56 s, new 28.91 s, identical output.
    """
    geo_open = fixes[lo].geo_alt_ft is None or fixes[hi].geo_alt_ft is None
    baro_open = fixes[lo].baro_alt_ft is None or fixes[hi].baro_alt_ft is None
    if not (geo_open or baro_open):
        return None
    for k in range(lo + 1, hi):
        point = fixes[k]
        if (geo_open and point.geo_alt_ft is not None) or (
            baro_open and point.baro_alt_ft is not None
        ):
            return k
    return None


def _error(lo: Point, hi: Point, point: Point) -> _Error:
    """Return the errors of point against the line between lo and hi, and their ratio to tolerance."""
    tol_m = tolerance_m(point.nacp)
    if point.nacp is None or tol_m is None:
        raise RuntimeError(f"{point.raw_ref}: an interior point must have a known NACp")
    lo_lat, lo_lon = _position(lo)
    hi_lat, hi_lon = _position(hi)
    lat, lon = _position(point)
    frac = _fraction(lo, hi, point)
    interp_lat = lo_lat + frac * (hi_lat - lo_lat)
    interp_lon = lo_lon + frac * (hi_lon - lo_lon)
    h_err_m = distance_m(lat, lon, interp_lat, interp_lon)
    v_err_ft = max(
        _alt_error(lo.geo_alt_ft, hi.geo_alt_ft, point.geo_alt_ft, frac),
        _alt_error(lo.baro_alt_ft, hi.baro_alt_ft, point.baro_alt_ft, frac),
    )
    ratio = max(h_err_m / tol_m, v_err_ft / VERTICAL_TOL_FT)
    return _Error(h_err_m, v_err_ft, ratio, point.nacp)


def _position(point: Point) -> tuple[float, float]:
    if point.lat is None or point.lon is None:
        raise RuntimeError(f"{point.raw_ref}: no position, so it cannot be interpolated")
    return point.lat, point.lon


def _fraction(lo: Point, hi: Point, point: Point) -> float:
    """Return the time of point between lo and hi: 0.0 at lo, 1.0 at hi. Equal times give 0.0."""
    span_s = (hi.ts - lo.ts).total_seconds()
    if span_s == 0:
        return 0.0
    return (point.ts - lo.ts).total_seconds() / span_s


def _alt_error(lo_ft: int | None, hi_ft: int | None, point_ft: int | None, frac: float) -> float:
    """Return the feet between point_ft and the interpolated altitude.

    A field missing on the point adds 0. A field missing on either end adds infinity, so
    the point is kept.
    """
    if point_ft is None:
        return 0.0
    if lo_ft is None or hi_ft is None:
        return math.inf
    return abs(point_ft - (lo_ft + frac * (hi_ft - lo_ft)))

