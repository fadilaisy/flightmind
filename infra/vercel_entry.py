"""Vercel entry point (SCRUM-38).

One Vercel Function serves everything, through serve.py, the same way the container does:
paths that start with /api/ go to the API app, every other path is a file from
services/intel/web_dist (written by infra/vercel_build.py during the build). Anything else is
404, so /docs and /openapi.json stay private.

The folder is passed explicitly, so FLIGHTMIND_WEB_DIST is not read here. When the folder has
no index.html (no build has run, as in the tests), only the API is served.
"""
import sys
from pathlib import Path

_INTEL = Path(__file__).resolve().parents[1] / "services" / "intel"
sys.path.insert(0, str(_INTEL))

from serve import build_app  # noqa: E402

WEB_DIST = _INTEL / "web_dist"

app = build_app(web_dist=str(WEB_DIST))
