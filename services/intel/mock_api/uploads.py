"""Mock recording upload flow (SCRUM-62, contract 1.2.0).

Serves every /api/recordings path in contracts/openapi.yaml so the web UI can be built
before the real API (SCRUM-64, SCRUM-68) exists. What is real and what is not:

- Real: the order checks (parts in order, complete only after every byte, process only a
  scanned recording and a supported stream), the sha256 of the bytes sent (so the same file
  twice returns the first upload), the first-bytes check (pcap, pcapng or a CAT021 block)
  and the status codes.
- Not real: the bytes are hashed and then dropped. Scanning and processing are a timeline
  (about 1.5 s to scanned, about 10 s from process to ready), the streams are one CAT021 and
  one CAT062 stream, and preview, recipe, quarantine and export return sample data. A ready
  upload serves the rec01 sample dataset, so its raw_refs still start with "rec01:".
- A file named bad.pcap fails after scanning, so the UI's failed state can be tried.

State lives in this process's memory. On Vercel each function instance has its own memory
and requests are limited to 4.5 MB, so uploads only work against a local mock.
"""
import csv
import hashlib
import io
import json
import os
import re
import secrets
import threading
import time
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel

from . import data

PART_SIZE_BYTES = 52_428_800  # 50 MB: the Cloudflare tunnel refuses requests over 100 MB


def part_size() -> int:
    """FLIGHTMIND_PART_SIZE_BYTES, else 50 MB. Tests lower it, as for the real API."""
    return int(os.environ.get("FLIGHTMIND_PART_SIZE_BYTES", str(PART_SIZE_BYTES)))
FORMATS = {".pcap": "pcap", ".pcapng": "pcapng", ".atx": "asterix_raw", ".ast": "asterix_raw", ".bin": "asterix_raw"}
PCAP_MAGICS = {bytes.fromhex(h) for h in ("a1b2c3d4", "d4c3b2a1", "a1b23c4d", "4d3cb2a1")}
PCAPNG_MAGIC = bytes.fromhex("0a0d0d0a")
CAT021 = 0x15

# Seconds after complete (scan) and after process (the other stages), as in the UI's own mock.
SCAN_S = 1.5
STAGES = (("queued", 1.0), ("decoding", 3.0), ("filtering", 2.0), ("detecting", 2.0), ("storing", 2.0))
PROCESS_S = sum(s for _, s in STAGES)
MOCK_RECORDS = 120_000
FAILED_NAME = "bad.pcap"

FIELD_QUALITY = [
    {"item": "I021/130", "label": "Position (WGS-84)", "present_pct": 99.9},
    {"item": "I021/140", "label": "Geometric height (WGS-84)", "present_pct": 97.3},
    {"item": "I021/145", "label": "Flight level (pressure, std 1013.25)", "present_pct": 99.2},
    {"item": "I021/170", "label": "Target identification", "present_pct": 96.4},
    {"item": "I021/040", "label": "Target report descriptor", "present_pct": 100.0},
]
RECIPE_STEPS = [
    ("duplicates", "Duplicate records", 1420, "Same target address, time and position as an earlier record."),
    ("position_jumps", "Position jumps", 160, "Implied speed between neighbours above 1,200 kt."),
    ("altitude_spikes", "Altitude spikes", 210, "More than 2,000 ft from both neighbours within 2 s."),
    ("fragments", "Fragment tracks", 70, "Fewer than 20 records for one target address."),
]
QUARANTINE_TOTAL = sum(n for _, _, n, _ in RECIPE_STEPS)
TOLERANCE_NOTE = (
    "Tracks are reduced within 25 m of position error and 50 ft of altitude error. "
    "Event windows are never reduced."
)

clock = time.monotonic  # tests replace this to move through the stages without waiting


def max_upload_bytes() -> int:
    return int(os.environ.get("FLIGHTMIND_MAX_UPLOAD_MB", "2048")) * 1024 * 1024


@dataclass
class _Upload:
    id: str
    filename: str
    size_bytes: int
    format: str
    recording_date: Optional[date]
    created_at: str
    created_mono: float
    bytes_received: int = 0
    next_part: int = 0
    last_part_len: int = 0
    head: bytes = b""
    hasher: Any = field(default_factory=hashlib.sha256)
    sha256: Optional[str] = None
    completed_at: Optional[float] = None
    processed_at: Optional[float] = None
    stream_id: Optional[str] = None


_lock = threading.Lock()
_uploads: dict = {}


