# Design: SCRUM-34 first MCP server with get_track

Part 2 (SCRUM-36, cited agent and three more tools) starts at "Part 2: SCRUM-36 cited agent" below; the design of Part 1 is unchanged.


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
- Two assumptions that must be checked on a real Kiro IDE before the task is closed: (a) workspace servers start with the workspace root as the working directory; (b) `python` on the teammate's PATH has `mcp` and `httpx` installed. If (a) is false, the fallback is `"args": ["${workspaceFolder}/services/intel/mcp_server/run.py"]` if Kiro expands that variable, otherwise a documented one-time user-level config. On macOS and Linux `python` may be `python3`; the README says to create a `python` alias or edit the file locally, and does not commit a machine-specific change. Checked on 2026-11-25 (task 7): both (a) and (b) hold on the Kiro IDE on Windows, once the folder is trusted; in Restricted Mode Kiro does not load the workspace MCP config at all. macOS and Linux were not checked, so `python` versus `python3` is still a risk there.
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
2. The two Kiro assumptions in "Registration" are verified in the last task. Whether Kiro Crew reads `.kiro/settings/mcp.json` is checked there and the answer goes in the README. Checked on 2026-11-26 (task 9): Kiro Crew 0.13.1 does not, so Crew users add the server by hand.
3. Root `README.md` disclosure line needs a Role 1 issue.


---

# Part 2: SCRUM-36 cited agent

Implements requirements 7 to 17 in `requirements.md`. Decisions taken: one `ApiClient` for agent and MCP server; the evidence rule is code, not prompt; the agent runs inside the API process and reads the API through the ASGI transport; the contract is not changed.

## Overview

```
web UI --POST /api/ask--> mock_api.ask --> guard --> endpoint.answer_question
                                                        |
                                              agent loop (Claude, 4 tools)
                                                        |
                                    tools.py --> ApiClient --ASGI--> same API app
                                                        ^
Kiro chat --stdio--> mcp_server (4 tools) --> tools.py --> ApiClient --HTTP--> API (FLIGHTMIND_API_BASE)
```

The agent never sees the database. Whatever the API serves (mock now, real in SCRUM-37) is what it can cite.

## Files

| Path | Purpose |
| --- | --- |
| `services/intel/agent/__init__.py` | Empty. |
| `services/intel/agent/api_client.py` | `ApiClient` (async, `httpx.AsyncClient`), `ApiError`. |
| `services/intel/agent/tools.py` | The four tool functions, their JSON schemas and descriptions, `TOOLS` registry, `ToolResult`. |
| `services/intel/agent/evidence.py` | `EvidenceSet`, citation validation, answer rendering, the fixed sentence. |
| `services/intel/agent/agent.py` | `run_agent(client, api, question, ...)`: the loop, limits, usage logging. |
| `services/intel/agent/guard.py` | `AskGuard` limiter with an injected clock. |
| `services/intel/agent/endpoint.py` | `agent_enabled()`, `answer_question(question, api_app)`. |
| `services/intel/mock_api/app.py` | Edit `ask` only: guard, then agent when enabled, else the existing canned code. |
| `services/intel/mcp_server/server.py` | Four tools through `tools.py`. `client.py` stays as is. |
| `services/intel/tests/test_agent_*.py` | Tests of requirement 16 (split by area, see Testing). |
| `services/intel/tests/test_mcp_server.py` | Only the expected tool list changes. |
| `services/intel/requirements.txt`, `requirements-serve.txt`, root `pyproject.toml` | Dependency lists only (requirement 15). |
| `services/intel/README.md` | Section "Cited agent (SCRUM-36)". |

Nothing in `web/`, `contracts/`, `services/pipeline/` or `.kiro/settings/` changes.

## Components

### `api_client.py`

```python
class ApiError(Exception):
    """Message safe to show to the model and in chat."""

class ApiClient:
    def __init__(self, base_url: str | None = None, *, app: Any | None = None,
                 transport: httpx.AsyncBaseTransport | None = None) -> None: ...
    async def events(self, *, since=None, type=None, airport=None) -> list[dict]
    async def event(self, event_id: str) -> dict
    async def track(self, icao24: str, from_: str | None = None, to: str | None = None) -> dict
    async def raw(self, raw_ref: str) -> dict
```

