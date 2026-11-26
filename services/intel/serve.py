"""Public entry point (SCRUM-38): one origin for the web UI and the API.

Paths that start with /api/ go to the API app. Every other path goes to the built web
UI. The API app is only called, never changed.

Run from services/intel:
    uvicorn serve:app --port 8000

Environment:
    FLIGHTMIND_API_APP   'module:attribute' of the API app (default mock_api.app:app)
    FLIGHTMIND_WEB_DIST  folder with the built web UI (needs index.html); unset = API only
"""
import importlib
import os
from pathlib import Path
from typing import Any, Optional

from starlette.exceptions import HTTPException
from starlette.responses import PlainTextResponse
from starlette.staticfiles import StaticFiles

DEFAULT_API_APP = "mock_api.app:app"
API_PREFIX = "/api/"


def load_api_app(spec: str) -> Any:
    """Import 'module:attribute'. Raise RuntimeError naming the value on any failure."""
    module_name, sep, attr = spec.partition(":")
    if not sep or not module_name or not attr:
        raise RuntimeError(f"Cannot load FLIGHTMIND_API_APP={spec!r}: expected 'module:attribute'")
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:  # any import-time failure must stop the server
        raise RuntimeError(f"Cannot load FLIGHTMIND_API_APP={spec!r}: {exc!r}") from exc
    try:
        return getattr(module, attr)
    except AttributeError as exc:
        raise RuntimeError(
            f"Cannot load FLIGHTMIND_API_APP={spec!r}: module {module_name!r} has no attribute {attr!r}"
        ) from exc


def _static_app(web_dist: Optional[str]) -> Optional[StaticFiles]:
    if not web_dist:
        return None
    folder = Path(web_dist)
    if not (folder.is_dir() and (folder / "index.html").is_file()):
        return None
    return StaticFiles(directory=str(folder), html=True)


async def _answer_lifespan(receive, send) -> None:
    """Complete the lifespan handshake ourselves (API app does not handle lifespan)."""
    while True:
        message = await receive()
        if message["type"] == "lifespan.startup":
            await send({"type": "lifespan.startup.complete"})
        elif message["type"] == "lifespan.shutdown":
            await send({"type": "lifespan.shutdown.complete"})
            return


def build_app(api_app: Optional[str] = None, web_dist: Optional[str] = None) -> Any:
    """api_app / web_dist default to FLIGHTMIND_API_APP / FLIGHTMIND_WEB_DIST."""
    if api_app is None:
        api_app = os.environ.get("FLIGHTMIND_API_APP")
    if web_dist is None:
        web_dist = os.environ.get("FLIGHTMIND_WEB_DIST")
    api = load_api_app(api_app or DEFAULT_API_APP)
    static = _static_app(web_dist)

    async def dispatch(scope, receive, send) -> None:
        kind = scope["type"]
        if kind == "lifespan":
            try:
                await api(scope, receive, send)
            except Exception:
                await _answer_lifespan(receive, send)
            return
        if scope["path"].startswith(API_PREFIX):
            await api(scope, receive, send)
            return
        if kind == "http":
            if static is None:
                response = PlainTextResponse("Not Found", status_code=404)
            else:
                try:
                    await static(scope, receive, send)
                    return
                except HTTPException as exc:
                    response = PlainTextResponse(exc.detail, status_code=exc.status_code)
            await response(scope, receive, send)
            return
        if kind == "websocket":
            await receive()  # websocket.connect
            await send({"type": "websocket.close", "code": 1008})

    return dispatch


app = build_app()
