"""HTTP client for GET /api/tracks/{icao24} (contract C5). No MCP code here.

The base URL comes from FLIGHTMIND_API_BASE so the mock API (services/intel/mock_api)
can be swapped for the real API with no change in this package.
"""
import logging
import os
from typing import Any
from urllib.parse import quote

import httpx

log = logging.getLogger("flightmind.mcp")

DEFAULT_BASE = "http://localhost:8000"
TIMEOUT_SECONDS = 10.0


class TrackError(Exception):
    """A failure whose message is safe to show in chat."""


def api_base() -> str:
    """FLIGHTMIND_API_BASE, or the default when unset or empty."""
    base = os.environ.get("FLIGHTMIND_API_BASE", "").strip()
    return (base or DEFAULT_BASE).rstrip("/")


async def fetch_track(
    icao24: str,
    from_: str | None = None,
    to: str | None = None,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    """Return the Track JSON from the API unchanged (every point keeps its raw_ref).

    `transport` exists so tests can route the call to an in-process app.
    """
    icao24 = (icao24 or "").strip()
    if not icao24:
        raise TrackError("icao24 is required, for example 8A0F21.")

    base = api_base()
    url = f"{base}/api/tracks/{quote(icao24, safe='')}"
    params: dict[str, str] = {}
    if from_:
        params["from"] = from_
    if to:
        params["to"] = to

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS, transport=transport) as client:
            response = await client.get(url, params=params)
    except httpx.TransportError as exc:
        log.warning("API unreachable at %s: %s", base, exc)
        raise TrackError(
            f"Cannot reach the FlightMind API at {base}. "
            "Check that the API is running or that FLIGHTMIND_API_BASE is correct."
        ) from None

    if response.status_code == 404:
        raise TrackError(f"No aircraft with icao24 '{icao24}' in the loaded recording.")
    if response.status_code != 200:
        raise TrackError(f"The API answered {response.status_code}: {_detail(response)}")
    try:
        body = response.json()
    except ValueError:
        raise TrackError("The API answered 200 but the body was not valid JSON.") from None
    if not isinstance(body, dict):
        raise TrackError("The API answered 200 but the body was not a JSON object.")
    return body


def _detail(response: httpx.Response) -> str:
    try:
        body = response.json()
        if isinstance(body, dict) and "detail" in body:
            return str(body["detail"])[:200]
    except ValueError:
        pass
    return response.text[:200]
