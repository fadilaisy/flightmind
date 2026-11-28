"""Database tests for store.write_recording. They need FLIGHTMIND_TEST_DSN and are skipped without it."""

import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import psycopg
import pytest

from flightmind_pipeline.events import DetectedEvent, event_id
from flightmind_pipeline.points import Point
from flightmind_pipeline.store import RecordingFile, write_recording

TEST_DSN = os.environ.get("FLIGHTMIND_TEST_DSN")
TEST_REC = "TEST_REC"
T0 = datetime(2026, 11, 15, 10, 0, tzinfo=UTC)

pytestmark = [
    pytest.mark.db,
    pytest.mark.skipif(TEST_DSN is None, reason="FLIGHTMIND_TEST_DSN is not set: database tests skipped"),
]


def _points() -> list[Point]:
    return [
        Point(
            ts=T0 + timedelta(seconds=i),
            record_index=i + 1,
            raw_ref=f"{TEST_REC}:{i + 1}",
            raw_offset=100 * i,
            icao24="8a09f6",
            callsign="GIA123",
            lat=-6.12,
            lon=106.65,
            baro_alt_ft=3000,
            geo_alt_ft=3050,
            gs_kt=200.0,
            track_deg=90.0,
            vrate_fpm=0,
            on_ground=False,
            nacp=8,
            sac=1,
            sic=2,
        )
        for i in range(3)
    ]


def _event(severity: int = 3) -> DetectedEvent:
    return DetectedEvent(
        type="squawk_7700",
        icao24="8a09f6",
        callsign="GIA123",
        start_ts=T0,
        end_ts=T0 + timedelta(seconds=1),
        airport=None,
        lat=-6.12,
        lon=106.65,
        severity=severity,
        details={"code": "7700"},
        raw_refs=(f"{TEST_REC}:1", f"{TEST_REC}:2"),
    )


def _recording(points: list[Point]) -> RecordingFile:
    return RecordingFile(
        id=TEST_REC,
        uri="test://TEST_REC",
        sha256="0" * 64,
        size_bytes=1,
        record_count=len(points),
        first_ts=min((p.ts for p in points), default=None),
        last_ts=max((p.ts for p in points), default=None),
    )


def _delete_test_rows(conn: psycopg.Connection) -> None:
    conn.rollback()
    conn.execute(
        "DELETE FROM telemetry WHERE left(raw_ref, length(%s) + 1) = %s || ':'",
        (TEST_REC, TEST_REC),
    )
    conn.execute(
        "DELETE FROM events WHERE cardinality(raw_refs) > 0 "
        "AND left(raw_refs[1], length(%s) + 1) = %s || ':'",
        (TEST_REC, TEST_REC),
    )
    conn.execute("DELETE FROM recording_files WHERE id = %s", (TEST_REC,))
    conn.commit()


@pytest.fixture
def conn() -> Iterator[psycopg.Connection]:
    assert TEST_DSN is not None
    with psycopg.connect(TEST_DSN) as connection:
        _delete_test_rows(connection)
        yield connection
        _delete_test_rows(connection)


def _counts(conn: psycopg.Connection) -> tuple[int, int]:
    telemetry = conn.execute(
        "SELECT count(*) FROM telemetry WHERE left(raw_ref, length(%s) + 1) = %s || ':'",
        (TEST_REC, TEST_REC),
    ).fetchone()
    events = conn.execute(
        "SELECT count(*) FROM events WHERE cardinality(raw_refs) > 0 "
        "AND left(raw_refs[1], length(%s) + 1) = %s || ':'",
        (TEST_REC, TEST_REC),
    ).fetchone()
    assert telemetry is not None and events is not None
    return telemetry[0], events[0]


def _event_ids(conn: psycopg.Connection) -> list:
    rows = conn.execute(
        "SELECT id FROM events WHERE cardinality(raw_refs) > 0 "
        "AND left(raw_refs[1], length(%s) + 1) = %s || ':' ORDER BY id",
        (TEST_REC, TEST_REC),
    ).fetchall()
    return [row[0] for row in rows]


def test_rewriting_same_recording_keeps_counts_and_event_ids(conn: psycopg.Connection):
    points = _points()
    event = _event()
    kept = {f"{TEST_REC}:1"}

    first_bytes = write_recording(conn, _recording(points), points, kept, [event])
    first_counts = _counts(conn)
    first_ids = _event_ids(conn)

    second_bytes = write_recording(conn, _recording(points), points, kept, [event])

    assert first_counts == (3, 1)
    assert _counts(conn) == first_counts
    assert _event_ids(conn) == first_ids == [event_id(event)]
    assert first_bytes > 0
    assert second_bytes == first_bytes


