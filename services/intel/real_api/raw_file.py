"""Read one recorded ASTERIX block back from its recording file (SCRUM-37).

A raw_ref is '<recording_id>:<record_index>', with record_index 1-based. The pipeline stores
raw_offset, the byte offset of the record in its file, for every telemetry row it keeps:

- classic pcap: the start of the 16-byte packet record header
- pcapng: the start of the Enhanced (or Simple) Packet Block
- raw ASTERIX (.atx/.ast/.bin): the start of the block (1-byte CAT, 2-byte LEN)

Records the pipeline did not keep have no row, so their offset is found by walking the file
from the start, reading headers only. The packet's link, IP and UDP headers are removed, so
what comes back is the ASTERIX block as it was sent.
"""
import os
import struct
from typing import BinaryIO, Iterator, Optional, Tuple

PCAP_MAGICS = {
    b"\xd4\xc3\xb2\xa1": "<",  # little-endian, microseconds
    b"\x4d\x3c\xb2\xa1": "<",  # little-endian, nanoseconds
    b"\xa1\xb2\xc3\xd4": ">",
    b"\xa1\xb2\x3c\x4d": ">",
}
PCAPNG_SHB = b"\x0a\x0d\x0d\x0a"
PCAPNG_IDB, PCAPNG_EPB, PCAPNG_SPB = 1, 6, 3

LINK_ETHERNET, LINK_RAW, LINK_RAW_IP, LINK_LINUX_SLL = 1, 101, 228, 113


class RawFileError(Exception):
    """The file is missing or not in a format this reader knows. The message is safe to show."""


def _format(f: BinaryIO) -> Tuple[str, str, int]:
    """(kind, byte order, link type) from the first bytes. kind is pcap, pcapng or raw."""
    head = f.read(24)
    if head[:4] in PCAP_MAGICS:
        order = PCAP_MAGICS[head[:4]]
        return "pcap", order, struct.unpack(order + "I", head[20:24])[0]
    if head[:4] == PCAPNG_SHB:
        order = "<" if head[8:12] == b"\x4d\x3c\x2b\x1a" else ">"
        return "pcapng", order, _pcapng_link_type(f, order)
    if head[:1] and len(head) >= 3:
        return "raw", ">", 0
    raise RawFileError("The recording file is empty.")


def _pcapng_link_type(f: BinaryIO, order: str) -> int:
    """Link type of the first Interface Description Block (one interface is assumed)."""
    f.seek(0)
    for block_type, offset, length in _pcapng_blocks(f, order):
        if block_type == PCAPNG_IDB:
            f.seek(offset + 8)
            return struct.unpack(order + "H", f.read(2))[0]
    return LINK_ETHERNET


def _pcapng_blocks(f: BinaryIO, order: str) -> Iterator[Tuple[int, int, int]]:
    offset = 0
    while True:
        f.seek(offset)
        head = f.read(8)
        if len(head) < 8:
            return
        block_type, length = struct.unpack(order + "II", head)
        if length < 12:
            raise RawFileError("The pcapng file has a broken block.")
        yield block_type, offset, length
        offset += length


def iter_offsets(f: BinaryIO, kind: str, order: str) -> Iterator[Tuple[int, int]]:
    """(record_index, offset) for every packet or block, record_index from 1."""
    index = 0
    if kind == "pcap":
        offset = 24
        while True:
            f.seek(offset)
            rec = f.read(16)
            if len(rec) < 16:
                return
            index += 1
            yield index, offset
            offset += 16 + struct.unpack(order + "I", rec[8:12])[0]
    elif kind == "pcapng":
        for block_type, offset, _ in _pcapng_blocks(f, order):
            if block_type in (PCAPNG_EPB, PCAPNG_SPB):
                index += 1
                yield index, offset
    else:
        offset = 0
        while True:
            f.seek(offset)
            head = f.read(3)
            if len(head) < 3:
                return
            length = struct.unpack(">H", head[1:3])[0]
            if length < 3:
                raise RawFileError("The ASTERIX file has a block shorter than its header.")
            index += 1
            yield index, offset
            offset += length


def _packet_at(f: BinaryIO, kind: str, order: str, offset: int) -> bytes:
    f.seek(offset)
    if kind == "pcap":
        rec = f.read(16)
        return f.read(struct.unpack(order + "I", rec[8:12])[0])
    if kind == "pcapng":
        block_type, _ = struct.unpack(order + "II", f.read(8))
        if block_type == PCAPNG_EPB:
            _iface, _hi, _lo, cap_len, _orig = struct.unpack(order + "IIIII", f.read(20))
            return f.read(cap_len)
        orig_len = struct.unpack(order + "I", f.read(4))[0]
        return f.read(orig_len)
    head = f.read(3)
    return head + f.read(struct.unpack(">H", head[1:3])[0] - 3)


def udp_ipv4(packet: bytes, link_type: int) -> bytes:
    """The IPv4 datagram inside a link-layer frame. Raise RawFileError when it is not UDP over IPv4."""
    if link_type == LINK_ETHERNET:
        pos, ether_type = 12, None
        while True:
            ether_type = struct.unpack(">H", packet[pos:pos + 2])[0]
            if ether_type in (0x8100, 0x88A8):  # VLAN tags
                pos += 4
                continue
            break
        ip = packet[pos + 2:]
    elif link_type == LINK_LINUX_SLL:
        ip = packet[16:]
    elif link_type in (LINK_RAW, LINK_RAW_IP):
        ip = packet
    else:
        raise RawFileError(f"Link type {link_type} is not supported.")
    if len(ip) < 28 or ip[0] >> 4 != 4 or ip[9] != 17:
        raise RawFileError("The packet is not UDP over IPv4.")
    return ip


def _udp_payload(packet: bytes, link_type: int) -> bytes:
    """Strip link, IPv4 and UDP headers."""
    ip = udp_ipv4(packet, link_type)
    return ip[(ip[0] & 0x0F) * 4 + 8:]


def read_block(path: str, record_index: int, offset: Optional[int]) -> bytes:
    """The ASTERIX bytes of one record. offset may be None; the file is then walked."""
    if not os.path.isfile(path):
        raise RawFileError("The recording file is no longer on this server.")
    with open(path, "rb") as f:
        kind, order, link_type = _format(f)
        if offset is None:
            offset = next((o for i, o in iter_offsets(f, kind, order) if i == record_index), None)
            if offset is None:
                raise LookupError(record_index)
        packet = _packet_at(f, kind, order, offset)
    return packet if kind == "raw" else _udp_payload(packet, link_type)
