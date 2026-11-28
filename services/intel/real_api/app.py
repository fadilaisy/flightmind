"""Real FlightMind API (SCRUM-37): contracts/openapi.yaml served from Postgres.

Run from services/intel with FLIGHTMIND_DSN set:
    uvicorn real_api.app:app --port 8000
or through serve.py with FLIGHTMIND_API_APP=real_api.app:app.

Tables come from contracts/schema.sql and are written by the pipeline
(services/pipeline, store.write_recording). Rows belong to a recording by the prefix of
their raw_ref, '<recording_id>:'; for events it is the first raw_ref. When a request has no
`recording`, the default is FLIGHTMIND_DEFAULT_RECORDING, else the recording ingested last.

Environment:
    FLIGHTMIND_DSN                 Postgres connection string (required)
    FLIGHTMIND_DEFAULT_RECORDING   recording used when a request names none
    FLIGHTMIND_REPORT_DIR          folder of the CLI's <id>.compression.json reports
                                   (default <repo>/data/reports)
    FLIGHTMIND_CORS_ORIGINS        comma-separated origins allowed to call the API from
                                   another origin; empty means same origin only
"""
import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent.endpoint import agent_enabled, answer_question
from agent.guard import AskGuard, client_key

from . import raw_file, uploads
from .db import connect, prefix_clause

REPO_ROOT = Path(__file__).resolve().parents[3]

@asynccontextmanager
async def _lifespan(_app):
    """Start the upload worker with the server (uvicorn, or serve.py, which passes startup on).

    When Postgres is not up yet (Docker Desktop still starting), startup goes on and the worker
    starts on the first upload request instead.
    """
    if os.environ.get("FLIGHTMIND_DSN", "").strip():
        try:
            uploads.ensure_worker()
        except Exception:
            logging.getLogger("flightmind.uploads").exception("upload worker not started; retrying on first upload")
    yield


app = FastAPI(title="FlightMind API", version="1.2.0", lifespan=_lifespan)
app.include_router(uploads.router)  # recording upload and the worker (SCRUM-64)
_guard = AskGuard()

_origins = [o.strip() for o in os.environ.get("FLIGHTMIND_CORS_ORIGINS", "").split(",") if o.strip()]
if _origins:
    app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_methods=["*"], allow_headers=["*"])


# ---------- helpers ----------

def _clock_now() -> datetime:
    """Current time for data: the shared clock (contract C6). services/pipeline is optional
    here (it needs Python 3.11+), so without it this is the wall clock, which is what the
    shared clock returns by default."""
    try:
        from flightmind_pipeline import clock
    except ImportError:
        return datetime.now(timezone.utc)
    return clock.now()


def iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def report_dir() -> Path:
    return Path(os.environ.get("FLIGHTMIND_REPORT_DIR") or REPO_ROOT / "data" / "reports")


def ready_files_sql(conn) -> str:
    """SELECT of recording_files rows that are ready: CLI loads, and uploads whose status is ready."""
    has_uploads = conn.execute("SELECT to_regclass('public.uploads') IS NOT NULL AS ok").fetchone()["ok"]
    if not has_uploads:
        return "SELECT f.* FROM recording_files f"
    return (
        "SELECT f.* FROM recording_files f LEFT JOIN uploads u ON u.id = f.id "
        "WHERE u.id IS NULL OR u.status = 'ready'"
    )


def default_recording(conn) -> Optional[str]:
    configured = os.environ.get("FLIGHTMIND_DEFAULT_RECORDING", "").strip()
    if configured:
        return configured
    row = conn.execute(f"SELECT id FROM ({ready_files_sql(conn)}) r ORDER BY ingested_at DESC, id LIMIT 1").fetchone()
    return row["id"] if row else None


def _resolve(conn, recording: Optional[str]) -> Optional[str]:
    return recording if recording else default_recording(conn)


def _event(row: dict) -> dict:
    out = {
        "id": str(row["id"]),
        "type": row["type"],
        "icao24": row["icao24"],
        "callsign": row["callsign"],
        "start_ts": iso(row["start_ts"]),
        "end_ts": iso(row["end_ts"]),
        "airport": row["airport"],
        "raw_refs": list(row["raw_refs"]),
    }
    if row["severity"] is not None:
        out["severity"] = row["severity"]
    return out


EVENT_COLUMNS = "id, type, icao24, callsign, start_ts, end_ts, airport, severity, raw_refs"
EVENT_SCOPE = "cardinality(raw_refs) > 0 AND " + prefix_clause("raw_refs[1]")


