"""HTTP client for the FlightMind API, shared by the agent and the MCP server (SCRUM-36).

It talks to the API only through HTTP (or an in-process ASGI app), so the mock API can be
swapped for the real one with no change here. It never imports `mock_api` and never reads
data files or the database. Error messages are safe to show to the model and in chat.
"""
import logging
import os
from typing import Any, Optional
from urllib.parse import quote

import httpx

log = logging.getLogger("flightmind.agent")

DEFAULT_BASE = "http://localhost:8000"
IN_PROCESS_BASE = "http://api"
TIMEOUT_SECONDS = 10.0


class ApiError(Exception):
    """A failure whose message is safe to show to the model and in chat."""


def _env_base() -> str:
    base = os.environ.get("FLIGHTMIND_API_BASE", "").strip()
    return (base or DEFAULT_BASE).rstrip("/")


def _detail(response: httpx.Response) -> str:
    try:
        body = response.json()
        if isinstance(body, dict) and "detail" in body:
            return str(body["detail"])[:200]
    except ValueError:
        pass
    return response.text[:200]


class ApiClient:
    """Async client for the four read endpoints the agent needs."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        *,
        app: Any = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        recording: Optional[str] = None,
    ) -> None:
        self._recording = (recording or "").strip() or None  # scopes events and tracks to one recording
        self._in_process = app is not None
        if app is not None:
            self._base = IN_PROCESS_BASE
            self._transport = transport or httpx.ASGITransport(app=app)
        else:
            self._base = (base_url or _env_base()).rstrip("/")
            self._transport = transport

    @property
    def base(self) -> str:
        return self._base

    async def _get(self, path: str, params: Optional[dict] = None, *, missing: str) -> Any:
        url = f"{self._base}{path}"
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS, transport=self._transport) as client:
                response = await client.get(url, params=params or {})
        except httpx.TransportError as exc:
            log.warning("API unreachable at %s: %s", self._base, type(exc).__name__)
            if self._in_process:
                raise ApiError("The FlightMind API app did not answer.") from None
            raise ApiError(
                f"Cannot reach the FlightMind API at {self._base}. "
                "Check that the API is running or that FLIGHTMIND_API_BASE is correct."
            ) from None
        if response.status_code == 404:
            raise ApiError(missing)
        if response.status_code != 200:
            raise ApiError(f"The API answered {response.status_code}: {_detail(response)}")
        try:
            return response.json()
        except ValueError:
            raise ApiError("The API answered 200 but the body was not valid JSON.") from None

    async def events(
        self,
        *,
        since: Optional[str] = None,
        type: Optional[str] = None,
        airport: Optional[str] = None,
    ) -> list:
        params = {k: v for k, v in (("since", since), ("type", type), ("airport", airport)) if v}
        if self._recording:
            params["recording"] = self._recording
        body = await self._get("/api/events", params, missing="No events endpoint on the API.")
        if not isinstance(body, list):
            raise ApiError("The API answered 200 but the body was not a JSON list.")
        return body

    async def event(self, event_id: str) -> dict:
        event_id = (event_id or "").strip()
        if not event_id:
            raise ApiError("event id is required.")
        body = await self._get(
            f"/api/events/{quote(event_id, safe='')}", missing=f"No event with id '{event_id}'."
        )
        return self._obj(body)

    async def track(self, icao24: str, from_: Optional[str] = None, to: Optional[str] = None) -> dict:
        icao24 = (icao24 or "").strip()
        if not icao24:
            raise ApiError("icao24 is required, for example 8A0F21.")
        params = {}
        if from_:
            params["from"] = from_
        if to:
            params["to"] = to
        if self._recording:
            params["recording"] = self._recording
        body = await self._get(
            f"/api/tracks/{quote(icao24, safe='')}",
            params,
            missing=f"No aircraft with icao24 '{icao24}' in the loaded recording.",
        )
        return self._obj(body)

    async def raw(self, raw_ref: str) -> dict:
        raw_ref = (raw_ref or "").strip()
        if not raw_ref:
            raise ApiError("raw_ref is required, for example rec01:0.")
        body = await self._get(
            f"/api/raw/{quote(raw_ref, safe='')}", missing=f"No raw record '{raw_ref}'."
        )
        return self._obj(body)

    @staticmethod
    def _obj(body: Any) -> dict:
        if not isinstance(body, dict):
            raise ApiError("The API answered 200 but the body was not a JSON object.")
        return body
