"""Detect emergency squawk codes (7500, 7600, 7700) on one track."""
from collections.abc import Sequence

from flightmind_pipeline.events import (
    DetectedEvent,
    collect_raw_refs,
    event_callsign,
    nacp_range,
)
from flightmind_pipeline.geo import airport_for
from flightmind_pipeline.points import Point

EMERGENCY_SEVERITY: dict[str, int] = {"7500": 3, "7600": 2, "7700": 3}


def detect_squawk(track: Sequence[Point]) -> list[DetectedEvent]:
    """Return one event per run of an emergency code, in track order.

    A run opens on a point carrying the code and closes at its last point with the code,
    when a different non-null code arrives, or when the track ends. Points with no squawk
    do not close or extend a run, but they are cited when they fall inside its window.
    """
    events: list[DetectedEvent] = []
    open_code: str | None = None
    start = 0
    last = 0
    for index, point in enumerate(track):
        code = point.squawk
        if code is None:
            continue
        if code == open_code:
            last = index
            continue
        if open_code is not None:
            events.append(_build_event(track, open_code, start, last))
            open_code = None
        if code in EMERGENCY_SEVERITY:
            open_code, start, last = code, index, index
    if open_code is not None:
        events.append(_build_event(track, open_code, start, last))
    return events


def _build_event(track: Sequence[Point], code: str, start: int, last: int) -> DetectedEvent:
    """Build the event for the points track[start:last + 1], which open and close with code."""
    opening = track[start]
    window = track[start : last + 1]
    start_ts, end_ts = opening.ts, track[last].ts

    positioned = next((p for p in window if p.lat is not None and p.lon is not None), None)
    lat = positioned.lat if positioned is not None else None
    lon = positioned.lon if positioned is not None else None

    baro = next((p.baro_alt_ft for p in window if p.baro_alt_ft is not None), None)
    geo = next((p.geo_alt_ft for p in window if p.geo_alt_ft is not None), None)
    alt_ft: int | None
    alt_kind: str | None
    if baro is not None:
        alt_ft, alt_kind = baro, "pressure"
    elif geo is not None:
        alt_ft, alt_kind = geo, "geometric"
    else:
        alt_ft, alt_kind = None, None

    details: dict[str, object] = {
        "code": code,
        "records_with_code": sum(1 for p in window if p.squawk == code),
        "first_raw_ref": opening.raw_ref,
        "alt_ft": alt_ft,
        "alt_kind": alt_kind,
        "nacp_range": nacp_range(window),
    }
    return DetectedEvent(
        type=f"squawk_{code}",
        icao24=opening.icao24,
        callsign=event_callsign(window, track),
        start_ts=start_ts,
        end_ts=end_ts,
        airport=airport_for(lat, lon),
        lat=lat,
        lon=lon,
        severity=EMERGENCY_SEVERITY[code],
        details=details,
        raw_refs=collect_raw_refs(window),
    )

