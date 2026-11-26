"""Build small Point tracks for tests: one point per second, no randomness."""
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from flightmind_pipeline.points import Point

T0 = datetime(2026, 11, 15, 10, 0, 0, tzinfo=UTC)


def synth_track(
    squawks: Sequence[str | None],
    *,
    icao24: str = "8a09f6",
    start_lat: float = -6.12,
    start_lon: float = 106.65,
    nacp: int = 8,
) -> list[Point]:
    """Return one Point per squawk value, 1 s apart from T0, all at the same position.

    record_index starts at 1 and raw_ref is f"SYN:{record_index}".
    """
    return [
        Point(
            ts=T0 + timedelta(seconds=i),
            record_index=i + 1,
            raw_ref=f"SYN:{i + 1}",
            raw_offset=0,
            icao24=icao24,
            lat=start_lat,
            lon=start_lon,
            nacp=nacp,
            squawk=code,
        )
        for i, code in enumerate(squawks)
    ]