def reset() -> None:
    """Forget every upload (tests)."""
    with _lock:
        _uploads.clear()


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _streams(fmt: str) -> list:
    cat21 = {"id": "s1", "src": "10.4.1.20:8600", "dst": "239.1.1.21:8600", "category": 21,
             "sac": data.SAC, "sic": data.SIC, "frames": 96_412, "records": MOCK_RECORDS, "supported": True}
    if fmt == "asterix_raw":
        return [{**cat21, "id": "raw", "src": "", "dst": "", "frames": 0}]
    cat62 = {"id": "s2", "src": "10.4.1.22:8610", "dst": "239.1.1.62:8610", "category": 62,
             "sac": data.SAC, "sic": 9, "frames": 41_077, "records": 0, "supported": False}
    return [cat21, cat62]


def _status(u: _Upload, t: float) -> str:
    if u.completed_at is None:
        return "uploading"
    if t - u.completed_at < SCAN_S:
        return "scanning"
    if u.filename.lower() == FAILED_NAME:
        return "failed"
    if u.processed_at is None:
        return "scanned"
    since = t - u.processed_at
    for name, seconds in STAGES:
        if since < seconds:
            return name
        since -= seconds
    return "ready"


def _view(u: _Upload) -> dict:
    t = clock()
    status = _status(u, t)
    progress = None
    if status in ("decoding", "filtering", "detecting", "storing"):
        done = int(MOCK_RECORDS * (t - u.processed_at - STAGES[0][1]) / (PROCESS_S - STAGES[0][1]))
        progress = {"records_done": max(0, min(done, MOCK_RECORDS)), "records_total": MOCK_RECORDS}
    elif status == "ready":
        progress = {"records_done": MOCK_RECORDS, "records_total": MOCK_RECORDS}
    ready = status == "ready"
    first, last = _sample_span()
    return {
        "id": u.id,
        "filename": u.filename,
        "size_bytes": u.size_bytes,
        "bytes_received": u.bytes_received,
        "part_size_bytes": part_size(),
        "format": u.format,
        "status": status,
        "streams": _streams(u.format) if status not in ("uploading", "scanning", "failed") else [],
        "progress": progress,
        "error": f"No CAT021 records found in {u.filename}." if status == "failed" else None,
        "record_count": MOCK_RECORDS if ready else None,
        "event_count": len(data.EVENTS) if ready else None,
        "first_ts": first if ready else None,
        "last_ts": last if ready else None,
        "created_at": u.created_at,
    }


def _sample_span():
    stamps = sorted(p["ts"] for t in data.TRACKS.values() for p in t["points"])
    return (stamps[0], stamps[-1]) if stamps else (None, None)


def _get(recording_id: str) -> _Upload:
    u = _uploads.get(recording_id)
    if u is None:
        raise HTTPException(status_code=404, detail=f"No recording with id '{recording_id}'.")
    return u


def is_ready(recording_id: str) -> bool:
    with _lock:
        u = _uploads.get(recording_id)
        return u is not None and _status(u, clock()) == "ready"


def ready_ids() -> list:
    with _lock:
        t = clock()
        return [u.id for u in sorted(_uploads.values(), key=lambda u: u.created_mono) if _status(u, t) == "ready"]


def _looks_like_capture(head: bytes) -> Optional[str]:
    """The format the first bytes show, or None when they are not pcap, pcapng or a CAT021 block."""
    if head[:4] in PCAP_MAGICS:
        return "pcap"
    if head[:4] == PCAPNG_MAGIC:
        return "pcapng"
    if len(head) >= 3 and head[0] == CAT021 and int.from_bytes(head[1:3], "big") >= 3:
        return "asterix_raw"
    return None


def _require_scanned(u: _Upload) -> str:
    status = _status(u, clock())
    if status in ("uploading", "scanning", "failed"):
        raise HTTPException(status_code=409, detail=f"Recording '{u.id}' is {status}, not scanned yet.")
    return status


MISMATCH = {
    True: "This is a raw ASTERIX file; name it .atx, .ast or .bin so its recording date can be given.",
    False: "This is a pcap or pcapng capture; name it .pcap or .pcapng.",
}


