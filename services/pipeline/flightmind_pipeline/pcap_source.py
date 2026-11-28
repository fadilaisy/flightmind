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


LINK_ETHERNET, LINK_RAW, LINK_RAW_IP, LINK_LINUX_SLL = 1, 101, 228, 113


def udp_endpoints(packet: bytes, link_type: int) -> tuple[str, str] | None:
    """Return ("src ip:port", "dst ip:port") of a UDP-over-IPv4 frame, or None for anything else."""
    found = udp_datagram(packet, link_type)
    return None if found is None else found[0]


def udp_datagram(packet: bytes, link_type: int) -> tuple[tuple[str, str], bytes] | None:
    """Return (("src ip:port", "dst ip:port"), UDP payload) of a UDP-over-IPv4 frame, else None.

    Same endpoint strings as the upload API's stream scan, so a stream id can be matched by
    its endpoints. Every length is checked, so a truncated frame gives None.
    """
    if link_type == LINK_ETHERNET:
        pos = 12
        while True:
            if len(packet) < pos + 2:
                return None
            ether_type = struct.unpack(">H", packet[pos : pos + 2])[0]
            if ether_type in (0x8100, 0x88A8):  # VLAN tags
                pos += 4
                continue
            break
        if ether_type != 0x0800:
            return None
        ip = packet[pos + 2 :]
    elif link_type == LINK_LINUX_SLL:
        ip = packet[16:]
    elif link_type in (LINK_RAW, LINK_RAW_IP):
        ip = packet
    else:
        return None
    if len(ip) < 20 or ip[0] >> 4 != 4 or ip[9] != 17:
        return None
    ihl = (ip[0] & 0x0F) * 4
    if ihl < 20 or len(ip) < ihl + 8:
        return None
    sport, dport = struct.unpack(">HH", ip[ihl : ihl + 4])
    src = ".".join(str(b) for b in ip[12:16]) + f":{sport}"
    dst = ".".join(str(b) for b in ip[16:20]) + f":{dport}"
    return (src, dst), ip[ihl + 8 :]


def walk_pcap_streams(
    path: str | os.PathLike[str],
) -> Iterator[tuple[int, int, datetime, tuple[str, str] | None]]:
    """Like walk_pcap, plus each packet's UDP endpoints, or None when it is not UDP over IPv4.

    record_index is still the packet number in the whole file, so a raw_ref built from it finds
    the same bytes whichever stream was chosen.
    """
    with open(path, "rb") as f:
        header = f.read(PCAP_FILE_HEADER_LEN)
        if header[:4] != PCAP_LE_MAGIC:
            raise ValueError(
                f"{os.fspath(path)}: only little-endian classic pcap is supported, "
                f"found magic bytes {header[:4].hex(' ')}"
            )
        link_type = struct.unpack("<I", header[20:24])[0] & 0xFFFF if len(header) >= 24 else 0
        record_index = 0
        while True:
            offset = f.tell()
            rec = f.read(PCAP_RECORD_HEADER_LEN)
            if len(rec) < PCAP_RECORD_HEADER_LEN:
                return
            ts_sec, ts_usec, cap_len, _orig_len = struct.unpack("<IIII", rec)
            record_index += 1
            ts = datetime.fromtimestamp(ts_sec, UTC) + timedelta(microseconds=ts_usec)
            yield record_index, offset, ts, udp_endpoints(f.read(cap_len), link_type)


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


def native_decoder_command(path: str | os.PathLike[str]) -> tuple[list[str], str]:
    """Command line and working directory for a native (Linux) asterix binary.

    Used when FLIGHTMIND_ASTERIX_BIN is set. FLIGHTMIND_ASTERIX_INI must name the decoder's
    asterix.ini; the XML category files it lists sit next to it, so the decoder runs from that
    folder. Raises an error that names the missing variable or file.
    """
    binary = os.environ["FLIGHTMIND_ASTERIX_BIN"]
    ini = os.environ.get("FLIGHTMIND_ASTERIX_INI")
    if not ini:
        raise KeyError(
            "missing environment variable FLIGHTMIND_ASTERIX_INI "
            "(required when FLIGHTMIND_ASTERIX_BIN is set)"
        )
    if not os.path.isfile(binary):
        raise FileNotFoundError(f"FLIGHTMIND_ASTERIX_BIN does not name a file: {binary}")
    if not os.path.isfile(ini):
        raise FileNotFoundError(f"FLIGHTMIND_ASTERIX_INI does not name a file: {ini}")
    ini = os.path.abspath(ini)
    cmd = [os.path.abspath(binary), "-P", "-d", ini, "-j", "-f", os.path.abspath(path)]
    return cmd, os.path.dirname(ini)


def _cygwin_command(path: str | os.PathLike[str]) -> tuple[list[str], dict[str, str]]:
    """Command line and environment for asterix.exe run through Cygwin bash (Windows)."""
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
    return [bash, "-lc", script], env


def decode_blocks(path: str | os.PathLike[str]) -> Iterator[dict]:
    """Run the ASTERIX decoder in JSON-per-line mode and yield one dict per output line.

    With FLIGHTMIND_ASTERIX_BIN set, runs that native binary directly (Linux, macOS);
    otherwise runs asterix.exe through Cygwin (FLIGHTMIND_ASTERIX_DIR, FLIGHTMIND_CYGWIN_BIN).
    """
    cwd: str | None = None
    if os.environ.get("FLIGHTMIND_ASTERIX_BIN"):
        cmd, cwd = native_decoder_command(path)
        env = None
    else:
        cmd, env = _cygwin_command(path)

    # stderr goes to a file so a chatty decoder cannot fill a pipe and block stdout.
    with tempfile.TemporaryFile() as err:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=err, env=env, cwd=cwd)
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
