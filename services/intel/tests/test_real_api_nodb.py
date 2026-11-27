"""Real API pieces that need no database (SCRUM-37): the raw file reader and the DSN check."""
import struct

import pytest
from fastapi.testclient import TestClient

from real_api import raw_file
from realdb import FIXTURE_PCAP, decoded_blocks


def _pcap_packets():
    data = FIXTURE_PCAP.read_bytes()
    pos, out = 24, []
    while pos + 16 <= len(data):
        ts_sec, ts_usec, cap, orig = struct.unpack("<IIII", data[pos:pos + 16])
        out.append((ts_sec, ts_usec, data[pos + 16:pos + 16 + cap]))
        pos += 16 + cap
    return out


def _pcapng(path, order="<"):
    """Write the fixture's packets as pcapng (one interface, Ethernet)."""
    def block(btype, body):
        body += b"\0" * (-len(body) % 4)
        total = 12 + len(body)
        return struct.pack(order + "II", btype, total) + body + struct.pack(order + "I", total)

    out = block(0x0A0D0D0A, struct.pack(order + "IHHq", 0x1A2B3C4D, 1, 0, -1))
    out += block(1, struct.pack(order + "HHI", 1, 0, 65535))
    for ts_sec, ts_usec, pkt in _pcap_packets():
        t = ts_sec * 1_000_000 + ts_usec
        out += block(6, struct.pack(order + "IIIII", 0, t >> 32, t & 0xFFFFFFFF, len(pkt), len(pkt)) + pkt)
    path.write_bytes(out)


def _payload(pkt):
    ip = pkt[14:]
    return ip[(ip[0] & 0x0F) * 4 + 8:]


@pytest.mark.parametrize("index", [1, 2, 250, 500])
def test_pcap_block_matches_the_decoder_output(index):
    block = raw_file.read_block(str(FIXTURE_PCAP), index, None)
    assert block[0] == 0x15
    assert block.hex().upper().endswith(decoded_blocks()[index - 1]["hexdata"])


@pytest.mark.parametrize("order", ["<", ">"])
def test_pcapng_gives_the_same_blocks(tmp_path, order):
    path = tmp_path / "fixture.pcapng"
    _pcapng(path, order)
    for index in (1, 77, 500):
        assert raw_file.read_block(str(path), index, None) == raw_file.read_block(str(FIXTURE_PCAP), index, None)


def test_raw_asterix_file_gives_the_same_blocks(tmp_path):
    path = tmp_path / "fixture.atx"
    path.write_bytes(b"".join(_payload(p) for _, _, p in _pcap_packets()))
    for index in (1, 77, 500):
        assert raw_file.read_block(str(path), index, None) == raw_file.read_block(str(FIXTURE_PCAP), index, None)


def test_offset_given_skips_the_walk():
    with open(FIXTURE_PCAP, "rb") as f:
        kind, order, _ = raw_file._format(f)
        offsets = dict(raw_file.iter_offsets(f, kind, order))
    assert raw_file.read_block(str(FIXTURE_PCAP), 10, offsets[10]) == raw_file.read_block(str(FIXTURE_PCAP), 10, None)


def test_index_past_the_end_and_missing_file(tmp_path):
    with pytest.raises(LookupError):
        raw_file.read_block(str(FIXTURE_PCAP), 501, None)
    with pytest.raises(raw_file.RawFileError):
        raw_file.read_block(str(tmp_path / "gone.pcap"), 1, None)


def test_no_dsn_is_503(monkeypatch):
    monkeypatch.delenv("FLIGHTMIND_DSN", raising=False)
    from real_api.app import app

    r = TestClient(app).get("/api/events")
    assert r.status_code == 503
    assert "FLIGHTMIND_DSN" in r.json()["detail"]