- With `app`, it uses `httpx.ASGITransport(app=app)` and the base `http://api`. With `base_url` (or neither: `FLIGHTMIND_API_BASE`, default `http://localhost:8000`) it uses the network. `transport` lets tests record requests. A new `AsyncClient` per call, timeout 10 s, as in Part 1.
- Messages for `track` equal those of `mcp_server/client.py` (same table), so the SCRUM-34 tests that check message text stay valid. Messages for the other three follow the same pattern: 404 names the id (`No event with id '...'`, `No raw record '...'`).
- `app` is the object `serve.build_app` or `mock_api.app` provides. Only `ASGITransport` is used, so the real API app works the same way.

### `tools.py`

```python
@dataclass
class ToolResult:
    data: Any                      # JSON-serialisable
    event_ids: list[str]           # events exposed in data
    raw_refs: list[str]            # raw_refs exposed in data
    is_error: bool = False
    result_count: int = 0

async def search_events(api, type=None, airport=None, since=None) -> ToolResult
async def get_track(api, icao24, from_=None, to=None, max_points=None) -> ToolResult
async def query_tracks(api, callsign=None, icao24=None, from_=None, to=None) -> ToolResult
async def get_raw(api, raw_ref) -> ToolResult
```

Each function catches `ApiError` and returns `ToolResult(data={"error": message}, is_error=True)`. The agent sends that to the model with `is_error: true`. The MCP server raises the message so the SDK returns `isError`.

**`search_events`.** `GET /api/events` with the given filters. Each event becomes `{id, type, icao24, callsign, start_ts, end_ts, airport, severity, raw_ref_count, first_raw_ref, last_raw_ref}`. Exposed: every event id, plus first and last raw_ref. The middle raw_refs are not in the result, so they are not citable from it (this is intended: the model must call `get_track` or `get_raw` to see them).

**`get_track`.** `GET /api/tracks/{icao24}` with `from` and `to`. Thinning when `max_points` is given and the track is longer (cap 200; minimum 2):

1. Always keep the first and last point.
2. Keep every point with `kept_for_event` true, in time order. If first, last and event points already exceed the cap, keep first, last and an even sample of the event points.
3. Fill the remaining slots with an even sample of the other points (index `round(i * (n - 1) / (k - 1))` over the remaining indexes).
4. Return the kept points in original order.

Result: `{icao24, callsign, points, total_points, returned_points, thinned}`. Without `max_points` the body is returned unchanged, with no added fields (requirement 8.4). Exposed: the `raw_ref` of every returned point. The agent dispatcher fills in `max_points = 60` when the model omits it.

**`query_tracks`.** Candidates are the distinct `icao24` in `GET /api/events` (no filters). Filter by `icao24` (case-insensitive) and by `callsign` (case-insensitive, exact) from the event rows. For each candidate, `GET /api/tracks/{icao24}` with `from` and `to` (run with `asyncio.gather`; there are few aircraft). Summary: `{icao24, callsign, points_in_window, first_ts, last_ts, min_alt_ft, max_alt_ft, first_raw_ref, last_raw_ref}`; `alt_ft` null values are ignored for min and max. Aircraft with zero points are left out. Exposed: first and last raw_ref per aircraft. The tool description says: "Only aircraft that have at least one detected event are searched, because the API has no list of aircraft." A candidate whose track call fails with 404 is skipped and noted in `skipped`.

**`get_raw`.** `GET /api/raw/{raw_ref}`; returns the body (`raw_ref`, `recording_file_id`, `record_index`, `sac`, `sic`, `decoded`, `hex`). Exposed: the `raw_ref` of the record.

`TOOLS` is a list of `ToolSpec(name, description, input_schema, func)`, built once at import time. The schemas are plain dicts. For the model, each gets `strict: true` and `additionalProperties: false`. The schema key for time arguments is `from` and `to` (as in the contract); the dispatcher maps them to `from_`. The MCP server uses the same schemas without `strict`. The text of descriptions and schemas is constant, so the tool list is byte-stable.

### `evidence.py`

```python
NOT_ENOUGH_TEXT = "Not enough evidence in the loaded recording to answer that."

class EvidenceSet:
    def add(self, result: ToolResult) -> None      # records event_ids and raw_refs
    def label_for(self, kind: str, id: str) -> str | None
    def render(self, final: dict | None) -> AskResponseDict
```

