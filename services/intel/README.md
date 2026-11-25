# services/intel

Role 3 (Zahran). Stories, embeddings, agent, MCP server, HTTP API.

## Mock API (SCRUM-33)

Serves every path in `contracts/openapi.yaml` from **synthetic** data in
`mock_api/data.py` (4 aircraft, 270 records, 4 events: 2 go-arounds, 1 holding, 1 squawk 7700).
The raw hex is shape-only, not valid ASTERIX. Every `raw_ref` in a track or event opens
through `/api/raw/{raw_ref}`.

```powershell
cd services/intel
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn mock_api.app:app --port 8000
```

Test (checks each response against `openapi.yaml`):

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Notes for the UI:

- CORS is open to any origin (mock only).
- `/api/stream` is a finite replay. The contract does not define its payload and the web UI
  does not use it (replay is the scrubber), so the `event: position` and `event: event`
  records the mock sends are our own assumption (see the docstring in `app.py`).
  Speed is set with `MOCK_STREAM_DELAY` seconds between items (default 0.05).
- `/api/ask` answers by keyword (7700 / go-around / hold) and otherwise returns
  `not_enough_evidence`. The real agent is SCRUM-36.

## MCP server (SCRUM-34)

`mcp_server/` is a stdio MCP server with one tool, `get_track(icao24, from?, to?)`. It calls
`GET /api/tracks/{icao24}` and returns the body unchanged, so every point keeps its `raw_ref`.
It is a thin HTTP client: it never reads the database, so the mock API can be replaced by the
real API with no change here.

Set the API address with `FLIGHTMIND_API_BASE` (default `http://localhost:8000`).

Setup from a clean clone:

```powershell
cd services/intel
python -m pip install -r requirements.txt     # into the same Python that Kiro will launch
.\.venv\Scripts\python.exe -m uvicorn mock_api.app:app --port 8000   # start the mock API
```

The server is registered in `.kiro/settings/mcp.json` as `flightmind`. It runs
`python services/intel/mcp_server/run.py`, a path relative to the workspace root, with no
absolute path or secret. Open the repo in Kiro and ask for the track of `8A0F21`
(optionally with `from` and `to`, ISO 8601). On macOS and Linux `python` may be `python3`:
add a `python` alias on your machine instead of editing the committed file.

Errors come back as tool errors with a readable message, and the server keeps running:

| Case | Message starts with |
| --- | --- |
| Unknown aircraft | `No aircraft with icao24 '<value>' in the loaded recording.` |
| API not running | `Cannot reach the FlightMind API at <base>.` |
| Other HTTP status | `The API answered <status>: <detail>` |
| Body not JSON | `The API answered 200 but the body was not valid JSON.` |
| Empty `icao24` | `icao24 is required, for example 8A0F21.` |

Checked on 2026-11-25 with the official `mcp` Python SDK client over stdio (not with Kiro):
six calls against the mock API, all as expected. Known aircraft returns 60 points with a
`raw_ref` each, `from` narrows it to 30, an unknown aircraft, a missing `icao24` and a stopped
API each return a tool error, and the server answered correctly after the API came back.

Not yet verified in Kiro (task 7 of the spec): that workspace servers start in the workspace
root, and whether Kiro Crew reads `.kiro/settings/mcp.json` at all. Until it is checked, assume
Kiro Crew does not, and add the server by hand in Customize, Connections, MCP Servers with an
absolute path to `run.py`.

Notes:

- `mcp` is pinned `>=1.2,<2`. Version 2 renamed `FastMCP` to `MCPServer`, and the server
  uses the low-level `Server` so the tool can keep the contract's parameter name `from`.
- Tests: `python -m pytest -q` from `services/intel` (`tests/test_mcp_server.py`).

### Third-party libraries (for the README disclosure list)

- `mcp` (official Model Context Protocol Python SDK): serves the MCP tool over stdio.
- `httpx`: HTTP client that calls the FlightMind API.
