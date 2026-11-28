"""Smoke check for a FlightMind deployment (SCRUM-38, SCRUM-65). Standard library only.

    python infra/smoke.py https://flightmind.vercel.app
    python infra/smoke.py https://<name>.trycloudflare.com --upload

Prints "ok <url>" per passed check. On the first failure prints "FAIL <url>: <reason>"
and exits 1. Exit 2 on bad usage, 0 when every check passes.

--upload also sends fixtures/adsb_sample_500.pcap in parts to the real API, processes its
stream, waits for ready (UPLOAD_TIMEOUT seconds) and reads its events. Only use it against the
real API (scripts/run-upload-demo.ps1); the public Vercel site runs the mock.
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


def send(method: str, url: str, body=None, expect=(200,)):
    """Send body (dict as JSON, or bytes) and return (status, parsed JSON or None)."""
    data, headers = None, {}
    if isinstance(body, dict):
        data, headers = json.dumps(body).encode(), {"Content-Type": "application/json"}
    elif body is not None:
        data, headers = body, {"Content-Type": "application/octet-stream"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with OPENER.open(req, timeout=60) as r:
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


def wait_for(base: str, rid: str, done: tuple) -> dict:
    """Poll the recording until its status is in done; fail on failed or after UPLOAD_TIMEOUT."""
    url = f"{base}/api/recordings/{rid}"
    deadline = time.monotonic() + UPLOAD_TIMEOUT
    while True:
        _, rec = send("GET", url)
        if rec["status"] in done:
            return rec
        if rec["status"] == "failed":
            raise Failure(url, f"recording failed: {rec.get('error')}")
        if time.monotonic() > deadline:
            raise Failure(url, f"still {rec['status']} after {UPLOAD_TIMEOUT} s")
        time.sleep(POLL_SECONDS)


def run_upload(base: str) -> None:
    content = FIXTURE.read_bytes()
    url = base + "/api/recordings"
    _, rec = send("POST", url, {"filename": FIXTURE.name, "size_bytes": len(content)}, expect=(201,))
    rid, part = rec["id"], rec["part_size_bytes"]
    print(f"ok {url} ({rid})")

    for n in range(-(-len(content) // part)):
        send("PUT", f"{url}/{rid}/parts/{n}", content[n * part:(n + 1) * part], expect=(204,))
    print(f"ok {url}/{rid}/parts")

    status, rec = send("POST", f"{url}/{rid}/complete", expect=(200, 202))
    if status == 200:  # the same bytes were uploaded before: the server returns that upload
        rid = rec["id"]
    print(f"ok {url}/{rid}/complete ({rec['status']})")

    rec = wait_for(base, rid, ("scanned", "ready") + PROCESSING)
    if rec["status"] == "scanned":
        stream = next((s for s in rec["streams"] if s["supported"]), None)
        if stream is None:
            raise Failure(f"{url}/{rid}", "no supported stream in the fixture")
        send("POST", f"{url}/{rid}/process", {"stream_id": stream["id"]}, expect=(202,))
    rec = wait_for(base, rid, ("ready",))
    print(f"ok {url}/{rid} (ready)")

    events_url = f"{base}/api/events?recording={urllib.parse.quote(rid)}"
    events = fetch_json(events_url)
    if not isinstance(events, list):
        raise Failure(events_url, "expected a list of events")
    print(f"ok {events_url} ({len(events)} events)")


def run(base: str) -> None:
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


def main(argv: list) -> int:
    args = argv[1:]
    upload = "--upload" in args
    args = [a for a in args if a != "--upload"]
    if len(args) != 1:
        print("usage: python infra/smoke.py <base-url> [--upload]", file=sys.stderr)
        return 2
    try:
        run(args[0])
        if upload:
            run_upload(args[0].rstrip("/"))
    except Failure as f:
        print(f"FAIL {f.url}: {f.reason}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
