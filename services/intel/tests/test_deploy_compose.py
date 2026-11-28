"""infra/deploy/docker-compose.prod.yml has three services, named volumes, and no inlined secrets.

Reads the file only; docker is not run. Skipped when PyYAML is not installed.
"""
import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

DEPLOY = Path(__file__).resolve().parents[3] / "infra" / "deploy"
COMPOSE = DEPLOY / "docker-compose.prod.yml"


@pytest.fixture(scope="module")
def compose():
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))


def test_three_services(compose):
    assert set(compose["services"]) == {"db", "app", "caddy"}


def test_restart_always(compose):
    for name, svc in compose["services"].items():
        assert svc.get("restart") == "always", name


def test_named_volumes_declared_and_used(compose):
    declared = set(compose["volumes"])
    assert {"flightmind_pgdata", "flightmind_uploads", "caddy_data"} <= declared
    used = set()
    for svc in compose["services"].values():
        for v in svc.get("volumes", []):
            source = v.split(":")[0]
            if not source.startswith((".", "/")):
                used.add(source)
    assert used <= declared, f"used but not declared: {used - declared}"
    assert {"flightmind_pgdata", "flightmind_uploads", "caddy_data"} <= used


def test_db_loads_schema_and_is_arm64_capable(compose):
    db = compose["services"]["db"]
    assert db["image"].startswith("timescale/timescaledb-ha:pg16")
    assert any(v.startswith("../../contracts/schema.sql:/docker-entrypoint-initdb.d/") for v in db["volumes"])
    assert (DEPLOY / ".." / ".." / "contracts" / "schema.sql").resolve().is_file()


def test_app_builds_the_app_target_and_uses_the_real_api(compose):
    build = compose["services"]["app"]["build"]
    assert build["dockerfile"] == "infra/Dockerfile.app"
    assert build["target"] == "app"
    dockerfile = (DEPLOY.parent / "Dockerfile.app").read_text(encoding="utf-8")
    assert re.search(r"^FROM runtime AS app$", dockerfile, re.M)
    assert "FLIGHTMIND_API_APP=real_api.app:app" in dockerfile


def test_only_caddy_publishes_ports(compose):
    assert "ports" not in compose["services"]["db"]
    assert "ports" not in compose["services"]["app"]
    published = {p.split(":")[0] for p in compose["services"]["caddy"]["ports"]}
    assert published == {"80", "443"}


def test_caddyfile_uses_the_host_variable():
    text = (DEPLOY / "Caddyfile").read_text(encoding="utf-8")
    assert "{$FLIGHTMIND_HOST}" in text
    assert "reverse_proxy app:8000" in text


SECRET_NAME = re.compile(r"PASSWORD|SECRET|TOKEN|API_KEY|DSN", re.I)
REFERENCE = re.compile(r"\$\{[A-Z_]+(:?[-?][^}]*)?\}")


def _environment(compose):
    for name, svc in compose["services"].items():
        env = svc.get("environment", {})
        if isinstance(env, list):
            env = dict(item.split("=", 1) for item in env)
        for key, value in env.items():
            yield name, key, str(value)


def test_no_secret_value_is_inlined(compose):
    checked = 0
    for name, key, value in _environment(compose):
        if SECRET_NAME.search(key):
            checked += 1
            assert "${" in value, f"{name}.{key} must come from .env, not be written in the file: {value!r}"
            # A default after :- may only be empty for secrets.
            for m in re.finditer(r"\$\{[A-Z_]+:-([^}]*)\}", value):
                assert m.group(1) == "", f"{name}.{key} has a default secret value"
    assert checked >= 3  # POSTGRES_PASSWORD, FLIGHTMIND_DSN, ANTHROPIC_API_KEY, GEMINI_API_KEY


def test_dsn_password_is_a_reference(compose):
    dsn = compose["services"]["app"]["environment"]["FLIGHTMIND_DSN"]
    assert "${POSTGRES_PASSWORD}" in dsn


def test_env_example_has_no_values_for_secrets():
    for line in (DEPLOY / ".env.example").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if SECRET_NAME.search(key):
            assert value == "", f"{key} must be empty in .env.example"


def test_up_script_is_present_and_strict():
    text = (DEPLOY / "up.sh").read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash")
    assert "set -euo pipefail" in text
