"""Recording upload and the processing worker for the real API (SCRUM-64, contract 1.2.0).

Flow: POST /api/recordings makes an `uploads` row and an empty file under
FLIGHTMIND_UPLOAD_DIR. Parts arrive in order (PUT .../parts/{n}) and are appended. Complete
checks size, first bytes and sha256 (the same file twice returns the first upload), then the
worker scans the file for streams (status scanning -> scanned). Process picks a CAT021
stream (queued), and the worker runs the pipeline job:

    flightmind_pipeline.run_recording(path, recording_id, dsn, on_progress, recording_date)

(SCRUM-63), which writes telemetry, events and recording_files with raw_refs '<id>:<n>'.
on_progress(stage, done, total) moves the row through decoding, filtering, detecting and
storing; the report it returns is saved and the row becomes ready, or failed with one
sentence on any exception.

One worker thread handles one job at a time. It starts with the app (uvicorn, or serve.py,
which passes the app its startup); if the database is not up yet it starts on the first upload
request instead. On start, rows left in decoding..storing become failed, and every 10 minutes
uploads idle in uploading for over an hour are deleted with their file. Run a single server
process (no `--workers 2`): each process has its own worker and would fail the other's job on
start. A long job delays the scan of newer uploads until it ends.

Errors shown to users come only from ValueError and RuntimeError (our own and the pipeline's
messages), with file paths reduced to file names; anything else shows a generic sentence and
the traceback goes to the log.

Preview, recipe, quarantine and export (SCRUM-68) read a sidecar `<upload_dir>/<id>.clean.json`,
written by the scan: a dry run that counts, from the file and with the pipeline's own rules, the
records it will set aside (see clean.py). Once ready, the pipeline report's numbers are used.
The sidecar is deleted wherever the upload file is.

Environment:
    FLIGHTMIND_UPLOAD_DIR        where uploaded files are kept (default <repo>/data/uploads)
    FLIGHTMIND_MAX_UPLOAD_MB     largest file accepted (default 2048)
    FLIGHTMIND_PART_SIZE_BYTES   part size given to clients (default 52428800; tests lower it)
    FLIGHTMIND_UPLOAD_WORKER     "off" keeps the worker thread from starting (tests)
"""
import csv
import hashlib
import importlib
import io
import json
import logging
import os
import re
import secrets
import shutil
import struct
import tempfile
import threading
import time
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi import Path as PathParam
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from . import clean, raw_file
from .db import connect, dsn

log = logging.getLogger("flightmind.uploads")

REPO_ROOT = Path(__file__).resolve().parents[3]
FORMATS = {".pcap": "pcap", ".pcapng": "pcapng", ".atx": "asterix_raw", ".ast": "asterix_raw", ".bin": "asterix_raw"}
PROCESSING = ("decoding", "filtering", "detecting", "storing")
RESTART_ERROR = "Server restarted during processing. Upload again."
STALE_UPLOAD = timedelta(hours=1)
STALE_SWEEP_SECONDS = 600
PROGRESS_EVERY_SECONDS = 0.5
DISK_HEADROOM_BYTES = 512 * 1024 * 1024
CAT021 = 21
GENERIC_ERROR = "Processing failed on the server. Try again, or upload the file again."
MISMATCH = {
    True: "This is a raw ASTERIX file; name it .atx, .ast or .bin so its recording date can be given.",
    False: "This is a pcap or pcapng capture; name it .pcap or .pcapng.",
}


def upload_dir() -> Path:
    return Path(os.environ.get("FLIGHTMIND_UPLOAD_DIR") or REPO_ROOT / "data" / "uploads")


def max_upload_bytes() -> int:
    return int(os.environ.get("FLIGHTMIND_MAX_UPLOAD_MB", "2048")) * 1024 * 1024


def part_size() -> int:
    return int(os.environ.get("FLIGHTMIND_PART_SIZE_BYTES", str(52_428_800)))


# ---------- the pipeline job ----------

Runner = Callable[..., dict]
runner: Optional[Runner] = None  # tests set a stand-in; None means flightmind_pipeline.run_recording


def _runner() -> Runner:
    if runner is not None:
        return runner
    try:
        return importlib.import_module("flightmind_pipeline").run_recording
    except (ImportError, AttributeError):
        raise RuntimeError("The pipeline job (run_recording, SCRUM-63) is not installed on this server.") from None


