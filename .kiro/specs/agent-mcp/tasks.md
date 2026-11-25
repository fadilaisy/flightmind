# Tasks: SCRUM-34 first MCP server with get_track

Implements `requirements.md` and `design.md` in this folder. All paths are relative to `E:\Flight Mind\flightmind`. Run commands from `services/intel` with the `.venv` there. Do not edit anything under `contracts/` or `services/intel/mock_api/`.

- [x] 1. Install the SDK and spike the `from` parameter name
  - **Result (2026-11-22):** `mcp` 2.x (2.3.0) renamed `FastMCP` to `MCPServer` and changed other APIs, so `requirements.txt` pins `mcp>=1.2,<2` (installed 1.30.0, Python 3.10.11). On 1.30.0, `FastMCP` with `Field(alias="from")` publishes `from` in the schema but fails at call time ("unexpected keyword argument 'from'"). The low-level `mcp.server.lowlevel.Server` with a hand-written `inputSchema` works: `from` reaches the handler, a raised exception returns `isError: true` with our exact message, a missing `icao24` returns `isError` from schema validation, and a returned dict is sent unchanged as structured content and JSON text. Tasks 3 and 4 use the low-level `Server`. The parameters stay named `from` and `to`, so requirement 1.1 is unchanged.
  - Add `mcp>=1.2` to `services/intel/requirements.txt` and install it in `services/intel/.venv`. Record the installed version and the confirmed floor.
  - In a throwaway script (not committed), build a `FastMCP` tool with `Annotated[str | None, Field(alias="from")]` and print its input schema from `list_tools()`. Check that a call with `{"from": "..."}` reaches the function.
  - If the alias does not work, try a hand-written `inputSchema`. If that also fails, stop and ask the user before renaming the parameters to `from_ts` and `to_ts`.
  - Also check that raising `ToolError` returns `isError: true` with the message text, and that a `dict[str, Any]` return reaches the caller unchanged.
  - Done when the working approach is written as a short comment at the top of `server.py` in task 3.
  - _Requirements: 1.1, 3.6_

- [x] 2. Write the HTTP client in `services/intel/mcp_server/client.py`
  - Create `services/intel/mcp_server/__init__.py` (empty).
  - Implement `DEFAULT_BASE`, `TIMEOUT_SECONDS = 10.0`, `TrackError`, `api_base()` and `fetch_track(...)` exactly as in design.md: strip and reject empty `icao24`, `quote(icao24, safe='')`, query parameters `from` and `to` only when given, the error message table, an optional `transport` argument for tests.
  - Use type hints. Python 3.10 syntax only. Log to stderr with `logging`; no `print`.
  - Done when `fetch_track` returns the mock API body for `8A0F21` through an `httpx.ASGITransport`.
  - _Requirements: 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3_

- [x] 3. Write the MCP server in `services/intel/mcp_server/server.py`
  - Create `Server("flightmind")` from `mcp.server.lowlevel`, register `list_tools` and `call_tool` handlers, and declare `get_track` with a hand-written `inputSchema` (`icao24` required string, optional `from` and `to`) and the tool description from design.md (6-character hex address, ISO 8601 times, cite `raw_ref`).
  - Let `TrackError` propagate from `call_tool`; the SDK turns it into `isError: true` with its message. Add `main()` that runs the stdio transport. Add the module-level `_transport = None` that tests can set.
  - Create `services/intel/mcp_server/__main__.py` (calls `main()`) and `services/intel/mcp_server/run.py` (adds its parent folder to `sys.path`, then calls `main()`).
  - Done when `python services/intel/mcp_server/run.py` started from the repo root stays running and answers an MCP `initialize` request on stdin with nothing else written to stdout.
  - _Requirements: 1.1, 1.6, 3.6, 3.7, 5.2_

