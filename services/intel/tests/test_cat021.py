"""The CAT021 FSPEC reader (SCRUM-68) against the reference decoder's output."""
import json
import re

from real_api import cat021
from realdb import FIXTURE_JSONL


def block_of(record: bytes) -> bytes:
    return bytes([21]) + (len(record) + 3).to_bytes(2, "big") + record


def test_items_match_the_reference_decoder_for_every_fixture_record():
    lines = [json.loads(line) for line in FIXTURE_JSONL.read_text(encoding="utf-8").splitlines() if line]
    assert len(lines) == 500
    for entry in lines:
        record = bytes.fromhex(entry["hexdata"])  # starts at the FSPEC, no block header
        items, sac_sic = cat021.items_of_block(block_of(record))
        expected = {k for k in entry["CAT021"] if re.fullmatch(r"I\d{3}", k)}
        assert items == expected, entry["id"]
        if "I010" in expected:
            i010 = entry["CAT021"]["I010"]
            assert sac_sic == (i010["SAC"], i010["SIC"])
        else:
            assert sac_sic is None


def test_two_octet_fspec():
    # FSPEC 0xC1 0x20: FRN 1, 2 and FX; octet 2 covers FRN 8-14 and 0x20 is its third bit, FRN 10 (I151).
    items, sac_sic = cat021.items_of_block(block_of(bytes([0xC1, 0x20, 0x32, 0xC9, 0x00])))
    assert items == {"I010", "I040", "I151"}
    assert sac_sic == (0x32, 0xC9)


def test_three_octet_fspec_and_item_without_i010():
    # 0x01 (FX only), 0x01 (FX only), 0x80: FRN 15 = I076 and nothing else
    items, sac_sic = cat021.items_of_block(block_of(bytes([0x01, 0x01, 0x80, 0xAA])))
    assert items == {"I076"} and sac_sic is None


def test_spare_frns_are_ignored_and_re_sp_are_named():
    # octet 6 holds FRN 36-42; octet 7 FRN 43-49: spare FRN 43 (0x80), RE is FRN 48 (0x04), SP FRN 49 (0x02)
    fspec = bytes([0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x86])
    items, _ = cat021.items_of_block(block_of(fspec))
    assert items == {"RE", "SP"}


def test_cut_short_fspec_raises():
    try:
        cat021.items_of_block(block_of(bytes([0x81])))
    except ValueError:
        return
    raise AssertionError("expected ValueError")
