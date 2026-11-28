"""Shared clock and replay source (SCRUM-24, C6). A fake monotonic source drives every test, so
nothing really sleeps."""

import json
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from flightmind_pipeline import clock
from flightmind_pipeline.cli import main
from flightmind_pipeline.clock import ReplayClock
from flightmind_pipeline.replay import load_records, replay_recording

JSONL = Path(__file__).resolve().parents[3] / "fixtures" / "adsb_sample_500.decoded.jsonl"
START = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


class FakeTime:
    """A monotonic source that moves only when told to; sleep() moves it."""

    def __init__(self) -> None:
        self.t = 1000.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.t += seconds


@pytest.fixture(autouse=True)
def wall_clock_after():
    yield
    clock.set_wall()


def secs(c: ReplayClock) -> float:
    return (c.now() - START).total_seconds()


@pytest.mark.parametrize("speed", [1, 10, 60])
def test_speed_scales_wall_time_to_recording_time(speed: float) -> None:
    ft = FakeTime()
    c = ReplayClock(START, speed, ft.monotonic)
    assert secs(c) == 0
    ft.t += 2
    assert secs(c) == pytest.approx(2 * speed)


def test_change_of_speed_does_not_jump() -> None:
    ft = FakeTime()
    c = ReplayClock(START, 10, ft.monotonic)
    ft.t += 3
    c.set_speed(60)
    assert secs(c) == pytest.approx(30)
    ft.t += 1
    assert secs(c) == pytest.approx(90)


def test_pause_freezes_and_resume_continues() -> None:
    ft = FakeTime()
    c = ReplayClock(START, 10, ft.monotonic)
    ft.t += 1
    c.pause()
    assert c.paused
    ft.t += 100
    assert secs(c) == pytest.approx(10)
    c.resume()
    assert secs(c) == pytest.approx(10)
    ft.t += 1
    assert secs(c) == pytest.approx(20)


def test_seek_jumps_and_keeps_speed_and_pause_state() -> None:
    ft = FakeTime()
    c = ReplayClock(START, 10, ft.monotonic)
    c.seek(START + timedelta(hours=1))
    assert secs(c) == pytest.approx(3600)
    ft.t += 1
    assert secs(c) == pytest.approx(3610)
    c.pause()
    c.seek(START + timedelta(seconds=5))
    ft.t += 50
    assert secs(c) == pytest.approx(5)
    assert c.paused


def test_bad_inputs_are_rejected() -> None:
    with pytest.raises(ValueError):
        ReplayClock(START, 0)
    with pytest.raises(ValueError):
        ReplayClock(datetime(2026, 1, 1), 1)
    with pytest.raises(ValueError):
        ReplayClock(START, 1).seek(datetime(2026, 1, 1))


def test_wait_until_sleeps_wall_time_and_stops_at_target() -> None:
    ft = FakeTime()
    c = ReplayClock(START, 60, ft.monotonic)
    c.wait_until(START + timedelta(seconds=120), ft.sleep)
    assert sum(ft.sleeps) == pytest.approx(2.0)
    assert secs(c) >= 120
    ft.sleeps.clear()
    c.wait_until(START, ft.sleep)  # already past: no sleep
    assert ft.sleeps == []


def test_wait_until_polls_while_paused_until_resumed() -> None:
    ft = FakeTime()
    c = ReplayClock(START, 10, ft.monotonic)
    c.pause()
    polls = 0

    def sleep(seconds: float) -> None:
        nonlocal polls
        polls += 1
        ft.sleep(seconds)
        if polls == 3:
            c.resume()

    c.wait_until(START + timedelta(seconds=1), sleep)
    assert polls >= 3
    assert secs(c) >= 1


def test_module_clock_defaults_to_wall_and_switches() -> None:
    assert abs((clock.now() - datetime.now(UTC)).total_seconds()) < 5
    ft = FakeTime()
    clock.set_replay(START, 60, ft.monotonic)
    assert clock.now() == START
    ft.t += 1
    assert clock.now() == START + timedelta(seconds=60)
    clock.pause()
    ft.t += 5
    assert clock.now() == START + timedelta(seconds=60)
    clock.resume()
    clock.seek(START)
    assert clock.now() == START
    clock.set_wall()
    assert clock.now().year >= 2026 and clock.now() != START
    with pytest.raises(RuntimeError):
        clock.pause()


