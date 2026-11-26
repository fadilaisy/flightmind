"""Routing tests for serve.py (SCRUM-38). Localhost only; nothing is edited in contracts/ or mock_api/."""
from contextlib import asynccontextmanager
from pathlib import Path

import jsonschema
import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

import serve
from mock_api.app import app as mock_app

SPEC = yaml.safe_load((Path(__file__).parents[3] / "contracts" / "openapi.yaml").read_text(encoding="utf-8"))


def inline(node):
    """Resolve $refs and turn OpenAPI 3.0 `nullable` into JSON Schema."""
    if isinstance(node, list):
        return [inline(n) for n in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        return inline(SPEC["components"]["schemas"][node["$ref"].split("/")[-1]])
    out = {k: inline(v) for k, v in node.items()}
    if out.pop("nullable", False) and "type" in out:
        out["type"] = [out["type"], "null"]
    return out


def check(body, path, method="get", code="200"):
    schema = SPEC["paths"][path][method]["responses"][code]["content"]["application/json"]["schema"]
    jsonschema.validate(body, inline(schema))


@pytest.fixture
def dist(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>flightmind</html>", encoding="utf-8")
    (tmp_path / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    return tmp_path


@pytest.fixture
def client(dist):
    return TestClient(serve.build_app(web_dist=str(dist)))


def test_root_serves_index_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.text == "<html>flightmind</html>"


def test_assets_are_served(client):
    r = client.get("/assets/app.js")
    assert r.status_code == 200
    assert r.text == "console.log(1)"


def test_meta_through_serve_matches_contract(client):
    body = client.get("/api/meta").json()
    check(body, "/api/meta")
    assert body["mode"] == "replay"


def test_events_answered_by_api(client):
    r = client.get("/api/events")
    assert r.status_code == 200
    check(r.json(), "/api/events")


def test_unknown_api_path_is_api_json_404(client):
    r = client.get("/api/nope")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/json")
    assert "detail" in r.json()


def test_unknown_non_api_path_is_404(client):
    assert client.get("/nope.txt").status_code == 404


def test_api_prefix_needs_trailing_slash(client):
    # '/apiary' and '/api' are not API paths: they go to the static side.
    for path in ("/apiary", "/api"):
        r = client.get(path)
        assert r.status_code == 404
        assert "detail" not in r.text


def test_post_on_static_side_is_405(client):
    assert client.post("/").status_code == 405


def test_no_dist_env_serves_api_only(monkeypatch):
    monkeypatch.delenv("FLIGHTMIND_WEB_DIST", raising=False)
    c = TestClient(serve.build_app())
    assert c.get("/api/meta").status_code == 200
    assert c.get("/").status_code == 404


def test_empty_dist_env_serves_api_only(monkeypatch):
    monkeypatch.setenv("FLIGHTMIND_WEB_DIST", "")
    c = TestClient(serve.build_app())
    assert c.get("/api/meta").status_code == 200
    assert c.get("/").status_code == 404


def test_explicit_empty_web_dist_ignores_environment(monkeypatch, dist):
    # Only None reads FLIGHTMIND_WEB_DIST; "" means API only (used by infra/vercel_entry.py).
    monkeypatch.setenv("FLIGHTMIND_WEB_DIST", str(dist))
    c = TestClient(serve.build_app(web_dist=""))
    assert c.get("/api/meta").status_code == 200
    assert c.get("/").status_code == 404
    assert TestClient(serve.build_app()).get("/").status_code == 200


def test_dist_without_index_serves_api_only(tmp_path):
    (tmp_path / "other.txt").write_text("x", encoding="utf-8")
    c = TestClient(serve.build_app(web_dist=str(tmp_path)))
    assert c.get("/api/meta").status_code == 200
    assert c.get("/").status_code == 404
    assert c.get("/other.txt").status_code == 404


def test_docs_and_openapi_not_exposed(client):
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404


def test_defaults_to_mock_api(monkeypatch):
    monkeypatch.delenv("FLIGHTMIND_API_APP", raising=False)
    assert serve.DEFAULT_API_APP == "mock_api.app:app"
    assert serve.load_api_app(serve.DEFAULT_API_APP) is mock_app
    monkeypatch.setenv("FLIGHTMIND_API_APP", "")
    c = TestClient(serve.build_app())
    assert c.get("/api/meta").json()["mode"] == "replay"


def make_other_app() -> FastAPI:
    other = FastAPI()

    @other.get("/api/ping")
    def ping():
        return {"pong": True}

    return other


OTHER_APP = make_other_app()


def test_api_app_chosen_by_variable(monkeypatch, dist):
    monkeypatch.setenv("FLIGHTMIND_API_APP", "test_serve:OTHER_APP")
    c = TestClient(serve.build_app(web_dist=str(dist)))
    assert c.get("/api/ping").json() == {"pong": True}
    assert c.get("/api/meta").status_code == 404


@pytest.mark.parametrize("value", ["no_such_module_xyz:app", "mock_api.app:missing_attr", "no-colon"])
def test_invalid_api_app_fails_with_value(monkeypatch, value):
    monkeypatch.setenv("FLIGHTMIND_API_APP", value)
    with pytest.raises(RuntimeError) as exc:
        serve.build_app()
    assert value in str(exc.value)


def test_api_app_is_not_mutated(dist):
    routes = list(mock_app.routes)
    middleware = list(mock_app.user_middleware)
    state = dict(vars(mock_app.state))
    c = TestClient(serve.build_app(web_dist=str(dist)))
    c.get("/api/meta")
    c.get("/")
    assert list(mock_app.routes) == routes
    assert list(mock_app.user_middleware) == middleware
    assert dict(vars(mock_app.state)) == state


def test_lifespan_events_reach_api_app(dist):
    events = []

    @asynccontextmanager
    async def lifespan(_app):
        events.append("up")
        yield
        events.append("down")

    lifespan_app = FastAPI(lifespan=lifespan)

    mod = type("M", (), {"lifespan_app": lifespan_app})
    import sys

    sys.modules["fm_lifespan_mod"] = mod  # type: ignore[assignment]
    try:
        with TestClient(serve.build_app(api_app="fm_lifespan_mod:lifespan_app", web_dist=str(dist))):
            assert events == ["up"]
        assert events == ["up", "down"]
    finally:
        del sys.modules["fm_lifespan_mod"]
