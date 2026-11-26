"""Tests for the evidence rule (SCRUM-36): what is kept, what is dropped, how it is rendered."""
import pytest

from agent.api_client import ApiClient
from agent.evidence import NOT_ENOUGH_TEXT, EvidenceSet, not_enough
from agent.tools import ToolResult, run_tool
from agent_fakes import check_ask_response
from mock_api.app import app as mock_app


def evidence_with(raw_refs=(), events=None):
    ev = EvidenceSet()
    events = events or {}
    ev.add(ToolResult(data={}, event_ids=list(events), raw_refs=list(raw_refs), event_labels=events))
    return ev


def cite(kind, id):
    return {"kind": kind, "id": id}


def ok(*claims):
    return {"status": "ok", "claims": list(claims)}


def test_valid_claim_is_kept_with_bracketed_label():
    ev = evidence_with(["rec01:5"])
    out = ev.render(ok({"text": "Altitude was 3000 ft.", "citations": [cite("cat021_record", "rec01:5")]}))
    assert out["status"] == "ok"
    assert out["answer_md"] == "Altitude was 3000 ft. [rec01:5]"
    assert out["citations"] == [{"kind": "cat021_record", "id": "rec01:5", "label": "rec01:5"}]
    check_ask_response(out)


def test_invalid_citation_is_dropped_and_logged(caplog):
    caplog.set_level("INFO", logger="flightmind.agent")
    ev = evidence_with(["rec01:5"])
    out = ev.render(ok({
        "text": "One fact.",
        "citations": [cite("cat021_record", "rec01:5"), cite("cat021_record", "rec01:999")],
    }))
    assert out["answer_md"] == "One fact. [rec01:5]"
    assert [c["id"] for c in out["citations"]] == ["rec01:5"]
    assert "rec01:999" in caplog.text and "Dropped invalid citation" in caplog.text


def test_only_invented_citations_gives_not_enough_evidence():
    ev = evidence_with(["rec01:5"])
    out = ev.render(ok({"text": "Invented.", "citations": [cite("cat021_record", "rec01:77")]}))
    assert out == not_enough([])
    assert out["status"] == "not_enough_evidence" and out["citations"] == []
    assert out["answer_md"] == NOT_ENOUGH_TEXT
    check_ask_response(out)


def test_kind_mismatch_is_dropped():
    ev = evidence_with(["rec01:5"], {"E1": "holding LNI456"})
    out = ev.render(ok(
        {"text": "Event id used as a record.", "citations": [cite("cat021_record", "E1")]},
        {"text": "Record id used as an event.", "citations": [cite("event", "rec01:5")]},
    ))
    assert out["status"] == "not_enough_evidence"


def test_claim_without_citations_is_dropped_but_others_stay():
    ev = evidence_with(["rec01:5"])
    out = ev.render(ok(
        {"text": "No source.", "citations": []},
        {"text": "With source.", "citations": [cite("cat021_record", "rec01:5")]},
    ))
    assert out["answer_md"] == "With source. [rec01:5]"


def test_event_label_is_type_and_callsign():
    ev = evidence_with([], {"E1": "holding LNI456"})
    out = ev.render(ok({"text": "LNI456 held.", "citations": [cite("event", "E1")]}))
    assert out["citations"] == [{"kind": "event", "id": "E1", "label": "holding LNI456"}]
    assert out["answer_md"] == "LNI456 held. [holding LNI456]"
    check_ask_response(out)


@pytest.mark.anyio
async def test_event_label_from_a_real_search_result():
    result = await run_tool(ApiClient(app=mock_app), "search_events", {"type": "holding"})
    ev = EvidenceSet()
    ev.add(result)
    (event_id,) = result.event_ids
    assert ev.label_for("event", event_id) == "holding LNI456"
    assert ev.label_for("cat021_record", event_id) is None


def test_citations_are_deduplicated_in_first_use_order():
    ev = evidence_with(["rec01:1", "rec01:2", "rec01:3"], {"E1": "go_around GIA123"})
    out = ev.render(ok(
        {"text": "A.", "citations": [cite("cat021_record", "rec01:2"), cite("event", "E1")]},
        {"text": "B.", "citations": [cite("cat021_record", "rec01:1"), cite("cat021_record", "rec01:2")]},
        {"text": "C.", "citations": [cite("cat021_record", "rec01:3"), cite("cat021_record", "rec01:3")]},
    ))
    assert [c["id"] for c in out["citations"]] == ["rec01:2", "E1", "rec01:1", "rec01:3"]
    assert out["answer_md"].splitlines() == [
        "A. [rec01:2] [go_around GIA123]",
        "B. [rec01:1] [rec01:2]",
        "C. [rec01:3]",
    ]
    check_ask_response(out)


def test_not_enough_evidence_status_or_no_claims_gives_fixed_response():
    ev = evidence_with(["rec01:5"])
    assert ev.render({"status": "not_enough_evidence", "claims": []})["status"] == "not_enough_evidence"
    assert ev.render({"status": "ok", "claims": []})["status"] == "not_enough_evidence"
    # A model that says not_enough_evidence but attaches a cited claim still gets no answer.
    sneaky = {"status": "not_enough_evidence", "claims": [
        {"text": "x", "citations": [cite("cat021_record", "rec01:5")]}]}
    assert ev.render(sneaky)["status"] == "not_enough_evidence"
    for bad in (None, "text", [], {"status": "ok"}, {"status": "ok", "claims": "x"}):
        assert ev.render(bad)["answer_md"] == NOT_ENOUGH_TEXT


def test_newline_in_claim_becomes_a_space_and_tool_calls_are_kept():
    ev = evidence_with(["rec01:5"])
    calls = [{"tool": "get_raw", "args": {"raw_ref": "rec01:5"}, "result_count": 1}]
    out = ev.render(ok({"text": "Line one\nline two", "citations": [cite("cat021_record", "rec01:5")]}), calls)
    assert out["answer_md"] == "Line one line two [rec01:5]"
    assert out["tool_calls"] == calls
    check_ask_response(out)


def test_error_results_expose_nothing():
    ev = EvidenceSet()
    ev.add(ToolResult(data={"error": "x"}, raw_refs=["rec01:5"], event_ids=["E1"], is_error=True))
    assert ev.label_for("cat021_record", "rec01:5") is None and ev.label_for("event", "E1") is None
