"""Detect holding patterns (racetrack orbits) on one track.

A holding pattern is two or more turns in one direction, with straight legs between them,
where each straight runs back against the straight before it. Each point gets a label from
its turn rate. Runs of one label form legs. Alternating turn and straight legs that fit the
pattern form one event.
"""

import math
import statistics
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
from flightmind_pipeline.geo import airport_for, angle_diff_deg
from flightmind_pipeline.points import Point

Label = Literal["R", "L", "S", "X"]
# label, first position in the run, last position in the run (both inclusive)
Span = tuple[Label, int, int]

RATE_LOOKAHEAD_S = 5  # plan step 5, Opus 2026-11-16
RATE_GAP_MAX_S = 30  # plan step 5, Opus 2026-11-16
TURN_RATE_MIN_DPS = 1.0  # plan step 5, Opus 2026-11-16
STRAIGHT_RATE_MAX_DPS = 0.5  # plan step 5, Opus 2026-11-16
MIN_LEG_S = 10  # plan step 5, Opus 2026-11-16
HALF_TURN_DEG = (150, 210)  # plan step 5, Opus 2026-11-16
STRAIGHT_S = (30, 120)  # plan step 5, Opus 2026-11-16
ANTIPARALLEL_TOL_DEG = 30  # plan step 5, Opus 2026-11-16
MIN_GS_KT = 60  # plan step 5, Opus 2026-11-16


@dataclass(frozen=True, slots=True)
class _Leg:
    label: Label
    start: int  # position in the run, inclusive
    end: int  # position in the run, inclusive
    duration_s: float
    heading_change_deg: float
    mean_track_deg: float


def detect_holding(track: Sequence[Point]) -> list[DetectedEvent]:
    """Return one holding event per holding pattern, in track order."""
    events: list[DetectedEvent] = []
    for lo, hi in _usable_runs(track):
        events.extend(_detect_in_run(track, lo, hi))
    return events


def _is_usable(point: Point) -> bool:
    return (
        point.track_deg is not None
        and point.gs_kt is not None
        and point.gs_kt >= MIN_GS_KT
        and point.on_ground is not True
    )


def _usable_runs(track: Sequence[Point]) -> list[tuple[int, int]]:
    """Return [lo, hi) index ranges of consecutive usable points. An unusable point ends a run."""
    runs: list[tuple[int, int]] = []
    lo: int | None = None
    for index, point in enumerate(track):
        if _is_usable(point):
            if lo is None:
                lo = index
        elif lo is not None:
            runs.append((lo, index))
            lo = None
    if lo is not None:
        runs.append((lo, len(track)))
    return runs


def _detect_in_run(track: Sequence[Point], lo: int, hi: int) -> list[DetectedEvent]:
    points = track[lo:hi]
    times = [p.ts for p in points]
    # Every point in a run passed _is_usable, so none of these track values is None.
    headings = [p.track_deg for p in points if p.track_deg is not None]
    spans = _absorb_short_legs(times, _spans(_labels(times, headings)))
    legs = _measure(times, headings, spans)

    events: list[DetectedEvent] = []
    index = 0
    while index < len(legs):
        if not _qualifies(legs[index]):
            index += 1
            continue
        run = [legs[index]]
        nxt = index + 1
        while nxt < len(legs) and _can_join(run, legs[nxt]):
            run.append(legs[nxt])
            nxt += 1
        if _is_holding(run):
            events.append(_build_event(track, lo, run))
            index = nxt
        else:
            index += 1
    return events


def _labels(times: Sequence[datetime], headings: Sequence[float]) -> list[Label]:
    """Label each point by the turn rate measured to the first point at least 5 s later."""
    labels: list[Label] = []
    count = len(times)
    ahead = 0
    for i in range(count):
        # Both pointers only move forward: times are sorted, so the first point 5 s ahead of
        # point i is never before the first point 5 s ahead of point i - 1.
        ahead = max(ahead, i + 1)
        while ahead < count and _gap_s(times[ahead], times[i]) < RATE_LOOKAHEAD_S:
            ahead += 1
        if ahead == count:
            labels.append("X")
            continue
        span_s = _gap_s(times[ahead], times[i])
        if span_s > RATE_GAP_MAX_S:
            labels.append("X")
            continue
        rate = _wrap180(headings[ahead] - headings[i]) / span_s
        labels.append(_label_for_rate(rate, labels))
    return labels


def _label_for_rate(rate: float, labels: Sequence[Label]) -> Label:
    if rate >= TURN_RATE_MIN_DPS:
        return "R"
    if rate <= -TURN_RATE_MIN_DPS:
        return "L"
    if abs(rate) <= STRAIGHT_RATE_MAX_DPS:
        return "S"
    # Between the thresholds the point keeps the previous label. The first point has none, so it
    # is straight.
    return labels[-1] if labels else "S"


def _spans(labels: Sequence[Label]) -> list[Span]:
    spans: list[Span] = []
    start = 0
    for pos in range(1, len(labels) + 1):
        if pos == len(labels) or labels[pos] != labels[start]:
            spans.append((labels[start], start, pos - 1))
            start = pos
    return spans


