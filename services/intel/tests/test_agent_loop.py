"""Tests for the agent loop (SCRUM-36), with a fake Claude client. No network, no key."""
import json

import pytest

from agent import agent as agent_mod
from agent.agent import ANSWER_SCHEMA, SYSTEM_PROMPT, run_agent
from agent.api_client import ApiClient
from agent.evidence import NOT_ENOUGH_TEXT
from agent_fakes import (
    FakeAnthropic, check_ask_response, claim, final_turn, response, text_block,
    thinking_block, tool_turn, tool_use, usage,
)
from mock_api import data
from mock_api.app import app as mock_app

HOLD = next(e for e in data.EVENTS if e["type"] == "holding")
SEARCH_ALL = {"type": None, "airport": None, "since": None}


def api():
    return ApiClient(app=mock_app)


async def ask(fake, question="How long did LNI456 hold?", **kw):
    return await run_agent(fake, api(), question, **kw)


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def two_turn_script():
    return [
        response("tool_use", [
            thinking_block(),
            tool_use("tu_1", "search_events", {"type": "holding", "airport": None, "since": None}),
            tool_use("tu_2", "get_raw", {"raw_ref": HOLD["raw_refs"][0]}),
        ]),
        final_turn("ok", [
            claim("LNI456 held at 8000 ft.", ("event", HOLD["id"]), ("cat021_record", HOLD["raw_refs"][0])),
            claim("Invented claim.", ("cat021_record", "rec01:99999")),
        ]),
    ]


@pytest.mark.anyio
async def test_two_turn_run_returns_valid_ask_response():
    fake = FakeAnthropic(two_turn_script())
    out = await ask(fake)
    assert out["status"] == "ok"
    assert out["answer_md"] == f"LNI456 held at 8000 ft. [holding LNI456] [{HOLD['raw_refs'][0]}]"
    assert [c["kind"] for c in out["citations"]] == ["event", "cat021_record"]
    assert [t["tool"] for t in out["tool_calls"]] == ["search_events", "get_raw"]
    assert all(t["result_count"] == 1 for t in out["tool_calls"])
    check_ask_response(out)
    assert len(fake.calls) == 2


@pytest.mark.anyio
async def test_all_tool_results_of_one_turn_go_back_in_one_user_message():
    fake = FakeAnthropic(two_turn_script())
    await ask(fake)
    second = fake.calls[1]["messages"]
    assert [m["role"] for m in second] == ["user", "assistant", "user"]
    assert second[0]["content"] == "How long did LNI456 hold?"
    results = second[2]["content"]
    assert [r["tool_use_id"] for r in results] == ["tu_1", "tu_2"]
    assert all(r["type"] == "tool_result" and isinstance(r["content"], str) for r in results)
    assert json.loads(results[0]["content"])["count"] == 1
    # The assistant content goes back whole, thinking block first, unchanged.
    sent = second[1]["content"]
    assert [b.type for b in sent] == ["thinking", "tool_use", "tool_use"]


@pytest.mark.anyio
async def test_tool_failures_become_is_error_results_and_the_run_continues():
    fake = FakeAnthropic([
        tool_turn(
            tool_use("a", "get_track", {"icao24": "ZZZZZZ", "from": None, "to": None, "max_points": None}),
            tool_use("b", "get_raw", {"wrong": 1}),
            tool_use("c", "no_such_tool", {}),
        ),
        final_turn("not_enough_evidence", []),
    ])
    out = await ask(fake)
    results = fake.calls[1]["messages"][2]["content"]
    assert len(results) == 3 and all(r["is_error"] is True for r in results)
    assert "ZZZZZZ" in json.loads(results[0]["content"])["error"]
    assert [("error" in t) for t in out["tool_calls"]] == [True, True, True]
    assert out["status"] == "not_enough_evidence"


@pytest.mark.anyio
async def test_agent_default_max_points_is_filled_in():
    fake = FakeAnthropic([
        tool_turn(tool_use("a", "get_track", {"icao24": "8A1C07", "from": None, "to": None, "max_points": None})),
        final_turn("ok", []),
    ])
    await ask(fake)
    body = json.loads(fake.calls[1]["messages"][2]["content"][0]["content"])
    assert body["total_points"] == 90 and body["returned_points"] == 60


@pytest.mark.anyio
async def test_call_limit_of_six():
    fake = FakeAnthropic(repeat=tool_turn(tool_use("x", "search_events", SEARCH_ALL)))
    out = await ask(fake)
    assert len(fake.calls) == agent_mod.MAX_MODEL_CALLS == 6
    assert out["status"] == "not_enough_evidence" and out["answer_md"] == NOT_ENOUGH_TEXT


@pytest.mark.anyio
async def test_deadline_stops_before_the_next_call():
    clock = Clock()

    def advance(n):
        clock.t += 26.0  # the first call "takes" 26 seconds

    fake = FakeAnthropic(repeat=tool_turn(tool_use("x", "search_events", SEARCH_ALL)), on_call=advance)
    out = await ask(fake, clock=clock)
    assert len(fake.calls) == 1
    assert out["status"] == "not_enough_evidence"


@pytest.mark.anyio
async def test_per_call_timeout_never_exceeds_time_left():
    clock = Clock()

    def advance(n):
        clock.t += 10.0

    fake = FakeAnthropic(repeat=tool_turn(tool_use("x", "search_events", SEARCH_ALL)), on_call=advance)
    await ask(fake, clock=clock)
    assert [c["timeout"] for c in fake.calls] == [20.0, 15.0, 5.0]