- `EvidenceSet` keeps `raw_refs: set[str]` and `events: dict[id, label]`. The event label is `f"{type} {callsign or icao24}"`, taken from the `search_events` result that exposed the id.
- `render(final)` takes the parsed structured output. Steps: for each claim, keep the citations whose `(kind, id)` is valid; drop and log the rest; drop a claim with no valid citation; if `final` is `None`, or its status is `not_enough_evidence`, or no claim is left, return the fixed response. Otherwise build `answer_md` as `"{text} [label1] [label2]"` per claim, joined by newlines, and `citations` as the de-duplicated `{kind, id, label}` list in first-use order.
- The fixed response is `{"answer_md": NOT_ENOUGH_TEXT, "citations": [], "status": "not_enough_evidence", "tool_calls": [...]}`. The text equals the canned answer today.
- A claim text that contains a newline has it replaced by a space, so one claim stays one line.
- A model that sets `status: ok` with zero claims gets the fixed response.

### `agent.py`

```python
async def run_agent(client, api: ApiClient, question: str, *,
                    model: str | None = None, clock=time.monotonic) -> dict
```

Request, per model call:

```python
client.messages.create(
    model=model, max_tokens=4096, system=SYSTEM_PROMPT, tools=TOOLS_FOR_MODEL,
    messages=messages, cache_control={"type": "ephemeral"},
    output_config={"effort": "medium", "format": {"type": "json_schema", "schema": ANSWER_SCHEMA}},
    timeout=min(20.0, time_left),
)
```

- No `thinking`, `temperature`, `top_p`, `top_k` or `budget_tokens`. The implementation (task 10) checks the argument names against the installed `anthropic` version, including top-level `cache_control` and `output_config`, and records any difference here before coding around it.
- `SYSTEM_PROMPT` is a module constant. It states the role (analyst assistant over recorded ADS-B data), the rules (use only tool results; cite with ids from the results; `not_enough_evidence` when the data does not answer; do not guess; about the `query_tracks` limit), and the answer format. It has no date, no per-request text. The question is the first user message.
- `ANSWER_SCHEMA`: object with `status` (enum `ok`, `not_enough_evidence`) and `claims` (array of `{text: string, citations: array of {kind: enum[cat021_record, event], id: string}}`), `additionalProperties: false`, all keys required.
- Loop:
  1. Check `len(question) <= 500` (else the endpoint returns 422 before `run_agent`; `run_agent` raises `ValueError` if called with a longer one).
  2. Record the start with `clock()`. Before each call, if `calls == 6` or `clock() - start >= 25`, stop with the fixed response.
  3. Call the model. Log usage (requirement 13.1).
  4. If `stop_reason == "tool_use"`: run every `tool_use` block (in order; they are independent, so `asyncio.gather` is fine), add each `ToolResult` to the `EvidenceSet`, append the assistant content and **one** user message holding all `tool_result` blocks (`is_error` set on failures). Content is `json.dumps(data, separators=(",", ":"))`. Continue.
  5. If `stop_reason == "end_turn"`: parse the text block as JSON (parse failure counts as no answer), call `evidence.render`.
  6. Any other stop reason (`max_tokens`, `refusal`, `pause_turn`, unknown): fixed response.
- `tool_calls` entries come from the `ToolResult`s: `{tool, args, result_count}`, plus `error` for failed ones. The args are what the model sent.
- A question of 500 characters at about 4 characters per token plus the system prompt and four tool schemas is far below 100K tokens (tech.md). A tool result is at most about 200 points, which is bounded by the thinning cap.
- Anthropic errors (`anthropic.APIError` and subclasses, including `APITimeoutError` and `APIConnectionError`) are not caught in `run_agent`; `endpoint.answer_question` catches them (requirement 11.5). The deadline is checked between calls, and each call's own timeout is `min(20, time_left)`.
- At the end, one summary line is logged (requirement 13.2).

### `guard.py`

```python
class AskGuard:
    def __init__(self, per_minute: int | None = None, per_day: int | None = None,
                 clock: Callable[[], float] = time.monotonic) -> None: ...
    def check(self, client_key: str) -> bool   # True = allowed; counts the request
def client_key(headers, client_host) -> str
```

- Limits come from `FLIGHTMIND_ASK_PER_MINUTE` (default 5) and `FLIGHTMIND_ASK_PER_DAY` (default 300); an unparsable or non-positive value falls back to the default.
- Per client: a deque of request times; entries older than 60 s are dropped. Per process: a counter that resets when `clock()` passes the start of its 24-hour window (a rolling window from the first request, not a calendar day). The per-client table is capped (for example 10,000 keys, oldest evicted) so a flood of fake `x-forwarded-for` values cannot grow memory without bound.
- `client_key`: the first comma-separated value of `x-forwarded-for`, stripped; else the client host; else `"unknown"`.
- `time.monotonic` is request throttling, not replay time, so contract C6 (`clock.now()`) does not apply. This is stated in the module docstring.
- The honest limit: serverless instances do not share memory and may restart, so one visitor can get several instances' worth of questions. The guard slows abuse; the Claude Console spend limit with auto-reload off caps spend.

