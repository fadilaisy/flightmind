import random
from collections.abc import Sequence
from datetime import timedelta

from synth import T0

from flightmind_pipeline.detect_holding import detect_holding
from flightmind_pipeline.points import Point

GS_KT = 220.0
ICAO24 = "8a09f6"
# Turn rate in deg/s. A 60 s turn at 3 deg/s changes the heading by about 177 deg.
RIGHT = 3.0
LEFT = -3.0
STRAIGHT = 0.0
TWO_CIRCUITS = [(RIGHT, 60), (STRAIGHT, 60)] * 4


def _headings(legs: Sequence[tuple[float, int]]) -> list[float]:
    """Return one heading per second. Each leg turns at its rate for its number of seconds."""
    headings: list[float] = []
    heading = 0.0
    for rate, seconds in legs:
        for _ in range(seconds):
            headings.append(heading % 360)
            heading += rate
    return headings


def _track(
    legs: Sequence[tuple[float, int]],
    *,
    noise: bool = False,
    gap: tuple[int, int] | None = None,
) -> list[Point]:
    """Return a 1 Hz track. gap = (first second, length) drops those seconds."""
    rng = random.Random(0)
    points: list[Point] = []
    for second, heading in enumerate(_headings(legs)):
        if gap is not None and gap[0] <= second < gap[0] + gap[1]:
            continue
        track_deg = (heading + rng.uniform(-1.0, 1.0)) % 360 if noise else heading
        points.append(
            Point(
                ts=T0 + timedelta(seconds=second),
                record_index=second + 1,
                raw_ref=f"SYN:{second + 1}",
                raw_offset=0,
                icao24=ICAO24,
                lat=-6.12,
                lon=106.65,
                gs_kt=GS_KT,
                track_deg=track_deg,
                on_ground=False,
            )
        )
    return points


def test_two_circuits_give_one_right_hand_holding_event() -> None:
    events = detect_holding(_track(TWO_CIRCUITS))

    assert len(events) == 1
    assert events[0].type == "holding"
    assert events[0].details["direction"] == "right"
    assert events[0].details["half_turns"] == 4


def test_one_degree_of_track_noise_keeps_the_holding_event() -> None:
    events = detect_holding(_track(TWO_CIRCUITS, noise=True))

    assert len(events) == 1


def test_continuous_orbit_without_straight_is_not_holding() -> None:
    assert detect_holding(_track([(RIGHT, 120)])) == []


def test_alternating_turn_directions_are_not_holding() -> None:
    legs = [(RIGHT, 60), (STRAIGHT, 60), (LEFT, 60), (STRAIGHT, 60)] * 2

    assert detect_holding(_track(legs)) == []


def test_straights_longer_than_120_s_are_not_holding() -> None:
    legs = [(RIGHT, 60), (STRAIGHT, 200)] * 3 + [(RIGHT, 60)]

    assert detect_holding(_track(legs)) == []


def test_single_half_turn_is_not_holding() -> None:
    legs = [(STRAIGHT, 60), (RIGHT, 60), (STRAIGHT, 60)]

    assert detect_holding(_track(legs)) == []


def test_gap_of_missing_data_splits_the_run() -> None:
    # The second straight is 100 s. The 40 s gap starts 50 s into it.
    legs = [
        (RIGHT, 60),
        (STRAIGHT, 60),
        (RIGHT, 60),
        (STRAIGHT, 100),
        (RIGHT, 60),
        (STRAIGHT, 60),
        (RIGHT, 60),
        (STRAIGHT, 60),
    ]
    gap_start, gap_len = 230, 40
    events = detect_holding(_track(legs, gap=(gap_start, gap_len)))

    gap_begin = T0 + timedelta(seconds=gap_start)
    gap_end = T0 + timedelta(seconds=gap_start + gap_len)
    assert len(events) == 2
    for event in events:
        assert event.end_ts <= gap_begin or event.start_ts >= gap_end


def test_empty_and_one_point_tracks_give_no_events() -> None:
    assert detect_holding([]) == []
    assert detect_holding(_track([(STRAIGHT, 1)])) == []


def test_same_track_gives_equal_events() -> None:
    track = _track(TWO_CIRCUITS)
    first = detect_holding(track)

    assert first
    assert detect_holding(track) == first
