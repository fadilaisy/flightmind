# Tasks: SCRUM-34 first MCP server with get_track

Part 2 (SCRUM-36, cited agent and three more tools) starts at "Part 2: SCRUM-36 cited agent" below; tasks 1 to 9 are done and unchanged.


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
  - **Result (2026-11-25):** In the Kiro IDE the folder first opened in Restricted Mode and `flightmind` was not loaded. After Trust and Developer: Reload Window, Kiro's log shows `mcp.connect.ok` for `flightmind` over stdio with the relative `args`, so (a) workspace servers start in the workspace root, and (b) `python` on PATH found `mcp` on this machine. A person did the Trust and Reload steps in the IDE. The three calls were then run through Kiro's chat CLI (`kiro-cli chat`, 3.1.0, same `.kiro/settings/mcp.json`), driven and recorded by Claude Code, not typed by a person: `8A0F21` returned 60 points, callsign GIA123, first `raw_ref` `rec01:0`; `ZZZZZZ` returned "No aircraft with icao24 'ZZZZZZ' in the loaded recording."; with the API stopped it returned "Cannot reach the FlightMind API at http://localhost:8000. ..." (`isError: true`). The server stayed up for all three. Clip and screenshot: `docs/kiro/scrum-34/`. The two checks left open (a person typing the calls into the IDE chat panel, and whether Kiro Crew reads `.kiro/settings/mcp.json`) moved to task 9.
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

- [x] 9. Finish the two checks left from task 7
  - Added on 2026-11-26 after the PR #15 review: task 7's calls were driven by Claude Code through `kiro-cli`, and Kiro Crew was not checked.
  - **Result (2026-11-26):** Zahran typed the three asks into the Kiro IDE chat panel: `8A0F21` returned 60 points, callsign GIA123, `raw_ref` `rec01:0` to `rec01:2`; `ZZZZZZ` returned the unknown-aircraft message; with the API stopped it returned the unreachable message. Claude Code started and stopped the mock API and recorded the screen. Clip: `docs/kiro/scrum-34/2026-11-26_role3_mcp-get_track-ide.mp4` (115 s, played at 1.75x). Kiro Crew 0.13.1 does not read `.kiro/settings/mcp.json`: its MCP Servers page lists 13 servers and not `flightmind` (`docs/kiro/scrum-34/2026-11-26_role3_crew-mcp-servers.png`); the README now says so. The clip is in the shared Drive and has a row in `docs/kiro/clips.md`.
  - With the mock API running, a person types the three asks from task 7 into the Kiro IDE chat panel (`8A0F21`, `ZZZZZZ`, then again with the API stopped) and records a short clip. Name it `YYYY-MM-DD_role3_mcp-get_track-ide.mp4`, upload it to the shared Drive folder and add a row to `docs/kiro/clips.md`.
  - In Kiro Crew, check whether the `flightmind` server shows up from `.kiro/settings/mcp.json` without a manual entry. Write yes or no in the "MCP server (SCRUM-34)" section of `services/intel/README.md`. If no, keep the manual steps that are there now.
  - Add a `KIRO.md` row for agent-mcp/9.
  - _Requirements: 3.1, 3.2, 5.1, 5.4_


---

# Part 2: SCRUM-36 cited agent

Implements requirements 7 to 17 in `requirements.md` and Part 2 of `design.md`. All paths are relative to `E:\Flight Mind\flightmind`. Run commands from `services/intel` with the `.venv` there. Edits are allowed only in `services/intel/`, the `dependencies` list of the root `pyproject.toml`, and this spec folder. Do not edit anything under `web/`, `contracts/` or `services/pipeline/`, and do not commit or switch branches unless the user asks. No task calls the Claude API except tasks 22 to 24, which need a key that only Zahran enters, in his own shell; the key is never written to a file in the repo.

