"""The six cleaning rules on small synthetic inputs, and the records_in chain between them."""

from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from flightmind_pipeline import cleaning
from flightmind_pipeline.cleaning import CleanInput, clean_records

T0 = datetime(2026, 11, 15, 10, 0, tzinfo=UTC)
STEP_ORDER = [
    "no_address",
    "no_position",
    "duplicates",
    "position_jumps",
    "altitude_spikes",
    "fragments",
]
DEG_PER_KT_S = 1852.0 / 3600.0 / 111195.0  # degrees of latitude flown in 1 s at 1 kt


def rec(
    n: int,
    t: float,
    *,
    icao24: str | None = "aaaaaa",
    lat: float | None = -6.0,
    lon: float | None = 106.0,
    alt: int | None = 3000,
) -> CleanInput:
    return CleanInput(f"r:{n}", icao24, T0 + timedelta(seconds=t), lat, lon, alt)


def line(count: int, *, icao24: str = "aaaaaa", start: int = 1, step_s: float = 1.0) -> list[CleanInput]:
    """count records of one aircraft flying north at 100 kt, one every step_s seconds."""
    return [
        rec(
            start + i,
            i * step_s,
            icao24=icao24,
            lat=-6.0 + 100 * DEG_PER_KT_S * i * step_s,
            alt=3000,
        )
        for i in range(count)
    ]


def refs(result, code: str) -> list[str]:
    return [r for r, c, _ in result.set_aside if c == code]


def counts(result) -> dict[str, int]:
    return {s["code"]: s["set_aside"] for s in result.steps}


def test_steps_come_in_pipeline_order_with_labels_and_reasons() -> None:
    result = clean_records(line(25))
    assert [s["code"] for s in result.steps] == STEP_ORDER
    assert [s["label"] for s in result.steps] == [
        "No target address",
        "No position",
        "Duplicate records",
        "Position jumps",
        "Altitude spikes",
        "Fragment tracks",
    ]
    assert result.steps[0]["reason"] == (
        "No target address (I021/080), so it cannot be assigned to an aircraft."
    )
    assert result.steps[1]["reason"] == (
        "No position (I021/130), so it cannot be placed on a track."
    )
    assert result.steps[2]["reason"] == "Same target address, time and position as an earlier record."
    assert result.steps[3]["reason"] == "Implied speed to its neighbours above 1,200 kt."
    assert result.steps[4]["reason"] == "More than 2,000 ft from both neighbours within 2 s."
    assert result.steps[5]["reason"] == "Fewer than 20 records for one target address."
    assert all(set(s) == {"code", "label", "records_in", "set_aside", "reason"} for s in result.steps)


def test_clean_input_is_kept_whole() -> None:
    records = line(30)
    result = clean_records(records)
    assert result.kept == records
    assert result.set_aside == []
    assert [s["set_aside"] for s in result.steps] == [0] * 6


def test_no_address_and_no_position() -> None:
    records = [
        *line(25),
        rec(100, 5, icao24=None),
        rec(101, 6, icao24=None, lat=None, lon=None),  # no address wins: it is counted once
        rec(102, 7, lat=None, lon=None),
        rec(103, 8, lon=None),
    ]
    result = clean_records(records)
    assert refs(result, "no_address") == ["r:100", "r:101"]
    assert refs(result, "no_position") == ["r:102", "r:103"]
    assert [s["records_in"] for s in result.steps[:2]] == [29, 27]
    reasons = {c: r for _, c, r in result.set_aside}
    assert reasons["no_address"] == cleaning.reason_of("no_address")


def test_duplicates_keep_the_first_record() -> None:
    first = rec(1, 0, lat=-6.0000001)
    same = rec(2, 0, lat=-6.00000011)  # equal after rounding to 1e-7 deg
    other_time = rec(3, 1, lat=-6.0000001)
    other_pos = rec(4, 0, lat=-6.0000003)
    other_aircraft = rec(5, 0, icao24="bbbbbb", lat=-6.0000001)
    result = clean_records([first, same, other_time, other_pos, other_aircraft])
    assert refs(result, "duplicates") == ["r:2"]


def test_a_duplicate_of_a_record_set_aside_earlier_is_not_a_duplicate() -> None:
    # r:1 has no position and goes in step 2, so r:2 is the first record of its time and place.
    records = [rec(1, 0, lat=None, lon=None), rec(2, 0)]
    assert refs(clean_records(records), "duplicates") == []


def test_position_jump_sets_aside_the_bad_point_and_not_the_next_good_one() -> None:
    records = line(30)
    records[10] = rec(11, 10, lat=records[10].lat + 3.0)  # 3 degrees away for one second
    result = clean_records(records)
    assert refs(result, "position_jumps") == ["r:11"]
    assert records[9] in result.kept and records[11] in result.kept


def test_position_jump_needs_both_neighbours_to_be_fast() -> None:
    # A real fast move: the aircraft is at the new place from here on, so the next hop is slow.
    records = line(30)
    for i in range(10, 30):
        records[i] = rec(i + 1, i, lat=records[i].lat + 3.0)
    assert refs(clean_records(records), "position_jumps") == []


def test_position_jump_ignores_simultaneous_records_and_the_ends() -> None:
    a = rec(1, 0)
    b = rec(2, 0, lat=-5.0)  # same time, different place: speed is undefined, nothing is flagged
    c = rec(3, 1, lat=-6.0001)
    result = clean_records([a, b, c, *line(25, start=10)[1:]])
    assert refs(result, "position_jumps") == []


