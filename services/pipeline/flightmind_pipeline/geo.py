"""Runway geometry for Jakarta Soekarno-Hatta (WIII) and simple flat-earth distances."""

import math
from dataclasses import dataclass

EARTH_RADIUS_M = 6371008.8
METRES_PER_DEG = EARTH_RADIUS_M * math.pi / 180

# 40 NM, decided 2026-11-16 (1 NM = 1852 m).
AIRPORT_RADIUS_M = 74_080


@dataclass(frozen=True, slots=True)
class Runway:
    name: str
    lat: float
    lon: float
    bearing_deg: float
    elev_ft: int


# advisor 2026-11-16, not verified against AIP
RUNWAYS: tuple[Runway, ...] = (
    Runway("07R", -6.14260, 106.64400, 068.3, 34),
    Runway("25L", -6.13032, 106.67400, 248.3, 27),
    Runway("07L", -6.12106, 106.63900, 068.3, 29),
    Runway("25R", -6.10899, 106.66900, 248.3, 21),
    Runway("06", -6.11389, 106.64459, 068.3, 24),
    Runway("24", -6.10384, 106.66977, 248.3, 24),
)

WIII_REF: tuple[float, float] = (
    sum(r.lat for r in RUNWAYS) / len(RUNWAYS),
    sum(r.lon for r in RUNWAYS) / len(RUNWAYS),
)


def runway_frame(lat: float, lon: float, rwy: Runway) -> tuple[float, float]:
    """Return (along_m, cross_m) of a point in a frame with origin at the runway threshold."""
    east = (lon - rwy.lon) * math.cos(math.radians(rwy.lat)) * METRES_PER_DEG
    north = (lat - rwy.lat) * METRES_PER_DEG
    bearing = math.radians(rwy.bearing_deg)
    along = east * math.sin(bearing) + north * math.cos(bearing)
    cross = east * math.cos(bearing) - north * math.sin(bearing)
    return along, cross


def angle_diff_deg(a: float, b: float) -> float:
    """Smallest difference between two headings, in [0, 180]."""
    diff = abs(a - b) % 360
    return min(diff, 360 - diff)


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Equirectangular distance in metres, scaled at the mean latitude."""
    mean_lat = math.radians((lat1 + lat2) / 2)
    x = (lon2 - lon1) * math.cos(mean_lat) * METRES_PER_DEG
    y = (lat2 - lat1) * METRES_PER_DEG
    return math.hypot(x, y)


def airport_for(lat: float | None, lon: float | None) -> str | None:
    """Return "WIII" when the position is within AIRPORT_RADIUS_M of WIII_REF, else None."""
    if lat is None or lon is None:
        return None
    if distance_m(lat, lon, *WIII_REF) <= AIRPORT_RADIUS_M:
        return "WIII"
    return None
