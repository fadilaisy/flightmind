"""Cleaning dry run, recipe and quarantine for an upload (SCRUM-68).

There is no ASTERIX decoder on the server at scan time and the pipeline has no cleaning steps
yet, so every number here is counted from the file with the rules the pipeline really applies:

- no_address: the record has no I021/080. The pipeline builds no Point for it
  (points.point_from_block returns None; the report counts it as skipped_no_icao).
- no_position: it has I021/080 but no I021/130. points.py reads lat and lon from I130 only, and
  compress.py drops a point without lat and lon unless an event pins it (dropped_no_position).
  I021/131 is not read by the pipeline, so a record with only I131 still counts as no_position.
- duplicates: the block bytes equal an earlier block of the stream. The pipeline does not drop
  these. They are flagged, kept, and not counted as set aside.

`dry_run` walks the file once and returns the sidecar dict that uploads.py saves as
<upload_dir>/<id>.clean.json. The other functions are pure, so tests need no database.
"""
import hashlib
import json
import os
import struct
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

from . import cat021, raw_file

SAMPLE_SIZE = 200
CAT021 = 21

# (CAT021 item, contract name, label), in display order.
FIELD_QUALITY = (
    ("I130", "I021/130", "Position (WGS-84)"),
    ("I131", "I021/131", "Position, high resolution"),
    ("I080", "I021/080", "Target address (ICAO 24-bit)"),
    ("I140", "I021/140", "Geometric height (WGS-84)"),
    ("I145", "I021/145", "Flight level (pressure, std 1013.25)"),
    ("I170", "I021/170", "Target identification"),
    ("I090", "I021/090", "Quality indicators (NACp)"),
    ("I040", "I021/040", "Target report descriptor"),
)

REASONS = {
    "no_address": "No target address (I021/080); the pipeline cannot assign it to an aircraft.",
    "no_position": "No position (I021/130); it cannot be placed on a track.",
    "duplicates": "Byte-for-byte copy of an earlier record.",
}
LABELS = {
    "no_address": "No target address",
    "no_position": "No position",
    "duplicates": "Duplicate records (flagged, kept)",
}
QUARANTINE_CODES = ("no_address", "no_position")

TOLERANCE_NOTE = (
    "Tracks are reduced within the position error each point reports: 92.6 m for NACp 8 or lower, "
    "30 m for NACp 9, 10 m for NACp 10 and 3 m for NACp 11, and within 25 ft of altitude error. "
    "Points with an unknown NACp, track endpoints, changes of squawk, callsign or on-ground state, "
    "and every record an event cites are always kept."
)
COMPRESSION_REASON = (
    "Dropped points can be rebuilt from their neighbours within the tolerance; event windows are kept whole."
)


# ---------- walking the file ----------

def iter_stream_blocks(path: str, stream: dict) -> Iterator[Tuple[int, int, bytes]]:
    """(record number n from 1, byte offset, ASTERIX block) of every CAT021 block of one stream.

    n counts every packet of the file, as raw_file.iter_offsets and the pipeline's walk_pcap do,
    so it is the number in the raw_ref. Reads end quietly at a record cut short by the file's end,
    as scan_streams does.
    """
    with open(path, "rb") as f:
        kind, order, link_type = raw_file._format(f)
        offsets = raw_file.iter_offsets(f, kind, order)
        while True:
            try:
                index, offset = next(offsets)
                packet = raw_file._packet_at(f, kind, order, offset)
            except StopIteration:
                return
            except (struct.error, IndexError, raw_file.RawFileError):
                return
            if kind == "raw":
                block = packet
            else:
                try:
                    block, ends = raw_file.udp_with_ends(packet, link_type)
                except (raw_file.RawFileError, struct.error, IndexError):
                    continue
                if ends != (stream.get("src"), stream.get("dst")):
                    continue
            if len(block) >= 3 and block[0] == CAT021:
                yield index, offset, block


def classify(items: Set[str]) -> Optional[str]:
    """The quarantine step that sets a record with these items aside, or None."""
    if "I080" not in items:
        return "no_address"
    if "I130" not in items:
        return "no_position"
    return None


def dry_run(path: str, stream: dict, recording_id: str) -> dict:
    """Count what the pipeline would set aside, from the file. Memory use does not grow with the file
    except for the quarantine list (one small entry per set-aside record) and 16 bytes per distinct block."""
    counts = {item: 0 for item, _, _ in FIELD_QUALITY}
    steps = {"no_address": 0, "no_position": 0, "duplicates": 0}
    quarantine: List[dict] = []
    sample: List[dict] = []
    seen: Set[bytes] = set()
    total = 0
    for n, offset, block in iter_stream_blocks(path, stream):
        total += 1
        try:
            items, sac_sic = cat021.items_of_block(block)
        except ValueError:
            items, sac_sic = set(), None  # no readable FSPEC: nothing can be said about the record
        for item in counts:
            if item in items:
                counts[item] += 1
        raw_ref = f"{recording_id}:{n}"
        code = classify(items)
        if code is not None:
            steps[code] += 1
            quarantine.append({"raw_ref": raw_ref, "step_code": code, "reason": REASONS[code]})
        digest = hashlib.blake2b(block, digest_size=16).digest()
        if digest in seen:
            if code is None:  # a copy that is already set aside is not counted twice
                steps["duplicates"] += 1
        else:
            seen.add(digest)
        if len(sample) < SAMPLE_SIZE:
            sample.append({
                "raw_ref": raw_ref,
                "record_index": n,
                "offset": offset,
                "items": sorted(items),
                "sac": sac_sic[0] if sac_sic else None,
                "sic": sac_sic[1] if sac_sic else None,
                "hex": block.hex().upper(),
            })
    return {
        "records_total": total,
        "item_counts": counts,
        "quarantine": quarantine,
        "steps": steps,
        "sample": sample,
    }


