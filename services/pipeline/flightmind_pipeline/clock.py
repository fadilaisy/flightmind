"""The shared clock (contract C6): every service reads `clock.now()`, never the system time.

The default is the wall clock. `set_replay(start, speed)` switches to a ReplayClock that maps
elapsed wall time onto recording time (1x, 10x, 60x ...), with pause, resume and seek.
`set_wall()` switches back. All functions are thread-safe.

    from flightmind_pipeline import clock
    clock.set_replay(datetime(2026, 1, 1, tzinfo=UTC), speed=60)
    clock.now()
"""

import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

POLL_SECONDS = 0.05  # how often a paused wait looks again


class WallClock:
    """Real time, in UTC."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class ReplayClock:
    """Recording time that advances `speed` seconds for every wall second.

    `monotonic` is the wall time source (seconds, never goes back); tests pass a fake one so
    nothing sleeps. The clock is anchored: recording time = anchor + (monotonic - mark) * speed.
    A pause freezes recording time; resume continues from the frozen value. A change of speed
    or a seek re-anchors, so recording time never jumps except on seek.
    """

    def __init__(
        self,
        start: datetime,
        speed: float = 1.0,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        _check_speed(speed)
        if start.tzinfo is None:
            raise ValueError("start must be timezone-aware")
        self._monotonic = monotonic
        self._lock = threading.RLock()
        self._anchor = start
        self._mark = monotonic()
        self._speed = float(speed)
        self._paused = False

    def now(self) -> datetime:
        with self._lock:
            if self._paused:
                return self._anchor
            return self._anchor + timedelta(seconds=(self._monotonic() - self._mark) * self._speed)

    @property
    def speed(self) -> float:
        with self._lock:
            return self._speed

    @property
    def paused(self) -> bool:
        with self._lock:
            return self._paused

    def set_speed(self, speed: float) -> None:
        _check_speed(speed)
        with self._lock:
            self._reanchor(self.now())
            self._speed = float(speed)

    def pause(self) -> None:
        with self._lock:
            if not self._paused:
                self._reanchor(self.now())
                self._paused = True

    def resume(self) -> None:
        with self._lock:
            if self._paused:
                self._paused = False
                self._mark = self._monotonic()

    def seek(self, to: datetime) -> None:
        """Jump to a recording time. Keeps the speed and the paused state."""
        if to.tzinfo is None:
            raise ValueError("seek target must be timezone-aware")
        with self._lock:
            self._reanchor(to)

    def wait_until(
        self,
        target: datetime,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """Block until recording time reaches `target`; return at once if it already has.

        While paused it polls every POLL_SECONDS. A seek or speed change during the wait is
        picked up on the next loop, because each pass recomputes from now().
        """
        while True:
            with self._lock:
                remaining = (target - self.now()).total_seconds()
                paused, speed = self._paused, self._speed
            if remaining <= 0:
                return
            sleep(POLL_SECONDS if paused else min(remaining / speed, POLL_SECONDS * 20))

    def _reanchor(self, recording_time: datetime) -> None:
        self._anchor = recording_time
        self._mark = self._monotonic()


def _check_speed(speed: float) -> None:
    if not speed > 0:
        raise ValueError(f"speed must be above 0, got {speed}")


_lock = threading.RLock()
_wall = WallClock()
_active: WallClock | ReplayClock = _wall


def now() -> datetime:
    """Current time for data: the wall clock, or recording time in replay mode."""
    with _lock:
        active = _active
    return active.now()


def set_replay(
    start: datetime,
    speed: float = 1.0,
    monotonic: Callable[[], float] = time.monotonic,
) -> ReplayClock:
    """Switch to replay mode, starting at `start`, and return the clock to pause, seek or retime."""
    global _active
    replay = ReplayClock(start, speed, monotonic)
    with _lock:
        _active = replay
    return replay


def set_wall() -> None:
    """Switch back to the wall clock."""
    global _active
    with _lock:
        _active = _wall


def current() -> WallClock | ReplayClock:
    """The clock now in use (for saving and restoring it)."""
    with _lock:
        return _active


def restore(clock: WallClock | ReplayClock) -> None:
    """Put back a clock returned earlier by current()."""
    global _active
    with _lock:
        _active = clock


def _replay() -> ReplayClock:
    active = current()
    if not isinstance(active, ReplayClock):
        raise RuntimeError("clock is in wall mode; call set_replay() first")
    return active


def pause() -> None:
    _replay().pause()


def resume() -> None:
    _replay().resume()


def seek(to: datetime) -> None:
    _replay().seek(to)