- [x] 10. Install the SDK and check its argument names
  - **Result (2026-11-26):** Installed `anthropic` 2.14.0 in `services/intel/.venv` (Python 3.10.11; `httpx` 0.28.1 also present). Floor written to the lists: `anthropic>=2.14,<3` in `requirements.txt` and `requirements-serve.txt`; `httpx>=0.27` added to `requirements-serve.txt`; `"anthropic>=2.14,<3"` and `"httpx>=0.27"` added to `dependencies` in the root `pyproject.toml` (nothing else changed there). `python -c "import anthropic, httpx"` works. Checked by `inspect.signature`, no request sent: `AsyncMessages.create` has `output_config`, `cache_control`, `timeout`, `tools`, `system`, `max_tokens`, `thinking`, and has no `temperature` parameter. `OutputConfigParam` has `effort` (`low`, `medium`, `high`, `xhigh`, `max`) and `format`; `JSONOutputFormatParam` is `{type: "json_schema", schema}`; `ToolParam` has `strict`. Names match design.md. One correction: the timeout error class is `anthropic.APITimeoutError` (design.md says `APITimeoutException`, which does not exist). `AsyncAnthropic(api_key=...)` ignores `ANTHROPIC_AUTH_TOKEN` (SDK docstring: an explicit argument means environment variables are not consulted).
  - Add `anthropic` to `services/intel/requirements.txt` and `services/intel/requirements-serve.txt`, and add `anthropic` and `httpx` to the `dependencies` list in the root `pyproject.toml` and `httpx` to `requirements-serve.txt`. Change nothing else in `pyproject.toml`. Install into `services/intel/.venv`.
  - Record here the installed `anthropic` version and the confirmed floor to put in the lists.
  - Without calling the API, check on the installed SDK that `AsyncAnthropic().messages.create` accepts `output_config` (with `effort` and `format`), top-level `cache_control`, per-call `timeout`, and tools with `strict`. If any name differs from design.md, update design.md before task 14.
  - Done when `python -c "import anthropic, httpx"` works in the venv, the version is written in this task, and the three dependency lists name `anthropic`.
  - _Requirements: 10.1, 10.2, 10.4, 15.1, 15.2, 15.3_

- [x] 11. Write the API client in `services/intel/agent/api_client.py`
  - **Result (2026-11-26):** `agent/__init__.py` and `agent/api_client.py` written (`ApiClient` with `events`, `event`, `track`, `raw`; `ApiError`; base URL from the argument or `FLIGHTMIND_API_BASE`; `app=` uses `httpx.ASGITransport`; timeout 10 s; path values quoted with `safe=''`). A script run from `services/intel` showed `await ApiClient(app=mock_api.app).track("8A0F21")` equal to the body of `GET /api/tracks/8A0F21` on the mock (`True`). It does not import `mock_api`.
  - Create `services/intel/agent/__init__.py` (empty).
  - Implement `ApiClient` and `ApiError` as in design.md: methods `events`, `event`, `track`, `raw`; construction with a base URL or with `app=` (ASGI transport); single-segment URL encoding; timeout 10 s; error messages (the `track` messages equal those in `mcp_server/client.py`).
  - It must not import `mock_api` or read any data file.
  - Done when `ApiClient(app=mock_api.app).track("8A0F21")` returns the same body as `GET /api/tracks/8A0F21` on the mock.
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 12. Write the four tools in `services/intel/agent/tools.py`
  - **Result (2026-11-26):** `tools.py` has `ToolResult`, the four functions, `TOOL_SPECS` (one description and property list per tool), `TOOLS_FOR_MODEL` (strict definitions derived from the specs: every property in `required`, optional ones `anyOf` string/integer and null, `additionalProperties` false, no range keywords), `mcp_schema` (plain schema for task 17), `validate_args` and `run_tool` (maps `from`/`to` to `from_`, fills `max_points = 60` only with `for_agent=True`, returns an error result for bad arguments). Run against the mock through the ASGI transport: `get_track` without `max_points` returned a body equal to the API body; with the agent default, `8A1C07` (90 points) came back as 60 of 90; `search_events(type=go_around)` gave 2 events; `query_tracks(callsign=lni456)` gave one summary (90 points, 8000 ft, `rec01:3` to `rec01:269`); `get_raw("nope")` gave `is_error` True. `ToolResult` has one field beyond the design, `event_labels`, so the evidence rule can write `<type> <callsign>` without parsing tool data.
  - Implement `ToolResult`, `search_events`, `get_track` (with thinning), `query_tracks`, `get_raw`, the `TOOLS` registry with constant descriptions and JSON schemas (`from` and `to` names, `additionalProperties: false`), and the dispatcher that maps `from` to `from_` and fills `max_points = 60` for the agent.
  - Tool failures return `ToolResult(is_error=True)`; no exception ends a run.
  - The `query_tracks` description states the candidate limit (aircraft that have at least one event).
  - Done when each tool returns the expected shape against the mock API through the ASGI transport, and `get_track` without `max_points` returns the API body unchanged.
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9_