# ---------- sidecar ----------

def sidecar_path(upload_path: str, recording_id: str) -> Path:
    return Path(upload_path).parent / f"{recording_id}.clean.json"


def save(path: Path, clean: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(clean, separators=(",", ":")), encoding="utf-8")
    os.replace(tmp, path)


def load(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return None


def remove_files(upload_path: str, recording_id: str) -> None:
    """Delete an upload's file and its sidecar."""
    Path(upload_path).unlink(missing_ok=True)
    sidecar_path(upload_path, recording_id).unlink(missing_ok=True)
    sidecar_path(upload_path, recording_id).with_name(f"{recording_id}.clean.json.tmp").unlink(missing_ok=True)


# ---------- views built from the sidecar (pure) ----------

def field_quality(clean: dict) -> List[dict]:
    total = clean["records_total"]
    return [
        {
            "item": name,
            "label": label,
            "present_pct": round(100 * clean["item_counts"].get(item, 0) / total, 1) if total else 0.0,
        }
        for item, name, label in FIELD_QUALITY
    ]


def preview_records(clean: dict, recording_id: str, limit: int) -> List[dict]:
    """The first `limit` sample records as RawRecord, with decoded = {"items": [...]}."""
    out = []
    for s in clean["sample"][:limit]:
        rec: Dict[str, Any] = {
            "raw_ref": s["raw_ref"],
            "recording_file_id": recording_id,
            "record_index": s["record_index"],
            "hex": s["hex"],
            "decoded": {"items": list(s["items"])},
        }
        if s["sac"] is not None:
            rec["sac"] = s["sac"]
        if s["sic"] is not None:
            rec["sic"] = s["sic"]
        out.append(rec)
    return out


def quarantine_items(clean: dict, kept_refs: Optional[Set[str]] = None) -> List[dict]:
    """The records set aside, in record order. kept_refs are raw_refs the pipeline stored anyway
    (an event pinned a record without a position), so they were not set aside."""
    kept = kept_refs or set()
    return [q for q in clean["quarantine"] if q["raw_ref"] not in kept]


def recipe(clean: dict, sha256: Optional[str], raw_bytes: int, report: Optional[dict] = None,
           kept_refs: Optional[Set[str]] = None) -> dict:
    """The Recipe body. report is the pipeline report once the recording is ready, else None."""
    total = clean["records_total"]
    listed = {code: 0 for code in QUARANTINE_CODES}
    for q in quarantine_items(clean, kept_refs):
        listed[q["step_code"]] += 1
    counts = dict(listed)
    if report:  # what the pipeline really did wins over the dry run
        counts["no_address"] = int(report.get("skipped_no_icao") or 0)
        counts["no_position"] = int(report.get("dropped_no_position") or 0)
    steps, left = [], total
    for code in QUARANTINE_CODES:
        reason = REASONS[code]
        if counts[code] > listed[code]:
            reason += f" {listed[code]} of them can be listed in quarantine."
        steps.append({"code": code, "label": LABELS[code], "records_in": left, "set_aside": counts[code], "reason": reason})
        left -= counts[code]
    dups = clean["steps"]["duplicates"]
    steps.append({
        "code": "duplicates",
        "label": LABELS["duplicates"],
        "records_in": left,
        "set_aside": 0,
        "reason": f"{dups} {'record is a' if dups == 1 else 'records are'} byte-for-byte "
                  f"{'copy' if dups == 1 else 'copies'} of an earlier record. They are flagged and kept.",
    })
    stored_bytes: Optional[int] = None
    ratio: Optional[float] = None
    if report:
        decoded = int(report.get("decoded_points") or 0)
        no_position = int(report.get("dropped_no_position") or 0)
        stored = int(report.get("rows_stored") or 0)
        positioned = max(decoded - no_position, 0)
        steps.append({
            "code": "compression",
            "label": "Track reduction within tolerance",
            "records_in": positioned,
            "set_aside": max(positioned - stored, 0),
            "reason": COMPRESSION_REASON,
        })
        if report.get("stored_bytes") is not None:
            stored_bytes = int(report["stored_bytes"])
            ratio = report.get("ratio_bytes")
            if ratio is None and raw_bytes:
                ratio = stored_bytes / raw_bytes
    return {
        "input_sha256": sha256,
        "steps": steps,
        "tolerance_note": TOLERANCE_NOTE,
        "raw_bytes": raw_bytes,
        "stored_bytes": stored_bytes,
        "ratio": ratio,
    }


def page(items: List[dict], offset: int, limit: int) -> dict:
    return {"total": len(items), "items": items[offset:offset + limit]}
