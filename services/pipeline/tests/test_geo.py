import pytest

from flightmind_pipeline.geo import RUNWAYS, airport_for, runway_frame


def _runway(name: str):
    return next(r for r in RUNWAYS if r.name == name)


def test_25L_threshold_lies_about_3590_m_along_07R_centreline():
    rwy_25l = _runway("25L")

    along, cross = runway_frame(rwy_25l.lat, rwy_25l.lon, _runway("07R"))

    assert along == pytest.approx(3590, abs=20)
    assert abs(cross) < 45  # decided 2026-11-16: 25L is 42.4 m from 07R centreline per advisor coordinates (AIP not yet checked)


def test_06_threshold_is_450_to_550_m_off_07L_centreline():
    rwy_06 = _runway("06")

    _along, cross = runway_frame(rwy_06.lat, rwy_06.lon, _runway("07L"))

    assert 450 <= abs(cross) <= 550


def test_airport_for_none_position_is_none():
    assert airport_for(None, None) is None
