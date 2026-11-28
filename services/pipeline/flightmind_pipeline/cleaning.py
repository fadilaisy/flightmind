"""Cleaning rules: which records of one stream are set aside before tracks are built (SCRUM-67).

Pure functions on a small record type, so the pipeline and the upload API's dry run apply the
same rules. `clean_records` takes the decoded records of one stream in file order and runs six
steps, each on what the previous step kept:

1. no_address       no ICAO 24-bit address (I021/080)
2. no_position      no position (I021/130)
3. duplicates       same address, time and position (to 1e-7 deg) as an earlier kept record
4. position_jumps   implied speed to the previous kept record and to the next record both above
                    1,200 kt, so the one bad point goes and the good point after it stays
5. altitude_spikes  altitude more than 2,000 ft from both neighbours, each within 2 s
6. fragments        every record of an address with fewer than 20 records left

`records_in` of step 1 is the number of records given; each next step starts with what the
previous step kept, so sum(set_aside) + len(kept) == records_in of step 1.
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from flightmind_pipeline.geo import distance_m

MAX_SPEED_KT = 1200.0
MAX_ALT_STEP_FT = 2000
SPIKE_WINDOW_S = 2.0
MIN_TRACK_RECORDS = 20
POSITION_DECIMALS = 7  # 1e-7 deg
METRES_PER_NM = 1852.0

_REASONS = {
    "no_address": "No target address (I021/080), so it cannot be assigned to an aircraft.",
    "no_position": "No position (I021/130), so it cannot be placed on a track.",
    "duplicates": "Same target address, time and position as an earlier record.",
    "position_jumps": "Implied speed to its neighbours above 1,200 kt.",
    "altitude_spikes": "More than 2,000 ft from both neighbours within 2 s.",
    "fragments": "Fewer than 20 records for one target address.",
}
_LABELS = {
    "no_address": "No target address",
    "no_position": "No position",
    "duplicates": "Duplicate records",
    "position_jumps": "Position jumps",
    "altitude_spikes": "Altitude spikes",
    "fragments": "Fragment tracks",
}
STEP_CODES = tuple(_REASONS)


def reason_of(code: str) -> str:
    return _REASONS[code]


def label_of(code: str) -> str:
    return _LABELS[code]


@dataclass(frozen=True, slots=True)
class CleanInput:
    """What the cleaning rules read from one decoded record.

    icao24 is None without a usable address, lat and lon are None without I021/130, and alt_ft
    is the barometric altitude, else the geometric one, else None.
    """

    raw_ref: str
    icao24: str | None
    ts: datetime
    lat: float | None
    lon: float | None
    alt_ft: int | None = None


@dataclass(frozen=True, slots=True)
class CleaningResult:
    kept: list[CleanInput]  # in the order given
    set_aside: list[tuple[str, str, str]]  # (raw_ref, step_code, reason), step by step
    steps: list[dict]  # {code, label, records_in, set_aside, reason}, in pipeline order


def clean_records(records: Sequence[CleanInput]) -> CleaningResult:
    """Run the six steps on records (one stream, file order) and return what is kept and why not."""
    current = list(records)
    set_aside: list[tuple[str, str, str]] = []
    steps: list[dict] = []
    for code, rule in _RULES:
        kept, removed = rule(current)
        reason = _REASONS[code]
        set_aside.extend((r.raw_ref, code, reason) for r in removed)
        steps.append(
            {
                "code": code,
                "label": _LABELS[code],
                "records_in": len(current),
                "set_aside": len(removed),
                "reason": reason,
            }
        )
        current = kept
    return CleaningResult(kept=current, set_aside=set_aside, steps=steps)


def _split(
    records: Sequence[CleanInput], drop: set[int]
) -> tuple[list[CleanInput], list[CleanInput]]:
    """Split records into (kept, removed) by index, both in the given order."""
    kept = [r for i, r in enumerate(records) if i not in drop]
    removed = [r for i, r in enumerate(records) if i in drop]
    return kept, removed


def _no_address(records: Sequence[CleanInput]) -> tuple[list[CleanInput], list[CleanInput]]:
    drop = {i for i, r in enumerate(records) if not r.icao24}
    return _split(records, drop)


def _no_position(records: Sequence[CleanInput]) -> tuple[list[CleanInput], list[CleanInput]]:
    drop = {i for i, r in enumerate(records) if r.lat is None or r.lon is None}
    return _split(records, drop)


def _duplicates(records: Sequence[CleanInput]) -> tuple[list[CleanInput], list[CleanInput]]:
    seen: set[tuple] = set()
    drop: set[int] = set()
    for i, r in enumerate(records):
        assert r.lat is not None and r.lon is not None  # step 2 removed the others
        key = (r.icao24, r.ts, round(r.lat, POSITION_DECIMALS), round(r.lon, POSITION_DECIMALS))
        if key in seen:
            drop.add(i)
        else:
            seen.add(key)
    return _split(records, drop)


def _by_address(records: Sequence[CleanInput]) -> dict[str | None, list[int]]:
    """Indexes of records per address, in time order (file order breaks ties)."""
    groups: dict[str | None, list[int]] = defaultdict(list)
    for i, r in enumerate(records):
        groups[r.icao24].append(i)
    for indexes in groups.values():
        indexes.sort(key=lambda i: (records[i].ts, i))
    return groups


def _speed_kt(a: CleanInput, b: CleanInput) -> float | None:
    """Implied ground speed between two positioned records, or None when they are simultaneous."""
    dt = (b.ts - a.ts).total_seconds()
    if dt <= 0:
        return None
    assert a.lat is not None and a.lon is not None and b.lat is not None and b.lon is not None
    return distance_m(a.lat, a.lon, b.lat, b.lon) / dt * 3600.0 / METRES_PER_NM


def _fast(a: CleanInput, b: CleanInput) -> bool:
    speed = _speed_kt(a, b)
    return speed is not None and speed > MAX_SPEED_KT


def _position_jumps(records: Sequence[CleanInput]) -> tuple[list[CleanInput], list[CleanInput]]:
    drop: set[int] = set()
    for indexes in _by_address(records).values():
        previous: CleanInput | None = None  # the last record of this aircraft that was kept
        for k, i in enumerate(indexes):
            record = records[i]
            following = records[indexes[k + 1]] if k + 1 < len(indexes) else None
            if (
                previous is not None
                and following is not None
                and _fast(previous, record)
                and _fast(record, following)
            ):
                drop.add(i)
            else:
                previous = record
    return _split(records, drop)


def _altitude_spikes(records: Sequence[CleanInput]) -> tuple[list[CleanInput], list[CleanInput]]:
    drop: set[int] = set()
    for indexes in _by_address(records).values():
        previous: CleanInput | None = None
        for k, i in enumerate(indexes):
            record = records[i]
            following = records[indexes[k + 1]] if k + 1 < len(indexes) else None
            if _is_spike(previous, record, following):
                drop.add(i)
            else:
                previous = record
    return _split(records, drop)


def _is_spike(
    previous: CleanInput | None, record: CleanInput, following: CleanInput | None
) -> bool:
    if previous is None or following is None:
        return False
    if previous.alt_ft is None or record.alt_ft is None or following.alt_ft is None:
        return False
    if (record.ts - previous.ts).total_seconds() > SPIKE_WINDOW_S:
        return False
    if (following.ts - record.ts).total_seconds() > SPIKE_WINDOW_S:
        return False
    return (
        abs(record.alt_ft - previous.alt_ft) > MAX_ALT_STEP_FT
        and abs(record.alt_ft - following.alt_ft) > MAX_ALT_STEP_FT
    )


def _fragments(records: Sequence[CleanInput]) -> tuple[list[CleanInput], list[CleanInput]]:
    counts: dict[str | None, int] = defaultdict(int)
    for r in records:
        counts[r.icao24] += 1
    drop = {i for i, r in enumerate(records) if counts[r.icao24] < MIN_TRACK_RECORDS}
    return _split(records, drop)


_RULES = (
    ("no_address", _no_address),
    ("no_position", _no_position),
    ("duplicates", _duplicates),
    ("position_jumps", _position_jumps),
    ("altitude_spikes", _altitude_spikes),
    ("fragments", _fragments),
)

assert tuple(code for code, _ in _RULES) == STEP_CODES
