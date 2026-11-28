"""Smoke check for a FlightMind deployment (SCRUM-38, SCRUM-65). Standard library only.

    python infra/smoke.py https://flightmind.vercel.app
    python infra/smoke.py https://<name>.trycloudflare.com --upload

Prints "ok <url>" per passed check. On the first failure prints "FAIL <url>: <reason>"
and exits 1. Exit 2 on bad usage, 0 when every check passes.

--upload runs the read checks first, on the recording the app opens by default. Then it sends
fixtures/adsb_sample_500.pcap in parts to the real API, processes its stream, waits for ready
(UPLOAD_TIMEOUT seconds) and reads that recording's events. Only use it against the real API
(scripts/run-upload-demo.ps1); the public Vercel site runs the mock. Unless the server pins
FLIGHTMIND_DEFAULT_RECORDING (-DefaultRecording), the upload becomes the recording everyone opens.

--upload-file <recording> does the same with a recording of your own (one hour to reach ready)
and prints the upload time and the time to ready, for infra/README.md (SCRUM-65).
"""
import json
import sys
import time
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT = 10
UPLOAD_TIMEOUT = 120
LARGE_TIMEOUT = 3600
PART_TIMEOUT = 600  # one 50 MB part on a slow uplink
POLL_SECONDS = 2
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "adsb_sample_500.pcap"
PROCESSING = ("queued", "decoding", "filtering", "detecting", "storing")


class Failure(Exception):
    def __init__(self, url: str, reason: str) -> None:
        super().__init__(reason)
        self.url = url
        self.reason = reason