def _absorb_short_legs(times: Sequence[datetime], spans: list[Span]) -> list[Span]:
    """Give each short leg the label of the leg before it (the leg after it, for the first).

    Decisions run left to right on the original durations. X legs never merge, so a short leg
    that takes the label X stays a separate leg.
    """
    durations = _durations(times, spans)
    labels: list[Label] = []
    for k, (label, _, _) in enumerate(spans):
        if len(spans) > 1 and durations[k] < MIN_LEG_S:
            labels.append(labels[k - 1] if k > 0 else spans[k + 1][0])
        else:
            labels.append(label)

    merged: list[Span] = []
    for label, (_, start, end) in zip(labels, spans, strict=True):
        if merged and merged[-1][0] == label and label != "X":
            merged[-1] = (label, merged[-1][1], end)
        else:
            merged.append((label, start, end))
    return merged


def _durations(times: Sequence[datetime], spans: Sequence[Span]) -> list[float]:
    """A leg lasts until the next leg starts. The last leg lasts until its last point."""
    starts = [times[start] for _, start, _ in spans]
    durations: list[float] = []
    for k, (_, _, end) in enumerate(spans):
        stop = starts[k + 1] if k + 1 < len(spans) else times[end]
        durations.append(_gap_s(stop, starts[k]))
    return durations


def _measure(
    times: Sequence[datetime], headings: Sequence[float], spans: Sequence[Span]
) -> list[_Leg]:
    durations = _durations(times, spans)
    return [
        _Leg(
            label=label,
            start=start,
            end=end,
            duration_s=duration,
            heading_change_deg=sum(
                _wrap180(headings[p + 1] - headings[p]) for p in range(start, end)
            ),
            mean_track_deg=_circular_mean(headings[start : end + 1]),
        )
        for (label, start, end), duration in zip(spans, durations, strict=True)
    ]


def _is_turn(leg: _Leg) -> bool:
    return leg.label in ("R", "L")


def _qualifies(leg: _Leg) -> bool:
    if _is_turn(leg):
        return HALF_TURN_DEG[0] <= abs(leg.heading_change_deg) <= HALF_TURN_DEG[1]
    if leg.label == "S":
        return STRAIGHT_S[0] <= leg.duration_s <= STRAIGHT_S[1]
    return False


def _can_join(run: Sequence[_Leg], leg: _Leg) -> bool:
    """Return True when leg extends the run of alternating turns and straights."""
    if not _qualifies(leg) or _is_turn(leg) == _is_turn(run[-1]):
        return False
    if _is_turn(leg):
        # All turns in a run share one direction.
        return all(r.label == leg.label for r in run if _is_turn(r))
    straights = [r for r in run if not _is_turn(r)]
    if straights:
        # A straight runs back against the previous straight in the run.
        previous = straights[-1].mean_track_deg + 180
        return angle_diff_deg(leg.mean_track_deg, previous) <= ANTIPARALLEL_TOL_DEG
    return True


def _is_holding(run: Sequence[_Leg]) -> bool:
    turns = sum(1 for leg in run if _is_turn(leg))
    return turns >= 2 and len(run) - turns >= 1


def _build_event(track: Sequence[Point], lo: int, run: Sequence[_Leg]) -> DetectedEvent:
    window = track[lo + run[0].start : lo + run[-1].end + 1]
    turns = [leg for leg in run if _is_turn(leg)]
    straights = [leg for leg in run if not _is_turn(leg)]
    lat, lon = _mean_position(window)
    alt_min, alt_max = _alt_range(window)
    start_ts, end_ts = window[0].ts, window[-1].ts
    details: dict[str, object] = {
        "direction": "right" if turns[0].label == "R" else "left",
        "half_turns": len(turns),
        "circuits": max(1, len(turns) // 2),
        "turn_leg_s": statistics.median([leg.duration_s for leg in turns]),
        "straight_leg_s": statistics.median([leg.duration_s for leg in straights]),
        "straight_tracks_deg": [leg.mean_track_deg for leg in straights],
        "min_alt_ft": alt_min,
        "max_alt_ft": alt_max,
        "duration_s": (end_ts - start_ts).total_seconds(),
        "nacp_range": nacp_range(window),
    }
    return DetectedEvent(
        type="holding",
        icao24=window[0].icao24,
        callsign=event_callsign(window, track),
        start_ts=start_ts,
        end_ts=end_ts,
        airport=airport_for(lat, lon),
        lat=lat,
        lon=lon,
        severity=1,
        details=details,
        raw_refs=collect_raw_refs(window),
    )


def _mean_position(window: Sequence[Point]) -> tuple[float | None, float | None]:
    lat_sum = lon_sum = 0.0
    count = 0
    for point in window:
        if point.lat is not None and point.lon is not None:
            lat_sum += point.lat
            lon_sum += point.lon
            count += 1
    if count == 0:
        return None, None
    return lat_sum / count, lon_sum / count


def _alt_range(window: Sequence[Point]) -> tuple[int | None, int | None]:
    """Min and max altitude in the window. Barometric values are used when any exist."""
    baro = [p.baro_alt_ft for p in window if p.baro_alt_ft is not None]
    geo = [p.geo_alt_ft for p in window if p.geo_alt_ft is not None]
    alts = baro or geo
    if not alts:
        return None, None
    return min(alts), max(alts)


def _gap_s(later: datetime, earlier: datetime) -> float:
    return (later - earlier).total_seconds()


def _wrap180(angle_deg: float) -> float:
    """Map an angle into [-180, 180)."""
    return (angle_deg + 180.0) % 360.0 - 180.0


def _circular_mean(headings: Sequence[float]) -> float:
    sin_sum = sum(math.sin(math.radians(h)) for h in headings)
    cos_sum = sum(math.cos(math.radians(h)) for h in headings)
    return math.degrees(math.atan2(sin_sum, cos_sum)) % 360.0