def test_clock_is_thread_safe() -> None:
    ft = FakeTime()
    c = ReplayClock(START, 10, ft.monotonic)
    errors: list[BaseException] = []

    def work() -> None:
        try:
            for i in range(500):
                c.pause()
                c.seek(START + timedelta(seconds=i))
                c.resume()
                c.set_speed(1 + i % 5)
                c.now()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=work) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []


def test_replay_fixture_emits_in_order_with_spacing_at_60x() -> None:
    ft = FakeTime()
    seen: list[tuple[str, datetime, datetime]] = []  # raw_ref, record ts, clock.now() at emit

    def on_record(record) -> None:
        seen.append((record.raw_ref, record.ts, clock.now()))

    count = replay_recording(JSONL, 60, on_record, monotonic=ft.monotonic, sleep=ft.sleep)
    assert count == len(seen) == 500
    assert [s[0] for s in seen] == [f"adsb_sample_500:{i}" for i in range(1, 501)]
    stamps = [s[1] for s in seen]
    assert stamps == sorted(stamps)

    # Each record arrives when recording time has reached its timestamp, and not much later.
    for _ref, ts, now in seen:
        assert ts <= now <= ts + timedelta(seconds=60 * 1.0)

    # Spacing: elapsed fake wall time x 60 equals the recording span, so no sleep was skipped.
    span = (stamps[-1] - stamps[0]).total_seconds()
    assert sum(ft.sleeps) * 60 == pytest.approx(span, rel=1e-6)
    assert ft.t - 1000.0 == pytest.approx(span / 60, rel=1e-6)
    # The first records are 1 s apart in the recording: 1/60 s of wall time between them.
    first_gap = (stamps[1] - stamps[0]).total_seconds()
    assert first_gap == 1.0

    assert clock.current() is not None
    assert abs((clock.now() - datetime.now(UTC)).total_seconds()) < 5  # wall clock restored


def test_replay_restores_the_clock_on_error() -> None:
    ft = FakeTime()

    def boom(_record) -> None:
        raise RuntimeError("consumer failed")

    with pytest.raises(RuntimeError):
        replay_recording(JSONL, 60, boom, monotonic=ft.monotonic, sleep=ft.sleep)
    assert abs((clock.now() - datetime.now(UTC)).total_seconds()) < 5


def test_load_records_sorts_by_time_and_keeps_file_order_on_ties(tmp_path: Path) -> None:
    lines = [{"timestamp": 5.0, "n": 1}, {"timestamp": 3.0, "n": 2}, {"timestamp": 5.0, "n": 3}]
    f = tmp_path / "r.jsonl"
    f.write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")
    assert [r.block["n"] for r in load_records(f)] == [2, 1, 3]
    assert [r.raw_ref for r in load_records(f)] == ["r:2", "r:1", "r:3"]


def test_jsonl_line_without_timestamp_is_an_error(tmp_path: Path) -> None:
    f = tmp_path / "r.jsonl"
    f.write_text('{"id": 1}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="timestamp"):
        load_records(f)


def test_cli_replay_prints_records(capsys: pytest.CaptureFixture[str], monkeypatch) -> None:
    ft = FakeTime()
    import flightmind_pipeline.replay as replay_mod

    real = replay_mod.replay_recording
    monkeypatch.setattr(
        replay_mod,
        "replay_recording",
        lambda path, speed, cb: real(path, speed, cb, monotonic=ft.monotonic, sleep=ft.sleep),
    )
    monkeypatch.delenv("FLIGHTMIND_DSN", raising=False)
    assert main(["replay", "--speed", "60", str(JSONL)]) == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 500
    first = json.loads(out[0])
    assert first["raw_ref"] == "adsb_sample_500:1"
    assert first["icao24"] == "76CC67"


def test_cli_replay_with_dsn_refuses_jsonl(monkeypatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("FLIGHTMIND_DSN", "postgresql://unused")
    assert main(["replay", "--speed", "60", str(JSONL)]) == 2
    assert "only a pcap" in capsys.readouterr().err