### `endpoint.py`

```python
def agent_enabled() -> bool        # ANTHROPIC_API_KEY non-empty and FLIGHTMIND_ASK != "canned"
async def answer_question(question: str, api_app: Any, *, client=None, clock=None) -> dict
```

- `agent_enabled` reads `os.environ["ANTHROPIC_API_KEY"]` itself. `AsyncAnthropic` is created with `api_key=` set explicitly from that value, never with no arguments, and `ANTHROPIC_AUTH_TOKEN` is never read. A test sets only `ANTHROPIC_AUTH_TOKEN` and expects canned answers.
- `client` and `clock` arguments exist for tests (the fake client).
- `answer_question` builds `ApiClient(app=api_app)`, calls `run_agent`, and catches `anthropic.APIError`, `asyncio.TimeoutError` and `httpx.HTTPError` raised by the SDK. On any of them: log `type(exc).__name__` (not `str(exc)`, which can echo request details) and return the fixed response with `tool_calls=[{"tool": "claude_api", "error": "<ClassName>"}]`.
- The edit in `mock_api/app.py`:

```python
@app.post("/api/ask")
async def ask(body: AskRequest, request: Request):
    if agent_enabled():
        if len(body.question) > 500: raise HTTPException(422, "Question is longer than 500 characters.")
        if not _guard.check(client_key(request.headers, request.client.host if request.client else None)):
            raise HTTPException(429, "Too many questions. Try again in a minute.")
        return await answer_question(body.question, request.app)
    ...existing canned code, unchanged...
```

  `ask` becomes `async`; the canned branch has no blocking work. Import of `agent.endpoint` is at the top of the file; `anthropic` is imported inside `endpoint.py` so a missing package does not break the canned path (import error handled: `agent_enabled()` returns false and logs once).

## Data flow for one question

1. `POST /api/ask {"question": "Any emergency squawk 7700?"}`.
2. Guard allows. The model calls `search_events(type="squawk_7700")`. The result lists the event with its id and first and last `raw_ref`.
3. The model calls `get_track` for that aircraft (and maybe `get_raw`). Tool results go back in one message.
4. The model returns structured output with claims and citation ids.
5. `evidence.render` keeps only claims whose ids came from tool results, writes `answer_md` and the citations, and the endpoint returns the `AskResponse`.

## Error handling summary

| Situation | Result |
| --- | --- |
| Question over 500 characters | HTTP 422, no model call |
| Over a rate limit | HTTP 429, no model call |
| Tool failure (404, unreachable, bad JSON) | Tool error result to the model; run continues; `tool_calls` has `error` |
| Claude API error or timeout | `not_enough_evidence`, `tool_calls` entry `claude_api` with the class name |
| 6 calls or 25 s reached | `not_enough_evidence` |
| `max_tokens`, `refusal`, bad JSON in the final text | `not_enough_evidence` |
| Claim cites an id no tool returned | The claim is dropped; if none left, `not_enough_evidence` |
| No key, or `FLIGHTMIND_ASK=canned` | Canned answers, no model, no guard |

## Testing strategy

Files in `services/intel/tests/` (names are a plan; the requirement is `test_agent*.py`): `test_agent_tools.py`, `test_agent_evidence.py`, `test_agent_loop.py`, `test_agent_endpoint.py`, `test_agent_guard.py`. MCP list change in `test_mcp_server.py`; four-tool call tests added to a new `test_agent_mcp.py`.

