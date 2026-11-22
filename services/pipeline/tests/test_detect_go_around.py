import math
from datetime import timedelta

from synth import T0

from flightmind_pipeline.detect_go_around import (
    FT_PER_HPA,
    QNH_HPA,
    STD_QNH_HPA,
    detect_go_around,
)
from flightmind_pipeline.geo import METRES_PER_DEG, RUNWAYS, Runway
from flightmind_pipeline.points import Point

GS_KT = 140.0
KT_TO_MPS = 1852 / 3600
# About 3 NM before the threshold. Kept just inside BOX_BEFORE_M so float rounding cannot
# push the first point outside the box.
START_ALONG_M = -5550.0
START_HAT_FT = 1485
# Index 93 is the lowest point, at 400 ft HAT (1485 - 94 * 700 / 60 steps).
MIN_INDEX = 93
DESCENT = [-700] * 94
CLIMB = [1500] * 20
BASE_VRATES = DESCENT + CLIMB


def _runway(name: str) -> Runway:
    return next(r for r in RUNWAYS if r.name == name)


def _position(rwy: Runway, along: float, cross: float) -> tuple[float, float]:
    """Return (lat, lon) for a point at (along, cross) metres from the threshold.

    This is the inverse of runway_frame.
    """
    bearing = math.radians(rwy.bearing_deg)
    east = along * math.sin(bearing) + cross * math.cos(bearing)
    north = along * math.cos(bearing) - cross * math.sin(bearing)
    lat = rwy.lat + north / METRES_PER_DEG
    lon = rwy.lon + east / (METRES_PER_DEG * math.cos(math.radians(rwy.lat)))
    return lat, lon


def _profile(
    rwy_name: str,
    vrates: list[int],
    *,
    heading_offset_deg: float = 0.0,
    cross_m: float = 0.0,
    on_ground_from: int | None = None,
) -> list[Point]:
    """Return one Point per vertical rate, 1 s apart.

    The aircraft flies at GS_KT along the runway bearing and starts on the extended centreline
    at START_ALONG_M. HAT changes by vrate / 60 each second. Baro is set so that hat_ft
    gives the intended HAT, with a constant +0.25 ft offset from rounding that cancels in
    differences.
    """
    rwy = _runway(rwy_name)
    track_deg = (rwy.bearing_deg + heading_offset_deg) % 360
    hat = float(START_HAT_FT)
    baro_offset_ft = round((STD_QNH_HPA - QNH_HPA) * FT_PER_HPA)
    points = []
    for k, vrate in enumerate(vrates):
        if k > 0:
            hat += vrate / 60
        along = START_ALONG_M + k * GS_KT * KT_TO_MPS
        lat, lon = _position(rwy, along, cross_m)
        points.append(
            Point(
                ts=T0 + timedelta(seconds=k),
                record_index=k + 1,
                raw_ref=f"SYN:{k + 1}",
                raw_offset=0,
                icao24="8a09f6",
                lat=lat,
                lon=lon,
                baro_alt_ft=round(hat) + rwy.elev_ft + baro_offset_ft,
                gs_kt=GS_KT,
                track_deg=track_deg,
                vrate_fpm=vrate,
                on_ground=on_ground_from is not None and k >= on_ground_from,
            )
        )
    return points


def test_base_profile_gives_one_go_around_on_07L_with_refs_from_arm_to_confirm():
    events = detect_go_around(_profile("07L", BASE_VRATES))
    assert len(events) == 1
    event = events[0]
    assert event.type == "go_around"
    assert event.details["runway"] == "07L"
    assert 390 <= event.details["min_hat_ft"] <= 410
    assert event.details["stabilized_below_1000_ft"] is True
    # Arm at SYN:1. The rebound first reaches 150 ft at index 99, which is record 100.
    assert event.raw_refs == tuple(f"SYN:{i}" for i in range(1, 101))


def test_on_ground_at_the_minimum_gives_no_go_around():
    assert detect_go_around(_profile("07L", BASE_VRATES, on_ground_from=MIN_INDEX)) == []


def test_climb_of_only_3_s_then_descent_gives_no_go_around():
    assert detect_go_around(_profile("07L", DESCENT + [1500] * 3 + [-700] * 30)) == []


def test_rebound_of_only_100_ft_gives_no_go_around():
    assert detect_go_around(_profile("07L", DESCENT + [1500] * 4 + [0] * 10)) == []


def test_track_offset_laterally_by_300_m_gives_no_go_around():
    assert detect_go_around(_profile("07L", BASE_VRATES, cross_m=300)) == []


def test_heading_20_deg_off_runway_bearing_gives_no_go_around():
    assert detect_go_around(_profile("07L", BASE_VRATES, heading_offset_deg=20)) == []


def test_same_profile_on_runway_06_gives_go_around_on_06():
    events = detect_go_around(_profile("06", BASE_VRATES))
    assert len(events) == 1
    assert events[0].details["runway"] == "06"


def test_reverse_direction_on_25R_gives_go_around_on_25R():
    events = detect_go_around(_profile("25R", BASE_VRATES))
    assert len(events) == 1
    assert events[0].details["runway"] == "25R"


def test_empty_track_gives_no_events():
    assert detect_go_around([]) == []


def test_one_point_track_gives_no_events():
    assert detect_go_around(_profile("07L", BASE_VRATES)[:1]) == []


def test_calling_twice_on_the_base_track_gives_equal_results():
    track = _profile("07L", BASE_VRATES)
    assert detect_go_around(track) == detect_go_around(track)
