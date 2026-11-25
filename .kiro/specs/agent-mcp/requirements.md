# Requirements: SCRUM-34 first MCP server with get_track

Source: SCRUM-34 and the spec description. Owner: Role 3 (Zahran). Folders: `services/intel/mcp_server/`, `.kiro/settings/mcp.json`.

## Introduction

FlightMind needs an MCP server so Kiro chat (and later the citation agent of SCRUM-36) can read a 4D track by calling a tool. This spec builds the server with one tool, `get_track`. The server is a thin client of the HTTP API in `contracts/openapi.yaml` (contract C5). It never touches the database. Today it talks to the mock API in `services/intel/mock_api`. Later the real API (SCRUM-37) replaces the mock with no MCP change.

## Requirements

### 1. Get a track by aircraft

**User story:** As an analyst using Kiro chat, I want to call `get_track` with an aircraft address, so that I get that aircraft's 4D track without leaving chat.

Acceptance criteria:
1. The server exposes exactly one tool, named `get_track`, with inputs `icao24` (required string), `from` (optional ISO 8601 date-time) and `to` (optional ISO 8601 date-time).
2. When the API answers 200, the tool returns the body of `GET /api/tracks/{icao24}` unchanged: `icao24`, `callsign`, and `points` with `ts`, `lat`, `lon`, `alt_ft` and `kept_for_event` as the API sent them.
3. Every point keeps its `raw_ref` (`<recording_file_id>:<record_index>`). The server never drops, rewrites or reorders `raw_ref` or any other field, and never filters or samples points.
4. When `from` or `to` is given, the server passes it to the API as the query parameter `from` or `to`, and the API does the time filtering. The server does not filter points itself.
5. When neither is given, the server sends no query parameters.
6. The tool description tells the model what `icao24` is (6 hex characters), the time format, and that every point carries a `raw_ref` to cite.

### 2. Thin client, swappable backend

**User story:** As the Role 3 developer, I want the server to depend only on the HTTP contract, so that swapping the mock for the real API needs no code change.

Acceptance criteria:
1. The server reads the base URL from the environment variable `FLIGHTMIND_API_BASE`. When it is unset or empty, the default is `http://localhost:8000`.
2. The server makes only HTTP calls to that base URL. It has no database driver, no import from `mock_api`, and no read of `data/` or fixtures.
3. Pointing `FLIGHTMIND_API_BASE` at any server that implements `GET /api/tracks/{icao24}` works with no code change.
4. The server does not read system time and does not need `clock.now()`. The time window is only passed through.

### 3. Clear errors, no crash

**User story:** As an analyst, I want a readable message when something goes wrong, so that I know whether to fix my input or start the API.

Acceptance criteria:
1. When the API answers 404 (unknown `icao24`), the tool returns an error result whose message names the `icao24` that was not found. The server keeps running.
2. When the API is unreachable (connection refused, DNS failure, timeout), the tool returns an error result whose message includes the base URL it tried and says to check that the API is running or that `FLIGHTMIND_API_BASE` is correct. The server keeps running.
3. When the API answers another non-200 status (for example 422 for a bad date-time, or 500), the tool returns an error result with the status code and the API's detail text when present.
4. When the API answers 200 with a body that is not valid JSON, the tool returns an error result saying the response was not valid JSON.
5. Each request has a timeout of 10 seconds.
6. Error results use the MCP tool-error flag (`isError`), not a successful result containing an error string, so the model can tell failure from data.
7. A stack trace never reaches the chat. The server logs details to stderr only, because stdout carries the MCP protocol.

### 4. Safe handling of input

**User story:** As a teammate, I want input handled safely, so that a bad value cannot reach a different API path.

Acceptance criteria:
1. `icao24` is URL-encoded as a single path segment before the request, so a value such as `../meta` or `abc/def` cannot reach another endpoint.
2. An empty or whitespace-only `icao24` returns an error result without calling the API.
3. The server sends no credentials. It logs no point data.

### 5. Works from Kiro chat on any teammate's laptop

**User story:** As a teammate, I want to open the repo in Kiro and have `get_track` available, so that I do not configure anything by hand.

Acceptance criteria:
1. `.kiro/settings/mcp.json` registers the server (name `flightmind`), committed to the repo.
2. The registration holds no absolute path, no user name and no secret. It uses a command and relative paths that resolve from the workspace root on Windows, macOS and Linux.
3. It sets `FLIGHTMIND_API_BASE` in `env` to `http://localhost:8000`, so a teammate can change it in one place.
4. The `services/intel/README.md` section for the MCP server gives the steps from a clean clone to a working call: install dependencies, start the mock API, open Kiro chat, call `get_track`. It states that Kiro Crew and Kiro IDE read the config from different places only if that proves true in testing (see Open items).
5. `mcp` (the official Python SDK) is added to `services/intel/requirements.txt`.

### 6. Tests

**User story:** As the Role 3 developer, I want automated tests, so that a contract drift or a regression is caught before merge.

Acceptance criteria:
1. Tests run with `pytest` from `services/intel`, with no network beyond localhost.
2. A test calls the tool against the real mock API app (in process) for a known aircraft and checks the result validates against the `Track` schema in `contracts/openapi.yaml`.
3. A test checks that every `raw_ref` returned by the tool equals the `raw_ref` returned by the API directly, in the same order.
4. A test checks `from` and `to` narrow the points and that the tool sends them as the query parameters `from` and `to`.
5. Tests cover: unknown `icao24` (404), API unreachable, 422 or 500 from the API, non-JSON 200 body, empty `icao24`, a path-traversal `icao24`, and the default and overridden `FLIGHTMIND_API_BASE`.
6. A test lists the server's tools and asserts the list is exactly `["get_track"]`.
7. Tests do not edit anything under `contracts/`.

## Rules this spec follows

- `tech.md`: Python, type hints, `pytest`; `raw_ref` is never dropped; no system time; third-party libraries are disclosed in the README.
- `data-contracts.md`: C5 is the API; `raw_ref` format is `<recording_file_id>:<record_index>`.
- Role 3 owns `services/intel/`; `.kiro/settings/mcp.json` is the one file outside it, named in the ticket.

## Not in scope

- `query_tracks`, `search_events`, `get_raw`, embeddings and the citation agent (SCRUM-36).
- Any change to `contracts/` or the mock API.
- Authentication, caching, retries, and remote (non-stdio) transport.
- Deploying the server (SCRUM-38).

## Open items

1. **Launch command (decision needed).** The config must work on every laptop, and the local Python is 3.10 while `tech.md` targets 3.12. Recommended: `python -m mcp_server` with `cwd` set to `services/intel`, after `pip install -r requirements.txt`. The alternative is `uv run`, which needs every teammate to install `uv`. If the Kiro config format has no `cwd` field, design.md will use a different relative form and say so.
2. **Error style (decision needed).** Recommended: `isError` tool results as in requirement 3.6. The alternative is raising an exception and letting the SDK wrap it, which gives less control over the message text.
3. **icao24 case.** The mock upper-cases `icao24`, and the contract does not say. The server passes the value through unchanged and leaves normalisation to the API. Say so if you want the server to upper-case it.
4. **Kiro Crew vs Kiro IDE.** The team builds in Kiro Crew, which may not read `.kiro/settings/mcp.json` (as with `.kiro/hooks/`, see SCRUM-19). The workspace file is for teammates on the Kiro IDE. Whether Crew needs its own registration is checked during the tasks phase, and the answer goes in the README.
