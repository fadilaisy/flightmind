import math
from bisect import bisect_left
from collections import Counter
from dataclasses import replace
from datetime import timedelta

from hypothesis import given, settings
from hypothesis import strategies as st
from synth import T0

from flightmind_pipeline.compress import compress_track, tolerance_m
from flightmind_pipeline.geo import METRES_PER_DEG, distance_m
from flightmind_pipeline.points import Point

# The plan's tolerance table, written out here as literals. The property tests must not read
# tolerances from compress.py, or a wrong value in the code would pass its own check (gate round 1).
PLAN_TOL_M: dict[int, float] = {**{n: 92.6 for n in range(1, 9)}, 9: 30.0, 10: 10.0, 11: 3.0}
PLAN_VERTICAL_FT = 25

LAT0 = -6.12
LON0 = 106.65
STEP_DEG = 1e-4
SLACK = 1e-6


def _point(
    k: int,
    *,
    lat: float | None = None,
    lon: float | None = None,
    nacp: int | None = 8,
    squawk: str | None = None,
    callsign: str | None = None,
    on_ground: bool | None = None,
    geo_alt_ft: int | None = None,
    baro_alt_ft: int | None = None,
) -> Point:
    return Point(
        ts=T0 + timedelta(seconds=k),
        record_index=k,
        raw_ref=f"T:{k}",
        raw_offset=0,
        icao24="8a09f6",
        lat=lat,
        lon=lon,
        nacp=nacp,
        squawk=squawk,
        callsign=callsign,
        on_ground=on_ground,
        geo_alt_ft=geo_alt_ft,
        baro_alt_ft=baro_alt_ft,
    )


def _line(count: int) -> list[Point]:
    """Return a constant-velocity straight line at NACp 8, one point per second."""
    return [
        _point(k, lat=LAT0 + k * STEP_DEG, lon=LON0 + k * STEP_DEG, baro_alt_ft=35000)
        for k in range(count)
    ]


def _has_position(point: Point) -> bool:
    return point.lat is not None and point.lon is not None


def _errors(lo: Point, hi: Point, point: Point) -> tuple[float, float]:
    """Return (horizontal m, vertical ft) of point from the interpolated line, written apart from the code."""
    assert lo.lat is not None and lo.lon is not None
    assert hi.lat is not None and hi.lon is not None
    assert point.lat is not None and point.lon is not None
    span = (hi.ts - lo.ts).total_seconds()
    frac = 0.0 if span == 0 else (point.ts - lo.ts).total_seconds() / span
    interp_lat = lo.lat + frac * (hi.lat - lo.lat)
    interp_lon = lo.lon + frac * (hi.lon - lo.lon)
    h = distance_m(point.lat, point.lon, interp_lat, interp_lon)
    v = 0.0
    for lo_ft, hi_ft, point_ft in (
        (lo.geo_alt_ft, hi.geo_alt_ft, point.geo_alt_ft),
        (lo.baro_alt_ft, hi.baro_alt_ft, point.baro_alt_ft),
    ):
        if point_ft is None:
            continue
        if lo_ft is None or hi_ft is None:
            return h, math.inf
        v = max(v, abs(point_ft - (lo_ft + frac * (hi_ft - lo_ft))))
    return h, v


@st.composite
def tracks(draw: st.DrawFn) -> tuple[list[Point], set[str]]:
    count = draw(st.integers(0, 300))
    track: list[Point] = []
    seconds = 0
    lat, lon = LAT0, LON0
    for k in range(count):
        seconds += draw(st.integers(0, 3))  # 0 gives equal timestamps
        if draw(st.booleans()):
            lat += draw(st.floats(-2e-4, 2e-4, allow_nan=False))
            lon += draw(st.floats(-2e-4, 2e-4, allow_nan=False))
            has_position = True
        else:
            has_position = False
        track.append(
            Point(
                ts=T0 + timedelta(seconds=seconds),
                record_index=k,
                raw_ref=f"T:{k}",
                raw_offset=0,
                icao24="8a09f6",
                lat=lat if has_position else None,
                lon=lon if has_position else None,
                nacp=draw(st.sampled_from([None, 0, 5, 8, 9, 10, 11])),
                squawk=draw(st.sampled_from([None, "1200", "7700"])),
                callsign=draw(st.sampled_from([None, "GA1"])),
                on_ground=draw(st.sampled_from([None, True, False])),
                geo_alt_ft=draw(st.one_of(st.none(), st.integers(0, 40000))),
                baro_alt_ft=draw(st.one_of(st.none(), st.integers(0, 40000))),
            )
        )
    pinned_idx = draw(st.sets(st.integers(0, max(count - 1, 0))))
    pinned = {f"T:{i}" for i in pinned_idx if i < count}
    return track, pinned


@settings(deadline=None, max_examples=200)
@given(tracks())
def test_every_pinned_point_is_kept(case: tuple[list[Point], set[str]]) -> None:
    track, pinned = case
    kept = {p.raw_ref for p in compress_track(track, pinned).kept}
    assert pinned <= kept


