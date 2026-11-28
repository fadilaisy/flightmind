"""infra/smoke.py --upload and --upload-file against the mock API on a real socket (SCRUM-65)."""
import importlib.util
import socket
import threading
import time
from pathlib import Path

import pytest
import uvicorn

ROOT = Path(__file__).resolve().parents[3]


def _load_smoke():
    spec = importlib.util.spec_from_file_location("smoke", ROOT / "infra" / "smoke.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


smoke = _load_smoke()


@pytest.fixture(scope="module")
def base():
    from mock_api.app import app

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(5)


def test_upload_reaches_ready_and_a_second_upload_reuses_it(base, capsys):
    smoke.run_upload(base)
    smoke.run_upload(base)  # same bytes: complete answers 200 with the first upload
    lines = capsys.readouterr().out.splitlines()
    first = lines[0].split("(")[1].rstrip(")")
    assert any(line.endswith(f"/{first}/complete (ready)") for line in lines)
    assert sum("(ready)" in line and "/complete" not in line for line in lines) == 2
    second = lines[lines.index(next(line for line in lines if "MB uploaded in" in line)) + 1:]
    assert sum(line.startswith(f"   duplicate of {first},") for line in second) == 1


def test_upload_file_prints_the_times(base, tmp_path, capsys):
    copy = tmp_path / "day1.pcap"
    data = bytearray(smoke.FIXTURE.read_bytes())
    data[-1] ^= 0xFF  # other bytes than the fixture, so it is a new upload
    copy.write_bytes(bytes(data))
    smoke.run_upload(base, copy, timeout=30)
    out = capsys.readouterr().out
    assert "day1.pcap:" in out and "MB uploaded in" in out and "after the upload" in out
    assert "duplicate of" not in out


def test_a_failed_recording_is_a_failure(base, monkeypatch):
    def failed(method, url, body=None, expect=(200,), timeout=60):
        if method == "GET":
            return 200, {"status": "failed", "error": "No CAT021 records found in x.pcap"}
        return real(method, url, body, expect, timeout)

    real = smoke.send
    monkeypatch.setattr(smoke, "send", failed)
    with pytest.raises(smoke.Failure, match="No CAT021 records"):
        smoke.run_upload(base)


def test_upload_runs_the_read_checks_before_it_uploads(base, capsys, monkeypatch):
    real = smoke.fetch
    # The mock API serves no web UI at /; serve.py adds it in a real run.
    monkeypatch.setattr(smoke, "fetch", lambda url: ("text/html", b"") if url == base + "/" else real(url))
    assert smoke.main(["smoke.py", base, "--upload"]) == 0
    lines = capsys.readouterr().out.splitlines()
    raw = next(i for i, line in enumerate(lines) if "/api/raw/" in line)
    post = next(i for i, line in enumerate(lines) if line.startswith(f"ok {base}/api/recordings ("))
    assert raw < post


@pytest.mark.parametrize("argv", [
    ["smoke.py"],
    ["smoke.py", "--upload"],
    ["smoke.py", "http://x", "--upload-file"],
    ["smoke.py", "http://x", "--upload-file", "no-such-file.pcap"],
    ["smoke.py", "http://x", "http://y"],
])
def test_bad_usage_exits_2(argv):
    assert smoke.main(argv) == 2