- [x] 13. Write the evidence rule in `services/intel/agent/evidence.py`
  - **Result (2026-11-26):** `evidence.py` has `NOT_ENOUGH_TEXT`, `not_enough()`, `EvidenceSet` (`add`, `label_for`) and `render(final, tool_calls)`. A script with one valid and one invented citation rendered only the valid one (`answer_md` `A b [holding LNI456]`, a newline in the claim became a space); an answer whose only citation was invented rendered `not_enough_evidence`. Invalid citations and uncited claims are logged on `flightmind.agent` with kind and id only. `render` takes the tool-call list as a second argument so the response carries `tool_calls`.
  - Implement `NOT_ENOUGH_TEXT`, `EvidenceSet` (`add`, `label_for`) and `render(final)` as in design.md: validate kind and id against what tools returned, drop and log invalid citations and uncited claims, one line per kept claim with bracketed labels, de-duplicated citations in first-use order, the fixed response in every other case.
  - Done when a scripted final answer with one valid and one invented citation renders only the valid one, and an answer with only invented citations renders `not_enough_evidence`.
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8_

- [x] 14. Write the agent loop in `services/intel/agent/agent.py`
  - **Result (2026-11-26):** `agent.py` has `SYSTEM_PROMPT`, `ANSWER_SCHEMA`, `TOOLS_FOR_MODEL`, `log_usage` and `run_agent(client, api, question, *, model=None, clock=time.monotonic)`; the request carries `model`, `max_tokens` 4096, `system`, `tools`, top-level `cache_control`, `output_config` (effort `medium` plus the json_schema format) and `timeout=min(20, time left)`, and none of `thinking`, `temperature`, `top_p`, `top_k`, `budget_tokens`, `tool_choice`. A scripted two-turn run (a thinking block plus two tool calls, then a final answer) against the mock returned an `AskResponse`-valid dict, and the captured `flightmind.agent` log had two `usage` lines and one `summary` line (`tests/test_agent_loop.py`). No real client was built in any check.
  - Implement `SYSTEM_PROMPT`, `ANSWER_SCHEMA`, `TOOLS_FOR_MODEL` and `run_agent(client, api, question, *, model=None, clock=time.monotonic)` as in design.md: the request arguments of requirement 10 (no `thinking`, `temperature`, `top_p`, `top_k`, `budget_tokens`), the 6-call, 25 s and 20 s limits, one user message per turn of tool results, the stop-reason handling, and the usage and summary logging on logger `flightmind.agent`.
  - The model id comes from `FLIGHTMIND_LLM_MODEL`, default `claude-haiku-5-5`. The system prompt and tool list contain no timestamp.
  - Done when a scripted two-turn run against the mock API returns an `AskResponse`-shaped dict and the log has one usage line per call plus one summary line.
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9, 13.1, 13.2, 13.4_

- [x] 15. Write the demo guard in `services/intel/agent/guard.py`
  - **Result (2026-11-26):** `guard.py` has `AskGuard` and `client_key`; defaults 5 per minute and 300 per day, from `FLIGHTMIND_ASK_PER_MINUTE` and `FLIGHTMIND_ASK_PER_DAY` (bad or non-positive values fall back), at most 10,000 tracked clients, refused requests are not counted. With a fake clock the sixth request in a minute was refused, 59 s later still refused, and allowed at 60 s (`tests/test_agent_guard.py`, 7 tests pass). The module docstring says this is throttling, not replay time, and that it does not cap spend on serverless.
  - Implement `AskGuard` and `client_key` as in design.md: per-client per-minute limit, per-process daily limit, defaults 5 and 300, settings `FLIGHTMIND_ASK_PER_MINUTE` and `FLIGHTMIND_ASK_PER_DAY`, injected clock (default `time.monotonic`), a cap on tracked clients. State in the module docstring that this is request throttling, not replay time, and that it does not cap spend on serverless.
  - Done when a test with a fake clock refuses the sixth request in a minute and allows it after 60 seconds.
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

