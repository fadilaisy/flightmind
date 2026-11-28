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

Preview, recipe, quarantine and export are SCRUM-68 and answer 501 until then.

Environment:
    FLIGHTMIND_UPLOAD_DIR        where uploaded files are kept (default <repo>/data/uploads)
    FLIGHTMIND_MAX_UPLOAD_MB     largest file accepted (default 2048)
    FLIGHTMIND_PART_SIZE_BYTES   part size given to clients (default 52428800; tests lower it)
    FLIGHTMIND_UPLOAD_WORKER     "off" keeps the worker thread from starting (tests)
"""
import hashlib
import importlib
import logging
import os
import re
import secrets
import shutil
import struct
import threading
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi import Path as PathParam
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from . import raw_file
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
    ip = raw_file.udp_ipv4(packet, link_type)  # checks that ip holds the full UDP header
    ihl = (ip[0] & 0x0F) * 4
    sport, dport = struct.unpack(">HH", ip[ihl:ihl + 4])
    src = ".".join(str(b) for b in ip[12:16]) + f":{sport}"
    dst = ".".join(str(b) for b in ip[16:20]) + f":{dport}"
    return ip[ihl + 8:], (src, dst)


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
            "DELETE FROM uploads WHERE status = 'uploading' AND updated_at < now() - %s RETURNING path",
            (STALE_UPLOAD,),
        ).fetchall()
    for row in stale:
        Path(row["path"]).unlink(missing_ok=True)


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
        if not any(s["supported"] for s in streams):
            raise ValueError(f"No CAT021 records found in {row['filename']}")
        with connect() as conn:
            _set(conn, row["id"], status="scanned", streams=streams, error=None)
    except Exception as exc:  # any failure is reported on the row, never raised
        log.exception("scan of %s failed", row["id"])
        with connect() as conn:
            _set(conn, row["id"], status="failed", error=one_sentence(exc))
        Path(row["path"]).unlink(missing_ok=True)  # nothing can use the file now


def _process(row: dict) -> None:
    recording_id = row["id"]
    last = {"stage": None, "at": 0.0}
    try:
        with connect() as conn:  # one connection for every progress update of this job

            def on_progress(stage: str, done: int, total: int) -> None:
                if stage not in PROCESSING:
                    return
                now = time.monotonic()
                if stage == last["stage"] and now - last["at"] < PROGRESS_EVERY_SECONDS and done < total:
                    return  # SCRUM-63 reports every 1000 records; the UI polls every 2 s
                last.update(stage=stage, at=now)
                _set(conn, recording_id, status=stage, records_done=done, records_total=total)

            report = _runner()(row["path"], recording_id, dsn(), on_progress, row["recording_date"])
            records = int(report.get("raw_records") or 0)
            _set(conn, recording_id, status="ready", report=report, error=None,
                 records_done=records, records_total=records)
    except Exception as exc:  # any failure is reported on the row, never raised
        log.exception("processing of %s failed", recording_id)
        _fail_processing(row, exc)


def _fail_processing(row: dict, exc: Exception) -> None:
    """Mark the job failed on a fresh connection, since the job's own one may be what dropped."""
    try:
        with connect() as conn:
            _set(conn, row["id"], status="failed", error=one_sentence(exc))
            stored = conn.execute("SELECT 1 FROM recording_files WHERE id = %s", (row["id"],)).fetchone()
    except Exception:
        log.exception("could not mark %s failed; recover() does at the next start", row["id"])
        return
    if stored is None:  # nothing cites the file, so it only takes disk space
        Path(row["path"]).unlink(missing_ok=True)


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
                # Only the length is compared: /complete checks the sha256 of the whole file.
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
                path.unlink(missing_ok=True)
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


def _not_built(recording_id: str) -> None:
    with connect() as conn:
        _get(conn, recording_id)
    raise HTTPException(status_code=501, detail="Not built yet in the real API (SCRUM-68).")


@router.get("/api/recordings/{recording_id}/preview")
def preview(recording_id: str):
    _not_built(recording_id)


@router.get("/api/recordings/{recording_id}/recipe")
def recipe(recording_id: str):
    _not_built(recording_id)


@router.get("/api/recordings/{recording_id}/quarantine")
def quarantine(recording_id: str):
    _not_built(recording_id)


@router.get("/api/recordings/{recording_id}/export")
def export(recording_id: str):
    _not_built(recording_id)
