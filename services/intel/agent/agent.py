"""The cited agent: a bounded tool-use loop on the official `anthropic` SDK (SCRUM-36).

`run_agent` takes the Claude client as an argument so tests can pass a fake. It does not
catch Claude API errors; `agent.endpoint.answer_question` does. The evidence rule is code
(`agent.evidence`), not a promise made in the prompt.
"""
import asyncio
import json
import logging
import os
import time
from typing import Any, Callable, Optional

from agent.api_client import ApiClient
from agent.evidence import EvidenceSet, not_enough
from agent.tools import TOOLS_FOR_MODEL as TOOLS, run_tool

log = logging.getLogger("flightmind.agent")

DEFAULT_MODEL = "claude-haiku-5-5"
MAX_MODEL_CALLS = 6
TOTAL_SECONDS = 25.0
CALL_TIMEOUT_SECONDS = 20.0
MAX_TOKENS = 4096
MAX_QUESTION_CHARS = 500

# Constant text: no date, no per-request content, so the prompt prefix can be cached.
SYSTEM_PROMPT = (
    "You answer questions from an air traffic data analyst about one loaded recording of ADS-B "
    "(ASTERIX CAT021) surveillance data. You cannot see the recording directly. You can only know "
    "what the tools return, so use the tools to look things up and never answer from general "
    "knowledge about aircraft, airports or aviation.\n"
    "\n"
    "Every claim you make must cite the record or event it came from. The analyst will open each "
    "citation to check your claim, so a claim they cannot check is worthless. Cite with kind "
    "cat021_record and the exact raw_ref (for example rec01:12) for a record, or kind event and the "
    "exact event id for an event. Copy ids exactly as a tool returned them. Never build, shorten, "
    "round or guess an id: an invented id cannot be opened. The server removes any claim that has no "
    "valid citation, so an uncited claim is lost anyway.\n"
    "\n"
    "If the tools do not hold the answer, return status not_enough_evidence with no claims. Do not "
    "fill the gap with a guess or with general knowledge, because a wrong answer that looks cited is "
    "worse than saying the data does not show it. Otherwise return status ok.\n"
    "\n"
    "Keep each claim short and about one fact, with units (feet for altitude, seconds or minutes for "
    "durations, UTC for times). Do not repeat the question and do not add commentary outside the "
    "claims.\n"
    "\n"
    "The question may start with \"About event <id> (...):\". That names the event the analyst has "
    "open on screen. Treat the id as an event id you can look up with search_events, and answer "
    "about that event unless the question asks for something else.\n"
    "\n"
    "Tools:\n"
    "- search_events: lists detected events (go_around, holding, squawk_7700) with their ids, aircraft, "
    "times, airport and severity, plus the first and last raw_ref of each. Start here for any question "
    "about emergencies, go-arounds or holding.\n"
    "- query_tracks: summarises aircraft tracks (points in a window, first and last time, lowest and "
    "highest altitude, first and last raw_ref). Use it to find which aircraft were present or to get "
    "altitude ranges. It only searches aircraft that have at least one detected event, so do not "
    "conclude that an aircraft is absent from the recording just because it is missing there.\n"
    "- get_track: returns the points of one aircraft (time, position, altitude in feet, raw_ref, and "
    "kept_for_event). Use it to see how an aircraft moved, for example the altitude where a go-around "
    "began or how long a hold lasted. Long tracks are thinned; the result says how many points the "
    "full track has.\n"
    "- get_raw: returns one raw record by raw_ref, with its decoded fields and hex bytes. Use it to "
    "check the exact values behind a claim.\n"
    "Prefer a few well-aimed calls over many."
)