def _recipe(u: _Upload) -> dict:
    left, steps = MOCK_RECORDS, []
    for code, label, set_aside, reason in RECIPE_STEPS:
        steps.append({"code": code, "label": label, "records_in": left, "set_aside": set_aside, "reason": reason})
        left -= set_aside
    # The stored size is only known after processing; before ready the counts are the scan's dry run.
    ready = _status(u, clock()) == "ready"
    stored = round(u.size_bytes / 7.6) if ready else None
    return {
        "input_sha256": u.sha256,
        "steps": steps,
        "tolerance_note": TOLERANCE_NOTE,
        "raw_bytes": u.size_bytes,
        "stored_bytes": stored,
        "ratio": stored / u.size_bytes if ready else None,
    }


def _quarantine_item(i: int) -> dict:
    refs = list(data.RAW)  # sample refs, so every quarantined raw_ref opens in /api/raw
    rest = i
    for code, _, set_aside, reason in RECIPE_STEPS:
        if rest < set_aside:
            return {"raw_ref": refs[i % len(refs)], "step_code": code, "reason": reason}
        rest -= set_aside
    raise IndexError(i)


def _csv(rows) -> str:
    out = io.StringIO()
    csv.writer(out, lineterminator="\n").writerows(rows)
    return out.getvalue()


router = APIRouter()


class CreateRecordingRequest(BaseModel):
    filename: str
    size_bytes: int
    recording_date: Optional[date] = None


class ProcessRecordingRequest(BaseModel):
    stream_id: str


@router.get("/api/recordings")
def list_recordings():
    with _lock:
        ups = sorted(_uploads.values(), key=lambda u: u.created_mono, reverse=True)
        return [_view(u) for u in ups]


@router.post("/api/recordings", status_code=201)
def create_recording(body: CreateRecordingRequest):
    name = body.filename.strip()
    ext = os.path.splitext(name)[1].lower()
    if ext not in FORMATS:
        raise HTTPException(status_code=415, detail="Use a .pcap, .pcapng, .atx, .ast or .bin file.")
    if body.size_bytes < 1:
        raise HTTPException(status_code=422, detail="size_bytes must be at least 1.")
    if body.size_bytes > max_upload_bytes():
        raise HTTPException(status_code=413, detail=f"The file is larger than {max_upload_bytes() // (1024 * 1024)} MB.")
    with _lock:
        u = _Upload(
            id="r" + secrets.token_hex(5),
            filename=name,
            size_bytes=body.size_bytes,
            format=FORMATS[ext],
            recording_date=body.recording_date,
            created_at=_now_iso(),
            created_mono=clock(),
        )
        _uploads[u.id] = u
        return _view(u)


@router.get("/api/recordings/{recording_id}")
def get_recording(recording_id: str):
    with _lock:
        return _view(_get(recording_id))


async def read_part(request: Request, limit: int) -> bytes:
    """The request body, refused with 413 as soon as it is longer than limit."""
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > limit:
        raise HTTPException(status_code=413, detail=f"A part can be at most {limit} bytes.")
    chunks, total = [], 0
    async for piece in request.stream():
        total += len(piece)
        if total > limit:
            raise HTTPException(status_code=413, detail=f"A part can be at most {limit} bytes.")
        chunks.append(piece)
    return b"".join(chunks)


@router.put("/api/recordings/{recording_id}/parts/{n}", status_code=204)
async def upload_part(recording_id: str, n: int, request: Request):
    size = part_size()
    chunk = await read_part(request, size)
    with _lock:
        u = _get(recording_id)
        if u.completed_at is not None:
            raise HTTPException(status_code=409, detail=f"Recording '{recording_id}' is no longer uploading.")
        if n == u.next_part - 1 and len(chunk) == u.last_part_len:
            return Response(status_code=204)  # a retry of the last stored part: nothing to do
        if n != u.next_part:
            raise HTTPException(status_code=409, detail=f"Part {n} is out of order; send part {u.next_part} next.")
        if u.bytes_received + len(chunk) > u.size_bytes:
            raise HTTPException(status_code=409, detail="The parts are larger than size_bytes.")
        if u.bytes_received + len(chunk) < u.size_bytes and len(chunk) != size:
            raise HTTPException(status_code=409, detail=f"Every part but the last must be {size} bytes.")
        if len(u.head) < 8:
            u.head += chunk[: 8 - len(u.head)]
        u.hasher.update(chunk)  # the bytes are hashed, then dropped
        u.bytes_received += len(chunk)
        u.next_part += 1
        u.last_part_len = len(chunk)
    return Response(status_code=204)