- **Fake client.** `FakeAnthropic` has `.messages.create(**kwargs)` (async) that pops the next scripted response and records `kwargs` and a deep copy of `messages`. Responses are small objects with `.stop_reason`, `.content` (blocks with `.type`, `.id`, `.name`, `.input`, `.text`) and `.usage` (four token counts). A scripted exception can be raised in place of a response (built with the real `anthropic` error classes, so the endpoint's `except` is exercised; the key is put in the exception message on purpose, to prove it is not logged).
- **Mock API.** Tools and the loop use `ApiClient(app=mock_api.app)`. Expected ids come from the mock data through the API, not by importing `mock_api.data` in the production code (tests may read it to find ids).
- **Time.** Deadline tests pass a fake `clock` that jumps past 25 s. Guard tests pass a fake clock. No test sleeps.

| Requirement | Test |
| --- | --- |
| 7.1 to 7.5 | `ApiClient` with `MockTransport`: paths and query parameters, encoded `a/b`, each error message, timeout 10.0; with `app=` the call reaches the mock. |
| 8.2 | `search_events` result has the cut-down fields, a count, first and last raw_ref, and no `raw_refs` list. |
| 8.3, 8.4 | Thinning keeps first, last and `kept_for_event` points, respects the cap (200), reports `total_points`; without `max_points` the body equals the API body. |
| 8.5, 8.6 | `query_tracks` summaries (min and max altitude, null altitudes ignored); only aircraft with events are candidates; filters by callsign and icao24; window excludes. |
| 8.7, 8.8 | `get_raw` returns decoded and hex; unknown id gives `is_error` and no exception. |
| 9.1 to 9.3 | Claim citing an unreturned raw_ref is dropped and logged; all dropped gives the fixed response; kind mismatch (event id used as `cat021_record`) is dropped. |
| 9.4 to 9.8 | `status: ok` output: `answer_md` lines with bracketed labels, citations de-duplicated in first-use order, event label `<type> <callsign>`, `tool_calls` entries, whole response validates against `AskResponse` (reuse the `inline` and `check` helpers). |
| 10.1, 10.7 | Loop with two tool calls in one turn: the second request's last message is one user message with two `tool_result` blocks. |
| 10.2 to 10.4, 10.8 | The recorded request kwargs: model default and override, `output_config` has effort `medium` and a format, no `thinking`/`temperature`/`top_p`/`top_k`, tools have `strict` true and `additionalProperties` false, the system prompt and tools are identical across two runs, `cache_control` ephemeral. |
| 10.6 | 6-call limit, deadline, `max_tokens` and `refusal` each give the fixed response; a 501-character question gets 422 through the endpoint. |
| 11.2, 11.3 | No key: canned answer, fake never called. `ANTHROPIC_AUTH_TOKEN` alone: canned. `FLIGHTMIND_ASK=canned` with a key: canned. Empty key: canned. |
| 11.5 | Scripted `anthropic` errors give `not_enough_evidence` with `claude_api` error entry; the key string is not in the body or in captured logs. |
| 12 | Guard: sixth question in a minute is refused; allowed again after 60 s; 301st per day refused; two clients are independent; `x-forwarded-for` first address; 429 through the endpoint with no model call; canned mode never limited. |
| 13 | Captured `flightmind.agent` logs have a usage line per call and one summary line; the HTTP body has no usage. |
| 14 | MCP `list_tools` is exactly the four names; each tool called through the in-memory session; `get_track` without `max_points` equals the API body. |
| 15 | A test that reads `requirements.txt`, `requirements-serve.txt` and root `pyproject.toml` and checks `anthropic` (and `httpx` where required) are listed. |

Run `python -m pytest -q` from `services/intel`; all existing tests (mock API, serve, MCP) must still pass.

## Cost and time budget

- Haiku 5.5 pricing is not written in this spec; task 22 reads the current price from the Claude API documentation and writes it, with the date, in the proof record. Cost per answer is computed from the logged token counts.
- A question takes at most 6 model calls and 25 s, and the tool results are bounded (60 points by default, 200 at most), so one answer is bounded in tokens. The per-call 20 s timeout keeps one slow call from using the whole budget.
- Prompt caching only helps when the prefix (system prompt and tools) passes the model's minimum cacheable length; the first cost record shows whether `cache_read` is above zero. If not, nothing breaks; the spec does not promise savings.

## Dependencies and disclosure (Part 2)

`anthropic` (official Claude SDK, the agent) and `httpx` (HTTP client, already disclosed in Part 1) do real work. `services/intel/README.md` names both. The installed `anthropic` version is recorded in tasks.md task 10.

## Open items (Part 2)

1. **Anthropic SDK argument names.** Top-level `cache_control`, `output_config` with `effort` and `format`, and the strict tool fields are taken from the decisions for this ticket. Task 10 checks them against the installed SDK; if the installed version names anything differently, the design is updated before the loop is written.
2. **Tracks list endpoint** for Role 1 (requirement open item 1).
3. **Python 3.10 locally, 3.12 on Vercel.** Use only syntax valid on 3.10.
4. **Shared rate limit.** Not planned (requirement open item 4).