def test_failed_write_leaves_previous_state_unchanged(conn: psycopg.Connection):
    points = _points()
    write_recording(conn, _recording(points), points, set(), [_event()])
    before_counts = _counts(conn)
    before_refs = conn.execute(
        "SELECT raw_ref FROM telemetry WHERE left(raw_ref, length(%s) + 1) = %s || ':' "
        "ORDER BY raw_ref",
        (TEST_REC, TEST_REC),
    ).fetchall()

    # The telemetry is replaced and copied before this event fails in the database
    # (severity 40000 overflows smallint). The rollback must undo all of it.
    new_points = points[:1]
    with pytest.raises(psycopg.Error):
        write_recording(conn, _recording(new_points), new_points, set(), [_event(severity=40000)])

    assert _counts(conn) == before_counts
    after_refs = conn.execute(
        "SELECT raw_ref FROM telemetry WHERE left(raw_ref, length(%s) + 1) = %s || ':' "
        "ORDER BY raw_ref",
        (TEST_REC, TEST_REC),
    ).fetchall()
    assert after_refs == before_refs


def test_rerun_with_shorter_range_deletes_telemetry_outside_new_range(conn: psycopg.Connection):
    points = _points()
    write_recording(conn, _recording(points), points, set(), [_event()])
    assert _counts(conn) == (3, 1)
    # Only the first point is written again, so the new range is narrower than the stored one.
    new_points = points[:1]
    write_recording(conn, _recording(new_points), new_points, set(), [])
    assert _counts(conn) == (1, 0)


def test_empty_recording_writes_only_the_recording_row(conn: psycopg.Connection):
    points = _points()
    write_recording(conn, _recording(points), points, set(), [_event()])

    stored = write_recording(conn, _recording([]), [], set(), [])

    assert stored == 0
    assert _counts(conn) == (0, 0)
    row = conn.execute(
        "SELECT record_count FROM recording_files WHERE id = %s", (TEST_REC,)
    ).fetchone()
    assert row == (0,)


def _embedding_vector() -> str:
    return "[" + ",".join("0" for _ in range(1024)) + "]"


def _notified_ids(conn: psycopg.Connection) -> list[str]:
    return [n.payload for n in conn.notifies(timeout=0.5, stop_after=50)]


def test_rerun_keeps_an_existing_event_embedding(conn: psycopg.Connection):
    points = _points()
    event = _event()
    write_recording(conn, _recording(points), points, {f"{TEST_REC}:1"}, [event])
    conn.execute(
        "INSERT INTO event_embeddings (event_id, story, model, embedding) "
        "VALUES (%s, 'story', 'test-model', %s::vector)",
        (event_id(event), _embedding_vector()),
    )
    conn.commit()

    write_recording(conn, _recording(points), points, {f"{TEST_REC}:1"}, [event])

    row = conn.execute(
        "SELECT count(*) FROM event_embeddings WHERE event_id = %s", (event_id(event),)
    ).fetchone()
    assert row is not None and row[0] == 1


def test_rerun_deletes_only_the_events_it_no_longer_produces(conn: psycopg.Connection):
    points = _points()
    kept = {f"{TEST_REC}:1"}
    kept_event = _event()
    dropped_event = DetectedEvent(
        type="squawk_7600",
        icao24="8a09f6",
        callsign="GIA123",
        start_ts=T0 + timedelta(seconds=2),
        end_ts=T0 + timedelta(seconds=2),
        airport=None,
        lat=-6.12,
        lon=106.65,
        severity=2,
        details={"code": "7600"},
        raw_refs=(f"{TEST_REC}:3",),
    )
    write_recording(conn, _recording(points), points, kept, [kept_event, dropped_event])
    assert _counts(conn) == (3, 2)

    write_recording(conn, _recording(points), points, kept, [kept_event])

    assert _counts(conn) == (3, 1)
    assert _event_ids(conn) == [event_id(kept_event)]


def test_rerun_does_not_announce_existing_events_again(conn: psycopg.Connection):
    points = _points()
    event = _event()
    conn.execute("LISTEN events_new")
    conn.commit()
    write_recording(conn, _recording(points), points, {f"{TEST_REC}:1"}, [event])
    first = _notified_ids(conn)
    assert first == [str(event_id(event))]

    write_recording(conn, _recording(points), points, {f"{TEST_REC}:1"}, [event])

    assert _notified_ids(conn) == []
