import copy
from datetime import UTC, datetime

import pytest

from flightmind_pipeline.pcap_source import walk_pcap
from flightmind_pipeline.points import point_from_block

TS = datetime(2026, 11, 15, 10, 0, 0, tzinfo=UTC)

SAMPLE_BLOCK = {
    "CAT021": {
        "I010": {"SAC": 50, "SIC": 201},
        "I040": {"GBS": 0},
        "I070": {"Mode3A": "0110"},
        "I080": {"TAddr": "8A09F6"},
        "I090": {"NACp": 8},
        "I130": {"Lat": -5.4361296, "Lon": 109.3361735},
        "I140": {"geometric_height": 34100},
        "I145": {"FL": 319.5},
        "I155": {"BVR": -1150},
        "I160": {"GS": 0.1153564, "TA": 145.6951904},
        "I170": {"TId": "MYU935  "},
    }
}


def _point(block: dict):
    return point_from_block(block, "rec1", 7, 1024, TS)


def test_sample_block_maps_every_field():
    point = _point(SAMPLE_BLOCK)

    assert point.icao24 == "8a09f6"
    assert point.nacp == 8
    assert point.geo_alt_ft == 34100
    assert point.baro_alt_ft == 31950
    assert point.gs_kt == pytest.approx(415.28, abs=0.01)
    assert point.vrate_fpm == -1150
    assert point.squawk == "0110"
    assert point.callsign == "MYU935"
    assert point.raw_ref == "rec1:7"
    assert point.raw_offset == 1024


def test_geometric_vertical_rate_is_used_when_barometric_is_absent():
    block = copy.deepcopy(SAMPLE_BLOCK)
    del block["CAT021"]["I155"]
    block["CAT021"]["I157"] = {"GVR": 0}
    del block["CAT021"]["I070"]

    point = _point(block)

    assert point.vrate_fpm == 0
    assert point.squawk is None


def test_geometric_height_at_sentinel_gives_no_altitude():
    block = copy.deepcopy(SAMPLE_BLOCK)
    block["CAT021"]["I140"] = {"geometric_height": 204793.75}

    assert _point(block).geo_alt_ft is None


def test_block_without_icao24_gives_no_point():
    block = copy.deepcopy(SAMPLE_BLOCK)
    del block["CAT021"]["I080"]["TAddr"]

    assert _point(block) is None


def test_walk_pcap_rejects_bad_magic(tmp_path):
    path = tmp_path / "bad.pcap"
    path.write_bytes(b"\x0a\x0d\x0d\x0a" + b"\x00" * 20)

    with pytest.raises(ValueError, match="0a 0d 0d 0a"):
        list(walk_pcap(path))
