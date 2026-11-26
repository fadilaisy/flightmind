"""Request throttling for the public /api/ask demo (SCRUM-36).

This limits how often one client may ask (default 5 per minute) and how many questions one
process answers per day (default 300). It uses a monotonic clock that tests replace. That is
request throttling, not replay time, so contract C6 (`clock.now()`) does not apply.

Honest limit: on serverless hosting every instance has its own memory and instances restart,
so this slows abuse but does not cap spend. The real cap is the spend limit in the Claude
Console with auto-reload off.
"""
import logging
import os
import time
from collections import OrderedDict, deque
from typing import Any, Callable, Mapping, Optional

log = logging.getLogger("flightmind.agent")

DEFAULT_PER_MINUTE = 5
DEFAULT_PER_DAY = 300
WINDOW_SECONDS = 60.0
DAY_SECONDS = 86400.0
MAX_TRACKED_CLIENTS = 10000


def _positive_int(env_name: str, default: int) -> int:
    raw = os.environ.get(env_name, "").strip()
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


class AskGuard:
    def __init__(
        self,
        per_minute: Optional[int] = None,
        per_day: Optional[int] = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._per_minute = per_minute
        self._per_day = per_day
        self._clock = clock
        self._clients: "OrderedDict[str, deque]" = OrderedDict()
        self._day_start: Optional[float] = None
        self._day_count = 0

    def _limits(self) -> tuple:
        per_minute = self._per_minute or _positive_int("FLIGHTMIND_ASK_PER_MINUTE", DEFAULT_PER_MINUTE)
        per_day = self._per_day or _positive_int("FLIGHTMIND_ASK_PER_DAY", DEFAULT_PER_DAY)
        return per_minute, per_day

    def check(self, client_key: str) -> bool:
        """True when the request is allowed; an allowed request is counted."""
        per_minute, per_day = self._limits()
        now = self._clock()

        if self._day_start is None or now - self._day_start >= DAY_SECONDS:
            self._day_start = now
            self._day_count = 0
        if self._day_count >= per_day:
            log.warning("ask refused: daily limit reached")
            return False

        times = self._clients.get(client_key)
        if times is None:
            times = deque()
            self._clients[client_key] = times
            while len(self._clients) > MAX_TRACKED_CLIENTS:
                self._clients.popitem(last=False)
        else:
            self._clients.move_to_end(client_key)
        while times and now - times[0] >= WINDOW_SECONDS:
            times.popleft()
        if len(times) >= per_minute:
            log.warning("ask refused: per-minute limit reached for a client")
            return False

        times.append(now)
        self._day_count += 1
        return True


def client_key(headers: Mapping[str, Any], client_host: Optional[str]) -> str:
    """First address of x-forwarded-for, else the client host, else 'unknown'."""
    forwarded = headers.get("x-forwarded-for") if headers is not None else None
    if forwarded:
        first = str(forwarded).split(",")[0].strip()
        if first:
            return first
    return client_host or "unknown"
