# Design: SCRUM-34 first MCP server with get_track

Implements `requirements.md` in this folder. Decisions taken: errors are `isError` tool results; launch is `python` from the workspace root (see "Registration" for why `cwd` is not used).

## Update after task 1 (spike result)

The `FastMCP` sketches below were written before the spike. Task 1 found that `FastMCP` cannot accept a parameter named `from` at call time, and that `mcp` 2.x renamed `FastMCP` to `MCPServer`. The implementation therefore uses `mcp>=1.2,<2` (tested on 1.30.0) and the low-level `mcp.server.lowlevel.Server` with a hand-written `inputSchema` that names the parameters `icao24`, `from` and `to`. `TrackError` propagates out of the `call_tool` handler and the SDK returns `isError: true` with the message, so the `ToolError` conversion is not needed. Everything else in this design (client, error table, registration, tests) is unchanged. Tests call the server through `mcp.shared.memory.create_connected_server_and_client_session`.

## Overview

A stdio MCP server built with the official `mcp` Python SDK (`FastMCP`). It has one tool, `get_track`, which calls `GET {FLIGHTMIND_API_BASE}/api/tracks/{icao24}` with `httpx` and returns the JSON body unchanged. It never imports `mock_api` and never opens the database.

```
Kiro chat --stdio--> mcp_server (get_track) --HTTP--> mock API now / real API later
```

## Files

All new code is under `services/intel/mcp_server/`, owned by Role 3.

| Path | Purpose |
| --- | --- |
| `services/intel/mcp_server/__init__.py` | Empty. Makes the folder a package. |
| `services/intel/mcp_server/client.py` | `fetch_track(...)`: builds the URL, calls the API, maps failures to `TrackError`. No MCP code. |
| `services/intel/mcp_server/server.py` | `FastMCP("flightmind")`, the `get_track` tool, `main()`. |
| `services/intel/mcp_server/__main__.py` | Lets `python -m mcp_server` work from `services/intel`. |
| `services/intel/mcp_server/run.py` | Entry script for `mcp.json`. Adds its parent folder to `sys.path`, then calls `main()`. |
| `services/intel/tests/test_mcp_server.py` | The tests in requirement 6. |
| `.kiro/settings/mcp.json` | Registration (new file; the folder does not exist yet). |
| `services/intel/requirements.txt` | Add `mcp>=1.2` (the SDK version that provides `FastMCP`). Implementation confirms the exact floor on install. |
| `services/intel/README.md` | New section "MCP server (SCRUM-34)". |
| `README.md` (root) | Role 1 owns it. Not edited here; open an issue for the third-party disclosure line (see Open items). |

Nothing in `contracts/` or `mock_api/` changes.

## Components

### `client.py`

```python
DEFAULT_BASE = "http://localhost:8000"
TIMEOUT_SECONDS = 10.0

class TrackError(Exception):
    """A failure with a message safe to show in chat."""

def api_base() -> str:
    """FLIGHTMIND_API_BASE, or DEFAULT_BASE when unset or empty. Trailing '/' stripped."""

async def fetch_track(
    icao24: str,
    from_: str | None = None,
    to: str | None = None,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    ...
```

Behaviour of `fetch_track`:

1. `icao24.strip()` is empty: raise `TrackError("icao24 is required, for example 8A0F21.")` before any request.
2. Build the URL as `f"{api_base()}/api/tracks/{quote(icao24, safe='')}"`. `safe=''` encodes `/` and `.` sequences cannot escape because `/` becomes `%2F`. Only the stripped value is sent; case is not changed.
3. Build `params` with `from` and `to` only when given. With neither, no query string.
4. `httpx.AsyncClient(timeout=10.0, transport=transport)`. The `transport` argument exists only so tests can route calls to the in-process mock app.
5. Map outcomes:

