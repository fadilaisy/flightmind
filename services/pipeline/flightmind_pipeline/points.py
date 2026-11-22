"""One CAT021 block becomes one Point. Each Point keeps the raw_ref that cites its record."""

import string
from dataclasses import dataclass
from datetime import datetime

# Spec sentinel: a geometric height of 150000 ft or more means "greater than", not a value.
GEO_ALT_SENTINEL_FT = 150000


@dataclass(frozen=True, slots=True)
class Point:
    ts: datetime
    record_index: int
    raw_ref: str
    raw_offset: int
    icao24: str
    callsign: str | None = None
    lat: float | None = None
    lon: float | None = None
    geo_alt_ft: int | None = None
    baro_alt_ft: int | None = None
    gs_kt: float | None = None
    track_deg: float | None = None
    vrate_fpm: int | None = None
    squawk: str | None = None
    on_ground: bool | None = None
    nacp: int | None = None
    sac: int | None = None
    sic: int | None = None


def point_from_block(
    block: dict,
    recording_id: str,
    record_index: int,
    raw_offset: int,
    ts: datetime,
) -> Point | None:
    """Return the Point for one decoded block, or None when it has no usable 6-hex ICAO24."""
    cat = block.get("CAT021", {})
    i010, i040 = cat.get("I010", {}), cat.get("I040", {})
    i070, i080 = cat.get("I070", {}), cat.get("I080", {})
    i090, i130 = cat.get("I090", {}), cat.get("I130", {})
    i140, i145 = cat.get("I140", {}), cat.get("I145", {})
    i155, i157 = cat.get("I155", {}), cat.get("I157", {})
    i160, i170 = cat.get("I160", {}), cat.get("I170", {})

    taddr = i080.get("TAddr")
    icao24 = taddr.lower() if isinstance(taddr, str) else ""
    if len(icao24) != 6 or not set(icao24) <= set(string.hexdigits):
        return None

    nacp = i090.get("NACp")
    bvr, gvr = i155.get("BVR"), i157.get("GVR")
    if bvr is not None:
        vrate_fpm = round(bvr)
    elif gvr is not None:
        vrate_fpm = round(gvr)
    else:
        vrate_fpm = None

    geo_height = i140.get("geometric_height")
    flight_level = i145.get("FL")
    gs_nm_s = i160.get("GS")
    callsign = i170.get("TId")
    gbs = i040.get("GBS")

    return Point(
        ts=ts,
        record_index=record_index,
        raw_ref=f"{recording_id}:{record_index}",
        raw_offset=raw_offset,
        icao24=icao24,
        callsign=callsign.strip() or None if isinstance(callsign, str) else None,
        lat=i130.get("Lat"),
        lon=i130.get("Lon"),
        geo_alt_ft=(
            round(geo_height)
            if geo_height is not None and geo_height < GEO_ALT_SENTINEL_FT
            else None
        ),
        baro_alt_ft=round(flight_level * 100) if flight_level is not None else None,
        gs_kt=gs_nm_s * 3600.0 if gs_nm_s is not None else None,
        track_deg=i160.get("TA"),
        vrate_fpm=vrate_fpm,
        squawk=i070.get("Mode3A"),
        on_ground=bool(gbs) if gbs is not None else None,
        nacp=nacp if isinstance(nacp, int) else None,
        sac=i010.get("SAC"),
        sic=i010.get("SIC"),
    )
