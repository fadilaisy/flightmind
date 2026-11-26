"""End-to-end smoke test on the committed 500-packet fixture, with no database and no decoder.

It reads the decoded JSON that the decoder produced earlier, pairs each JSON block with its packet
in the pcap, and runs points, tracks and compression. This guards the packet-to-block alignment
that the CLI relies on (review 2026-11-22).
"""

import json
from pathlib import Path

from flightmind_pipeline.compress import compress_track
from flightmind_pipeline.pcap_source import walk_pcap
from flightmind_pipeline.points import point_from_block
from flightmind_pipeline.tracks import split_tracks

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"
PCAP = FIXTURES / "adsb_sample_500.pcap"
JSONL = FIXTURES / "adsb_sample_500.decoded.jsonl"
RECORDING = "adsb_sample_500"


def _points() -> list:
    packets = list(walk_pcap(PCAP))
    blocks = [json.loads(line) for line in JSONL.read_text(encoding="utf-8").splitlines() if line]
    assert len(blocks) == len(packets) == 500
    points = []
    for (record_index, offset, ts), block in zip(packets, blocks):
        point = point_from_block(block, RECORDING, record_index, offset, ts)
        if point is not None:
            points.append(point)
    return points


def test_fixture_packets_match_decoded_blocks_one_to_one() -> None:
    assert len(_points()) == 500


def test_fixture_runs_through_tracks_and_compression() -> None:
    tracks = split_tracks(_points())
    assert len(tracks) == 208
    kept = sum(len(compress_track(track, set()).kept) for track in tracks)
    assert kept == 383