| Outcome | Raised message |
| --- | --- |
| `httpx.ConnectError`, `httpx.TimeoutException`, other `httpx.TransportError` | `Cannot reach the FlightMind API at {base}. Check that the API is running or that FLIGHTMIND_API_BASE is correct.` |
| 404 | `No aircraft with icao24 '{icao24}' in the loaded recording.` |
| other non-200 | `The API answered {status}: {detail}` where `detail` is the JSON `detail` field if present, else the first 200 characters of the body. |
| 200 with invalid JSON | `The API answered 200 but the body was not valid JSON.` |
| 200 with valid JSON | the parsed dict, unchanged |

The message for a 404 uses the value the caller gave (stripped), not a server string, so it stays predictable.

### `server.py`

```python
mcp = FastMCP("flightmind")

@mcp.tool()
async def get_track(icao24: str, from_: str | None = None, to: str | None = None) -> dict[str, Any]:
    """<description, see below>"""
    try:
        return await fetch_track(icao24, from_, to, transport=_transport)
    except TrackError as e:
        raise ToolError(str(e)) from None
```

- The tool parameter must be named `from` to match the contract and the requirement. `from` is a Python keyword, so the function parameter is `from_` and the published JSON schema name is `from`. The implementation does this with `Annotated[str | None, Field(alias="from")]` or, if the SDK does not honour the alias in the tool schema, with a hand-written `inputSchema` through the low-level `Server`. The first task in `tasks.md` is a spike that checks which works and records the result. If neither works, the fallback is to name the parameters `from_ts` and `to_ts`, tell the user, and ask before changing requirement 1.
- `ToolError` (from `mcp.server.fastmcp.exceptions`) makes the SDK return `isError: true` with our message as the text. Anything else that escapes (a bug) is also turned into `isError` by the SDK, and is logged to stderr.
- `_transport` is `None` in production. A test sets it to an `httpx.ASGITransport(app=mock_api.app)`.
- Tool description (shown to the model): it says the tool returns the 4D track (time, lat, lon, altitude in feet) of one aircraft; `icao24` is the 6-character hex Mode S address, for example `8A0F21`; `from` and `to` are optional ISO 8601 date-times such as `2026-11-12T08:00:00Z`; and every point has a `raw_ref` that must be cited for any claim made from it.
- `main()` calls `mcp.run(transport="stdio")`. Logging uses the `logging` module on stderr only. No `print`, because stdout is the protocol channel.

The return type `dict[str, Any]` makes the SDK send the dict as structured content and as JSON text, so the model sees exactly the API body.

### `run.py` and `__main__.py`