@pytest.mark.anyio
@pytest.mark.parametrize("stop", ["max_tokens", "refusal", "pause_turn", "something_new"])
async def test_other_stop_reasons_give_not_enough_evidence(stop):
    fake = FakeAnthropic([response(stop, [text_block('{"status":"ok","claims":[]}')])])
    out = await ask(fake)
    assert out["status"] == "not_enough_evidence" and out["citations"] == []
    check_ask_response(out)


@pytest.mark.anyio
async def test_final_text_that_is_not_json_gives_not_enough_evidence():
    fake = FakeAnthropic([response("end_turn", [thinking_block(), text_block("not json")])])
    assert (await ask(fake))["status"] == "not_enough_evidence"


@pytest.mark.anyio
async def test_text_block_is_found_by_type_not_position():
    body = json.dumps({"status": "ok", "claims": [claim("x", ("event", HOLD["id"]))]})
    fake = FakeAnthropic([
        tool_turn(tool_use("a", "search_events", {"type": "holding", "airport": None, "since": None})),
        response("end_turn", [thinking_block(), text_block(body)]),
    ])
    assert (await ask(fake))["status"] == "ok"


@pytest.mark.anyio
async def test_question_over_500_characters_is_refused_before_any_call():
    fake = FakeAnthropic()
    with pytest.raises(ValueError):
        await ask(fake, "x" * 501)
    assert fake.calls == []
    await ask(FakeAnthropic([final_turn("not_enough_evidence", [])]), "x" * 500)


# --- request arguments ---------------------------------------------------------------

@pytest.mark.anyio
async def test_request_arguments():
    fake = FakeAnthropic(two_turn_script())
    await ask(fake)
    first = fake.calls[0]
    for forbidden in ("thinking", "temperature", "top_p", "top_k", "budget_tokens", "tool_choice", "output_format"):
        assert forbidden not in first, forbidden
    assert first["model"] == "claude-haiku-5-5"
    assert first["max_tokens"] == 4096
    assert first["cache_control"] == {"type": "ephemeral"}
    assert first["output_config"] == {
        "effort": "medium",
        "format": {"type": "json_schema", "schema": ANSWER_SCHEMA},
    }
    assert first["system"] == SYSTEM_PROMPT and isinstance(first["system"], str)
    assert first["messages"][0] == {"role": "user", "content": "How long did LNI456 hold?"}
    assert 0 < first["timeout"] <= 20.0
    assert [t["name"] for t in first["tools"]] == ["query_tracks", "search_events", "get_track", "get_raw"]
    assert all(t["strict"] is True and t["input_schema"]["additionalProperties"] is False for t in first["tools"])


@pytest.mark.anyio
async def test_system_prompt_and_tools_are_identical_across_calls_and_runs():
    one, two = FakeAnthropic(two_turn_script()), FakeAnthropic(two_turn_script())
    await ask(one)
    await ask(two, "A different question?")
    serial = [json.dumps([c["system"], c["tools"], c["output_config"]]) for c in one.calls + two.calls]
    assert len(set(serial)) == 1


@pytest.mark.anyio
async def test_model_from_environment_and_argument(monkeypatch):
    monkeypatch.setenv("FLIGHTMIND_LLM_MODEL", "claude-opus-5-5")
    fake = FakeAnthropic([final_turn("not_enough_evidence", [])])
    await ask(fake)
    assert fake.calls[0]["model"] == "claude-opus-5-5"
    fake = FakeAnthropic([final_turn("not_enough_evidence", [])])
    await ask(fake, model="some-other-model")
    assert fake.calls[0]["model"] == "some-other-model"


def test_answer_schema_obeys_strict_limits():
    banned = {"minimum", "maximum", "multipleOf", "minLength", "maxLength", "$ref"}

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"])
            assert not banned & set(node)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(ANSWER_SCHEMA)
    assert ANSWER_SCHEMA["properties"]["status"]["enum"] == ["ok", "not_enough_evidence"]
    cite = ANSWER_SCHEMA["properties"]["claims"]["items"]["properties"]["citations"]["items"]
    assert cite["properties"]["kind"]["enum"] == ["cat021_record", "event"]


def test_system_prompt_states_the_rules_and_has_no_timestamp():
    text = SYSTEM_PROMPT.lower()
    for needle in ("not_enough_evidence", "exact", "cite", "about event", "query_tracks", "search_events",
                   "get_track", "get_raw", "never build"):
        assert needle in text, needle
    assert "2026" not in text


# --- logging -------------------------------------------------------------------------

@pytest.mark.anyio
async def test_usage_and_summary_lines_are_logged(caplog):
    caplog.set_level("INFO", logger="flightmind.agent")
    script = two_turn_script()
    script[0].usage = usage(1000, 50, 800, 0)
    script[1].usage = usage(1200, 80, 0, 800)
    fake = FakeAnthropic(script)
    out = await ask(fake)
    lines = [r.getMessage() for r in caplog.records if r.name == "flightmind.agent"]
    usage_lines = [l for l in lines if l.startswith("usage ")]
    summary = [l for l in lines if l.startswith("summary ")]
    assert len(usage_lines) == 2 and len(summary) == 1
    assert "model=claude-haiku-5-5" in usage_lines[0]
    assert "input_tokens=1000 output_tokens=50 cache_creation_input_tokens=800 cache_read_input_tokens=0" in usage_lines[0]
    assert "cache_read_input_tokens=800" in usage_lines[1]
    s = summary[0]
    assert "model_calls=2" in s and "tool_calls=2" in s and "input_tokens=2200" in s
    assert "output_tokens=130" in s and "cache_creation_input_tokens=800" in s and "elapsed_s=" in s
    assert "input_tokens" not in json.dumps(out)
    assert "8A1C07" not in " ".join(lines)
