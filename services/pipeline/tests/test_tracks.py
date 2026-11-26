from datetime import UTC, datetime, timedelta

from flightmind_pipeline.points import Point
from flightmind_pipeline.tracks import split_tracks

T0 = datetime(2026, 11, 15, 10, 0, 0, tzinfo=UTC)


def _point(icao24: str, seconds: float, record_index: int) -> Point:
    return Point(
        ts=T0 + timedelta(seconds=seconds),
        record_index=record_index,
        raw_ref=f"rec1:{record_index}",
        raw_offset=0,
        icao24=icao24,
    )


def test_gap_under_one_hour_keeps_one_track():
    points = [_point("8a09f6", 0, 1), _point("8a09f6", 3599, 2)]

    assert len(split_tracks(points)) == 1


def test_gap_of_one_hour_starts_a_new_track():
    points = [_point("8a09f6", 0, 1), _point("8a09f6", 3600, 2)]

    assert len(split_tracks(points)) == 2


def test_two_aircraft_make_two_tracks():
    points = [_point("8a09f6", 0, 1), _point("c0ffee", 5, 2)]

    tracks = split_tracks(points)

    assert len(tracks) == 2
    assert {t[0].icao24 for t in tracks} == {"8a09f6", "c0ffee"}


def test_no_points_give_no_tracks():
    assert split_tracks([]) == []