_WINDOWS_PATH = re.compile(r"[A-Za-z]:\\[^\s:]*\\([^\s\\:]+)")
_POSIX_PATH = re.compile(r"(?<![\w.])/(?:[^\s/:]+/)+([^\s/:]+)")


def one_sentence(exc: BaseException) -> str:
    """The message users see. Only our own kinds of error keep their text, and paths lose their folders."""
    if not isinstance(exc, (ValueError, RuntimeError)):
        return GENERIC_ERROR
    text = " ".join(str(exc).split()) or type(exc).__name__
    text = _POSIX_PATH.sub(r"\1", _WINDOWS_PATH.sub(r"\1", text))
    text = text[:300].rstrip()
    return text if text.endswith((".", "!", "?")) else text + "."


# ---------- rows and views ----------

def _iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


VIEW_SQL = (
    "SELECT u.*, f.first_ts, f.last_ts FROM uploads u "
    "LEFT JOIN recording_files f ON f.id = u.id AND u.status = 'ready'"
)


def view(row: dict) -> dict:
    report = row.get("report") or {}
    ready = row["status"] == "ready"
    progress = None
    if row["records_total"] is not None and row["status"] in PROCESSING + ("ready",):
        progress = {"records_done": row["records_done"] or 0, "records_total": row["records_total"]}
    return {
        "id": row["id"],
        "filename": row["filename"],
        "size_bytes": row["size_bytes"],
        "bytes_received": row["bytes_received"],
        "part_size_bytes": part_size(),
        "format": row["format"],
        "status": row["status"],
        "streams": row["streams"] or [],
        "progress": progress,
        "error": row["error"],
        "record_count": report.get("raw_records") if ready else None,
        "event_count": sum((report.get("events_by_type") or {}).values()) if ready else None,
        "first_ts": _iso(row.get("first_ts")) if ready else None,
        "last_ts": _iso(row.get("last_ts")) if ready else None,
        "created_at": _iso(row["created_at"]),
    }