def test_position_jump_slow_aircraft_is_never_flagged() -> None:
    records = line(30, step_s=10)  # 100 kt
    assert refs(clean_records(records), "position_jumps") == []


def test_altitude_spike_needs_both_neighbours_within_two_seconds() -> None:
    records = line(30)
    records[10] = rec(11, 10, lat=records[10].lat, alt=9000)
    result = clean_records(records)
    assert refs(result, "altitude_spikes") == ["r:11"]


def test_altitude_spike_window_is_two_seconds() -> None:
    inside = line(30)
    inside[10] = rec(11, 10, lat=inside[10].lat, alt=9000)
    # Neighbours exactly 2 s away still count.
    spaced = [rec(n + 1, 2 * n, lat=-6.0 + 100 * DEG_PER_KT_S * 2 * n) for n in range(30)]
    spaced[10] = rec(11, 20, lat=spaced[10].lat, alt=9000)
    assert refs(clean_records(spaced), "altitude_spikes") == ["r:11"]
    # With the next record 2.5 s later the window is not met, so nothing is a spike.
    wide = [rec(n + 1, 2 * n, lat=-6.0 + 100 * DEG_PER_KT_S * 2 * n) for n in range(30)]
    wide[10] = rec(11, 20, lat=wide[10].lat, alt=9000)
    wide[11] = rec(12, 22.5, lat=wide[11].lat)
    assert refs(clean_records(wide), "altitude_spikes") == []


def test_altitude_step_of_exactly_2000_ft_is_not_a_spike() -> None:
    records = line(30)
    records[10] = rec(11, 10, lat=records[10].lat, alt=5000)  # 2,000 ft from both neighbours
    assert refs(clean_records(records), "altitude_spikes") == []


def test_a_level_change_is_not_a_spike() -> None:
    # The altitude jumps once and stays: the next record agrees with it, so it is not a single bad point.
    records = line(30)
    for i in range(10, 30):
        records[i] = rec(i + 1, i, lat=records[i].lat, alt=9000)
    assert refs(clean_records(records), "altitude_spikes") == []


def test_missing_altitude_is_never_a_spike() -> None:
    records = line(30)
    records[10] = rec(11, 10, lat=records[10].lat, alt=None)
    assert refs(clean_records(records), "altitude_spikes") == []


def test_fragments_threshold_is_twenty_records_left() -> None:
    result = clean_records([*line(19, icao24="aaaaaa"), *line(20, icao24="bbbbbb", start=100)])
    assert refs(result, "fragments") == [f"r:{n}" for n in range(1, 20)]
    assert {r.icao24 for r in result.kept} == {"bbbbbb"}


def test_fragments_count_what_earlier_steps_kept() -> None:
    # 20 records, one of them without a position: 19 are left, so the whole aircraft goes.
    records = line(20)
    records[5] = rec(6, 5, lat=None, lon=None)
    result = clean_records(records)
    assert len(refs(result, "fragments")) == 19
    assert result.kept == []


def test_records_in_chain_and_total() -> None:
    records = [
        *line(30),
        *line(5, icao24="bbbbbb", start=100),
        rec(200, 1, icao24=None),
        rec(201, 2, lat=None, lon=None),
    ]
    records.append(records[1])  # a duplicate of r:2
    result = clean_records(records)
    steps = result.steps
    assert steps[0]["records_in"] == len(records)
    for before, after in zip(steps, steps[1:]):
        assert after["records_in"] == before["records_in"] - before["set_aside"]
    assert sum(s["set_aside"] for s in steps) + len(result.kept) == steps[0]["records_in"]
    assert len(result.set_aside) == sum(s["set_aside"] for s in steps)


def test_kept_keeps_the_given_order() -> None:
    a, b = line(20, icao24="aaaaaa"), line(20, icao24="bbbbbb", start=100)
    mixed = [x for pair in zip(a, b) for x in pair]
    assert clean_records(mixed).kept == mixed


@settings(max_examples=100, deadline=None)
@given(
    st.lists(
        st.tuples(
            st.sampled_from(["aaaaaa", "bbbbbb", None]),
            st.integers(0, 30),
            st.sampled_from([None, -6.0, -6.0001, 20.0]),
            st.sampled_from([None, 3000, 9000]),
        ),
        max_size=120,
    )
)
def test_every_record_is_kept_or_set_aside_exactly_once(items) -> None:
    records = [
        CleanInput(f"r:{i}", icao24, T0 + timedelta(seconds=t), lat, 106.0 if lat is not None else None, alt)
        for i, (icao24, t, lat, alt) in enumerate(items, start=1)
    ]
    result = clean_records(records)
    aside = [r for r, _, _ in result.set_aside]
    assert len(aside) == len(set(aside))
    assert sorted(aside + [r.raw_ref for r in result.kept]) == sorted(r.raw_ref for r in records)
    assert sum(s["set_aside"] for s in result.steps) + len(result.kept) == len(records)
    assert result.steps[0]["records_in"] == len(records)


@pytest.mark.parametrize("code", STEP_ORDER)
def test_every_code_has_a_label_and_reason(code: str) -> None:
    assert cleaning.label_of(code) and cleaning.reason_of(code).endswith(".")