class SameHostRedirect(urllib.request.HTTPRedirectHandler):
    """Follow redirects only when they stay on the same host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).netloc != urllib.parse.urlsplit(req.full_url).netloc:
            raise urllib.error.HTTPError(req.full_url, code, f"redirect to another host: {newurl}", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = urllib.request.build_opener(SameHostRedirect)


def fetch(url: str):
    """Return (content_type, body_bytes) for a 200 response, else raise Failure."""
    try:
        with OPENER.open(urllib.request.Request(url), timeout=TIMEOUT) as r:
            if r.status != 200:
                raise Failure(url, f"status {r.status}, expected 200")
            return r.headers.get("Content-Type", ""), r.read()
    except Failure:
        raise
    except urllib.error.HTTPError as e:
        raise Failure(url, f"status {e.code} {e.reason}")
    except urllib.error.URLError as e:
        raise Failure(url, f"cannot connect: {e.reason}")
    except OSError as e:  # timeouts, resets
        raise Failure(url, f"request failed: {e}")


def fetch_json(url: str):
    _, body = fetch(url)
    try:
        return json.loads(body)
    except ValueError:
        raise Failure(url, "body is not valid JSON")


def send(method: str, url: str, body=None, expect=(200,), timeout: float = 60):
    """Send body (dict as JSON, or bytes) and return (status, parsed JSON or None)."""
    data, headers = None, {}
    if isinstance(body, dict):
        data, headers = json.dumps(body).encode(), {"Content-Type": "application/json"}
    elif body is not None:
        data, headers = body, {"Content-Type": "application/octet-stream"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with OPENER.open(req, timeout=timeout) as r:
            status, raw = r.status, r.read()
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read()
    except urllib.error.URLError as e:
        raise Failure(url, f"cannot connect: {e.reason}")
    except OSError as e:
        raise Failure(url, f"request failed: {e}")
    try:
        parsed = json.loads(raw) if raw else None
    except ValueError:
        parsed = None
    if status not in expect:
        detail = parsed.get("detail") if isinstance(parsed, dict) else raw[:200]
        raise Failure(url, f"status {status}, expected {' or '.join(map(str, expect))}: {detail}")
    return status, parsed


def wait_for(base: str, rid: str, done: tuple, timeout: float = UPLOAD_TIMEOUT) -> dict:
    """Poll the recording until its status is in done; fail on failed or after timeout seconds."""
    url = f"{base}/api/recordings/{rid}"
    deadline = time.monotonic() + timeout
    while True:
        _, rec = send("GET", url)
        if rec["status"] in done:
            return rec
        if rec["status"] == "failed":
            raise Failure(url, f"recording failed: {rec.get('error')}")
        if time.monotonic() > deadline:
            raise Failure(url, f"still {rec['status']} after {timeout:.0f} s")
        time.sleep(POLL_SECONDS)


def run_upload(base: str, path: Path = FIXTURE, timeout: float = UPLOAD_TIMEOUT) -> None:
    size = path.stat().st_size
    url = base + "/api/recordings"
    started = time.monotonic()
    _, rec = send("POST", url, {"filename": path.name, "size_bytes": size}, expect=(201,))
    rid, part = rec["id"], rec["part_size_bytes"]
    print(f"ok {url} ({rid})")

    parts = -(-size // part)
    with path.open("rb") as f:
        for n in range(parts):
            send("PUT", f"{url}/{rid}/parts/{n}", f.read(part), expect=(204,), timeout=PART_TIMEOUT)
            if parts > 3:
                print(f"   part {n + 1}/{parts}", flush=True)
    print(f"ok {url}/{rid}/parts")

    status, rec = send("POST", f"{url}/{rid}/complete", expect=(200, 202))
    duplicate = status == 200  # the same bytes were uploaded before: the server returns that upload
    if duplicate:
        rid = rec["id"]
    print(f"ok {url}/{rid}/complete ({rec['status']})")

    uploaded = time.monotonic()

    rec = wait_for(base, rid, ("scanned", "ready") + PROCESSING, timeout)
    if rec["status"] == "scanned":
        stream = next((s for s in rec["streams"] if s["supported"]), None)
        if stream is None:
            raise Failure(f"{url}/{rid}", f"no supported stream in {path.name}")
        send("POST", f"{url}/{rid}/process", {"stream_id": stream["id"]}, expect=(202,))
    rec = wait_for(base, rid, ("ready",), timeout)
    print(f"ok {url}/{rid} (ready)")
    ready = time.monotonic()
    mb = size / 1e6
    print(f"   {path.name}: {mb:.1f} MB uploaded in {uploaded - started:.1f} s "
          f"({mb / max(uploaded - started, 1e-3):.1f} MB/s); ready {ready - uploaded:.1f} s after the upload")
    if duplicate:
        print(f"   duplicate of {rid}, which the server already had: these are not upload times, "
              "so leave them out of the README table")

    events_url = f"{base}/api/events?recording={urllib.parse.quote(rid)}"
    events = fetch_json(events_url)
    if not isinstance(events, list):
        raise Failure(events_url, "expected a list of events")
    print(f"ok {events_url} ({len(events)} events)")


def run(base: str, allow_no_events: bool = False) -> None:
    base = base.rstrip("/")

    url = base + "/"
    ctype, _ = fetch(url)
    if "text/html" not in ctype.lower():
        raise Failure(url, f"Content-Type is {ctype!r}, expected text/html")
    print(f"ok {url}")

    url = base + "/api/meta"
    meta = fetch_json(url)
    if not isinstance(meta, dict) or meta.get("mode") != "replay":
        raise Failure(url, f"mode is {meta.get('mode') if isinstance(meta, dict) else meta!r}, expected 'replay'")
    print(f"ok {url}")

    url = base + "/api/events"
    events = fetch_json(url)
    if isinstance(events, list) and not events and allow_no_events:
        # The fixture has no detected events, so a database holding only it has none to read.
        print(f"ok {url} (empty; skipping the event, raw and track checks)")
        return
    if not isinstance(events, list) or not events:
        raise Failure(url, "expected a non-empty list of events")
    first = events[0]
    if not isinstance(first, dict) or "id" not in first or "icao24" not in first:
        raise Failure(url, "first event has no id or icao24")
    print(f"ok {url}")

    url = f"{base}/api/events/{urllib.parse.quote(str(first['id']), safe='')}"
    detail = fetch_json(url)
    refs = detail.get("raw_refs") if isinstance(detail, dict) else None
    if not refs:
        raise Failure(url, "event detail has no raw_refs")
    print(f"ok {url}")

    url = f"{base}/api/raw/{urllib.parse.quote(str(refs[0]), safe='')}"
    fetch_json(url)
    print(f"ok {url}")

    url = f"{base}/api/tracks/{urllib.parse.quote(str(first['icao24']), safe='')}"
    track = fetch_json(url)
    if not isinstance(track, dict) or not track.get("points"):
        raise Failure(url, "track has no points")
    print(f"ok {url}")


USAGE = "usage: python infra/smoke.py <base-url> [--upload] [--upload-file <recording>]"


def main(argv: list) -> int:
    args, upload, files = argv[1:], False, []
    while "--upload-file" in args:
        i = args.index("--upload-file")
        if i + 1 >= len(args) or not Path(args[i + 1]).is_file():
            print(USAGE, file=sys.stderr)
            return 2
        files.append(Path(args[i + 1]))
        del args[i:i + 2]
    if "--upload" in args:
        upload = True
        args.remove("--upload")
    if len(args) != 1:
        print(USAGE, file=sys.stderr)
        return 2
    base = args[0].rstrip("/")
    try:
        # Before the uploads, while the default is still the recording with events, so the
        # event, raw and track checks run. An empty database has none: skip them then.
        run(base, allow_no_events=upload or bool(files))
        if upload:
            run_upload(base)
        for path in files:  # a big recording: an hour for upload and processing each
            run_upload(base, path, timeout=LARGE_TIMEOUT)
    except Failure as f:
        print(f"FAIL {f.url}: {f.reason}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
