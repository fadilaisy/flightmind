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

One worker thread per process handles one job at a time. It starts with the app (and, when
serve.py hides the app's startup, on the first upload request). On start, rows left in
decoding..storing become failed and uploads stuck in uploading for over an hour are deleted.

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
import secrets
import struct
import threading
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from . import raw_file
from .db import connect, dsn

log = logging.getLogger("flightmind.uploads")

REPO_ROOT = Path(__file__).resolve().parents[3]
FORMATS = {".pcap": "pcap", ".pcapng": "pcapng", ".atx": "asterix_raw", ".ast": "asterix_raw", ".bin": "asterix_raw"}
PROCESSING = ("decoding", "filtering", "detecting", "storing")
RESTART_ERROR = "Server restarted during processing. Upload again."
STALE_UPLOAD = timedelta(hours=1)
CAT021 = 21


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


def one_sentence(exc: BaseException) -> str:
    text = " ".join(str(exc).split()) or type(exc).__name__
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

def sniff(head: bytes) -> Optional[str]:
    """pcap, pcapng or asterix_raw from the first bytes; None when it is none of them."""
    if head[:4] in raw_file.PCAP_MAGICS:
        return "pcap"
    if head[:4] == raw_file.PCAPNG_SHB:
        return "pcapng"
    if len(head) >= 3 and head[0] == CAT021 and struct.unpack(">H", head[1:3])[0] >= 3:
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
        for _index, offset in raw_file.iter_offsets(f, kind, order):
            packet = raw_file._packet_at(f, kind, order, offset)
            if kind == "raw":
                key, block = ("", ""), packet
            else:
                try:
                    block, key = _udp_with_ends(packet, link_type)
                except raw_file.RawFileError:
                    continue
            if len(block) < 3:
                continue
            entry = found.setdefault(key + (block[0],), {"frames": 0, "sac_sic": _sac_sic(block)})
            entry["frames"] += 1
    streams = []
    for (src, dst, category), entry in sorted(found.items(), key=lambda kv: -kv[1]["frames"]):
        sac, sic = entry["sac_sic"]
        supported = category == CAT021
        streams.append({
            "id": "raw" if kind == "raw" else f"s{len(streams) + 1}",
            "src": src, "dst": dst, "category": category, "sac": sac, "sic": sic,
            "frames": 0 if kind == "raw" else entry["frames"],
            "records": entry["frames"] if supported else 0,
            "supported": supported,
        })
        if kind == "raw":
            break  # a raw file is one stream
    return streams


def _udp_with_ends(packet: bytes, link_type: int) -> tuple:
    """(ASTERIX payload, (src ip:port, dst ip:port)) of one UDP packet."""
    ip = raw_file.udp_ipv4(packet, link_type)
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
        log.warning("scan of %s failed: %s", row["id"], type(exc).__name__)
        with connect() as conn:
            _set(conn, row["id"], status="failed", error=one_sentence(exc))


def _process(row: dict) -> None:
    recording_id = row["id"]

    def on_progress(stage: str, done: int, total: int) -> None:
        if stage not in PROCESSING:
            return
        with connect() as conn:
            _set(conn, recording_id, status=stage, records_done=done, records_total=total)

    try:
        report = _runner()(row["path"], recording_id, dsn(), on_progress, row["recording_date"])
        records = int(report.get("raw_records") or 0)
        with connect() as conn:
            _set(conn, recording_id, status="ready", report=report, error=None,
                 records_done=records, records_total=records)
    except Exception as exc:  # any failure is reported on the row, never raised
        log.warning("processing of %s failed: %s", recording_id, type(exc).__name__)
        with connect() as conn:
            _set(conn, recording_id, status="failed", error=one_sentence(exc))


def _loop() -> None:
    while not _stop.is_set():
        try:
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


@router.put("/api/recordings/{recording_id}/parts/{n}", status_code=204)
async def upload_part(recording_id: str, n: int, request: Request):
    chunk = await request.body()
    _append(recording_id, n, chunk)
    return Response(status_code=204)


def _append(recording_id: str, n: int, chunk: bytes) -> None:
    size = part_size()
    with connect() as conn:
        with conn.transaction():
            row = _get(conn, recording_id, lock=True)
            if row["status"] != "uploading":
                raise HTTPException(status_code=409, detail=f"Recording '{recording_id}' is no longer uploading.")
            received = row["bytes_received"]
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
            if row["bytes_received"] < row["size_bytes"] or on_disk != row["size_bytes"]:
                raise HTTPException(
                    status_code=409,
                    detail=f"Only {row['bytes_received']} of {row['size_bytes']} bytes arrived; send the missing parts first.",
                )
            with path.open("rb") as f:
                fmt = sniff(f.read(8))
            if fmt is None:
                raise HTTPException(status_code=415, detail="The file does not start like pcap, pcapng or an ASTERIX CAT021 block.")
            sha = _sha256(path)
            earlier = conn.execute("SELECT * FROM uploads WHERE sha256 = %s FOR UPDATE", (sha,)).fetchone()
            if earlier is not None and earlier["status"] != "failed":
                conn.execute("DELETE FROM uploads WHERE id = %s", (recording_id,))
                path.unlink(missing_ok=True)
                response.status_code = 200
                return _view_of(conn, earlier["id"])
            if earlier is not None:  # a failed upload of the same file: this one replaces it
                conn.execute("DELETE FROM uploads WHERE id = %s", (earlier["id"],))
                if earlier["path"] != str(path):
                    Path(earlier["path"]).unlink(missing_ok=True)
            _set(conn, recording_id, sha256=sha, format=fmt, status="scanning")
            result = _view_of(conn, recording_id)
    wake()
    response.status_code = 202
    return result


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
            if not any(s["id"] == body.stream_id and s["supported"] for s in row["streams"] or []):
                raise HTTPException(status_code=409, detail=f"Stream '{body.stream_id}' is not a supported CAT021 stream.")
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
