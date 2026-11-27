"""Mock FlightMind API (SCRUM-33): serves contracts/openapi.yaml from synthetic data.

Run from services/intel:
    uvicorn mock_api.app:app --port 8000
"""
import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent.endpoint import agent_enabled, answer_question
from agent.guard import AskGuard, client_key

from . import data, uploads

app = FastAPI(title="FlightMind mock API", version="1.2.0")

_guard = AskGuard()  # only used when the cited agent is on (SCRUM-36)

# Mock only: lets the web UI on another local port call it. The real API (SCRUM-37)
# should restrict origins.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(uploads.router)  # recording upload flow (SCRUM-62)


def _has_sample(recording: Optional[str]) -> bool:
    """True when the ?recording= filter selects the sample dataset.

    No filter or rec01 is the sample. A ready upload also serves the sample, because the
    mock never decodes the bytes sent. Any other id has no data yet.
    """
    return recording is None or recording == data.RECORDING_ID or uploads.is_ready(recording)


def _parse(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _ts(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _track_slice(icao24: str, start: Optional[datetime], end: Optional[datetime]):
    track = data.TRACKS.get(icao24.upper())
    if track is None:
        raise HTTPException(status_code=404, detail="Unknown icao24")
    points = [
        p for p in track["points"]
        if (start is None or _ts(p["ts"]) >= start) and (end is None or _ts(p["ts"]) <= end)
    ]
    return {**track, "points": points}


@app.get("/api/meta")
def meta():
    return {
        "mode": "replay",
        "sim_time": data.SIM_TIME,
        "recordings": [data.RECORDING_ID, *uploads.ready_ids()],
        "airports": [data.AIRPORT],
    }


@app.get("/api/events")
def events(
    since: Optional[datetime] = None,
    type: Optional[str] = None,
    airport: Optional[str] = None,
    recording: Optional[str] = None,
):
    if not _has_sample(recording):
        return []
    since = _parse(since)
    out = data.EVENTS
    if since is not None:
        out = [e for e in out if _ts(e["start_ts"]) >= since]
    if type:
        out = [e for e in out if e["type"] == type]
    if airport:
        out = [e for e in out if e["airport"] == airport]
    return out


@app.get("/api/events/{event_id}")
def event_detail(event_id: str):
    event = data.EVENTS_BY_ID.get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Unknown event id")
    similar = [e for e in data.EVENTS if e["type"] == event["type"] and e["id"] != event["id"]]
    return {**event, "track": _track_slice(event["icao24"], None, None), "similar": similar}


@app.get("/api/tracks/{icao24}")
def track(
    icao24: str,
    from_: Optional[datetime] = Query(None, alias="from"),
    to: Optional[datetime] = None,
    recording: Optional[str] = None,
):
    if not _has_sample(recording):
        raise HTTPException(status_code=404, detail="Unknown icao24")
    return _track_slice(icao24, _parse(from_), _parse(to))


@app.get("/api/raw/{raw_ref}")
def raw(raw_ref: str):
    record = data.RAW.get(raw_ref)
    if record is None:
        raise HTTPException(status_code=404, detail="Unknown raw_ref")
    return record


@app.get("/api/compression/{recording_id}")
def compression(recording_id: str):
    report = data.COMPRESSION.get(recording_id)
    if report is None and uploads.is_ready(recording_id):
        report = {**data.COMPRESSION[data.RECORDING_ID], "recording_id": recording_id}
    if report is None:
        raise HTTPException(status_code=404, detail="Unknown recording_id")
    if report["raw_bytes"] == 0:
        raise HTTPException(status_code=404, detail=f"Recording '{recording_id}' has no data yet.")
    return report


@app.get("/api/stream")
async def stream(recording: Optional[str] = None):
    """Finite replay of the sample recording as server-sent events.

    The contract does not define the payload. The web UI does not use this endpoint
    (web-ui requirements, note 6: "Replay is the scrubber"), so this shape is our own
    assumption and nothing depends on it: `event: position` carries
    {icao24, callsign, ts, lat, lon, alt_ft, raw_ref} and `event: event` carries an
    Event object, emitted at the event's end_ts. Define it in the contract first if a
    consumer ever needs it.
    """
    delay = float(os.environ.get("MOCK_STREAM_DELAY", "0.05"))
    items = []
    tracks = data.TRACKS.values() if _has_sample(recording) else []
    events = data.EVENTS if _has_sample(recording) else []
    for t in tracks:
        for p in t["points"]:
            items.append((p["ts"], "position", {"icao24": t["icao24"], "callsign": t["callsign"], **p}))
    for e in events:
        items.append((e["end_ts"], "event", e))
    items.sort(key=lambda x: x[0])

    async def gen():
        for _, name, payload in items:
            yield f"event: {name}\ndata: {json.dumps(payload)}\n\n"
            await asyncio.sleep(delay)

    return StreamingResponse(gen(), media_type="text/event-stream")


class AskRequest(BaseModel):
    question: str
    recording_id: Optional[str] = None


def _first_ref(event):
    return event["raw_refs"][0]


@app.post("/api/ask")
async def ask(body: AskRequest, request: Request):
    """Cited agent when ANTHROPIC_API_KEY is set (SCRUM-36); otherwise canned answers by keyword.

    The agent does not read recording_id yet: it always answers from the default recording.
    """
    if agent_enabled():
        if len(body.question) > 500:
            raise HTTPException(status_code=422, detail="Question is longer than 500 characters.")
        host = request.client.host if request.client else None
        if not _guard.check(client_key(request.headers, host)):
            raise HTTPException(status_code=429, detail="Too many questions. Try again in a minute.")
        return await answer_question(body.question, request.app)
    q = body.question.lower()
    if not _has_sample(body.recording_id):
        q = ""  # nothing loaded for that recording, so no keyword can match
    if any(w in q for w in ("7700", "emergency", "squawk", "mayday")):
        etype = "squawk_7700"
    elif "go-around" in q or "go around" in q or "goaround" in q:
        etype = "go_around"
    elif "hold" in q:
        etype = "holding"
    else:
        return {
            "answer_md": "Not enough evidence in the loaded recording to answer that.",
            "citations": [],
            "tool_calls": [{"tool": "search_events", "args": {"query": body.question}, "result_count": 0}],
            "status": "not_enough_evidence",
        }

    found = [e for e in data.EVENTS if e["type"] == etype]
    citations, lines = [], []
    for e in found:
        label = f"{etype} {e['callsign']} ({e['icao24']})"
        citations.append({"kind": "event", "id": e["id"], "label": label})
        citations.append({"kind": "cat021_record", "id": _first_ref(e), "label": f"first record of {label}"})
        lines.append(f"- {label} from {e['start_ts']} to {e['end_ts']} [{len(e['raw_refs'])} records]")
    return {
        "answer_md": f"Found {len(found)} `{etype}` event(s) in the recording:\n" + "\n".join(lines),
        "citations": citations,
        "tool_calls": [{"tool": "search_events", "args": {"type": etype}, "result_count": len(found)}],
        "status": "ok",
    }