@router.post("/api/recordings/{recording_id}/complete")
def complete_recording(recording_id: str, response: Response):
    with _lock:
        u = _get(recording_id)
        if u.completed_at is not None:
            raise HTTPException(status_code=409, detail=f"Recording '{recording_id}' is no longer uploading.")
        if u.bytes_received < u.size_bytes:
            raise HTTPException(
                status_code=409,
                detail=f"Only {u.bytes_received} of {u.size_bytes} bytes arrived; send the missing parts first.",
            )
        fmt = _looks_like_capture(u.head)
        if fmt is None:
            raise HTTPException(status_code=415, detail="The file does not start like pcap, pcapng or an ASTERIX CAT021 block.")
        if (fmt == "asterix_raw") != (u.format == "asterix_raw"):
            raise HTTPException(status_code=415, detail=MISMATCH[fmt == "asterix_raw"])
        sha = u.hasher.hexdigest()
        t = clock()
        earlier = next(
            (o for o in _uploads.values() if o.sha256 == sha and o.id != u.id and _status(o, t) != "failed"), None
        )
        if earlier is not None:
            del _uploads[u.id]
            response.status_code = 200
            return _view(earlier)
        u.sha256, u.format, u.completed_at = sha, fmt, clock()
        response.status_code = 202
        return _view(u)


@router.post("/api/recordings/{recording_id}/process", status_code=202)
def process_recording(recording_id: str, body: ProcessRecordingRequest):
    with _lock:
        u = _get(recording_id)
        status = _status(u, clock())
        if status != "scanned":
            raise HTTPException(status_code=409, detail=f"Recording '{recording_id}' is {status}, not scanned.")
        if not any(s["id"] == body.stream_id and s["supported"] for s in _streams(u.format)):
            raise HTTPException(status_code=409, detail=f"Stream '{body.stream_id}' is not a supported CAT021 stream.")
        u.processed_at, u.stream_id = clock(), body.stream_id
        return _view(u)


@router.get("/api/recordings/{recording_id}/preview")
def preview(recording_id: str, stream: str, limit: int = Query(8, ge=1, le=200)):
    with _lock:
        u = _get(recording_id)
        _require_scanned(u)
        if not any(s["id"] == stream and s["supported"] for s in _streams(u.format)):
            raise HTTPException(status_code=409, detail=f"Stream '{stream}' is not a supported CAT021 stream.")
    records = list(data.RAW.values())[:limit]
    return {"records": records, "field_quality": FIELD_QUALITY, "sample_size": 5000}


@router.get("/api/recordings/{recording_id}/recipe")
def recipe(recording_id: str):
    with _lock:
        u = _get(recording_id)
        _require_scanned(u)
        return _recipe(u)


@router.get("/api/recordings/{recording_id}/quarantine")
def quarantine(recording_id: str, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=500)):
    with _lock:
        _require_scanned(_get(recording_id))
    end = min(QUARANTINE_TOTAL, offset + limit)
    return {"total": QUARANTINE_TOTAL, "items": [_quarantine_item(i) for i in range(offset, end)]}


@router.get("/api/recordings/{recording_id}/export")
def export(recording_id: str):
    with _lock:
        u = _get(recording_id)
        status = _status(u, clock())
        if status != "ready":
            raise HTTPException(status_code=409, detail=f"Recording '{recording_id}' is {status}, not ready.")
        rec = _recipe(u)
        stem = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.splitext(u.filename)[0]) or u.id
    cleaned = [["raw_ref", "icao24", "ts", "lat", "lon", "alt_ft"]] + [
        [p["raw_ref"], icao, p["ts"], p["lat"], p["lon"], p["alt_ft"]]
        for icao, t in data.TRACKS.items() for p in t["points"]
    ]
    events = [["id", "type", "icao24", "callsign", "start_ts", "end_ts", "raw_refs"]] + [
        [e["id"], e["type"], e["icao24"], e["callsign"], e["start_ts"], e["end_ts"], " ".join(e["raw_refs"])]
        for e in data.EVENTS
    ]
    quarantined = [["raw_ref", "step_code", "reason"]] + [
        [q["raw_ref"], q["step_code"], q["reason"]] for q in map(_quarantine_item, range(QUARANTINE_TOTAL))
    ]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("cleaned.csv", _csv(cleaned))
        z.writestr("events.csv", _csv(events))
        z.writestr("quarantine.csv", _csv(quarantined))
        z.writestr("recipe.json", json.dumps(rec, indent=2))
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{stem}-flightmind.zip"'},
    )
