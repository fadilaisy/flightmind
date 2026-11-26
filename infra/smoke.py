"""Smoke check for a FlightMind deployment (SCRUM-38). Standard library only.

    python infra/smoke.py https://<name>.up.railway.app

Prints "ok <url>" per passed check. On the first failure prints "FAIL <url>: <reason>"
and exits 1. Exit 2 on bad usage, 0 when every check passes.
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT = 10


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
    if len(argv) != 2:
        print("usage: python infra/smoke.py <base-url>", file=sys.stderr)
        return 2
    try:
        run(argv[1])
    except Failure as f:
        print(f"FAIL {f.url}: {f.reason}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
