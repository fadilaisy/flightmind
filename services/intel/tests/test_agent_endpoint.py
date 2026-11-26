"""Tests for the /api/ask wiring (SCRUM-36): switch-on rules, errors, guard, dependency lists."""
import json
import re
from pathlib import Path

import anthropic
import httpx
import pytest

import mock_api.app as app_mod
from agent import endpoint
from agent.guard import AskGuard
from agent_fakes import FakeAnthropic, check_ask_response, claim, final_turn, tool_turn, tool_use
from mock_api import data

FAKE_KEY = "sk-ant-TESTONLY-SECRET-0000"  # not a real key
HOLD = next(e for e in data.EVENTS if e["type"] == "holding")
SEARCH_HOLD = {"type": "holding", "airport": None, "since": None}
REQ = httpx.Request("POST", "https://api.invalid/v1/messages")


def good_script():
    return [
        tool_turn(tool_use("a", "search_events", SEARCH_HOLD)),
        final_turn("ok", [claim("LNI456 held.", ("event", HOLD["id"]))]),
    ]


async def post(question="Any emergency squawk 7700?", headers=None):
    transport = httpx.ASGITransport(app=app_mod.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        return await c.post("/api/ask", json={"question": question}, headers=headers or {})


@pytest.fixture
def agent_on(monkeypatch):
    """Key set, guard fresh, make_client returns a holder whose .fake the test fills in."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY)
    monkeypatch.setattr(app_mod, "_guard", AskGuard(clock=lambda: 0.0))
    holder = type("Holder", (), {})()
    holder.fake = FakeAnthropic()
    monkeypatch.setattr(endpoint, "make_client", lambda: holder.fake)
    return holder


@pytest.fixture
def no_client(monkeypatch):
    def boom():
        raise AssertionError("the Claude client must not be built")

    monkeypatch.setattr(endpoint, "make_client", boom)


def is_canned_squawk(body):
    return body["status"] == "ok" and body["answer_md"].startswith("Found 1 `squawk_7700` event(s)")


# --- switching on and off -------------------------------------------------------------

@pytest.mark.anyio
async def test_no_key_serves_canned_answers_and_never_builds_a_client(no_client):
    r = await post()
    assert r.status_code == 200 and is_canned_squawk(r.json())


@pytest.mark.anyio
@pytest.mark.parametrize("name,value", [
    ("ANTHROPIC_AUTH_TOKEN", "a-token-set-for-another-program"),
    ("ANTHROPIC_API_KEY", ""),
    ("ANTHROPIC_API_KEY", "   "),
])
async def test_other_credentials_or_empty_key_stay_canned(monkeypatch, no_client, name, value):
    monkeypatch.setenv(name, value)
    assert endpoint.agent_enabled() is False
    assert is_canned_squawk((await post()).json())


@pytest.mark.anyio
async def test_canned_switch_wins_over_a_key(monkeypatch, no_client):
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY)
    monkeypatch.setenv("FLIGHTMIND_ASK", "canned")
    assert endpoint.agent_enabled() is False
    assert is_canned_squawk((await post()).json())


def test_agent_is_on_only_with_the_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY)
    assert endpoint.agent_enabled() is True
    monkeypatch.setenv("FLIGHTMIND_ASK", "agent")
    assert endpoint.agent_enabled() is True


def test_make_client_uses_the_key_explicitly_with_limits(monkeypatch):
    seen = {}

    class Spy:
        def __init__(self, **kwargs):
            seen.update(kwargs)

    monkeypatch.setattr(anthropic, "AsyncAnthropic", Spy)
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY)
    endpoint.make_client()
    assert seen == {"api_key": FAKE_KEY, "timeout": 20.0, "max_retries": 1}


# --- the agent through /api/ask -------------------------------------------------------

@pytest.mark.anyio
async def test_agent_answer_comes_through_the_endpoint(agent_on):
    agent_on.fake = FakeAnthropic(good_script())
    r = await post("How long did LNI456 hold?")
    body = r.json()
    assert r.status_code == 200 and body["status"] == "ok"
    assert body["answer_md"] == "LNI456 held. [holding LNI456]"
    assert body["citations"] == [{"kind": "event", "id": HOLD["id"], "label": "holding LNI456"}]
    check_ask_response(body)
    assert len(agent_on.fake.calls) == 2
    assert "usage" not in body and "input_tokens" not in json.dumps(body)


@pytest.mark.anyio
async def test_question_over_500_characters_is_422_with_no_model_call(agent_on):
    r = await post("x" * 501)
    assert r.status_code == 422 and "500" in r.json()["detail"]
    assert agent_on.fake.calls == []
    agent_on.fake = FakeAnthropic([final_turn("not_enough_evidence", [])])
    assert (await post("x" * 500)).status_code == 200


def claude_errors():
    def resp(code):
        return httpx.Response(code, request=REQ)

    msg = f"leaked {FAKE_KEY}"
    return [
        anthropic.AuthenticationError(msg, response=resp(401), body=None),
        anthropic.RateLimitError(msg, response=resp(429), body=None),
        anthropic.APITimeoutError(request=REQ),
        anthropic.APIConnectionError(message=msg, request=REQ),
        anthropic.InternalServerError(msg, response=resp(500), body=None),
    ]


@pytest.mark.anyio
@pytest.mark.parametrize("error", claude_errors(), ids=lambda e: type(e).__name__)
async def test_claude_errors_give_not_enough_evidence_without_the_key(agent_on, caplog, error):
    caplog.set_level("DEBUG")
    agent_on.fake = FakeAnthropic([error])
    r = await post()
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "not_enough_evidence" and body["citations"] == []
    assert body["tool_calls"] == [{"tool": "claude_api", "error": type(error).__name__}]
    check_ask_response(body)
    assert FAKE_KEY not in r.text and FAKE_KEY not in caplog.text
    assert type(error).__name__ in caplog.text


# --- guard through the endpoint -------------------------------------------------------

@pytest.mark.anyio
async def test_sixth_question_in_a_minute_is_429_without_a_model_call(agent_on):
    agent_on.fake = FakeAnthropic(repeat=final_turn("not_enough_evidence", []))
    for _ in range(5):
        assert (await post()).status_code == 200
    assert len(agent_on.fake.calls) == 5
    r = await post()
    assert r.status_code == 429 and "Too many" in r.json()["detail"]
    assert len(agent_on.fake.calls) == 5


@pytest.mark.anyio
async def test_x_forwarded_for_separates_clients(agent_on):
    agent_on.fake = FakeAnthropic(repeat=final_turn("not_enough_evidence", []))
    for _ in range(5):
        assert (await post(headers={"x-forwarded-for": "203.0.113.5, 10.0.0.1"})).status_code == 200
    assert (await post(headers={"x-forwarded-for": "203.0.113.5, 10.9.9.9"})).status_code == 429
    assert (await post(headers={"x-forwarded-for": "198.51.100.7"})).status_code == 200


@pytest.mark.anyio
async def test_daily_limit_through_the_endpoint(agent_on, monkeypatch):
    monkeypatch.setattr(app_mod, "_guard", AskGuard(per_minute=100, per_day=3, clock=lambda: 0.0))
    agent_on.fake = FakeAnthropic(repeat=final_turn("not_enough_evidence", []))
    codes = [(await post(headers={"x-forwarded-for": f"192.0.2.{i}"})).status_code for i in range(4)]
    assert codes == [200, 200, 200, 429]


@pytest.mark.anyio
async def test_canned_mode_is_never_limited(monkeypatch, no_client):
    monkeypatch.setattr(app_mod, "_guard", AskGuard(per_minute=1, per_day=1, clock=lambda: 0.0))
    assert [(await post()).status_code for _ in range(8)] == [200] * 8


# --- dependency lists -----------------------------------------------------------------

ROOT = Path(__file__).parents[3]
INTEL = ROOT / "services" / "intel"


def lines(path):
    return [l.strip().lower() for l in path.read_text(encoding="utf-8").splitlines()]


def test_dependency_lists_name_anthropic_and_httpx():
    anth = re.compile(r"^anthropic>=2\.14,<3$")
    for path in (INTEL / "requirements.txt", INTEL / "requirements-serve.txt"):
        assert any(anth.match(l) for l in lines(path)), path
    assert any(l.startswith("httpx>=") for l in lines(INTEL / "requirements-serve.txt"))
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    deps = re.search(r"^dependencies\s*=\s*\[(.*?)\]", pyproject, re.S | re.M).group(1)
    assert "anthropic>=2.14,<3" in deps and "httpx" in deps and "fastapi" in deps
