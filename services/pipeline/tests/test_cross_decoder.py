"""Dev-only cross-check: aviconv-asterix must decode the fixture to the same fields as the
Croatia Control decoder that produced fixtures/adsb_sample_500.decoded.jsonl.

This is an independent check of the decode step. It is skipped when aviconv-asterix is not
installed (install the dev extras to run it). The round trip is not tested here: aviconv re-emits
unmodified records from their stored octets, so that test would pass by construction.
"""

import json
import math
import struct
from collections import Counter
from pathlib import Path

import pytest

aviconv = pytest.importorskip("aviconv_asterix")

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"
PCAP = FIXTURES / "adsb_sample_500.pcap"
JSONL = FIXTURES / "adsb_sample_500.decoded.jsonl"


def _udp_payloads(path: Path) -> list[bytes]:
    """Return the UDP payload of each packet: one ASTERIX data block per packet."""
    data = path.read_bytes()
    payloads = []
    pos = 24
    while pos + 16 <= len(data):
        _, _, cap, _ = struct.unpack("<IIII", data[pos : pos + 16])
        pos += 16
        pkt = data[pos : pos + cap]
        pos += cap
        udp = 14 + (pkt[14] & 0x0F) * 4
        payloads.append(pkt[udp + 8 :])
    return payloads


def test_aviconv_agrees_with_croatia_control_on_shared_fields() -> None:
    blocks = _udp_payloads(PCAP)
    reference = [json.loads(line) for line in JSONL.read_text(encoding="utf-8").splitlines() if line]
    assert len(blocks) == len(reference) == 500

    checked: Counter[str] = Counter()
    mismatches: list[str] = []
    for n, (block, ref) in enumerate(zip(blocks, reference), start=1):
        records = list(aviconv.iter_records(block))
        assert len(records) == 1, f"packet {n}: expected one record"
        rec = records[0]
        cat = ref["CAT021"]
        pairs = {
            "icao": (rec.icao_address, cat.get("I080", {}).get("TAddr")),
            "lat": (rec.lat, cat.get("I130", {}).get("Lat")),
            "lon": (rec.lon, cat.get("I130", {}).get("Lon")),
            "callsign": ((rec.callsign or "").strip(), (cat.get("I170", {}).get("TId") or "").strip()),
            "mode3a": (rec.mode3a, cat.get("I070", {}).get("Mode3A")),
            "flight_level": (rec.flight_level, cat.get("I145", {}).get("FL")),
        }
        for name, (mine, theirs) in pairs.items():
            if mine is None or theirs is None:
                continue
            checked[name] += 1
            if isinstance(mine, float) or isinstance(theirs, float):
                same = math.isclose(float(mine), float(theirs), rel_tol=0, abs_tol=1e-3)
            else:
                same = mine == theirs
            if not same:
                mismatches.append(f"packet {n} {name}: aviconv={mine!r} croatia={theirs!r}")

    assert not mismatches, "\n".join(mismatches[:10])
    # Guard against a vacuous pass: every field must have been compared on many blocks.
    assert checked["icao"] == checked["lat"] == checked["lon"] == checked["callsign"] == 500
    assert checked["mode3a"] > 300
    assert checked["flight_level"] > 400