def _track(conn, recording: str, icao24: str, start: Optional[datetime], end: Optional[datetime]) -> dict:
    # The pipeline keeps the decoder's spelling, which mixes upper and lower case, so match either.
    scope = prefix_clause("raw_ref")
    found = conn.execute(
        f"SELECT icao24 FROM telemetry WHERE upper(icao24) = upper(%s) AND {scope} LIMIT 1",
        (icao24.strip(), recording, recording),
    ).fetchone()
    if found is None:
        raise HTTPException(status_code=404, detail="Unknown icao24")
    icao = found["icao24"]
    sql = (
        "SELECT ts, lat, lon, coalesce(baro_alt_ft, geo_alt_ft) AS alt_ft, raw_ref, callsign, "
        "'kept_for_event' = ANY(flags) AS kept "
        f"FROM telemetry WHERE icao24 = %s AND {scope} AND lat IS NOT NULL AND lon IS NOT NULL"
    )
    args: list = [icao, recording, recording]
    if start is not None:
        sql += " AND ts >= %s"
        args.append(start)
    if end is not None:
        sql += " AND ts <= %s"
        args.append(end)
    rows = conn.execute(sql + " ORDER BY ts, raw_ref", args).fetchall()
    callsign = next((r["callsign"].strip() for r in reversed(rows) if r["callsign"]), None)
    return {
        "icao24": icao,
        "callsign": callsign,
        "points": [
            {
                "ts": iso(r["ts"]),
                "lat": r["lat"],
                "lon": r["lon"],
                "alt_ft": r["alt_ft"],
                "raw_ref": r["raw_ref"],
                "kept_for_event": bool(r["kept"]),
            }
            for r in rows
        ],
    }


def load_report(conn, recording_id: str) -> Optional[dict]:
    """The pipeline's compression report: uploads.report for an upload, else the CLI's file."""
    has_uploads = conn.execute("SELECT to_regclass('public.uploads') IS NOT NULL AS ok").fetchone()["ok"]
    if has_uploads:
        row = conn.execute("SELECT report FROM uploads WHERE id = %s", (recording_id,)).fetchone()
        if row and row["report"]:
            return row["report"]
    path = report_dir() / f"{recording_id}.compression.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


# ---------- endpoints ----------

@app.get("/api/meta")
def meta():
    with connect() as conn:
        recordings = [r["id"] for r in conn.execute(f"SELECT id FROM ({ready_files_sql(conn)}) r ORDER BY ingested_at, id")]
        current = default_recording(conn)
        last = None
        if current:
            row = conn.execute("SELECT last_ts FROM recording_files WHERE id = %s", (current,)).fetchone()
            last = row["last_ts"] if row else None
        airports = [r["airport"] for r in conn.execute(
            "SELECT DISTINCT airport FROM events WHERE airport IS NOT NULL ORDER BY airport"
        )]
    return {
        "mode": "replay",
        "sim_time": iso(last) or iso(_clock_now()),
        "recordings": recordings,
        "airports": airports,
    }


@app.get("/api/events")
def events(
    since: Optional[datetime] = None,
    type: Optional[str] = None,
    airport: Optional[str] = None,
    recording: Optional[str] = None,
):
    with connect() as conn:
        rec = _resolve(conn, recording)
        if rec is None:
            return []
        sql = f"SELECT {EVENT_COLUMNS} FROM events WHERE {EVENT_SCOPE}"
        args: list = [rec, rec]
        if since is not None:
            sql += " AND start_ts >= %s"
            args.append(_utc(since))
        if type:
            sql += " AND type = %s"
            args.append(type)
        if airport:
            sql += " AND airport = %s"
            args.append(airport)
        rows = conn.execute(sql + " ORDER BY start_ts, id", args).fetchall()
    return [_event(r) for r in rows]


