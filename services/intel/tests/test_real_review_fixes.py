"""Cases from the PR #28 and #29 reviews: bad frames, retries, failed-then-retry, safe errors, agent scope."""
import struct

import httpx
import pytest

from real_api import raw_file
from realdb import FIXTURE_PCAP
from test_real_uploads import drop_first, env, db, get, upload  # noqa: F401  (fixtures)


def _record(frame: bytes) -> bytes:
    return struct.pack("<IIII", 1, 0, len(frame), len(frame)) + frame


def with_junk(data: bytes) -> bytes:
    """data plus a 10-byte frame (as a short snaplen leaves) and an ARP frame."""
    arp = b"\xff" * 6 + b"\x00" * 6 + b"\x08\x06" + bytes(28)
    return data + _record(b"\x01" * 10) + _record(arp)


def two_streams(data: bytes) -> bytes:
    """The fixture with packets 251 on sent to another UDP port, so it holds two CAT021 streams."""
    out, pos, index = bytearray(data), 24, 0
    while pos + 16 <= len(out):
        cap = struct.unpack("<I", out[pos + 8:pos + 12])[0]
        index += 1
        if index > 250:
            port = pos + 16 + 14 + 20 + 2
            out[port:port + 2] = struct.pack(">H", 28702)
        pos += 16 + cap
    return bytes(out)


# ---------- no database ----------

def test_truncated_record_is_a_raw_file_error(tmp_path):
    path = tmp_path / "cut.pcap"
    path.write_bytes(FIXTURE_PCAP.read_bytes() + struct.pack("<IIII", 1, 0, 400, 400) + b"\x01" * 10)
    with pytest.raises(raw_file.RawFileError):
        raw_file.read_block(str(path), 501, None)
    assert raw_file.read_block(str(path), 500, None) == raw_file.read_block(str(FIXTURE_PCAP), 500, None)


def test_non_udp_frames_are_raw_file_errors():
    for frame in (b"\x01" * 10, b"\xff" * 12 + b"\x08\x06" + bytes(28), b"\x00" * 12 + b"\x08\x00" + b"\x45" + bytes(5)):
        with pytest.raises(raw_file.RawFileError):
            raw_file.udp_ipv4(frame, raw_file.LINK_ETHERNET)


def test_scan_skips_truncated_and_non_ip_frames(tmp_path):
    from real_api.uploads import scan_streams

    path = tmp_path / "junk.pcap"
    path.write_bytes(with_junk(FIXTURE_PCAP.read_bytes()))
    assert [(s["category"], s["frames"]) for s in scan_streams(str(path))] == [(21, 500)]


def test_error_text_hides_server_paths():
    from real_api.uploads import GENERIC_ERROR, one_sentence

    assert one_sentence(RuntimeError(r"C:\Users\someone\data\r1.pcap: decoder produced 4 blocks")) == (
        "r1.pcap: decoder produced 4 blocks."
    )
    assert one_sentence(RuntimeError("/srv/flightmind/data/r1.pcap: bad")) == "r1.pcap: bad."
    assert one_sentence(FileNotFoundError(2, "No such file", r"C:\x\y")) == GENERIC_ERROR


@pytest.mark.anyio
async def test_agent_client_scopes_events_and_tracks_to_the_recording():
    from agent.api_client import ApiClient

    seen = []

    def handler(request):
        seen.append((request.url.path, dict(request.url.params)))
        body = [] if request.url.path == "/api/events" else {"icao24": "8A0F21", "points": []}
        return httpx.Response(200, json=body)

    api = ApiClient("http://api", transport=httpx.MockTransport(handler), recording="r0123456789")
    await api.events(type="holding")
    await api.track("8A0F21")
    assert seen == [
        ("/api/events", {"type": "holding", "recording": "r0123456789"}),
        ("/api/tracks/8A0F21", {"recording": "r0123456789"}),
    ]


# ---------- database ----------

@pytest.mark.db
def test_upload_with_junk_frames_scans_and_raw_404s(env):
    client, uploads = env["client"], env["uploads"]
    rid, r = upload(client, with_junk(drop_first(5)))
    assert r.status_code == 202
    uploads.run_pending_once()
    rec = get(client, rid)
    assert rec["status"] == "scanned", rec["error"]
    assert [(s["category"], s["frames"]) for s in rec["streams"]] == [(21, 495)]


@pytest.mark.db
def test_a_failed_upload_does_not_block_the_same_file(env, monkeypatch):
    client, uploads = env["client"], env["uploads"]

    def broken(path, recording_id, dsn, on_progress=None, recording_date=None):
        raise ValueError("No CAT021 records found in flight.pcap")

    monkeypatch.setattr(uploads, "runner", broken)
    content = drop_first(6)
    first, _ = upload(client, content)
    uploads.run_pending_once()
    client.post(f"/api/recordings/{first}/process", json={"stream_id": "s1"})
    uploads.run_pending_once()
    assert get(client, first)["status"] == "failed"
    second, r = upload(client, content)
    assert r.status_code == 202 and second != first


@pytest.mark.db
def test_complete_refuses_raw_bytes_in_a_pcap_name(env):
    _, r = upload(env["client"], b"\x15\x00\x30" + bytes(45), filename="day1.pcap")
    assert r.status_code == 415 and "name it" in r.json()["detail"]


@pytest.mark.db
def test_file_with_two_cat021_streams_cannot_be_processed_yet(env):
    client, uploads = env["client"], env["uploads"]
    rid, _ = upload(client, two_streams(drop_first(7)))
    uploads.run_pending_once()
    assert [s["supported"] for s in get(client, rid)["streams"]] == [True, True]
    r = client.post(f"/api/recordings/{rid}/process", json={"stream_id": "s1"})
    assert r.status_code == 409 and "2 CAT021 streams" in r.json()["detail"]


@pytest.mark.db
def test_users_never_see_server_paths(env, monkeypatch):
    client, uploads = env["client"], env["uploads"]

    def broken(path, recording_id, dsn, on_progress=None, recording_date=None):
        open(str(path) + ".missing")

    monkeypatch.setattr(uploads, "runner", broken)
    rid, _ = upload(client, drop_first(8))
    uploads.run_pending_once()
    client.post(f"/api/recordings/{rid}/process", json={"stream_id": "s1"})
    uploads.run_pending_once()
    rec = get(client, rid)
    assert rec["status"] == "failed" and rec["error"] == uploads.GENERIC_ERROR
    assert not (env["dir"] / f"{rid}.pcap").exists()  # a failed upload's file is deleted
