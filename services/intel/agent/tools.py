"""The four tools shared by the cited agent and the MCP server (SCRUM-36).

Each tool is a plain async function over an `ApiClient` that returns a `ToolResult`: the
JSON-serialisable data plus the evidence ids (event ids and raw_refs) the data exposed.
The agent may cite only ids that were exposed by a tool result. No tool reads system time
or writes anything. A failure is a `ToolResult` with `is_error=True`, never an exception.
"""
import asyncio
import copy
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

from agent.api_client import ApiClient, ApiError

MAX_POINTS_CAP = 200
AGENT_DEFAULT_MAX_POINTS = 60
MAX_CANDIDATES = 20  # aircraft query_tracks fetches per call
MAX_IN_FLIGHT = 5  # track requests running at once


@dataclass
class ToolResult:
    data: Any
    event_ids: list = field(default_factory=list)
    raw_refs: list = field(default_factory=list)
    is_error: bool = False
    result_count: int = 0
    event_labels: dict = field(default_factory=dict)


def _error(message: str) -> ToolResult:
    return ToolResult(data={"error": message}, is_error=True)


# --- search_events ---------------------------------------------------------------------

async def search_events(
    api: ApiClient,
    type: Optional[str] = None,
    airport: Optional[str] = None,
    since: Optional[str] = None,
) -> ToolResult:
    try:
        events = await api.events(since=since, type=type, airport=airport)
    except ApiError as exc:
        return _error(str(exc))
    rows, event_ids, raw_refs, labels = [], [], [], {}
    for e in events:
        refs = e.get("raw_refs") or []
        first = refs[0] if refs else None
        last = refs[-1] if refs else None
        rows.append({
            "id": e.get("id"),
            "type": e.get("type"),
            "icao24": e.get("icao24"),
            "callsign": e.get("callsign"),
            "start_ts": e.get("start_ts"),
            "end_ts": e.get("end_ts"),
            "airport": e.get("airport"),
            "severity": e.get("severity"),
            "raw_ref_count": len(refs),
            "first_raw_ref": first,
            "last_raw_ref": last,
        })
        event_ids.append(e.get("id"))
        labels[e.get("id")] = f"{e.get('type')} {e.get('callsign') or e.get('icao24')}"
        raw_refs.extend(r for r in (first, last) if r)
    return ToolResult(
        data={"count": len(rows), "events": rows},
        event_ids=event_ids,
        raw_refs=raw_refs,
        result_count=len(rows),
        event_labels=labels,
    )


# --- get_track -------------------------------------------------------------------------