@settings(deadline=None, max_examples=200)
@given(tracks())
def test_first_and_last_positioned_points_are_kept(case: tuple[list[Point], set[str]]) -> None:
    track, pinned = case
    positioned = [p.raw_ref for p in track if _has_position(p)]
    if not positioned:
        return
    kept = {p.raw_ref for p in compress_track(track, pinned).kept}
    assert positioned[0] in kept
    assert positioned[-1] in kept


@settings(deadline=None, max_examples=200)
@given(tracks())
def test_dropped_positioned_points_are_within_tolerance_of_kept_neighbours(
    case: tuple[list[Point], set[str]],
) -> None:
    track, pinned = case
    kept_refs = {p.raw_ref for p in compress_track(track, pinned).kept}
    kept_pos = [i for i, p in enumerate(track) if p.raw_ref in kept_refs and _has_position(p)]
    for i, point in enumerate(track):
        if not _has_position(point) or point.raw_ref in kept_refs:
            continue
        # Dropped points lie between two kept positioned points, because the endpoints are kept.
        after = bisect_left(kept_pos, i)
        lo, hi = track[kept_pos[after - 1]], track[kept_pos[after]]
        h, v = _errors(lo, hi, point)
        tol = PLAN_TOL_M.get(point.nacp) if point.nacp is not None else None
        assert tol is not None
        assert h <= tol + SLACK, f"{point.raw_ref}: {h} m > {tol} m"
        assert v <= PLAN_VERTICAL_FT + SLACK, f"{point.raw_ref}: {v} ft > {PLAN_VERTICAL_FT} ft"


@settings(deadline=None, max_examples=200)
@given(tracks())
def test_positioned_points_with_nacp_none_or_zero_are_kept(
    case: tuple[list[Point], set[str]],
) -> None:
    track, pinned = case
    kept = {p.raw_ref for p in compress_track(track, pinned).kept}
    for point in track:
        if _has_position(point) and point.nacp in (None, 0):
            assert point.raw_ref in kept


@settings(deadline=None, max_examples=200)
@given(tracks())
def test_same_input_gives_equal_results(case: tuple[list[Point], set[str]]) -> None:
    track, pinned = case
    assert compress_track(track, pinned) == compress_track(track, pinned)


def test_straight_constant_velocity_line_keeps_only_its_two_ends() -> None:
    result = compress_track(_line(1000), set())
    assert [p.raw_ref for p in result.kept] == ["T:0", "T:999"]


def test_empty_track_keeps_nothing_and_reports_zero_stats() -> None:
    result = compress_track([], set())
    assert result.kept == []
    assert result.kept_reason == {}
    assert result.max_h_err_m == 0.0
    assert result.max_v_err_ft == 0.0
    assert result.max_ratio == 0.0
    assert result.dropped_by_nacp == Counter()
    assert result.dropped_no_position == 0


def test_single_positioned_point_is_kept_as_endpoint() -> None:
    track = [_point(0, lat=LAT0, lon=LON0)]
    result = compress_track(track, set())
    assert [p.raw_ref for p in result.kept] == ["T:0"]
    assert result.kept_reason == {"T:0": "endpoint"}


def test_point_with_nacp_zero_is_kept_on_a_straight_line() -> None:
    track = _line(11)
    track[5] = replace(track[5], nacp=0)
    result = compress_track(track, set())
    assert "T:5" in {p.raw_ref for p in result.kept}
    assert result.kept_reason["T:5"] == "nacp_unknown"


def test_pinned_point_in_the_middle_of_a_line_is_kept_as_event() -> None:
    result = compress_track(_line(11), {"T:5"})
    assert result.kept_reason["T:5"] == "event"


def test_squawk_change_on_a_straight_line_is_kept_as_attribute_change() -> None:
    track = [replace(p, squawk="1200" if p.record_index < 50 else "7700") for p in _line(101)]
    result = compress_track(track, set())
    assert result.kept_reason["T:50"] == "attribute_change"


def test_point_two_km_off_the_line_is_kept_as_shape() -> None:
    track = _line(101)
    track[50] = replace(track[50], lat=track[50].lat + 2000 / METRES_PER_DEG)
    result = compress_track(track, set())
    assert result.kept_reason["T:50"] == "shape"


@settings(deadline=None, max_examples=200)
@given(tracks())
def test_max_ratio_is_at_most_one(case: tuple[list[Point], set[str]]) -> None:
    track, pinned = case
    assert 0.0 <= compress_track(track, pinned).max_ratio <= 1.0 + SLACK


def test_tolerance_m_matches_the_plan_table() -> None:
    for nacp in [None, 0, 1, 7, 8, 9, 10, 11, 12]:
        assert tolerance_m(nacp) == (None if nacp is None else PLAN_TOL_M.get(nacp))


def test_altitude_missing_on_an_anchor_keeps_an_interior_point_as_shape() -> None:
    # Task 6.3: the last point has no altitude, so the interior altitude error is infinite.
    track = [replace(p, baro_alt_ft=10000) for p in _line(5)]
    track[-1] = replace(track[-1], baro_alt_ft=None)
    result = compress_track(track, set())
    assert "shape" in result.kept_reason.values()