`run.py`:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mcp_server.server import main
main()
```

This makes the registration independent of the current folder except for finding `run.py` itself.

## Registration: `.kiro/settings/mcp.json`

```json
{
  "mcpServers": {
    "flightmind": {
      "command": "python",
      "args": ["services/intel/mcp_server/run.py"],
      "env": { "FLIGHTMIND_API_BASE": "http://localhost:8000" },
      "disabled": false,
      "autoApprove": ["get_track"]
    }
  }
}
```

- The documented fields for Kiro workspace MCP config are `command`, `args`, `env`, `disabled` and `autoApprove` ([Kiro MCP configuration](https://kiro.dev/docs/mcp/configuration/); I could not confirm a `cwd` field). So the design does not use `cwd`. It uses a path relative to the workspace root and `run.py` fixes `sys.path` itself.
- Two assumptions that must be checked on a real Kiro IDE before the task is closed: (a) workspace servers start with the workspace root as the working directory; (b) `python` on the teammate's PATH has `mcp` and `httpx` installed. If (a) is false, the fallback is `"args": ["${workspaceFolder}/services/intel/mcp_server/run.py"]` if Kiro expands that variable, otherwise a documented one-time user-level config. On macOS and Linux `python` may be `python3`; the README says to create a `python` alias or edit the file locally, and does not commit a machine-specific change.
- `autoApprove: ["get_track"]` is safe because the tool is read-only. Remove it if you want a prompt per call.
- The file holds no secret and no absolute path.

## Data flow

1. Kiro starts `python services/intel/mcp_server/run.py` and speaks MCP over stdio.
2. The model calls `get_track({icao24: "8A0F21", from: "...", to: "..."})`.
3. `fetch_track` sends `GET /api/tracks/8A0F21?from=...&to=...`.
4. The API filters by time and returns the Track JSON. The server returns it unchanged. `raw_ref` is in every point; the model cites it, and `/api/raw/{raw_ref}` (later `get_raw`) opens it.

## Error handling summary

Every failure is a `TrackError` converted to `ToolError`, so the server process never exits on a bad call. A bug raises through the SDK, which still returns `isError`. Details go to stderr; no stack trace reaches the chat.

## Testing strategy

File: `services/intel/tests/test_mcp_server.py`. Reuse the `inline` and `check` schema helpers from `test_mock_api.py` by moving them to `tests/conftest.py` only if needed; otherwise copy the 10 lines, since changing the existing test file is outside this ticket.

Test API: `httpx.ASGITransport(app=mock_api.app)` injected as `transport`, so no port is opened. Error cases use `httpx.MockTransport` that returns a chosen status, a non-JSON body, or raises `httpx.ConnectError`.

| Requirement | Test |
| --- | --- |
| 1.1, 6.6 | `list_tools()` names equal `["get_track"]`; input schema has `icao24` required and properties `from`, `to`. |
| 1.2, 6.2 | `get_track("8A0F21")` through `mcp.call_tool` returns a dict that validates against the `Track` schema. |
| 1.3, 6.3 | `raw_ref` list from the tool equals the list from `GET /api/tracks/8A0F21` on the mock directly. |
| 1.4, 1.5, 6.4 | `MockTransport` records the request: with times, the query has `from` and `to`; without, the query is empty. On the mock, a narrow window returns fewer points than the full track. |
| 2.1, 6.5 | `api_base()` returns the default when unset or empty, and the env value (trailing `/` stripped) when set. |
| 3.1 | 404 gives `isError` and a message containing the `icao24`. |
| 3.2 | `ConnectError` and a timeout give `isError` and a message containing the base URL. |
| 3.3 | 422 and 500 give `isError` with the status code; the JSON `detail` appears when present. |
| 3.4 | 200 with body `not json` gives `isError`. |
| 3.5 | The client is built with `timeout=10.0` (assert on the constructed value). |
| 4.1 | `icao24="../meta"` and `"a/b"`: the recorded request path is `/api/tracks/..%2Fmeta` and `/api/tracks/a%2Fb`; no request goes to `/api/meta`. |
| 4.2 | Empty and whitespace `icao24` give `isError` and the transport records zero requests. |

`pytest` runs from `services/intel` with `pytest-asyncio` or `anyio` for the async tests. The existing `pytest.ini` has no async mode, so the implementation adds `anyio` (already a dependency of `httpx` and `mcp`) with `@pytest.mark.anyio`, which needs no change to `pytest.ini`. Property tests with Hypothesis are not used: the tool has no transform that could drop a `raw_ref`, and the equality test in row 1.3 covers that.

A manual end-to-end check, run once and noted in `KIRO.md`'s log: start the mock API, open Kiro chat, ask for the track of `8A0F21`, and confirm points with `raw_ref` come back; stop the API and confirm the error message.

## Dependencies and disclosure

- `mcp` (official Python SDK, MCP server) and `httpx` (HTTP client) do real work. The README disclosure list must name them. The root `README.md` is owned by Role 1, so the implementation opens an issue for that line and documents both in `services/intel/README.md` meanwhile.
- Local Python is 3.10 and `tech.md` targets 3.12. The `mcp` SDK supports 3.10, so the code runs on both. Use only syntax available in 3.10 (`X | None` is fine).

## Open items

1. The `from` parameter name and SDK alias support is settled by the first spike task (see `server.py`).
2. The two Kiro assumptions in "Registration" are verified in the last task. Whether Kiro Crew reads `.kiro/settings/mcp.json` is checked there and the answer goes in the README.
3. Root `README.md` disclosure line needs a Role 1 issue.
