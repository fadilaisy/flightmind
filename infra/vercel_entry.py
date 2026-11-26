"""Vercel entry point (SCRUM-38).

Vercel serves the web UI from `public/`, this function answers `/api/` and returns 404 for
anything else, so `/docs` and `/openapi.json` stay private as in the container.

`web_dist=""` means "API only" even when FLIGHTMIND_WEB_DIST is set: only None reads the
environment (see `serve.build_app`).
"""
import sys
from pathlib import Path

_INTEL = Path(__file__).resolve().parents[1] / "services" / "intel"
sys.path.insert(0, str(_INTEL))

from serve import build_app  # noqa: E402

app = build_app(web_dist="")