- [x] 16. Wire the agent into `/api/ask`
  - **Result (2026-11-26):** `agent/endpoint.py` has `agent_enabled()` (non-empty `ANTHROPIC_API_KEY`, `FLIGHTMIND_ASK` not `canned`, SDK importable), `make_client()` (`AsyncAnthropic(api_key=..., timeout=20.0, max_retries=1)`) and `answer_question`, which catches `AuthenticationError`, `RateLimitError`, `APITimeoutError`, `APIConnectionError`, `APIStatusError` (then `AnthropicError`, `asyncio.TimeoutError`, `httpx.HTTPError`) and logs only the class name. In `mock_api/app.py` only the imports, `_guard` and `ask` changed (`ask` is now `async` and takes `request`). With no key the existing canned tests pass unchanged and a test makes `make_client` raise if called; with a fake client and a dummy key the endpoint returned the agent's cited answer; 422 for 501 characters and 429 on the sixth question, both with no model call. Full suite: see task 20.
  - Write `services/intel/agent/endpoint.py` (`agent_enabled`, `answer_question`) as in design.md: the key check on `ANTHROPIC_API_KEY` only, the explicit `api_key=` for `AsyncAnthropic`, Claude error handling with the class name only.
  - In `services/intel/mock_api/app.py` change only `ask`: when `agent_enabled()`, check length (422) and the guard (429), then `await answer_question(...)`; otherwise run the existing canned code unchanged.
  - Done when `/api/ask` with no key still returns the canned answers in the existing tests, and with a fake client and a key it returns the agent's answer.
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 12.3, 12.6, 10.6, 13.3_

- [x] 17. Expose the four tools in the MCP server
  - **Result (2026-11-26):** `mcp_server/server.py` now lists `query_tracks`, `search_events`, `get_track`, `get_raw` from `TOOL_SPECS` (`from` and `to` kept) and runs them through `run_tool` on an `ApiClient(transport=_transport)`; a tool error raises `ValueError(message)`, which the client sees as `isError`. `client.py` is untouched, `.kiro/settings/mcp.json` is untouched. The 23 existing tests in `test_mcp_server.py` pass (`23 passed`) with two expectation changes, both in `test_tool_list_is_exactly_get_track`: the tool list, and the `get_track` property set, which now includes `max_points` (the spec said only the tool list changes, but the new optional argument makes the old property assertion false). `get_track` without `max_points` returns the unchanged body (`test_agent_mcp.py`).
  - Edit `services/intel/mcp_server/server.py` so `list_tools` returns `query_tracks`, `search_events`, `get_track` and `get_raw` (descriptions and schemas from `tools.py`, `from` and `to` kept) and `call_tool` runs the function in `tools.py` through an `ApiClient` on `FLIGHTMIND_API_BASE` (using `_transport` when set). A tool error result raises so the client gets `isError`. `get_track` without `max_points` returns the unchanged body. Leave `client.py` as it is.
  - In `services/intel/tests/test_mcp_server.py` change only the expected tool list. Do not edit `.kiro/settings/mcp.json`.
  - Done when the 23 existing MCP tests pass with only that one expectation changed.
  - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6_

