"""Group points into aircraft tracks: one track per ICAO24, split at gaps of one hour or more."""

import itertools
from collections import defaultdict
from collections.abc import Iterable

from flightmind_pipeline.points import Point

TRACK_GAP_S = 3600


def split_tracks(points: Iterable[Point]) -> list[list[Point]]:
    by_icao24: dict[str, list[Point]] = defaultdict(list)
    for point in points:
        by_icao24[point.icao24].append(point)

    tracks: list[list[Point]] = []
    for icao24 in sorted(by_icao24):
        ordered = sorted(by_icao24[icao24], key=lambda p: (p.ts, p.record_index))
        current = [ordered[0]]
        for prev, point in itertools.pairwise(ordered):
            if (point.ts - prev.ts).total_seconds() >= TRACK_GAP_S:
                tracks.append(current)
                current = []
            current.append(point)
        tracks.append(current)
    return tracks
