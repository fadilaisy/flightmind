"""Stream choice for a recording: list its ASTERIX streams and preview one before processing.

`scan_recording` groups a classic pcap's UDP packets by source and destination ("ip:port"),
reads the ASTERIX category from the first payload byte and SAC/SIC from the first record's
I010. A raw ASTERIX file is one stream with id "raw". Stream ids, field names and counting
follow the upload API's scan (services/intel/real_api/uploads.py): ids are s1, s2, ... with the
busiest stream first, and a supported stream has one record per frame.

`preview` decodes a stream with the ASTERIX decoder, without a database, and reports how often
the main CAT021 items are present.

pcapng is not read here, because pcap_source reads classic little-endian pcap only.
"""

import os
import struct
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from flightmind_pipeline.pcap_source import (
    PCAP_FILE_HEADER_LEN,
    PCAP_LE_MAGIC,
    PCAP_RECORD_HEADER_LEN,
    decode_blocks,
    udp_datagram,
    walk_pcap_streams,
)

CAT021 = 21
RAW_STREAM_ID = "raw"
PREVIEW_SAMPLE_LIMIT = 100_000
# Decoder item key -> label shown to the analyst.
QUALITY_ITEMS = {
    "I130": "I021/130",
    "I140": "I021/140",
    "I145": "I021/145",
    "I170": "I021/170",
    "I040": "I021/040",
}


@dataclass(frozen=True, slots=True)
class Stream:
    id: str
    src: str
    dst: str
    category: int
    sac: int
    sic: int
    frames: int
    records: int
    supported: bool


def _sac_sic(block: bytes) -> tuple[int, int]:
    """SAC and SIC from data item 010 when the first record has it (FRN 1), else (0, 0)."""
    pos = 3
    if len(block) <= pos or not block[pos] & 0x80:
        return 0, 0
    while pos < len(block) and block[pos] & 0x01:
        pos += 1
    pos += 1
    return (block[pos], block[pos + 1]) if pos + 1 < len(block) else (0, 0)


def _is_pcap(path: str | os.PathLike[str]) -> bool:
    with open(path, "rb") as f:
        return f.read(4) == PCAP_LE_MAGIC


def _pcap_payloads(path: str | os.PathLike[str]) -> Iterator[tuple[tuple[str, str], bytes]]:
    """Yield (endpoints, UDP payload) for each UDP-over-IPv4 packet; a cut-off last record ends it."""
    with open(path, "rb") as f:
        header = f.read(PCAP_FILE_HEADER_LEN)
        if header[:4] != PCAP_LE_MAGIC:
            raise ValueError(
                f"{os.fspath(path)}: only little-endian classic pcap is supported, "
                f"found magic bytes {header[:4].hex(' ')}"
            )
        link_type = struct.unpack("<I", header[20:24])[0] & 0xFFFF if len(header) >= 24 else 0
        while True:
            rec = f.read(PCAP_RECORD_HEADER_LEN)
            if len(rec) < PCAP_RECORD_HEADER_LEN:
                return
            cap_len = struct.unpack("<IIII", rec)[2]
            packet = f.read(cap_len)
            if len(packet) < cap_len:
                return
            found = udp_datagram(packet, link_type)
            if found is not None:
                yield found


def _raw_blocks(path: str | os.PathLike[str]) -> Iterator[bytes]:
    """Yield each ASTERIX block (1-byte CAT, 2-byte LEN, body) of a raw ASTERIX file."""
    with open(path, "rb") as f:
        while True:
            head = f.read(3)
            if len(head) < 3:
                return
            length = struct.unpack(">H", head[1:3])[0]
            if length < 3:
                return
            body = f.read(length - 3)
            if len(body) < length - 3:
                return
            yield head + body


def scan_recording(path: str | os.PathLike[str]) -> list[Stream]:
    """List the streams of a recording, busiest first. Reads packet headers only, no decoder."""
    found: dict[tuple[str, str, int], list[Any]] = {}  # key -> [frames, (sac, sic)]
    if _is_pcap(path):
        for ends, block in _pcap_payloads(path):
            if len(block) < 3:
                continue
            entry = found.setdefault((*ends, block[0]), [0, _sac_sic(block)])
            entry[0] += 1
    else:
        for block in _raw_blocks(path):
            entry = found.setdefault(("", "", block[0]), [0, _sac_sic(block)])
            entry[0] += 1
        if found:
            # A raw file is one stream; CAT021 wins over a bigger other category.
            key = max(found, key=lambda k: (k[2] == CAT021, found[k][0]))
            found = {key: found[key]}
    streams: list[Stream] = []
    for (src, dst, category), (frames, (sac, sic)) in sorted(
        found.items(), key=lambda kv: -kv[1][0]
    ):
        supported = category == CAT021
        raw = _is_raw_stream(src, dst)
        streams.append(
            Stream(
                id=RAW_STREAM_ID if raw else f"s{len(streams) + 1}",
                src=src,
                dst=dst,
                category=category,
                sac=sac,
                sic=sic,
                frames=frames,
                records=frames if supported else 0,
                supported=supported,
            )
        )
    return streams


def _is_raw_stream(src: str, dst: str) -> bool:
    return src == "" and dst == ""


def stream_ends(path: str | os.PathLike[str], stream_id: str) -> tuple[str, str] | None:
    """Return the (src, dst) endpoints of a supported stream, or None for the raw stream.

    Raise ValueError when the id is unknown or the stream is not CAT021.
    """
    for stream in scan_recording(path):
        if stream.id == stream_id:
            if not stream.supported:
                raise ValueError(f"Stream '{stream_id}' is CAT{stream.category:03d}, not CAT021.")
            return None if _is_raw_stream(stream.src, stream.dst) else (stream.src, stream.dst)
    raise ValueError(f"Stream '{stream_id}' is not in this recording.")


def preview(
    path: str | os.PathLike[str], stream_id: str, limit: int = 8
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Decode a stream without a database; return (first `limit` records, field quality).

    Each record is the decoder's CAT021 dict plus "record_index", the packet number in the
    whole file (the block number for a raw file). field_quality is
    {"sample_size": n, "present_pct": {"I021/130": pct, ...}}: the share of the first 100,000
    records of the stream that carry each item. Records beyond 100,000 are not read.
    """
    ends = stream_ends(path, stream_id)
    packet_ends = [p[3] for p in walk_pcap_streams(path)] if ends is not None else None
    records: list[dict[str, Any]] = []
    present: Counter[str] = Counter()
    sample = 0
    for number, block in enumerate(decode_blocks(path), start=1):
        if packet_ends is not None:
            if number > len(packet_ends):
                break
            if packet_ends[number - 1] != ends:
                continue
        cat = block.get("CAT021")
        if cat is None:
            continue
        sample += 1
        for item in QUALITY_ITEMS:
            if item in cat:
                present[item] += 1
        if len(records) < limit:
            records.append({"record_index": number, **cat})
        if sample >= PREVIEW_SAMPLE_LIMIT:
            break
    quality = {
        "sample_size": sample,
        "present_pct": {
            label: round(100.0 * present[item] / sample, 1) if sample else 0.0
            for item, label in QUALITY_ITEMS.items()
        },
    }
    return records, quality