@app.get("/api/events/{event_id}")
def event_detail(event_id: str):
    try:
        uuid.UUID(event_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Unknown event id") from None
    with connect() as conn:
        row = conn.execute(f"SELECT {EVENT_COLUMNS} FROM events WHERE id = %s", (event_id,)).fetchone()
        if row is None or not row["raw_refs"]:
            raise HTTPException(status_code=404, detail="Unknown event id")
        rec = row["raw_refs"][0].split(":", 1)[0]
        try:
            track = _track(conn, rec, row["icao24"], None, None)
        except HTTPException:
            track = {"icao24": row["icao24"], "callsign": row["callsign"], "points": []}
        similar = conn.execute(
            f"SELECT {EVENT_COLUMNS} FROM events WHERE type = %s AND id <> %s ORDER BY start_ts LIMIT 5",
            (row["type"], row["id"]),
        ).fetchall()
    return {**_event(row), "track": track, "similar": [_event(s) for s in similar]}


@app.get("/api/tracks/{icao24}")
def track(
    icao24: str,
    from_: Optional[datetime] = Query(None, alias="from"),
    to: Optional[datetime] = None,
    recording: Optional[str] = None,
):
    with connect() as conn:
        rec = _resolve(conn, recording)
        if rec is None:
            raise HTTPException(status_code=404, detail="Unknown icao24")
        return _track(conn, rec, icao24, _utc(from_), _utc(to))


@app.get("/api/raw/{raw_ref}")
def raw(raw_ref: str):
    rec, sep, index_text = raw_ref.rpartition(":")
    if not sep or not rec or not index_text.isdigit() or int(index_text) < 1:
        raise HTTPException(status_code=404, detail="Unknown raw_ref")
    index = int(index_text)
    with connect() as conn:
        file_row = conn.execute("SELECT uri FROM recording_files WHERE id = %s", (rec,)).fetchone()
        if file_row is None:
            raise HTTPException(status_code=404, detail="Unknown raw_ref")
        row = conn.execute(
            "SELECT ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, vrate_fpm, "
            "squawk, on_ground, sac, sic, raw_offset FROM telemetry WHERE raw_ref = %s LIMIT 1",
            (raw_ref,),
        ).fetchone()
    try:
        block = raw_file.read_block(file_row["uri"], index, row["raw_offset"] if row else None)
    except LookupError:
        raise HTTPException(status_code=404, detail="Unknown raw_ref") from None
    except raw_file.RawFileError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    out: dict[str, Any] = {"raw_ref": raw_ref, "recording_file_id": rec, "record_index": index, "hex": block.hex().upper()}
    if row is None:
        out["decoded"] = {"stored": False, "note": "Not kept after compression; only the original bytes are on file."}
        return out
    decoded = {k: row[k] for k in ("icao24", "callsign", "lat", "lon", "baro_alt_ft", "geo_alt_ft",
                                    "gs_kt", "track_deg", "vrate_fpm", "squawk", "on_ground")
               if row[k] is not None}
    decoded["ts"] = iso(row["ts"])
    if row["sac"] is not None:
        out["sac"] = row["sac"]
    if row["sic"] is not None:
        out["sic"] = row["sic"]
    out["decoded"] = decoded
    return out


@app.get("/api/compression/{recording_id}")
def compression(recording_id: str):
    with connect() as conn:
        file_row = conn.execute("SELECT size_bytes FROM recording_files WHERE id = %s", (recording_id,)).fetchone()
        if file_row is None:
            raise HTTPException(status_code=404, detail="Unknown recording_id")
        report = load_report(conn, recording_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"No compression report for recording '{recording_id}'.")
    raw_bytes = int(report.get("raw_bytes") or file_row["size_bytes"] or 0)
    if raw_bytes == 0:
        raise HTTPException(status_code=404, detail=f"Recording '{recording_id}' has no data yet.")
    stored = int(report.get("stored_bytes") or 0)
    events_total = sum(int(v) for v in (report.get("events_by_type") or {}).values())
    with connect() as conn:  # an event is kept when every record it cites is still stored
        kept_row = conn.execute(
            f"SELECT count(*) AS n FROM events e WHERE {EVENT_SCOPE} AND NOT EXISTS ("
            "SELECT 1 FROM unnest(e.raw_refs) r WHERE NOT EXISTS (SELECT 1 FROM telemetry t WHERE t.raw_ref = r))",
            (recording_id, recording_id),
        ).fetchone()
    events_kept = min(int(kept_row["n"]), events_total)
    return {
        "recording_id": recording_id,
        "raw_bytes": raw_bytes,
        "stored_bytes": stored,
        "ratio": stored / raw_bytes,
        "max_position_error_m": float(report.get("max_h_err_m") or 0.0),
        "points_in": int(report.get("decoded_points") or 0),
        "points_kept": int(report.get("rows_stored") or 0),
        "events_total": events_total,
        "events_kept": events_kept,
    }


@app.get("/api/stream")
def stream(recording: Optional[str] = None):  # plain def: the queries run in the threadpool
    """Finite replay of one recording as server-sent events, same payload as the mock (not in the contract)."""
    delay = float(os.environ.get("FLIGHTMIND_STREAM_DELAY", "0.05"))
    with connect() as conn:
        rec = _resolve(conn, recording)
        items: list = []
        if rec is not None:
            for r in conn.execute(
                "SELECT ts, icao24, callsign, lat, lon, coalesce(baro_alt_ft, geo_alt_ft) AS alt_ft, raw_ref "
                f"FROM telemetry WHERE {prefix_clause('raw_ref')} AND lat IS NOT NULL ORDER BY ts",
                (rec, rec),
            ):
                items.append((r["ts"], "position", {**r, "ts": iso(r["ts"])}))
            for r in conn.execute(f"SELECT {EVENT_COLUMNS} FROM events WHERE {EVENT_SCOPE}", (rec, rec)):
                items.append((r["end_ts"], "event", _event(r)))
    items.sort(key=lambda x: x[0])

    async def gen():
        for _, name, payload in items:
            yield f"event: {name}\ndata: {json.dumps(payload)}\n\n"
            await asyncio.sleep(delay)

    return StreamingResponse(gen(), media_type="text/event-stream")


class AskRequest(BaseModel):
    question: str
    recording_id: Optional[str] = None


@app.post("/api/ask")
async def ask(body: AskRequest, request: Request):
    if not agent_enabled():
        return {
            "answer_md": "The analyst agent is off on this server (ANTHROPIC_API_KEY is not set).",
            "citations": [],
            "tool_calls": [],
            "status": "not_enough_evidence",
        }
    if len(body.question) > 500:
        raise HTTPException(status_code=422, detail="Question is longer than 500 characters.")
    host = request.client.host if request.client else None
    if not _guard.check(client_key(request.headers, host)):
        raise HTTPException(status_code=429, detail="Too many questions. Try again in a minute.")
    return await answer_question(body.question, request.app, recording_id=body.recording_id)