- [x] 4. Write the tests in `services/intel/tests/test_mcp_server.py`
  - Use `httpx.ASGITransport(app=mock_api.app)` for success cases and `httpx.MockTransport` for error cases and request recording. Use `@pytest.mark.anyio` for async tests.
  - Cover every row of the testing table in design.md: tool list is exactly `["get_track"]`; result validates against the `Track` schema (copy the `inline` and `check` helpers from `test_mock_api.py`); `raw_ref` list equals the API's list in the same order; `from` and `to` sent as query parameters and narrowing points; default and overridden `FLIGHTMIND_API_BASE`; 404, unreachable, 422, 500, non-JSON 200; timeout value 10.0; `../meta` and `a/b` stay on `/api/tracks/` as a single encoded segment; empty `icao24` makes zero requests.
  - Run `python -m pytest -q` from `services/intel`. Both `test_mock_api.py` and the new file must pass.
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

- [x] 5. Register the server in `.kiro/settings/mcp.json`
  - Create the file with the `flightmind` entry from design.md: `command: python`, `args: ["services/intel/mcp_server/run.py"]`, `env.FLIGHTMIND_API_BASE = http://localhost:8000`, `disabled: false`, `autoApprove: ["get_track"]`.
  - Check that the file is valid JSON, contains no absolute path and no secret, and is not matched by `.gitignore` (`git check-ignore .kiro/settings/mcp.json` prints nothing).
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 6. Document in `services/intel/README.md`
  - Add the section "MCP server (SCRUM-34)": what it does, install (`pip install -r requirements.txt` into the Python that Kiro will launch), start the mock API, the env var and its default, how to call `get_track` from chat, the error messages, and the `python` vs `python3` note for macOS and Linux.
  - Add the third-party disclosure for `mcp` (official Python SDK) and `httpx`.
  - _Requirements: 5.4, 5.5_

- [x] 7. Verify in Kiro and record what is true
  - **Result (2026-11-25):** In the Kiro IDE the folder first opened in Restricted Mode and `flightmind` was not loaded. After Trust and Developer: Reload Window, Kiro's log shows `mcp.connect.ok` for `flightmind` over stdio with the relative `args`, so (a) workspace servers start in the workspace root, and (b) `python` on PATH found `mcp` on this machine. The three calls were then run through Kiro's chat CLI (`kiro-cli chat`, 3.1.0, same `.kiro/settings/mcp.json`) and recorded: `8A0F21` returned 60 points, callsign GIA123, first `raw_ref` `rec01:0`; `ZZZZZZ` returned "No aircraft with icao24 'ZZZZZZ' in the loaded recording."; with the API stopped it returned "Cannot reach the FlightMind API at http://localhost:8000. ..." (`isError: true`). The server stayed up for all three. Clip and screenshot: `docs/kiro/scrum-34/`. Not done: the calls were not typed into the IDE chat panel (the server is connected there), and whether Kiro Crew reads `.kiro/settings/mcp.json` was not checked.
  - Start the mock API (`uvicorn mock_api.app:app --port 8000`). In Kiro chat, ask for the track of `8A0F21` and confirm points with `raw_ref` come back. Ask for `ZZZZZZ` and confirm the unknown-aircraft message. Stop the API, ask again, and confirm the unreachable message. The server must stay alive in all three cases.
  - Confirm the two assumptions from design.md: workspace servers start in the workspace root, and `python` on PATH finds `mcp`. If the first is false, switch `args` to the documented fallback and update design.md and the README.
  - Check whether Kiro Crew reads `.kiro/settings/mcp.json`. Write the answer in the README section. If it does not, state how a Crew user registers the server.
  - A person must do this task at a Kiro window. If no one is available, leave it unchecked and say so in the final report; do not mark it done from the tests alone.
  - _Requirements: 3.1, 3.2, 5.1, 5.4_

- [x] 8. Hand-offs and log
  - **Result (2026-11-26):** Role 1 issue for the root README line is fadilaisy/flightmind#16. The SCRUM-34 lines are in `KIRO.md` (agent-mcp and agent-mcp/7). Commits use the `Kiro:` trailer; the task 7 work is in PR #15.
  - Open an issue for Role 1 asking for the `mcp` and `httpx` line in the root `README.md` third-party list, noting nothing else changes there.
  - Add the SCRUM-34 line to `KIRO.md` following the existing row format, with the date, Role 3 and the `(chat)` task suffix used for SCRUM-33.
  - Commit with the `Kiro:` trailer from `.gitmessage`. Stage files by name, not `git add .`.
  - _Requirements: 5.5_