- [x] 18. Tests for the client and the tools: `services/intel/tests/test_agent_tools.py`
  - **Result (2026-11-26):** `pytest -q tests/test_agent_tools.py`: 22 passed (written in the previous turn, re-run in the full suite below).
  - Cover the rows for requirements 7 and 8 in the design testing table: request paths, query parameters and encoding; each error message; thinning keeps first, last and event points and respects the cap of 200; unchanged body without `max_points`; `query_tracks` summaries, filters and the events-only candidate limit; `get_raw`; unknown ids give a tool error result.
  - Use `ApiClient(app=mock_api.app)` and `httpx.MockTransport`. Use `@pytest.mark.anyio`.
  - Done when `python -m pytest -q tests/test_agent_tools.py` passes.
  - _Requirements: 16.1, 16.8, 7.1, 7.2, 7.3, 7.4, 7.5, 8.2, 8.3, 8.4, 8.5, 8.7, 8.8_

- [x] 19. Tests for evidence and the loop: `services/intel/tests/test_agent_evidence.py` and `test_agent_loop.py`
  - **Result (2026-11-26):** `pytest -q tests/test_agent_evidence.py tests/test_agent_loop.py`: 31 passed, no network, no key (fake client from `tests/agent_fakes.py`).
  - Build the `FakeAnthropic` stand-in (scripted responses, recorded request arguments, scripted errors). Cover: all tool results of a turn in one user message; claim citing an unreturned raw_ref dropped; kind mismatch dropped; all dropped gives `not_enough_evidence`; valid run validates against `AskResponse` in `contracts/openapi.yaml`; event label `<type> <callsign>`; first-use order and de-duplication; the 6-call limit, the deadline (fake clock), `max_tokens` and `refusal`; request arguments (no forbidden parameters, `strict`, `cache_control`, `output_config`, stable prompt and tools); usage and summary log lines.
  - Done when `python -m pytest -q tests/test_agent_evidence.py tests/test_agent_loop.py` passes with no network and no key.
  - _Requirements: 16.1, 16.2, 16.3, 16.4, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 10.2, 10.3, 10.4, 10.6, 10.7, 10.8, 13.1, 13.2_

- [x] 20. Tests for the endpoint, the guard, the MCP tools and the dependency lists: `services/intel/tests/test_agent_endpoint.py`, `test_agent_guard.py`, `test_agent_mcp.py`
  - **Result (2026-11-26):** `test_agent_mcp.py` (5 tests: four tools listed, each runs through the in-memory session, unknown raw_ref is an error, `get_track` unchanged without `max_points`) and `tests/test_dockerfile.py` (2 tests, the Dockerfile guard requested for this turn) added. Whole suite from `services/intel`: `152 passed in 6.91s`.
  - Cover: no key gives canned answers and the fake is never called; `ANTHROPIC_AUTH_TOKEN` alone, an empty key and `FLIGHTMIND_ASK=canned` give canned answers; Claude API errors give `not_enough_evidence` with a `claude_api` error entry and the key in neither body nor logs; 422 for 501 characters; guard per minute, per day, two clients, `x-forwarded-for`, 429 with no model call, canned mode not limited; MCP lists exactly four tools and each runs through the in-memory session; the three dependency lists name `anthropic`.
  - Run the whole suite: `python -m pytest -q` from `services/intel`. Existing tests must pass.
  - Done when the whole suite passes; record the pass count here.
  - _Requirements: 16.1, 16.5, 16.6, 16.7, 16.9, 16.10, 11.2, 11.3, 11.5, 12.1, 12.2, 12.3, 12.4, 12.6, 14.1, 15.1_

- [x] 21. Document in `services/intel/README.md`
  - **Result (2026-11-26):** Added "Cited agent (SCRUM-36)" (modes, switch-on rule, the five variables plus `FLIGHTMIND_API_BASE`, evidence rule, limits including the `query_tracks` candidate limit, guard and its honest limit, local run and the three demo questions) and rewrote the MCP section for four tools; `anthropic` is in the disclosure list with `mcp` and `httpx`.
  - **Extra fix this turn (allowed once):** root `Dockerfile` got one line, `COPY services/intel/agent/ agent/`, because `mock_api/app.py` imports `agent`. `tests/test_dockerfile.py` parses the imports of `mock_api/app.py`, `serve.py` and the `agent/` and `mock_api/` modules and fails if a top-level `services/intel` package is not copied. Docker was not run.
  - Add the section "Cited agent (SCRUM-36)": what `/api/ask` does with and without a key, the environment variables (`ANTHROPIC_API_KEY`, `FLIGHTMIND_LLM_MODEL`, `FLIGHTMIND_ASK`, `FLIGHTMIND_ASK_PER_MINUTE`, `FLIGHTMIND_ASK_PER_DAY`), the four tools, the `query_tracks` limit, the evidence rule, the guard and its honest limit (the Claude Console spend limit with auto-reload off is the real cap), and how to run the agent locally with the key set in the shell only.
  - Update the MCP section to list the four tools. Disclose `anthropic` (official Claude SDK) next to `mcp` and `httpx`.
  - _Requirements: 12.5, 14.4, 15.4_

