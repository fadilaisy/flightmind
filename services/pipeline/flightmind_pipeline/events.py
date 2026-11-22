"""Detected events and the helpers detectors share: stable ids, raw_ref citations, callsigns.

Severity scale (3 is the most urgent):
- 3: squawk 7500 (unlawful interference) or 7700 (general emergency)
- 2: squawk 7600 (radio failure) and go-around
- 1: holding
"""
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from flightmind_pipeline.points import Point

EVENT_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "flightmind/events")


@dataclass(frozen=True, slots=True)
class DetectedEvent:
    type: str
    icao24: str
    callsign: str | None
    start_ts: datetime
    end_ts: datetime
    airport: str | None
    lat: float | None
    lon: float | None
    severity: int
    details: dict[str, object]
    raw_refs: tuple[str, ...]


def event_id(event: DetectedEvent) -> uuid.UUID:
    """Return an id that stays the same on every re-run for the same event."""
    return uuid.uuid5(EVENT_NAMESPACE, f"{event.type}|{event.icao24}|{event.raw_refs[0]}")


def collect_raw_refs(window: Sequence[Point]) -> tuple[str, ...]:
    """Return the raw_ref of every point in the window, in order.

    The window is a slice of the track by position, not by timestamp. Points that share a
    timestamp with the event's edge but lie outside it are therefore not cited.
    """
    return tuple(p.raw_ref for p in window)


def event_callsign(window: Sequence[Point], track: Sequence[Point]) -> str | None:
    """Return the last callsign in the window, else the last one in the track, else None."""
    in_window = [p.callsign for p in window if p.callsign is not None]
    if in_window:
        return in_window[-1]
    in_track = [p.callsign for p in track if p.callsign is not None]
    return in_track[-1] if in_track else None
