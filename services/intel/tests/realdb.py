"""Test database for the real API (SCRUM-37, SCRUM-64).

FLIGHTMIND_TEST_DSN points at a Postgres that has TimescaleDB and pgvector, for example the
local stack: postgresql://flightmind:flightmind@localhost:5432/flightmind. Each test session
creates its own database from contracts/schema.sql and drops it at the end, so dev data is
never touched. Without FLIGHTMIND_TEST_DSN, or without psycopg, the db tests are skipped.

`seed_fixture` fills it with the committed 500-packet fixture through the pipeline itself
(services/pipeline, Python 3.11+). The decoder is not needed: its output for this pcap is
committed as fixtures/adsb_sample_500.decoded.jsonl and is replayed instead.
"""
import json
import os
import secrets
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest

REPO = Path(__file__).resolve().parents[3]
SCHEMA = REPO / "contracts" / "schema.sql"
FIXTURE_PCAP = REPO / "fixtures" / "adsb_sample_500.pcap"
FIXTURE_JSONL = REPO / "fixtures" / "adsb_sample_500.decoded.jsonl"
FIXTURE_ID = "adsb_sample_500"


def admin_dsn() -> str:
    dsn = os.environ.get("FLIGHTMIND_TEST_DSN", "").strip()
    if not dsn:
        pytest.skip("FLIGHTMIND_TEST_DSN is not set")
    return dsn


def _with_db(dsn: str, name: str) -> str:
    parts = urlsplit(dsn)
    return urlunsplit((parts.scheme, parts.netloc, "/" + name, parts.query, parts.fragment))


def create_database():
    """Create a fresh database from schema.sql. Returns (dsn, drop function)."""
    psycopg = pytest.importorskip("psycopg")
    admin = admin_dsn()
    name = "fm_test_" + secrets.token_hex(4)
    try:
        with psycopg.connect(admin, autocommit=True, connect_timeout=5) as conn:
            conn.execute(f'CREATE DATABASE "{name}"')
    except psycopg.OperationalError as exc:
        pytest.skip(f"test Postgres not reachable: {exc}")
    dsn = _with_db(admin, name)
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(SCHEMA.read_text(encoding="utf-8"))

    def drop():
        with psycopg.connect(admin, autocommit=True) as conn:
            conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')

    return dsn, drop


def decoded_blocks():
    return [json.loads(line) for line in FIXTURE_JSONL.read_text(encoding="utf-8").splitlines() if line]


def replay_decoder(monkeypatch, blocks_by_path=None):
    """Make the pipeline's decoder return the committed JSON instead of running asterix.exe."""
    from flightmind_pipeline import cli

    blocks = decoded_blocks()

    def fake_decode(path):
        return iter((blocks_by_path or {}).get(str(path), blocks))

    monkeypatch.setattr(cli, "decode_blocks", fake_decode)


def seed_fixture(dsn: str, report_dir: Path) -> dict:
    """Run the pipeline CLI on the fixture pcap into dsn. Returns its compression report."""
    pytest.importorskip("flightmind_pipeline", reason="services/pipeline needs Python 3.11+ and must be installed")
    from flightmind_pipeline import cli

    with pytest.MonkeyPatch.context() as mp:
        replay_decoder(mp)
        mp.setenv("FLIGHTMIND_DSN", dsn)
        return cli.run_pcap(FIXTURE_PCAP, report_dir)