- [x] 22. Proof run against the real Claude API, locally
  - **Result (2026-11-26):** Done by hand outside Kiro, against `mock_api.app:app` on localhost with the key set by Zahran in his own terminal, model `claude-haiku-5-5`, branch at e0ed6fb. All three `ok`, all under 30 seconds, and every cited id was opened in the mock API and supports its claim.

    | Question | Time | Model calls | Tool calls | Citations | input / output / cache write / cache read tokens | Cost |
    | --- | --- | --- | --- | --- | --- | --- |
    | (a) squawk 7700 | 7.2 s | 2 | search_events | event squawk_7700 SIA9 | 6 / 508 / 3751 / 3478 | $0.0008 |
    | (b) go-around at WIII | 8.0 s | 3 | search_events, get_track x2 | events go_around GIA123 and CTV88, rec01:107, rec01:141 | 8 / 891 / 6686 / 7415 | $0.0014 |
    | (c) LNI456 hold | 5.6 s | 3 | search_events, get_track | event holding LNI456, rec01:68, rec01:269 | 8 / 717 / 9243 / 7304 | $0.0016 |

    Cost uses the list rates for prompts up to 100K tokens ($0.10 input, $0.50 output, $0.125 cache write, $0.01 cache read per million tokens): about $0.0012 a question, so the $100 credit is roughly 80,000 questions of this size. An earlier run on 5a44506 (before the review fixes) gave the same answers in 15.5 s, 7.4 s and 5.8 s; the 15.5 s was the first call after the server started.
    What the run showed: (1) the request shape is accepted by the API (strict tools, `output_config` with `effort` and `format`, no `thinking`); (2) the usage lines were not printed at first because nothing configured logging, fixed in 56806e4; (3) the system prompt and tools (about 3,480 tokens) are written to the cache again for every question, because the only cache breakpoint is after the question. A breakpoint on the system prompt would let later questions read them instead; not done, the saving is about $0.0004 a question; (4) for (b) the model reports the altitude at the start of the flagged event window (833 ft, still descending), not the lowest point before the climb. The cited record shows 833 ft, so the claim is checkable; whether "start" should mean the lowest point is a wording question for the demo.
  - Needs `ANTHROPIC_API_KEY`, set by Zahran in his own shell. Do not write it to any file and do not ask for it in chat.
  - Start the API (`uvicorn serve:app --port 8000` or `mock_api.app:app`). Ask the three demo questions through `POST /api/ask`: (a) "Any emergency squawk 7700?" (b) "Which aircraft went around at WIII, and at what altitude did the go-around start?" (c) "How long did LNI456 hold, and at what altitude?"
  - Record the results in this task (not under `docs/`, which is outside the allowed folders), for each question: the wall-clock time, `status`, the citations, the model id, the four token counts from the `flightmind.agent` log, and the cost in dollars. Read the current Haiku price from the Claude API documentation and write it with the date.
  - Check that every cited id exists in the mock API (`GET /api/raw/{raw_ref}` or `GET /api/events/{id}`) and that each answer took under 30 seconds. If a question fails, fix the cause in the prompt or tools, not by loosening the evidence rule.
  - Done when the three rows are written here, all `ok`, all under 30 seconds.
  - _Requirements: 17.1, 17.2, 17.3, 17.6, 13.1_

