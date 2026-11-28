"""A small CAT021 FSPEC reader (SCRUM-68). Pure Python, no dependencies.

The server has no ASTERIX decoder at scan time, but which data items a record carries is
written in its FSPEC (field specification) alone. `items_of_block` reads the FSPEC of the first
record of one block (one record per block, as the pipeline assumes) and returns the item names
such as "I130". The UAP (the FRN to item table) is CAT021 edition 2.x and is checked against the
reference decoder's output in fixtures/adsb_sample_500.decoded.jsonl by tests/test_cat021.py.
The table differs from the first draft at FRN 34-42: I110 is FRN 34, then I016, I008, I271,
I132, I250, I260, I400, I295 (the fixture has I132 where the draft put I250).
"""
from typing import Optional, Set, Tuple

# FRN 1.. in order; None is a spare FRN. FRN 48 is the Reserved Expansion field, FRN 49 the
# Special Purpose field.
UAP = (
    "I010", "I040", "I161", "I015", "I071", "I130", "I131",
    "I072", "I150", "I151", "I080", "I073", "I074", "I075",
    "I076", "I140", "I090", "I210", "I070", "I230", "I145",
    "I152", "I200", "I155", "I157", "I160", "I165", "I077",
    "I170", "I020", "I220", "I146", "I148", "I110", "I016",
    "I008", "I271", "I132", "I250", "I260", "I400", "I295",
    None, None, None, None, None, "RE", "SP",
)

HEADER_LEN = 3  # CAT (1 byte) + LEN (2 bytes)


def fspec_items(data: bytes, pos: int = 0) -> Tuple[Set[str], int]:
    """(items present, offset of the first byte after the FSPEC) for the record starting at pos.

    Raises ValueError when the FSPEC runs past the end of data.
    """
    items: Set[str] = set()
    frn = 0
    while True:
        if pos >= len(data):
            raise ValueError("The FSPEC is cut short.")
        octet = data[pos]
        pos += 1
        for bit in range(7):  # MSB first; the lowest bit is FX
            frn += 1
            if octet & (0x80 >> bit) and frn <= len(UAP) and UAP[frn - 1]:
                items.add(UAP[frn - 1])
        if not octet & 0x01:
            return items, pos


def items_of_block(block: bytes) -> Tuple[Set[str], Optional[Tuple[int, int]]]:
    """(items of the first record, (SAC, SIC) when I010 is present) for one ASTERIX data block.

    Raises ValueError when the block is too short to hold an FSPEC.
    """
    if len(block) <= HEADER_LEN:
        raise ValueError("The block has no record.")
    items, after = fspec_items(block, HEADER_LEN)
    sac_sic = None
    if "I010" in items and after + 2 <= len(block):
        sac_sic = (block[after], block[after + 1])  # I010 is FRN 1, so it is the first item after the FSPEC
    return items, sac_sic