def _even_sample(indexes: list, k: int) -> list:
    """Pick k items spread evenly over `indexes` (k <= len(indexes))."""
    m = len(indexes)
    if k <= 0:
        return []
    if k >= m:
        return list(indexes)
    if k == 1:
        return [indexes[m // 2]]
    return [indexes[round(j * (m - 1) / (k - 1))] for j in range(k)]


def thin_points(points: list, max_points: int) -> list:
    """Keep first, last and event points first, then fill with an even sample of the rest."""
    cap = max(2, min(int(max_points), MAX_POINTS_CAP))
    n = len(points)
    if n <= cap:
        return list(points)
    must = {0, n - 1}
    event_idx = [i for i, p in enumerate(points) if p.get("kept_for_event") and i not in must]
    slots = cap - len(must)
    if len(event_idx) >= slots:
        keep = must | set(_even_sample(event_idx, slots))
    else:
        keep = must | set(event_idx)
        others = [i for i in range(n) if i not in keep]
        keep |= set(_even_sample(others, slots - len(event_idx)))
    return [points[i] for i in sorted(keep)]


async def get_track(
    api: ApiClient,
    icao24: str,
    from_: Optional[str] = None,
    to: Optional[str] = None,
    max_points: Optional[int] = None,
) -> ToolResult:
    try:
        body = await api.track(icao24, from_, to)
    except ApiError as exc:
        return _error(str(exc))
    points = body.get("points") or []
    if max_points is None:
        data = body  # unchanged, as the API sent it
    else:
        kept = thin_points(points, max_points)
        data = {
            **{k: v for k, v in body.items() if k != "points"},
            "points": kept,
            "total_points": len(points),
            "returned_points": len(kept),
            "thinned": len(kept) < len(points),
        }
    shown = data.get("points") or []
    return ToolResult(
        data=data,
        raw_refs=[p["raw_ref"] for p in shown if p.get("raw_ref")],
        result_count=len(shown),
    )


# --- query_tracks ----------------------------------------------------------------------

async def query_tracks(
    api: ApiClient,
    callsign: Optional[str] = None,
    icao24: Optional[str] = None,
    from_: Optional[str] = None,
    to: Optional[str] = None,
) -> ToolResult:
    try:
        events = await api.events()
    except ApiError as exc:
        return _error(str(exc))
    candidates: dict = {}
    for e in events:
        key = (e.get("icao24") or "").upper()
        if key and key not in candidates:
            candidates[key] = e.get("callsign")
    if icao24:
        want = icao24.strip().upper()
        candidates = {k: v for k, v in candidates.items() if k == want}
    if callsign:
        want_cs = callsign.strip().upper()
        candidates = {k: v for k, v in candidates.items() if (v or "").upper() == want_cs}

    candidates_total = len(candidates)
    ids = list(candidates)[:MAX_CANDIDATES]
    gate = asyncio.Semaphore(MAX_IN_FLIGHT)

    async def fetch(ident: str):
        async with gate:
            return await api.track(ident, from_, to)

    results = await asyncio.gather(*(fetch(i) for i in ids), return_exceptions=True)
    summaries, raw_refs, skipped = [], [], []
    for ident, res in zip(ids, results):
        if isinstance(res, ApiError):
            if str(res).startswith("No aircraft"):
                skipped.append(ident)
                continue
            return _error(str(res))
        if isinstance(res, BaseException):
            raise res
        pts = res.get("points") or []
        if not pts:
            continue
        with_alt = [p for p in pts if p.get("alt_ft") is not None]
        # min()/max() return the first point holding the extreme value.
        low = min(with_alt, key=lambda p: p["alt_ft"]) if with_alt else None
        high = max(with_alt, key=lambda p: p["alt_ft"]) if with_alt else None
        first, last = pts[0], pts[-1]
        min_ref = low.get("raw_ref") if low else None
        max_ref = high.get("raw_ref") if high else None
        summaries.append({
            "icao24": res.get("icao24", ident),
            "callsign": res.get("callsign", candidates[ident]),
            "points_in_window": len(pts),
            "first_ts": first.get("ts"),
            "last_ts": last.get("ts"),
            "min_alt_ft": low["alt_ft"] if low else None,
            "max_alt_ft": high["alt_ft"] if high else None,
            "first_raw_ref": first.get("raw_ref"),
            "last_raw_ref": last.get("raw_ref"),
            "min_alt_raw_ref": min_ref,
            "max_alt_raw_ref": max_ref,
        })
        raw_refs.extend(dict.fromkeys(r for r in (first.get("raw_ref"), last.get("raw_ref"), min_ref, max_ref) if r))
    data: dict = {"count": len(summaries), "aircraft": summaries}
    if candidates_total > len(ids):
        data["truncated"] = True
        data["candidates_total"] = candidates_total
    if skipped:
        data["skipped"] = skipped
    return ToolResult(data=data, raw_refs=raw_refs, result_count=len(summaries))

# --- get_raw ---------------------------------------------------------------------------

async def get_raw(api: ApiClient, raw_ref: str) -> ToolResult:
    try:
        body = await api.raw(raw_ref)
    except ApiError as exc:
        return _error(str(exc))
    ref = body.get("raw_ref") or raw_ref.strip()
    return ToolResult(data=body, raw_refs=[ref], result_count=1)


# --- registry --------------------------------------------------------------------------

@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    properties: dict  # JSON Schema property dicts; types are "string" or "integer"
    required: tuple
    run: Callable[..., Awaitable[ToolResult]]


def _prop(kind: str, description: str) -> dict:
    return {"type": kind, "description": description}


_TIME_NOTE = "ISO 8601 date-time such as 2026-11-12T08:00:00Z"

TOOL_SPECS: list = [
    ToolSpec(
        name="query_tracks",
        description=(
            "Summarise the tracks of aircraft in the recording: for each aircraft, how many points "
            "it has in the time window, its first and last time, its lowest and highest altitude in "
            "feet, and the first and last raw_ref. It also gives min_alt_raw_ref and max_alt_raw_ref, the records where the lowest and highest altitude occur: cite those for any claim about an altitude extreme, never first_raw_ref or last_raw_ref. Use it to find which aircraft were present, or "
            "how long or how high one flew, before fetching a full track. Filter by callsign or "
            "icao24, and optionally by a time window. Only aircraft that have at least one detected "
            "event are searched, because the API has no list of aircraft; an aircraft missing from "
            "the result may still exist. At most 20 aircraft are searched; when the result has truncated true, candidates_total says how many matched, so repeat the call with callsign or icao24 to narrow it. Cite the raw_ref values from the result for any claim."
        ),
        properties={
            "callsign": _prop("string", "Callsign to match exactly, case-insensitive, e.g. LNI456"),
            "icao24": _prop("string", "6-character hex Mode S address, e.g. 8A0F21"),
            "from": _prop("string", "Start of the time window, " + _TIME_NOTE),
            "to": _prop("string", "End of the time window, " + _TIME_NOTE),
        },
        required=(),
        run=query_tracks,
    ),
    ToolSpec(
        name="search_events",
        description=(
            "List detected events in the recording: go_around, holding, squawk_7500 (unlawful interference), squawk_7600 (radio failure) and squawk_7700 (general emergency). "
            "Each event has an id, type, aircraft, start and end time, airport, severity, the number "
            "of records behind it, and its first and last raw_ref. Use it first for questions about "
            "emergencies, go-arounds or holding. Cite the event id, or a raw_ref, for any claim."
        ),
        properties={
            "type": _prop("string", "Event type: go_around, holding, squawk_7500, squawk_7600 or squawk_7700"),
            "airport": _prop("string", "Airport code, e.g. WIII"),
            "since": _prop("string", "Only events starting at or after this time, " + _TIME_NOTE),
        },
        required=(),
        run=search_events,
    ),
    ToolSpec(
        name="get_track",
        description=(
            "Get the 4D track (time, latitude, longitude, altitude in feet) of one aircraft. icao24 is "
            "the 6-character hex Mode S address, for example 8A0F21. from and to are optional ISO 8601 "
            "date-times, for example 2026-11-12T08:00:00Z. Every point has a raw_ref "
            "(<recording_file_id>:<record_index>) that must be cited for any claim made from that "
            "point, and kept_for_event marks points that belong to a detected event. max_points "
            "(2 to 200) thins long tracks evenly while always keeping the first, last and event "
            "points; the result says how many points the full track has."
        ),
        properties={
            "icao24": _prop("string", "6-character hex aircraft address, e.g. 8A0F21"),
            "from": _prop("string", "Optional start time, " + _TIME_NOTE),
            "to": _prop("string", "Optional end time, " + _TIME_NOTE),
            "max_points": _prop("integer", "Optional cap on returned points, 2 to 200"),
        },
        required=("icao24",),
        run=get_track,
    ),
    ToolSpec(
        name="get_raw",
        description=(
            "Get one raw CAT021 record by its raw_ref (for example rec01:12): the decoded fields and "
            "the record's hex bytes. Use it to check the exact values behind a claim, such as the "
            "squawk or altitude at one moment. Cite the raw_ref for any claim made from it."
        ),
        properties={"raw_ref": _prop("string", "Record id from a tool result, <recording_file_id>:<record_index>")},
        required=("raw_ref",),
        run=get_raw,
    ),
]

SPECS_BY_NAME = {s.name: s for s in TOOL_SPECS}


def mcp_schema(spec: ToolSpec) -> dict:
    """Plain input schema: optional properties are simply not required."""
    return {
        "type": "object",
        "properties": copy.deepcopy(spec.properties),
        "required": list(spec.required),
    }


def model_tool(spec: ToolSpec) -> dict:
    """Strict tool definition for the Messages API: every property required, optional ones nullable."""
    props = {}
    for name, schema in spec.properties.items():
        if name in spec.required:
            props[name] = copy.deepcopy(schema)
        else:
            desc = schema["description"]
            props[name] = {
                "anyOf": [{"type": schema["type"]}, {"type": "null"}],
                "description": desc,
            }
    return {
        "name": spec.name,
        "description": spec.description,
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": props,
            "required": list(spec.properties),
            "additionalProperties": False,
        },
    }


# Built once at import time so the list is byte-stable between calls.
TOOLS_FOR_MODEL: list = [model_tool(s) for s in TOOL_SPECS]


def validate_args(spec: ToolSpec, args: Any) -> Optional[str]:
    """Return an error message, or None when `args` fits the tool's schema."""
    if not isinstance(args, dict):
        return "Tool arguments must be a JSON object."
    unknown = sorted(set(args) - set(spec.properties))
    if unknown:
        return f"Unknown argument(s) for {spec.name}: {', '.join(unknown)}."
    for name in spec.required:
        value = args.get(name)
        if not isinstance(value, str) or not value.strip():
            return f"Argument '{name}' is required and must be a non-empty string."
    for name, value in args.items():
        if value is None:
            continue
        kind = spec.properties[name]["type"]
        if kind == "string" and not isinstance(value, str):
            return f"Argument '{name}' must be a string."
        if kind == "integer" and (isinstance(value, bool) or not isinstance(value, int)):
            return f"Argument '{name}' must be an integer."
    return None


async def run_tool(api: ApiClient, name: str, args: Any, *, for_agent: bool = False) -> ToolResult:
    """Validate and run one tool. Never raises for bad input or API failures.

    The schema names are `from` and `to`; the functions take `from_`. With `for_agent`, a
    get_track call without max_points gets the agent default (60).
    """
    spec = SPECS_BY_NAME.get(name)
    if spec is None:
        return _error(f"Unknown tool '{name}'. Tools: {', '.join(SPECS_BY_NAME)}.")
    problem = validate_args(spec, args)
    if problem:
        return _error(problem)
    kwargs = {("from_" if k == "from" else k): v for k, v in args.items() if v is not None}
    if for_agent and name == "get_track" and "max_points" not in kwargs:
        kwargs["max_points"] = AGENT_DEFAULT_MAX_POINTS
    return await spec.run(api, **kwargs)