- [x] 23. Repeat the proof on the public site
  - **Result (2026-11-26):** Done by hand outside Kiro. Zahran added `ANTHROPIC_API_KEY` to the Vercel project `flightmind` himself (Production only, stored as a sensitive variable; nobody else saw the value). A production deployment of `main` at 20e1789 was built on Vercel from Git after a preview of the same commit had been checked, and `infra/smoke.py` passed 6 of 6 against https://flightmind.vercel.app.

    | Question on the public site | Time | Status | Tool calls | Citations |
    | --- | --- | --- | --- | --- |
    | (a) squawk 7700 | 6.9 s | ok | search_events | event squawk_7700 SIA9 |
    | (b) go-around at WIII | 7.1 s | ok | search_events, get_track x2 | events go_around GIA123 and CTV88, rec01:107, rec01:141 |
    | (c) LNI456 hold | 3.9 s | ok | search_events, query_tracks | event holding LNI456, rec01:3 |
    | "What is the weather in Paris today?" | 1.8 s | not_enough_evidence | none | none |

    Checks: the key string and the variable name are not in the web bundle (`/assets/index-*.js`) or in `/api/meta` and `/api/events`. Guard: the sixth question within a minute from one address got HTTP 429, and so did the next five; a 501-character question got HTTP 422. Token counts for these runs are in the Vercel runtime logs (kept one hour on the Hobby plan) and were not copied here; the local run in task 22 has them. Not confirmed here: that the Claude Console has a spend limit and auto-reload off. Only Zahran can see that; he was asked to check it before adding the key.
  - Zahran sets `ANTHROPIC_API_KEY` as a server-side environment variable on the Vercel project (not `NEXT_PUBLIC_` or any variable the web bundle reads). Redeploy, then ask the same three questions on https://flightmind.vercel.app and record time, status and citations here. Check that the key is not in the web bundle and that a sixth question in a minute gets 429.
  - Confirm in the Claude Console that a spend limit is set and auto-reload is off. Write the result here without the key or the limit's account details.
  - Done when the three rows are written here and the guard check is noted.
  - _Requirements: 17.4, 17.6, 12.1, 12.3, 12.5_

- [ ] 24. Compare `claude-haiku-5-5` with `claude-opus-5-5` before the video
  - With Zahran's key, run questions (b) and (c) on both models (`FLIGHTMIND_LLM_MODEL`), three runs each. Record correctness, citations, time and cost per answer.
  - Switch the default or the Vercel variable only if Opus is clearly better and the measured cost fits the $100 credit (tech.md). Write the decision and the numbers here. Do not edit `tech.md` (Role 1 owns it); if the decision changes it, open an issue for Role 1.
  - Done when the table and the decision are written here.
  - _Requirements: 17.5, 13.1_

- [ ] 25. Hand-offs and log
  - Open an issue for Role 1 asking for a `GET /api/tracks` list endpoint in `contracts/openapi.yaml`, so `query_tracks` can find aircraft without events. Add one line for the open items about the UI (500-character limit with the event prefix, how the UI shows HTTP 429).
  - Add the SCRUM-36 lines to `KIRO.md` (what Kiro did, what was fixed by hand), if that file is editable by the task's owner at that time; otherwise hand the lines to Role 1. Commits use the `Kiro:` trailer and stage files by name.
  - Done when the issue link is written here.
  - _Requirements: 8.6, 17.1_

### After review (PR #22)

Fixes applied after review, with their tests; nothing above was unticked.

- `query_tracks` gives `min_alt_raw_ref` and `max_alt_raw_ref` (also in the evidence raw_refs), so altitude claims can cite a record that shows the value.
- The 25 s deadline also covers the tool batch (`asyncio.wait_for` with the time left; reason `deadline`).
- `query_tracks` fetches at most 20 aircraft with at most 5 requests in flight; `truncated` and `candidates_total` report a cut.
- `_run_one` catches `Exception`, logs the class name and returns an `is_error` result with a fixed message; no tool failure is an HTTP 500.
- `client_key` prefers `x-vercel-forwarded-for`, then `x-forwarded-for`, then the host.
- The system prompt and the `search_events` description name all five event types; a test checks them against `contracts/openapi.yaml`.
- `mcp_server/client.py` is kept for the SCRUM-34 tests and says so in its docstring.
