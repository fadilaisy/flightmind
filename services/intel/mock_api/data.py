"""Synthetic sample data for the mock API (SCRUM-33).

Everything here is invented. It is NOT real CAT021 data and the hex is NOT valid
ASTERIX; it only has the same shape as the contract (contracts/openapi.yaml,
contracts/schema.sql) so the UI and agent can be built before real fixtures exist.
Swap this module for real database queries in SCRUM-37; the endpoints stay the same.
"""
import math
import struct
import uuid
from datetime import datetime, timedelta, timezone

RECORDING_ID = "rec01"
AIRPORT = "WIII"
T0 = datetime(2026, 11, 14, 3, 0, 0, tzinfo=timezone.utc)
STEP_S = 5
SAC, SIC = 51, 7

# Approximate runway threshold the approaches are built around.
RWY_LAT, RWY_LON = -6.1256, 106.6559

# kind -> (event type, severity, airport)
EVENT_KINDS = {
    "go_around": ("go_around", 2, AIRPORT),
    "holding": ("holding", 1, AIRPORT),
    "cruise_7700": ("squawk_7700", 3, None),
}

SPECS = [
    dict(icao24="8A0F21", callsign="GIA123", start_s=0, n=60, kind="go_around", dlat=0.0),
    dict(icao24="8A2E55", callsign="CTV88", start_s=40, n=60, kind="go_around", dlat=0.004),
    dict(icao24="8A1C07", callsign="LNI456", start_s=10, n=90, kind="holding", dlat=0.0),
    dict(icao24="76CD11", callsign="SIA9", start_s=20, n=60, kind="cruise_7700", dlat=0.0),
]


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _position(spec, i):
    """Return (lat, lon, alt_ft, squawk) for sample i of an aircraft."""
    n, kind, dlat = spec["n"], spec["kind"], spec["dlat"]
    squawk = "2000"
    if kind == "go_around":
        split = int(n * 0.6)
        if i < split:
            t = i / split
            lat = RWY_LAT + dlat + 0.01 * (1 - t)
            lon = RWY_LON + 0.14 * (1 - t)
            alt = 3000 - 2600 * t
        else:
            t = (i - split) / (n - split)
            lat = RWY_LAT + dlat - 0.02 * t
            lon = RWY_LON - 0.10 * t
            alt = 400 + 2600 * t
    elif kind == "holding":
        a = 2 * math.pi * i / (n / 3)
        lat = -6.0 + 0.03 * math.sin(a)
        lon = 106.9 + 0.05 * math.cos(a)
        alt = 8000
    else:
        lat = -5.9 + 0.004 * i
        lon = 106.2 + 0.006 * i
        alt = 35000
        if 20 <= i <= 39:
            squawk = "7700"
    return lat, lon, int(alt), squawk


def _event_window(spec):
    n, kind = spec["n"], spec["kind"]
    if kind == "go_around":
        return int(n * 0.5), int(n * 0.75)
    if kind == "holding":
        return int(n * 0.2), n - 1
    return 20, 39


def _fake_hex(icao24, lat, lon, alt):
    """Shape-only bytes: category 21, a length, icao24, scaled lat/lon, altitude."""
    body = bytes.fromhex(icao24) + struct.pack(">iih", int(lat * 1e5), int(lon * 1e5), int(alt / 25))
    return (bytes([21]) + struct.pack(">H", len(body) + 3) + body).hex()


