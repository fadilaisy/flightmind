"""Replay source: feed decoded CAT021 records in recording-time order, paced by the shared clock.

`replay_recording(path, speed, on_record)` accepts either a decoded JSON-lines file (one
decoder block per line, as in fixtures/*.decoded.jsonl) or a classic pcap (decoded with the
ASTERIX decoder, packet times from the pcap headers).

Record time:
- pcap: the packet's capture time, so it equals `Point.ts` in the stored data.
- jsonl: the block's `timestamp` field (seconds). Only the spacing between records matters
  for replay; the absolute value is whatever the decoder wrote.

`raw_ref` is `<recording id>:<n>` (the file stem, minus a trailing ".decoded"), n starting at 1 in file order, the same numbering the
pipeline uses for packets, so a replayed record cites the same bytes as the stored one.
"""

import json
import os
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from flightmind_pipeline import clock
from flightmind_pipeline.pcap_source import PCAP_LE_MAGIC, decode_blocks, walk_pcap


@dataclass(frozen=True, slots=True)
class ReplayRecord:
    raw_ref: str
    ts: datetime
    block: dict[str, Any]


def load_records(path: str | os.PathLike[str]) -> list[ReplayRecord]:
    """Read a recording into records, sorted by recording time (file order breaks ties)."""
    p = Path(path)
    with p.open("rb") as f:
        magic = f.read(len(PCAP_LE_MAGIC))
    if magic == PCAP_LE_MAGIC:
        records = list(_pcap_records(p))
    else:
        records = list(_jsonl_records(p))
    return sorted(records, key=lambda r: r.ts)  # sorted() is stable


def _recording_id(path: Path) -> str:
    stem = path.stem
    return stem.removesuffix(".decoded") if path.suffix == ".jsonl" else stem


def _pcap_records(path: Path) -> Iterator[ReplayRecord]:
    packets = walk_pcap(path)
    for (record_index, _offset, ts), block in zip(packets, decode_blocks(path), strict=False):
        yield ReplayRecord(f"{_recording_id(path)}:{record_index}", ts, block)


def _jsonl_records(path: Path) -> Iterator[ReplayRecord]:
    with path.open(encoding="utf-8") as f:
        index = 0
        for line in f:
            if not line.strip():
                continue
            index += 1
            block = json.loads(line)
            seconds = block.get("timestamp")
            if not isinstance(seconds, (int, float)):
                raise ValueError(f"{path}: line {index} has no numeric 'timestamp'")
            ts = datetime.fromtimestamp(0, UTC) + timedelta(seconds=seconds)
            yield ReplayRecord(f"{_recording_id(path)}:{index}", ts, block)


def replay_recording(
    path: str | os.PathLike[str],
    speed: float,
    on_record: Callable[[ReplayRecord], None],
    *,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Call `on_record` for every record at `speed` times real time. Return the record count.

    Sets the shared clock to replay mode at the first record's time for the duration of the
    call, so code inside `on_record` that reads `clock.now()` sees recording time; the previous
    clock is put back afterwards, also on an error. Pause, resume and seek through `clock`
    while it runs. `monotonic` and `sleep` are injectable so tests need no real waiting.
    """
    records = load_records(path)
    if not records:
        return 0
    previous = clock.current()
    replay = clock.set_replay(records[0].ts, speed, monotonic)
    try:
        for record in records:
            replay.wait_until(record.ts, sleep)
            on_record(record)
    finally:
        clock.restore(previous)
    return len(records)