def _get(conn, recording_id: str, lock: bool = False) -> dict:
    sql = "SELECT * FROM uploads WHERE id = %s" + (" FOR UPDATE" if lock else "")
    row = conn.execute(sql, (recording_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No recording with id '{recording_id}'.")
    return row


def _view_of(conn, recording_id: str) -> dict:
    return view(conn.execute(VIEW_SQL + " WHERE u.id = %s", (recording_id,)).fetchone())


def _set(conn, recording_id: str, **fields: Any) -> None:
    from psycopg.types.json import Jsonb

    cols = ", ".join(f"{k} = %s" for k in fields)
    values = [Jsonb(v) if k in ("streams", "report") and v is not None else v for k, v in fields.items()]
    conn.execute(f"UPDATE uploads SET {cols}, updated_at = now() WHERE id = %s", (*values, recording_id))


# ---------- file checks and stream scan ----------

def sniff(head: bytes, size: int) -> Optional[str]:
    """pcap, pcapng or asterix_raw from the first bytes; None when it is none of them."""
    if head[:4] in raw_file.PCAP_MAGICS:
        return "pcap"
    if head[:4] == raw_file.PCAPNG_SHB:
        return "pcapng"
    if len(head) >= 3 and head[0] == CAT021 and 3 <= struct.unpack(">H", head[1:3])[0] <= size:
        return "asterix_raw"
    return None


def _sac_sic(block: bytes) -> tuple:
    """SAC and SIC from data item 010 when the first record has it (FRN 1), else (0, 0)."""
    pos = 3
    if len(block) <= pos or not block[pos] & 0x80:
        return 0, 0
    while pos < len(block) and block[pos] & 0x01:
        pos += 1
    pos += 1
    return (block[pos], block[pos + 1]) if pos + 1 < len(block) else (0, 0)


def scan_streams(path: str) -> list:
    """Group the file's ASTERIX blocks by UDP source and destination. Header reads only."""
    found: dict = {}
    with open(path, "rb") as f:
        kind, order, link_type = raw_file._format(f)
        offsets = raw_file.iter_offsets(f, kind, order)
        while True:
            try:
                _index, offset = next(offsets)
                packet = raw_file._packet_at(f, kind, order, offset)
            except StopIteration:
                break
            except (struct.error, IndexError, raw_file.RawFileError):
                break  # the file ends inside a record: keep what was read
            if kind == "raw":
                key, block = ("", ""), packet
            else:
                try:
                    block, key = _udp_with_ends(packet, link_type)
                except (raw_file.RawFileError, struct.error, IndexError):
                    continue  # other traffic or a truncated frame
            if len(block) < 3:
                continue
            entry = found.setdefault(key + (block[0],), {"frames": 0, "sac_sic": _sac_sic(block)})
            entry["frames"] += 1
    streams = []
    # Most frames first; in a raw file, which is one stream, CAT021 wins over a bigger other category.
    ordered = sorted(found.items(), key=lambda kv: (kind == "raw" and kv[0][2] != CAT021, -kv[1]["frames"]))
    for (src, dst, category), entry in ordered:
        sac, sic = entry["sac_sic"]
        supported = category == CAT021
        streams.append({
            "id": "raw" if kind == "raw" else f"s{len(streams) + 1}",
            "src": src, "dst": dst, "category": category, "sac": sac, "sic": sic,
            "frames": 0 if kind == "raw" else entry["frames"],
            "records": entry["frames"] if supported else 0,  # one record per frame, as the pipeline assumes
            "supported": supported,
        })
        if kind == "raw":
            break  # a raw file is one stream
    return streams


def _udp_with_ends(packet: bytes, link_type: int) -> tuple:
    """(ASTERIX payload, (src ip:port, dst ip:port)) of one UDP packet."""
    return raw_file.udp_with_ends(packet, link_type)


# ---------- worker ----------

_worker_lock = threading.Lock()
_worker: Optional[threading.Thread] = None
_wake = threading.Event()
_stop = threading.Event()


def recover() -> None:
    """After a restart: fail rows left mid-processing, delete uploads idle for over an hour."""
    with connect() as conn:
        conn.execute(
            "UPDATE uploads SET status = 'failed', error = %s, updated_at = now() WHERE status = ANY(%s)",
            (RESTART_ERROR, list(PROCESSING)),
        )
    sweep_stale()


def sweep_stale() -> None:
    """Delete uploads idle in uploading for over an hour, with their files."""
    with connect() as conn:
        stale = conn.execute(
            "DELETE FROM uploads WHERE status = 'uploading' AND updated_at < now() - %s RETURNING id, path",
            (STALE_UPLOAD,),
        ).fetchall()
    for row in stale:
        clean.remove_files(row["path"], row["id"])


def run_pending_once() -> bool:
    """Do one job: scan one scanning upload, else process one queued upload. False when idle."""
    with connect() as conn:
        with conn.transaction():
            row = conn.execute(
                "SELECT * FROM uploads WHERE status IN ('scanning', 'queued') "
                "ORDER BY (status = 'scanning') DESC, updated_at LIMIT 1 FOR UPDATE SKIP LOCKED"
            ).fetchone()
            if row is None:
                return False
            if row["status"] == "queued":
                _set(conn, row["id"], status="decoding", records_done=None, records_total=None)
    if row["status"] == "scanning":
        _scan(row)
    else:
        _process(row)
    return True


def _scan(row: dict) -> None:
    try:
        streams = scan_streams(row["path"])
        supported = [s for s in streams if s["supported"]]
        if not supported:
            raise ValueError(f"No CAT021 records found in {row['filename']}")
        _make_clean(row, supported[0])
        with connect() as conn:
            _set(conn, row["id"], status="scanned", streams=streams, error=None)
    except Exception as exc:  # any failure is reported on the row, never raised
        log.exception("scan of %s failed", row["id"])
        with connect() as conn:
            _set(conn, row["id"], status="failed", error=one_sentence(exc))
        clean.remove_files(row["path"], row["id"])  # nothing can use the file now


def _make_clean(row: dict, stream: dict) -> dict:
    """Run the cleaning dry run on one stream and save the sidecar next to the upload."""
    data = clean.dry_run(row["path"], stream, row["id"])
    data["stream_id"] = stream["id"]
    clean.save(clean.sidecar_path(row["path"], row["id"]), data)
    return data


def _process(row: dict) -> None:
    recording_id = row["id"]
    last = {"stage": None, "at": 0.0}

    with connect() as conn:  # one connection for every progress update of this job

        def on_progress(stage: str, done: int, total: int) -> None:
            if stage not in PROCESSING:
                return
            now = time.monotonic()
            if stage == last["stage"] and now - last["at"] < PROGRESS_EVERY_SECONDS and done < total:
                return  # SCRUM-63 reports every 1000 records; the UI polls every 2 s
            last.update(stage=stage, at=now)
            _set(conn, recording_id, status=stage, records_done=done, records_total=total)

        try:
            report = _runner()(row["path"], recording_id, dsn(), on_progress, row["recording_date"])
            records = int(report.get("raw_records") or 0)
            _set(conn, recording_id, status="ready", report=report, error=None,
                 records_done=records, records_total=records)
        except Exception as exc:  # any failure is reported on the row, never raised
            log.exception("processing of %s failed", recording_id)
            _set(conn, recording_id, status="failed", error=one_sentence(exc))
            stored = conn.execute("SELECT 1 FROM recording_files WHERE id = %s", (recording_id,)).fetchone()
            if stored is None:  # nothing cites the file, so it only takes disk space
                clean.remove_files(row["path"], recording_id)


def _loop() -> None:
    swept = time.monotonic()
    while not _stop.is_set():
        try:
            if time.monotonic() - swept > STALE_SWEEP_SECONDS:
                swept = time.monotonic()
                sweep_stale()
            busy = run_pending_once()
        except Exception:  # database down: wait and try again
            log.exception("upload worker step failed")
            busy = False
        if not busy:
            _wake.wait(timeout=2.0)
            _wake.clear()


def ensure_worker() -> None:
    """Start the worker thread once per process, after recovering from a restart."""
    global _worker
    if os.environ.get("FLIGHTMIND_UPLOAD_WORKER", "on").strip().lower() == "off":
        return
    with _worker_lock:
        if _worker is not None and _worker.is_alive():
            return
        _stop.clear()
        recover()
        _worker = threading.Thread(target=_loop, name="flightmind-upload-worker", daemon=True)
        _worker.start()


def wake() -> None:
    _wake.set()


def stop_worker(timeout: float = 5.0) -> None:
    """Stop the worker thread (tests)."""
    global _worker
    with _worker_lock:
        _stop.set()
        _wake.set()
        if _worker is not None:
            _worker.join(timeout)
        _worker = None


# ---------- endpoints ----------

router = APIRouter()


class CreateRecordingRequest(BaseModel):
    filename: str
    size_bytes: int
    recording_date: Optional[date] = None


class ProcessRecordingRequest(BaseModel):
    stream_id: str


def _started() -> None:
    try:
        ensure_worker()
    except HTTPException:
        raise
    except Exception:  # the worker must not break a request
        log.exception("could not start the upload worker")


@router.get("/api/recordings")
def list_recordings():
    _started()
    with connect() as conn:
        return [view(r) for r in conn.execute(VIEW_SQL + " ORDER BY u.created_at DESC, u.id")]


@router.post("/api/recordings", status_code=201)
def create_recording(body: CreateRecordingRequest):
    _started()
    name = os.path.basename(body.filename.strip().replace("\\", "/"))
    ext = os.path.splitext(name)[1].lower()
    if ext not in FORMATS:
        raise HTTPException(status_code=415, detail="Use a .pcap, .pcapng, .atx, .ast or .bin file.")
    if body.size_bytes < 1:
        raise HTTPException(status_code=422, detail="size_bytes must be at least 1.")
    if body.size_bytes > max_upload_bytes():
        raise HTTPException(status_code=413, detail=f"The file is larger than {max_upload_bytes() // (1024 * 1024)} MB.")
    folder = upload_dir()
    folder.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(folder).free < body.size_bytes + DISK_HEADROOM_BYTES:
        raise HTTPException(status_code=413, detail="The server does not have enough free disk space for this file.")
    recording_id = "r" + secrets.token_hex(5)
    path = folder / f"{recording_id}{ext}"
    path.write_bytes(b"")
    with connect() as conn:
        conn.execute(
            "INSERT INTO uploads (id, filename, size_bytes, format, recording_date, path) VALUES (%s, %s, %s, %s, %s, %s)",
            (recording_id, name, body.size_bytes, FORMATS[ext], body.recording_date, str(path)),
        )
        return _view_of(conn, recording_id)


@router.get("/api/recordings/{recording_id}")
def get_recording(recording_id: str):
    with connect() as conn:
        _get(conn, recording_id)
        return _view_of(conn, recording_id)


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
async def upload_part(recording_id: str, request: Request, n: int = PathParam(..., ge=0)):
    chunk = await read_part(request, part_size())
    await run_in_threadpool(_append, recording_id, n, chunk)  # database and disk work off the event loop
    return Response(status_code=204)


def _append(recording_id: str, n: int, chunk: bytes) -> None:
    """Write part n whole, or not at all. A repeat of the last stored part is a no-op."""
    size = part_size()
    with connect() as conn:
        with conn.transaction():
            row = _get(conn, recording_id, lock=True)
            if row["status"] != "uploading":
                raise HTTPException(status_code=409, detail=f"Recording '{recording_id}' is no longer uploading.")
            received = row["bytes_received"]
            stored_parts = -(-received // size)
            if received and n == stored_parts - 1 and len(chunk) == received - n * size:
                return  # the response to this part was lost and the client sent it again
            if n * size != received:
                raise HTTPException(status_code=409, detail=f"Part {n} is out of order; send part {received // size} next.")
            after = received + len(chunk)
            if after > row["size_bytes"]:
                raise HTTPException(status_code=409, detail="The parts are larger than size_bytes.")
            if after < row["size_bytes"] and len(chunk) != size:
                raise HTTPException(status_code=409, detail=f"Every part but the last must be {size} bytes.")
            with open(row["path"], "r+b") as f:
                f.seek(received)
                f.write(chunk)
                f.truncate()
            _set(conn, recording_id, bytes_received=after)


@router.post("/api/recordings/{recording_id}/complete")
def complete_recording(recording_id: str, response: Response):
    with connect() as conn:
        with conn.transaction():
            row = _get(conn, recording_id, lock=True)
            if row["status"] != "uploading":
                raise HTTPException(status_code=409, detail=f"Recording '{recording_id}' is no longer uploading.")
            path = Path(row["path"])
            on_disk = path.stat().st_size if path.exists() else 0
            if row["bytes_received"] < row["size_bytes"]:
                raise HTTPException(
                    status_code=409,
                    detail=f"Only {row['bytes_received']} of {row['size_bytes']} bytes arrived; send the missing parts first.",
                )
            if on_disk != row["size_bytes"]:
                raise HTTPException(
                    status_code=409,
                    detail=f"The stored file has {on_disk} bytes, not {row['size_bytes']}; upload the file again.",
                )
            with path.open("rb") as f:
                fmt = sniff(f.read(8), on_disk)
            if fmt is None:
                raise HTTPException(status_code=415, detail="The file does not start like pcap, pcapng or an ASTERIX CAT021 block.")
            if (fmt == "asterix_raw") != (row["format"] == "asterix_raw"):
                raise HTTPException(status_code=415, detail=MISMATCH[fmt == "asterix_raw"])
            sha = _sha256(path)
            earlier = conn.execute(
                "SELECT id FROM uploads WHERE sha256 = %s AND status <> 'failed' AND id <> %s", (sha, recording_id)
            ).fetchone()
            if earlier is None:
                try:
                    with conn.transaction():  # savepoint: a concurrent complete of the same bytes may win
                        _set(conn, recording_id, sha256=sha, format=fmt, status="scanning")
                except _unique_violation():
                    earlier = conn.execute(
                        "SELECT id FROM uploads WHERE sha256 = %s AND status <> 'failed' AND id <> %s", (sha, recording_id)
                    ).fetchone()
            if earlier is not None:
                conn.execute("DELETE FROM uploads WHERE id = %s", (recording_id,))
                clean.remove_files(str(path), recording_id)
                response.status_code = 200
                return _view_of(conn, earlier["id"])
            result = _view_of(conn, recording_id)
    wake()
    response.status_code = 202
    return result


def _unique_violation():
    from psycopg import errors

    return errors.UniqueViolation


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


@router.post("/api/recordings/{recording_id}/process", status_code=202)
def process_recording(recording_id: str, body: ProcessRecordingRequest):
    with connect() as conn:
        with conn.transaction():
            row = _get(conn, recording_id, lock=True)
            if row["status"] != "scanned":
                raise HTTPException(status_code=409, detail=f"Recording '{recording_id}' is {row['status']}, not scanned.")
            supported = [s for s in row["streams"] or [] if s["supported"]]
            if not any(s["id"] == body.stream_id for s in supported):
                raise HTTPException(status_code=409, detail=f"Stream '{body.stream_id}' is not a supported CAT021 stream.")
            if len(supported) > 1:  # run_recording (SCRUM-63) cannot be told which stream yet
                raise HTTPException(
                    status_code=409,
                    detail=f"This file has {len(supported)} CAT021 streams; processing one of several is not supported yet.",
                )
            _set(conn, recording_id, status="queued", stream_id=body.stream_id)
            result = _view_of(conn, recording_id)
    _started()
    wake()
    return result


def _require_scanned(row: dict) -> None:
    if row["status"] in ("uploading", "scanning", "failed"):
        raise HTTPException(status_code=409, detail=f"Recording '{row['id']}' is {row['status']}, not scanned yet.")


def _supported(row: dict) -> list:
    return [s for s in row["streams"] or [] if s["supported"]]


def _clean_of(row: dict) -> dict:
    """The sidecar of a scanned upload. One made before the sidecar existed is computed once and saved."""
    data = clean.load(clean.sidecar_path(row["path"], row["id"]))
    if data is not None:
        return data
    supported = _supported(row)
    if not supported:
        raise HTTPException(status_code=409, detail=f"Recording '{row['id']}' has no supported stream.")
    if not Path(row["path"]).is_file():
        raise HTTPException(status_code=409, detail="The recording file is no longer on this server.")
    return _make_clean(row, supported[0])


def _kept_refs(conn, data: dict) -> set:
    """raw_refs of no_position records the pipeline stored anyway (an event pinned them), so they were not set aside."""
    refs = [q["raw_ref"] for q in data["quarantine"] if q["step_code"] == "no_position"]
    kept: set = set()
    for i in range(0, len(refs), 5000):
        found = conn.execute("SELECT raw_ref FROM telemetry WHERE raw_ref = ANY(%s)", (refs[i:i + 5000],))
        kept.update(r["raw_ref"] for r in found)
    return kept


def _quarantine_and_recipe(conn, row: dict) -> tuple:
    """(quarantine items, Recipe body) of a scanned or later upload; one source for both and for the export."""
    data = _clean_of(row)
    ready = row["status"] == "ready"
    report = row["report"] if ready else None
    kept = _kept_refs(conn, data) if ready else None
    items = clean.quarantine_items(data, kept)
    return items, clean.recipe(data, row["sha256"], row["size_bytes"], report, kept)


def _decoded(row: dict) -> dict:
    """Decoded telemetry columns of one stored row, the same ones GET /api/raw returns."""
    decoded = {k: row[k] for k in ("icao24", "callsign", "lat", "lon", "baro_alt_ft", "geo_alt_ft",
                                    "gs_kt", "track_deg", "vrate_fpm", "squawk", "on_ground")
               if row[k] is not None}
    decoded["ts"] = _iso(row["ts"])
    return decoded


@router.get("/api/recordings/{recording_id}/preview")
def preview(recording_id: str, stream: str, limit: int = Query(8, ge=1, le=200)):
    with connect() as conn:
        row = _get(conn, recording_id)
        _require_scanned(row)
        if not any(s["id"] == stream for s in _supported(row)):
            raise HTTPException(status_code=409, detail=f"Stream '{stream}' is not a supported CAT021 stream.")
        data = _clean_of(row)
        if data.get("stream_id", stream) != stream:
            raise HTTPException(status_code=409, detail=f"Only stream '{data['stream_id']}' of this file is read.")
        records = clean.preview_records(data, recording_id, limit)
        if row["status"] == "ready" and records:
            stored = conn.execute(
                "SELECT raw_ref, ts, icao24, callsign, lat, lon, baro_alt_ft, geo_alt_ft, gs_kt, track_deg, "
                "vrate_fpm, squawk, on_ground FROM telemetry WHERE raw_ref = ANY(%s)",
                ([r["raw_ref"] for r in records],),
            ).fetchall()
            by_ref = {r["raw_ref"]: r for r in stored}
            for rec in records:
                if rec["raw_ref"] in by_ref:
                    rec["decoded"] = {**rec["decoded"], **_decoded(by_ref[rec["raw_ref"]])}
    return {"records": records, "field_quality": clean.field_quality(data)}


@router.get("/api/recordings/{recording_id}/recipe")
def recipe(recording_id: str):
    with connect() as conn:
        row = _get(conn, recording_id)
        _require_scanned(row)
        return _quarantine_and_recipe(conn, row)[1]


@router.get("/api/recordings/{recording_id}/quarantine")
def quarantine(recording_id: str, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=500)):
    with connect() as conn:
        row = _get(conn, recording_id)
        _require_scanned(row)
        return clean.page(_quarantine_and_recipe(conn, row)[0], offset, limit)


TELEMETRY_COLUMNS = ("ts", "icao24", "callsign", "lat", "lon", "baro_alt_ft", "geo_alt_ft", "gs_kt", "track_deg",
                     "vrate_fpm", "squawk", "on_ground", "sac", "sic", "track_number", "raw_ref", "raw_offset", "flags")
EVENT_COLUMNS = ("id", "type", "icao24", "callsign", "start_ts", "end_ts", "airport", "severity", "raw_refs")
EXPORT_BATCH = 2000


def _cell(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return _iso(value)
    if isinstance(value, (list, tuple)):
        return " ".join(str(v) for v in value)
    return value


def _write_csv_member(zf: zipfile.ZipFile, name: str, header: tuple, rows) -> None:
    with zf.open(name, "w", force_zip64=True) as member:
        text = io.TextIOWrapper(member, encoding="utf-8", newline="")
        writer = csv.writer(text, lineterminator="\n")
        writer.writerow(header)
        for r in rows:
            writer.writerow(r)
        text.flush()
        text.detach()


def _build_export(conn, row: dict, target) -> None:
    items, body = _quarantine_and_recipe(conn, row)
    rid = row["id"]
    scope = "left({col}, length(%s) + 1) = %s || ':'"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        with conn.transaction():  # a named (server-side) cursor lives inside a transaction
            with conn.cursor(name="export_telemetry") as cur:
                cur.itersize = EXPORT_BATCH
                cur.execute(
                    f"SELECT {', '.join(TELEMETRY_COLUMNS)} FROM telemetry WHERE {scope.format(col='raw_ref')} "
                    "ORDER BY ts, raw_ref",
                    (rid, rid),
                )
                _write_csv_member(zf, "cleaned.csv", TELEMETRY_COLUMNS,
                                  ([_cell(r[c]) for c in TELEMETRY_COLUMNS] for r in cur))
            with conn.cursor(name="export_events") as cur:
                cur.itersize = EXPORT_BATCH
                cur.execute(
                    f"SELECT {', '.join(EVENT_COLUMNS)} FROM events WHERE cardinality(raw_refs) > 0 AND "
                    f"{scope.format(col='raw_refs[1]')} ORDER BY start_ts, id",
                    (rid, rid),
                )
                _write_csv_member(zf, "events.csv", EVENT_COLUMNS,
                                  ([_cell(r[c]) for c in EVENT_COLUMNS] for r in cur))
        _write_csv_member(zf, "quarantine.csv", ("raw_ref", "step_code", "reason"),
                          ([q["raw_ref"], q["step_code"], q["reason"]] for q in items))
        zf.writestr("recipe.json", json.dumps(body, indent=2))


@router.get("/api/recordings/{recording_id}/export")
def export(recording_id: str):
    with connect() as conn:
        row = _get(conn, recording_id)
        if row["status"] != "ready":
            raise HTTPException(status_code=409, detail=f"Recording '{recording_id}' is {row['status']}, not ready.")
        stem = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.splitext(row["filename"])[0]) or recording_id
        tmp = tempfile.NamedTemporaryFile(prefix="flightmind-export-", suffix=".zip", delete=False)
        try:
            with tmp:
                _build_export(conn, row, tmp)
        except BaseException:
            os.unlink(tmp.name)
            raise
    return FileResponse(
        tmp.name,
        media_type="application/zip",
        filename=f"{stem}-flightmind.zip",
        background=BackgroundTask(os.unlink, tmp.name),
    )
