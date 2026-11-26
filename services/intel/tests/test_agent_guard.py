"""Tests for the /api/ask guard (SCRUM-36), with an injected clock. No test sleeps."""
from agent.guard import AskGuard, client_key


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_sixth_request_in_a_minute_is_refused_and_allowed_after_sixty_seconds():
    clock = Clock()
    guard = AskGuard(clock=clock)
    assert [guard.check("a") for _ in range(5)] == [True] * 5
    assert guard.check("a") is False
    clock.t += 59.0
    assert guard.check("a") is False
    clock.t += 1.0
    assert guard.check("a") is True


def test_clients_are_independent():
    guard = AskGuard(per_minute=2, clock=Clock())
    assert guard.check("a") and guard.check("a") and not guard.check("a")
    assert guard.check("b") and guard.check("b") and not guard.check("b")


def test_daily_limit_is_per_process_and_resets_after_a_day():
    clock = Clock()
    guard = AskGuard(per_minute=1000, per_day=300, clock=clock)
    assert all(guard.check(f"client{i}") for i in range(300))
    assert guard.check("another") is False  # the 301st
    clock.t += 86399.0
    assert guard.check("another") is False
    clock.t += 1.0
    assert guard.check("another") is True


def test_refused_requests_do_not_count_toward_the_day():
    guard = AskGuard(per_minute=1, per_day=2, clock=Clock())
    assert guard.check("a") is True
    for _ in range(10):
        assert guard.check("a") is False
    assert guard.check("b") is True  # the day has used 2 of 2 only if refusals were counted


def test_limits_come_from_environment_and_bad_values_fall_back(monkeypatch):
    monkeypatch.setenv("FLIGHTMIND_ASK_PER_MINUTE", "2")
    guard = AskGuard(clock=Clock())
    assert guard.check("a") and guard.check("a") and not guard.check("a")
    for bad in ("abc", "0", "-3", ""):
        monkeypatch.setenv("FLIGHTMIND_ASK_PER_MINUTE", bad)
        guard = AskGuard(clock=Clock())
        assert [guard.check("a") for _ in range(5)] == [True] * 5 and guard.check("a") is False


def test_tracked_clients_are_capped(monkeypatch):
    import agent.guard as guard_mod

    monkeypatch.setattr(guard_mod, "MAX_TRACKED_CLIENTS", 3)
    guard = AskGuard(per_minute=5, per_day=1000, clock=Clock())
    for i in range(10):
        guard.check(f"spoofed{i}")
    assert len(guard._clients) == 3


def test_client_key_prefers_first_forwarded_address():
    assert client_key({"x-forwarded-for": "203.0.113.5, 10.0.0.1"}, "10.0.0.1") == "203.0.113.5"
    assert client_key({"x-forwarded-for": "  198.51.100.7  "}, "10.0.0.1") == "198.51.100.7"
    assert client_key({}, "10.0.0.1") == "10.0.0.1"
    assert client_key({"x-forwarded-for": ""}, "10.0.0.1") == "10.0.0.1"
    assert client_key({}, None) == "unknown"