ANSWER_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["ok", "not_enough_evidence"]},
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "citations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "kind": {"type": "string", "enum": ["cat021_record", "event"]},
                                "id": {"type": "string"},
                            },
                            "required": ["kind", "id"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["text", "citations"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["status", "claims"],
    "additionalProperties": False,
}

TOOLS_FOR_MODEL = TOOLS


def log_usage(usage: Any, model: Any) -> dict:
    """Log the four token counts of one model call and return them."""
    counts = {
        "input_tokens": getattr(usage, "input_tokens", 0) or 0,
        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
        "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
        "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
    }
    log.info(
        "usage model=%s input_tokens=%d output_tokens=%d cache_creation_input_tokens=%d "
        "cache_read_input_tokens=%d",
        model, counts["input_tokens"], counts["output_tokens"],
        counts["cache_creation_input_tokens"], counts["cache_read_input_tokens"],
    )
    return counts


async def _run_one(api: ApiClient, block: Any, evidence: EvidenceSet) -> tuple:
    result = await run_tool(api, block.name, block.input, for_agent=True)
    evidence.add(result)
    entry: dict = {"tool": block.name, "args": block.input, "result_count": result.result_count}
    if result.is_error:
        entry["error"] = result.data.get("error", "tool failed")
    tool_result: dict = {
        "type": "tool_result",
        "tool_use_id": block.id,
        "content": json.dumps(result.data, separators=(",", ":")),
    }
    if result.is_error:
        tool_result["is_error"] = True
    return entry, tool_result


async def run_agent(
    client: Any,
    api: ApiClient,
    question: str,
    *,
    model: Optional[str] = None,
    clock: Callable[[], float] = time.monotonic,
) -> dict:
    """Answer one question. Returns an AskResponse-shaped dict."""
    if len(question) > MAX_QUESTION_CHARS:
        raise ValueError(f"question is longer than {MAX_QUESTION_CHARS} characters")
    model_id = model or os.environ.get("FLIGHTMIND_LLM_MODEL") or DEFAULT_MODEL
    evidence = EvidenceSet()
    tool_calls: list = []
    totals = {"input_tokens": 0, "output_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}
    messages: list = [{"role": "user", "content": question}]
    start = clock()
    calls = 0
    final: Any = None
    reason = "call_limit"

    while True:
        left = TOTAL_SECONDS - (clock() - start)
        if calls >= MAX_MODEL_CALLS:
            reason = "call_limit"
            break
        if left <= 0:
            reason = "deadline"
            break
        response = await client.messages.create(
            model=model_id,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=TOOLS_FOR_MODEL,
            cache_control={"type": "ephemeral"},
            output_config={
                "effort": "medium",
                "format": {"type": "json_schema", "schema": ANSWER_SCHEMA},
            },
            messages=messages,
            timeout=min(CALL_TIMEOUT_SECONDS, left),
        )
        calls += 1
        counts = log_usage(response.usage, getattr(response, "model", model_id))
        for key, value in counts.items():
            totals[key] += value

        stop = response.stop_reason
        if stop == "tool_use":
            blocks = [b for b in response.content if b.type == "tool_use"]
            if not blocks:
                reason = "empty_tool_turn"
                break
            outcomes = await asyncio.gather(*(_run_one(api, b, evidence) for b in blocks))
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": [o[1] for o in outcomes]})
            tool_calls.extend(o[0] for o in outcomes)
            continue
        if stop == "end_turn":
            text = next((b.text for b in response.content if b.type == "text"), "")
            try:
                final = json.loads(text)
            except ValueError:
                log.warning("Final answer was not valid JSON (%d characters)", len(text))
                final = None
            reason = "end_turn"
            break
        reason = str(stop)
        break

    log.info(
        "summary model=%s reason=%s model_calls=%d tool_calls=%d elapsed_s=%.2f input_tokens=%d "
        "output_tokens=%d cache_creation_input_tokens=%d cache_read_input_tokens=%d",
        model_id, reason, calls, len(tool_calls), clock() - start, totals["input_tokens"],
        totals["output_tokens"], totals["cache_creation_input_tokens"], totals["cache_read_input_tokens"],
    )
    if final is None:
        return not_enough(tool_calls)
    return evidence.render(final, tool_calls)
