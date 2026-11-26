from datetime import UTC

from synth import synth_track

from flightmind_pipeline.detect_squawk import detect_squawk


def test_ten_7700_points_then_none_make_one_event_citing_only_the_code_window():
    events = detect_squawk(synth_track(["7700"] * 10 + [None] * 2000))
    assert len(events) == 1
    assert events[0].severity == 3
    assert len(events[0].raw_refs) == 10
    assert events[0].raw_refs == tuple(f"SYN:{i}" for i in range(1, 11))


def test_7700_7600_7700_make_three_events_in_order():
    events = detect_squawk(synth_track(["7700", "7600", "7700"]))
    assert [e.type for e in events] == ["squawk_7700", "squawk_7600", "squawk_7700"]


def test_none_points_between_same_code_are_cited_in_the_event():
    events = detect_squawk(synth_track(["7700", None, "7700"]))
    assert len(events) == 1
    assert events[0].raw_refs == ("SYN:1", "SYN:2", "SYN:3")


def test_code_7701_makes_no_event():
    assert detect_squawk(synth_track(["7701"] * 5)) == []


def test_single_7500_point_gives_event_with_start_equal_to_end():
    events = detect_squawk(synth_track(["7500"]))
    assert len(events) == 1
    assert events[0].start_ts == events[0].end_ts


def test_empty_track_gives_no_events():
    assert detect_squawk([]) == []


def test_one_point_track_without_squawk_gives_no_events():
    assert detect_squawk(synth_track([None])) == []


def test_calling_twice_on_the_same_track_gives_equal_results():
    track = synth_track(["7700", None, "7600", "7600", None])
    assert detect_squawk(track) == detect_squawk(track)


def test_point_sharing_the_closing_timestamp_is_not_cited():
    # Record 2 shares record 1's timestamp but comes after the event closes on a different code,
    # so it must not be cited, even though its timestamp falls inside the event window.
    from datetime import datetime

    from flightmind_pipeline.points import Point

    t0 = datetime(2026, 11, 15, 10, 0, tzinfo=UTC)
    track = [
        Point(ts=t0, record_index=1, raw_ref="SYN:1", raw_offset=0, icao24="8a09f6", squawk="7700"),
        Point(ts=t0, record_index=2, raw_ref="SYN:2", raw_offset=0, icao24="8a09f6", squawk="0110"),
    ]
    events = detect_squawk(track)
    assert len(events) == 1
    assert events[0].raw_refs == ("SYN:1",)


def test_7600_event_has_severity_2():
    events = detect_squawk(synth_track(["7600"] * 3))
    assert len(events) == 1
    assert events[0].severity == 2