def _build():
    points = []
    for spec in SPECS:
        for i in range(spec["n"]):
            lat, lon, alt, squawk = _position(spec, i)
            points.append(dict(
                spec=spec, i=i,
                ts=T0 + timedelta(seconds=spec["start_s"] + STEP_S * i),
                lat=round(lat, 6), lon=round(lon, 6), alt=alt, squawk=squawk,
            ))
    points.sort(key=lambda p: (p["ts"], p["spec"]["icao24"]))

    raw = {}
    ref_of = {}
    for idx, p in enumerate(points):
        spec = p["spec"]
        raw_ref = f"{RECORDING_ID}:{idx}"
        ref_of[(spec["icao24"], p["i"])] = raw_ref
        raw[raw_ref] = {
            "raw_ref": raw_ref,
            "recording_file_id": RECORDING_ID,
            "record_index": idx,
            "sac": SAC,
            "sic": SIC,
            "decoded": {
                "icao24": spec["icao24"],
                "callsign": spec["callsign"],
                "ts": iso(p["ts"]),
                "lat": p["lat"],
                "lon": p["lon"],
                "baro_alt_ft": p["alt"],
                "squawk": p["squawk"],
                "synthetic": True,
            },
            "hex": _fake_hex(spec["icao24"], p["lat"], p["lon"], p["alt"]),
        }

    events = []
    kept = set()
    for spec in SPECS:
        lo, hi = _event_window(spec)
        refs = [ref_of[(spec["icao24"], i)] for i in range(lo, hi + 1)]
        kept.update(refs)
        etype, severity, airport = EVENT_KINDS[spec["kind"]]
        start = T0 + timedelta(seconds=spec["start_s"] + STEP_S * lo)
        end = T0 + timedelta(seconds=spec["start_s"] + STEP_S * hi)
        events.append({
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"flightmind-mock/{spec['icao24']}/{etype}")),
            "type": etype,
            "icao24": spec["icao24"],
            "callsign": spec["callsign"],
            "start_ts": iso(start),
            "end_ts": iso(end),
            "airport": airport,
            "severity": severity,
            "raw_refs": refs,
        })
    events.sort(key=lambda e: e["start_ts"])

    tracks = {}
    for spec in SPECS:
        tracks[spec["icao24"]] = {"icao24": spec["icao24"], "callsign": spec["callsign"], "points": []}
    for p in points:
        spec = p["spec"]
        raw_ref = ref_of[(spec["icao24"], p["i"])]
        tracks[spec["icao24"]]["points"].append({
            "ts": iso(p["ts"]),
            "lat": p["lat"],
            "lon": p["lon"],
            "alt_ft": p["alt"],
            "raw_ref": raw_ref,
            "kept_for_event": raw_ref in kept,
        })
    return tracks, events, raw


TRACKS, EVENTS, RAW = _build()
EVENTS_BY_ID = {e["id"]: e for e in EVENTS}

# Invented, like everything in this module. Sits under the 10 m bound of NACp 10.
MOCK_MAX_POSITION_ERROR_M = 8.4


# Both sizes here are synthetic record bytes; the real report compares the recording file
# size with the Postgres row size, so its ratio will differ. Do not quote this ratio.
def _build_compression():
    kept = set()
    for t in TRACKS.values():
        pts = t["points"]
        kept.update(p["raw_ref"] for p in pts if p["kept_for_event"])  # "event" rule
        kept.update((pts[0]["raw_ref"], pts[-1]["raw_ref"]))  # "endpoint" rule
    raw_bytes = sum(len(r["hex"]) // 2 for r in RAW.values())
    stored_bytes = sum(len(RAW[ref]["hex"]) // 2 for ref in kept)
    return {
        RECORDING_ID: {
            "recording_id": RECORDING_ID,
            "raw_bytes": raw_bytes,
            "stored_bytes": stored_bytes,
            "ratio": round(stored_bytes / raw_bytes, 4),
            "max_position_error_m": MOCK_MAX_POSITION_ERROR_M,
            "points_in": len(RAW),
            "points_kept": len(kept),
            "events_total": len(EVENTS),
            "events_kept": sum(1 for e in EVENTS if set(e["raw_refs"]) <= kept),
        }
    }


COMPRESSION = _build_compression()
SIM_TIME = iso(max(datetime.strptime(e["end_ts"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) for e in EVENTS))
