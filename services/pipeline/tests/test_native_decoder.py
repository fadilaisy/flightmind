"""The native-binary path of decode_blocks (FLIGHTMIND_ASTERIX_BIN), SCRUM-71.

Most tests use a fake decoder, a small Python script, so no real asterix binary is needed.
The last test runs the real binary on the committed fixture and is skipped unless
FLIGHTMIND_ASTERIX_BIN (and FLIGHTMIND_ASTERIX_INI) are set.
"""

import json
import os
import stat
import sys
from pathlib import Path

import pytest

from flightmind_pipeline.pcap_source import decode_blocks, native_decoder_command

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"
PCAP = FIXTURES / "adsb_sample_500.pcap"
JSONL = FIXTURES / "adsb_sample_500.decoded.jsonl"

FAKE_DECODER = """\
import json, os, sys
if os.environ.get("FAKE_EXIT"):
    sys.stderr.write("fake decoder failure")
    sys.exit(int(os.environ["FAKE_EXIT"]))
print("not json, ignored")
print(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd()}))
print(json.dumps({"second": True}))
"""


def _fake_binary(tmp_path: Path) -> Path:
    """A runnable file that behaves like the decoder; a .cmd wrapper on Windows."""
    script = tmp_path / "fake_asterix.py"
    script.write_text(FAKE_DECODER, encoding="utf-8")
    if os.name == "nt":
        binary = tmp_path / "fake_asterix.cmd"
        binary.write_text(f'@"{sys.executable}" "{script}" %*\r\n', encoding="ascii")
    else:
        binary = tmp_path / "fake_asterix"
        binary.write_text(f"#!{sys.executable}\n{FAKE_DECODER}", encoding="utf-8")
        binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    return binary


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    config = tmp_path / "config"
    config.mkdir()
    ini = config / "asterix.ini"
    ini.write_text("asterix_cat021_2_6.xml\n", encoding="utf-8")
    binary = _fake_binary(tmp_path)
    monkeypatch.setenv("FLIGHTMIND_ASTERIX_BIN", str(binary))
    monkeypatch.setenv("FLIGHTMIND_ASTERIX_INI", str(ini))
    # The Cygwin variables must not matter once BIN is set.
    monkeypatch.delenv("FLIGHTMIND_ASTERIX_DIR", raising=False)
    monkeypatch.delenv("FLIGHTMIND_CYGWIN_BIN", raising=False)
    return {"bin": binary, "ini": ini}


def test_command_is_built_without_cygwin(env: dict[str, Path], tmp_path: Path) -> None:
    cmd, cwd = native_decoder_command(tmp_path / "rec.pcap")
    assert cmd == [
        str(env["bin"]),
        "-P",
        "-d",
        str(env["ini"]),
        "-j",
        "-f",
        str((tmp_path / "rec.pcap").absolute()),
    ]
    assert cwd == str(env["ini"].parent)


def test_missing_ini_variable_is_named(env: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FLIGHTMIND_ASTERIX_INI")
    with pytest.raises(KeyError, match="FLIGHTMIND_ASTERIX_INI"):
        native_decoder_command("x.pcap")
    with pytest.raises(KeyError, match="FLIGHTMIND_ASTERIX_INI"):
        list(decode_blocks("x.pcap"))


def test_missing_binary_file_is_named(env: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FLIGHTMIND_ASTERIX_BIN", str(env["bin"]) + ".gone")
    with pytest.raises(FileNotFoundError, match="FLIGHTMIND_ASTERIX_BIN"):
        native_decoder_command("x.pcap")


def test_missing_ini_file_is_named(env: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FLIGHTMIND_ASTERIX_INI", str(env["ini"]) + ".gone")
    with pytest.raises(FileNotFoundError, match="FLIGHTMIND_ASTERIX_INI"):
        native_decoder_command("x.pcap")


def test_decode_blocks_runs_the_binary_directly(env: dict[str, Path], tmp_path: Path) -> None:
    pcap = tmp_path / "rec.pcap"
    pcap.write_bytes(b"")
    blocks = list(decode_blocks(pcap))
    assert len(blocks) == 2  # the non-JSON line is skipped
    assert blocks[0]["argv"] == ["-P", "-d", str(env["ini"]), "-j", "-f", str(pcap.absolute())]
    assert os.path.samefile(blocks[0]["cwd"], env["ini"].parent)
    assert blocks[1] == {"second": True}


def test_decode_blocks_reports_a_failing_binary(
    env: dict[str, Path], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("FAKE_EXIT", "3")
    with pytest.raises(RuntimeError, match="code 3: fake decoder failure"):
        list(decode_blocks(tmp_path / "rec.pcap"))


def test_cygwin_path_is_used_when_bin_is_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FLIGHTMIND_ASTERIX_BIN", raising=False)
    monkeypatch.delenv("FLIGHTMIND_ASTERIX_DIR", raising=False)
    monkeypatch.delenv("FLIGHTMIND_CYGWIN_BIN", raising=False)
    with pytest.raises(KeyError, match="FLIGHTMIND_ASTERIX_DIR"):
        list(decode_blocks("x.pcap"))


@pytest.mark.skipif(
    not os.environ.get("FLIGHTMIND_ASTERIX_BIN"), reason="FLIGHTMIND_ASTERIX_BIN is not set"
)
def test_real_binary_matches_the_committed_fixture() -> None:
    expected = [json.loads(line) for line in JSONL.read_text(encoding="utf-8").splitlines() if line]
    actual = list(decode_blocks(PCAP))
    assert len(actual) == len(expected) == 500
    for n, (got, want) in enumerate(zip(actual, expected), start=1):
        assert got == want, f"block {n} differs from fixtures/adsb_sample_500.decoded.jsonl"
