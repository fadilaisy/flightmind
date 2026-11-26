"""Tests for the Vercel entry point and pyproject.toml (SCRUM-38). Localhost only."""
import importlib.util
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO = Path(__file__).parents[3]
ENTRY = REPO / "infra" / "vercel_entry.py"
PYPROJECT = REPO / "pyproject.toml"
REQUIREMENTS_SERVE = REPO / "services" / "intel" / "requirements-serve.txt"


def load_entry():
    spec = importlib.util.spec_from_file_location("vercel_entry_under_test", ENTRY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WEB_DIST = REPO / "services" / "intel" / "web_dist"


@pytest.fixture
def no_web_dist():
    """These tests need the build output folder to be absent; skip when a local build left one."""
    if WEB_DIST.exists():
        pytest.skip(f"{WEB_DIST} exists (a local Vercel build ran); remove it to run this test")


@pytest.fixture
def client(monkeypatch, no_web_dist):
    monkeypatch.delenv("FLIGHTMIND_WEB_DIST", raising=False)
    return TestClient(load_entry().app)


def test_meta_is_replay(client):
    r = client.get("/api/meta")
    assert r.status_code == 200
    assert r.json()["mode"] == "replay"


def test_root_is_404_without_a_build(client):
    assert client.get("/").status_code == 404


def test_serves_the_web_build_when_present(no_web_dist):
    """After infra/vercel_build.py has run, the function serves the page and its assets itself."""
    try:
        (WEB_DIST / "assets").mkdir(parents=True)
        (WEB_DIST / "index.html").write_text("<html>flightmind</html>", encoding="utf-8")
        (WEB_DIST / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
        c = TestClient(load_entry().app)
        assert c.get("/").text == "<html>flightmind</html>"
        assert c.get("/assets/app.js").status_code == 200
        assert c.get("/api/meta").json()["mode"] == "replay"
        assert c.get("/docs").status_code == 404
    finally:
        import shutil

        shutil.rmtree(WEB_DIST, ignore_errors=True)


def test_docs_and_openapi_are_404(client):
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404


def test_env_web_dist_is_not_read_by_the_entry(monkeypatch, tmp_path, no_web_dist):
    (tmp_path / "index.html").write_text("<html>flightmind</html>", encoding="utf-8")
    monkeypatch.setenv("FLIGHTMIND_WEB_DIST", str(tmp_path))
    c = TestClient(load_entry().app)
    assert c.get("/").status_code == 404
    assert c.get("/api/meta").status_code == 200


def pyproject_value(key: str) -> str:
    """Value of `key = "..."` inside the [tool.vercel] table (tomllib is not in Python 3.10)."""
    in_table = False
    for line in PYPROJECT.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_table = stripped == "[tool.vercel]"
            continue
        match = re.fullmatch(rf'{key}\s*=\s*"([^"]+)"', stripped)
        if in_table and match:
            return match.group(1)
    raise AssertionError(f"{key} not found in [tool.vercel] of pyproject.toml")


def test_entrypoint_names_an_existing_module_file():
    module, _, variable = pyproject_value("entrypoint").partition(":")
    assert variable == "app"
    assert (REPO / Path(*module.split("."))).with_suffix(".py").is_file()


def fastapi_floor(text: str) -> str:
    match = re.search(r"fastapi\s*>=\s*([0-9][0-9.]*)", text)
    assert match, "no fastapi>= floor found"
    return match.group(1)


def test_fastapi_floor_matches_requirements_serve():
    assert fastapi_floor(PYPROJECT.read_text(encoding="utf-8")) == fastapi_floor(
        REQUIREMENTS_SERVE.read_text(encoding="utf-8")
    )
