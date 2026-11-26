"""Read packet positions from a pcap file and run the ASTERIX decoder on it."""

import json
import os
import shlex
import struct
import subprocess
import tempfile
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

PCAP_LE_MAGIC = b"\xd4\xc3\xb2\xa1"
PCAP_FILE_HEADER_LEN = 24
PCAP_RECORD_HEADER_LEN = 16


def walk_pcap(path: str | os.PathLike[str]) -> Iterator[tuple[int, int, datetime]]:
    """Yield (record_index, byte_offset, ts_utc) for each packet, record_index starting at 1."""
    with open(path, "rb") as f:
        header = f.read(PCAP_FILE_HEADER_LEN)
        if header[:4] != PCAP_LE_MAGIC:
            raise ValueError(
                f"{os.fspath(path)}: only little-endian classic pcap is supported, "
                f"found magic bytes {header[:4].hex(' ')}"
            )
        record_index = 0
        while True:
            offset = f.tell()
            rec = f.read(PCAP_RECORD_HEADER_LEN)
            if len(rec) < PCAP_RECORD_HEADER_LEN:
                return
            ts_sec, ts_usec, cap_len, _orig_len = struct.unpack("<IIII", rec)
            record_index += 1
            ts = datetime.fromtimestamp(ts_sec, UTC) + timedelta(microseconds=ts_usec)
            yield record_index, offset, ts
            f.seek(cap_len, os.SEEK_CUR)


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if value is None:
        raise KeyError(f"missing environment variable {name}")
    return value


def _cygpath(windows_path: str) -> str:
    """E:\\a\\b -> /cygdrive/e/a/b, the form bash inside Cygwin expects."""
    if len(windows_path) < 3 or windows_path[1:3] != ":\\":
        raise ValueError(f"not an absolute Windows path with a drive letter: {windows_path!r}")
    return f"/cygdrive/{windows_path[0].lower()}{windows_path[2:].replace(chr(92), '/')}"


def decode_blocks(path: str | os.PathLike[str]) -> Iterator[dict]:
    """Run the ASTERIX decoder in JSON-per-line mode and yield one dict per output line."""
    asterix_dir = _require_env("FLIGHTMIND_ASTERIX_DIR")
    cygwin_bin = _require_env("FLIGHTMIND_CYGWIN_BIN")

    script = (
        f"cd {shlex.quote(_cygpath(asterix_dir))} && "
        f"./asterix.exe -P -d config/asterix.ini -j "
        f"-f {shlex.quote(_cygpath(os.path.abspath(path)))}"
    )
    env = dict(os.environ)
    env["PATH"] = cygwin_bin + os.pathsep + env.get("PATH", "")
    bash = os.path.join(cygwin_bin, "bash.exe")

    # stderr goes to a file so a chatty decoder cannot fill a pipe and block stdout.
    with tempfile.TemporaryFile() as err:
        proc = subprocess.Popen(
            [bash, "-lc", script], stdout=subprocess.PIPE, stderr=err, env=env
        )
        stdout = proc.stdout
        assert stdout is not None  # set by Popen because stdout=PIPE
        try:
            for raw in stdout:
                line = raw.strip()
                if line.startswith(b"{"):
                    yield json.loads(line)
            returncode = proc.wait()
        finally:
            # The consumer stopped early: stop the decoder instead of leaving it running.
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            stdout.close()
        if returncode != 0:
            err.seek(0)
            message = err.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"decoder exited with code {returncode}: {message}")
