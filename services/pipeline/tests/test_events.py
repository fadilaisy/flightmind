from datetime import UTC, datetime

from flightmind_pipeline.events import nacp_range
from flightmind_pipeline.points import Point

T0 = datetime(2026, 11, 15, 10, 0, tzinfo=UTC)


def _point(index: int, nacp: int | None) -> Point:
    return Point(
        ts=T0, record_index=index, raw_ref=f"SYN:{index}", raw_offset=0, icao24="8a09f6", nacp=nacp
    )


def test_nacp_range_is_min_and_max_of_window():
    assert nacp_range([_point(1, 8), _point(2, 11), _point(3, 9)]) == [8, 11]


def test_nacp_range_ignores_points_without_nacp():
    assert nacp_range([_point(1, None), _point(2, 9)]) == [9, 9]


def test_nacp_range_is_none_when_no_point_has_nacp():
    assert nacp_range([_point(1, None)]) is None
    assert nacp_range([]) is None
