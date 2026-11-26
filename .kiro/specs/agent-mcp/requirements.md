# Requirements: SCRUM-34 first MCP server with get_track

Part 2 (SCRUM-36, cited agent and three more tools) starts at "Part 2: SCRUM-36 cited agent" below; requirements 1 to 6 are unchanged.


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


---

# Part 2: SCRUM-36 cited agent

Source: SCRUM-36, "Agent with cited answers and not enough evidence": "Tools: query_tracks, search_events, get_track, get_raw. Every claim cites a cat021_record or event; otherwise status not_enough_evidence. Same tools exposed through the MCP server. Proof: three demo questions answered with citations in under 30 seconds each." Owner: Role 3 (Zahran). Folders: `services/intel/agent/` (new), `services/intel/` (including a small hook in `mock_api/app.py` for `/api/ask`, and `mcp_server/`), the dependency list in the root `pyproject.toml`, and this spec folder. Nothing under `web/`, `contracts/` or `services/pipeline/`.

## Introduction (Part 2)

Part 1 gave Kiro chat one tool, `get_track`. Part 2 adds an agent behind `POST /api/ask`. The agent calls four tools (`query_tracks`, `search_events`, `get_track`, `get_raw`) against the HTTP API, and the same four tools are exposed through the MCP server. The agent is built on the Claude API (tech.md, "Third-party model APIs").

The contract does not change. The response is exactly `AskResponse` in `contracts/openapi.yaml`: `answer_md`, `citations` of `{kind, id, label}`, optional `tool_calls`, and `status` `ok` or `not_enough_evidence`. The web UI shows `answer_md` as plain text with line breaks and the citations as chips under it, so the bracketed labels in `answer_md` are what tie a claim to its chips.

The rule that matters most is enforced in code, not only in the prompt: a claim is shown only if it cites a record or event that a tool actually returned in this run.

## Requirements (Part 2)

### 7. One data layer for the agent and the MCP server

**User story:** As the Role 3 developer, I want one HTTP client used by both the agent and the MCP server, so that swapping the mock API for the real API (SCRUM-37) needs no code change.

Acceptance criteria:
1. `services/intel/agent/api_client.py` has an `ApiClient` with async methods for `GET /api/events` (filters `since`, `type`, `airport`), `GET /api/events/{id}`, `GET /api/tracks/{icao24}` (`from`, `to`) and `GET /api/raw/{raw_ref}`, built on `httpx.AsyncClient`.
2. `ApiClient` is constructed either with a base URL (from `FLIGHTMIND_API_BASE`, default `http://localhost:8000`, as the MCP server does today) or with an in-process ASGI app through `httpx.ASGITransport`, so the agent running inside the API process reads the same API without a network call.
3. `ApiClient` never imports `mock_api.data`, never reads `data/` or fixtures, and never touches the database.
4. Path values (`icao24`, `raw_ref`, event id) are URL-encoded as a single path segment, as in requirement 4.1.
5. Errors are readable, as in `mcp_server/client.py`: unknown id (404) names the id; API unreachable names the base URL (or, in process, says the API app did not answer); another non-200 status gives the status and the API's `detail`; a 200 body that is not JSON says so. Each request has a timeout of 10 seconds. The message never contains a credential.

### 8. Four tools with bounded output

**User story:** As the agent, I want four small tools that return compact data with their evidence ids, so that I can answer within the token and time budget.

Acceptance criteria:
1. `services/intel/agent/tools.py` has four plain async functions over an `ApiClient`: `search_events`, `get_track`, `query_tracks`, `get_raw`. Each returns JSON-serialisable data plus the evidence ids it exposed (raw_refs and event ids).
2. `search_events(type?, airport?, since?)` returns the matching events. Each event is cut down to `id`, `type`, `icao24`, `callsign`, `start_ts`, `end_ts`, `airport`, `severity`, the count of `raw_refs`, and the first and last `raw_ref`. The full `raw_refs` list is not returned.
3. `get_track(icao24, from?, to?, max_points?)` returns the track. When `max_points` is given and the track has more points, the points are thinned evenly. The first point, the last point and every point with `kept_for_event` true are always kept, up to the cap. `max_points` is at most 200; a larger value is lowered to 200. The result says how many points the full track has. Every returned point keeps its `raw_ref` and its other fields unchanged.
4. When `max_points` is not given, `get_track` returns the API body unchanged, as in requirement 1.2 and 1.3. The agent always passes `max_points`; its default is 60.
5. `query_tracks(callsign?, icao24?, from?, to?)` returns one summary per matching aircraft: `icao24`, `callsign`, number of points in the window, first and last `ts`, lowest and highest `alt_ft`, and first and last `raw_ref`. Aircraft with no points in the window are left out.
6. The contract has no endpoint that lists aircraft. The candidates for `query_tracks` are therefore the aircraft that have at least one event (found through `GET /api/events`). The tool description says so, so the model does not claim that an aircraft without events does not exist.
7. `get_raw(raw_ref)` returns the decoded record and its hex.
8. An unknown id, an unreachable API or any other API failure comes back as a tool error result (a message the model can read), not an exception that ends the run. For the MCP server the same failure is an `isError` result (requirement 3.6).
9. No tool reads system time or writes anything.

### 9. Evidence rule enforced in code

**User story:** As an analyst, I want every claim in an answer to link to the CAT021 record or event behind it, so that I can check it and never read an invented claim.

Acceptance criteria:
1. `services/intel/agent/evidence.py` collects, while the loop runs, every raw_ref and every event id that a tool result contained. Only ids that were actually in a result count.
2. A citation is valid only if its id is in that set and its kind matches: `cat021_record` for a raw_ref, `event` for an event id.
3. A claim with no valid citation is dropped. An invalid citation is dropped and logged (logger `flightmind.agent`, with the kind and id, never the question text beyond its length).
4. If the model returns `not_enough_evidence`, or no claim is left, or the model stopped for another reason (`max_tokens`, `refusal`, deadline, call limit), the response is `status: "not_enough_evidence"`, `citations: []` and one fixed `answer_md` sentence.
5. Otherwise the response is `status: "ok"`. `answer_md` has one line per kept claim: the claim text followed by its citation labels in square brackets. `citations` is the de-duplicated list in first-use order.
6. Labels: for a record, the raw_ref itself; for an event, `<type> <callsign or icao24>`.
7. `tool_calls` lists each tool call as `{tool, args, result_count}`, plus `error` when the call failed.
8. A valid response validates against `AskResponse` in `contracts/openapi.yaml`.

### 10. The agent loop and its limits

**User story:** As the Role 3 developer, I want a bounded loop on the official Claude SDK, so that one question cannot run long or cost much.

Acceptance criteria:
1. `services/intel/agent/agent.py` uses the official `anthropic` Python SDK: the Messages API with client-side tools, a manual loop, `AsyncAnthropic`. The client is passed in as an argument, so tests can pass a fake.
2. The model id is read from `FLIGHTMIND_LLM_MODEL`, default `claude-haiku-5-5`. Effort is `medium`, set through `output_config`.
3. Adaptive thinking is on by default on this model, so the request does not send `thinking`, `temperature`, `top_p`, `top_k` or `budget_tokens`.
4. The four tools are declared with `strict: true` and `additionalProperties: false`.
5. The final answer is structured output (`output_config.format`, a JSON schema): `status` (`ok` or `not_enough_evidence`) and `claims`, a list of `{text, citations: [{kind, id}]}` with kind `cat021_record` or `event`.
6. Limits: at most 6 model calls per question; 25 seconds for the whole question; 20 seconds timeout per model call (never longer than the time left); `max_tokens` 4096; question length at most 500 characters. A longer question is refused with HTTP 422 and a short detail, before any model call.
7. The results of all tool calls of one model turn go back in one user message.
8. The system prompt and the tool list are byte-stable (no timestamps, no per-request text) so prompt caching can work. Top-level `cache_control` of type `ephemeral` is set.
9. The system prompt tells the model: use only tool results, cite every claim with the ids from the results, say `not_enough_evidence` when the data does not answer, and state the `query_tracks` limit (requirement 8.6). Requirement 9 does not depend on the model obeying it.

### 11. Wiring into `/api/ask`

**User story:** As a visitor to the public demo, I want `/api/ask` to give cited answers, and as a teammate I want everything to work without a key.

Acceptance criteria:
1. `services/intel/agent/endpoint.py` has `async def answer_question(question, api_app)` that builds an `ApiClient` on the in-process `api_app` and runs the agent.
2. The agent is used only when the environment variable `ANTHROPIC_API_KEY` is set and non-empty, and `FLIGHTMIND_ASK` is not `canned`. The code checks that variable itself. It never relies on any other credential the SDK could find, and never reads `ANTHROPIC_AUTH_TOKEN`.
3. Otherwise `/api/ask` keeps today's canned keyword answers, so the public demo and the tests work without a key.
4. In `mock_api/app.py` only the `ask` function changes: it calls the agent when enabled and the existing canned code otherwise. The API is built from the same app object, so the real API (SCRUM-37) can make the same call.
5. A Claude API error (authentication, rate limit, server error, timeout, connection) does not crash the request. The error is logged. The answer is `not_enough_evidence` with a `tool_calls` entry `{tool: "claude_api", error: "<error class name>"}`. The key never appears in the body or the logs.
6. The answer for a failed or bounded run uses the same fixed sentence as requirement 9.4.

### 12. Public demo guard

**User story:** As the project owner, I want visitors to be unable to drain the fixed API credit, so that the demo stays up until judging.

Acceptance criteria:
1. `services/intel/agent/guard.py` limits questions per client (default 5 per minute) and per process per day (default 300). The settings are `FLIGHTMIND_ASK_PER_MINUTE` and `FLIGHTMIND_ASK_PER_DAY`. Both limits are in memory.
2. The client key is the first address in the `x-forwarded-for` header, otherwise the client host.
3. Over a limit the endpoint answers HTTP 429 with a short detail and makes no model call.
4. The limiter takes a clock argument so tests do not read system time. Production uses a monotonic clock. This is request throttling, not replay time, so contract C6 does not apply.
5. The limit is stated honestly in the README and design: serverless instances do not share memory, so the guard slows abuse but does not cap spend. The real cap is the spend limit in the Claude Console with auto-reload off (tech.md).
6. The guard applies only when the agent is enabled. Canned answers cost nothing and are not limited.

### 13. Cost logging

**User story:** As the project owner, I want the real cost per answer measured, so that the model choice rests on numbers (tech.md).

Acceptance criteria:
1. After every model call the agent logs, with `logging` on the logger `flightmind.agent`: input tokens, output tokens, cache-creation tokens, cache-read tokens and the model id.
2. After every question it logs one summary line: the totals of those four counts, the number of model calls, the number of tool calls and the elapsed seconds.
3. Nothing about usage goes into the HTTP response.
4. Logs never contain the API key or point data.

### 14. The same four tools through the MCP server

**User story:** As an analyst in Kiro chat, I want the same tools the agent uses, so that I can run the queries by hand.

Acceptance criteria:
1. `services/intel/mcp_server/server.py` exposes exactly four tools: `query_tracks`, `search_events`, `get_track`, `get_raw`. This replaces requirement 6.6 of Part 1 (the list is no longer `["get_track"]`).
2. Each tool calls the function in `agent/tools.py` through an `ApiClient` on `FLIGHTMIND_API_BASE`. The server still has no database driver and no import from `mock_api`.
3. `get_track` keeps the behaviour and tests of SCRUM-34 when `max_points` is not given: the body unchanged, nothing dropped. The existing 23 MCP tests keep passing; the only edit allowed in them is the expected tool list in the test of requirement 6.6.
4. Each tool has a description that says what its inputs are, that evidence ids must be cited, and (for `query_tracks`) the limit of requirement 8.6. Parameters are `from` and `to` as in requirement 1.1.
5. Failures are `isError` results with readable messages, as in requirement 3.
6. `.kiro/settings/mcp.json` is not edited in Part 2. It auto-approves only `get_track`, so Kiro asks before the three new tools run. If the team wants them auto-approved, that is a separate change to a file outside this part's folders.

### 15. Dependencies and disclosure

**User story:** As a teammate, I want the new libraries declared and disclosed, so that the deploy and the README are correct.

Acceptance criteria:
1. `anthropic` is added to `services/intel/requirements.txt`, `services/intel/requirements-serve.txt` and the `dependencies` list in the root `pyproject.toml` (Vercel).
2. `httpx` is added to `services/intel/requirements-serve.txt` and to the `dependencies` list in the root `pyproject.toml`, because `ApiClient` needs it at run time (it is already in `requirements.txt` through Part 1).
3. The installed `anthropic` version is recorded in `tasks.md`. Only the dependency list of `pyproject.toml` changes.
4. The SDK is disclosed in `services/intel/README.md`. The root `README.md` already names the Claude API and is not edited.

### 16. Tests

**User story:** As the Role 3 developer, I want tests that never call the Claude API, so that CI is free and repeatable.

Acceptance criteria:
1. Tests live in `services/intel/tests/test_agent*.py` and run with `pytest` from `services/intel`. They never call the Claude API and need no key. A fake client object with scripted responses stands in for `AsyncAnthropic`.
2. Loop: tools run and all results of one turn go back in one user message.
3. Evidence: a claim citing a raw_ref no tool returned is dropped; all claims dropped gives `not_enough_evidence`; event citations get the `<type> <callsign>` label; a valid run validates against `AskResponse` in `contracts/openapi.yaml`.
4. Limits: the 6-call limit, the deadline, `max_tokens` and `refusal` each give `not_enough_evidence`; a question over 500 characters is refused.
5. Errors: a Claude API error gives `not_enough_evidence` with an error entry, and the key is not in the body or the logs.
6. Wiring: with no `ANTHROPIC_API_KEY` the canned answers are served and the fake is never called; `ANTHROPIC_AUTH_TOKEN` alone does not enable the agent; `FLIGHTMIND_ASK=canned` disables it.
7. Guard: per minute, per day and the 429, with an injected clock.
8. Tools: each of the four against the mock API through the ASGI transport, including thinning that keeps the first, last and event points.
9. MCP: the server lists exactly the four tools.
10. Existing tests keep passing. Tests do not edit anything under `contracts/`.

### 17. Proof: three demo questions

**User story:** As Role 1, I want three questions answered with citations in under 30 seconds each, so that the demo video shows the agent working.

Acceptance criteria:
1. The three demo questions are:
   - (a) "Any emergency squawk 7700?"
   - (b) "Which aircraft went around at WIII, and at what altitude did the go-around start?"
   - (c) "How long did LNI456 hold, and at what altitude?"
2. Against the real Claude API with the mock data, each question gets `status: ok`, every claim cites a record or event that exists in the mock API, and the answer arrives in under 30 seconds. Each time is measured and recorded.
3. The record per answer holds the model id, token usage (input, output, cache-creation, cache-read) and the cost in dollars.
4. The same three questions are repeated on https://flightmind.vercel.app with the key set as a server-side environment variable on the Vercel project.
5. Before the video, `claude-haiku-5-5` is compared with `claude-opus-5-5` on the hard questions (b) and (c). `FLIGHTMIND_LLM_MODEL` changes only if the answers are clearly better and the measured cost fits the $100 credit (tech.md).
6. `ANTHROPIC_API_KEY` is set by Zahran in his own shell. Nobody else enters the key, and it is never written to a file in the repo.

## Rules this spec follows (Part 2)

- `tech.md`: `claude-haiku-5-5` through the official `anthropic` SDK; effort `medium` for cited answers; prompts under 100K tokens; `usage` logged for every call; `/api/ask` rate-limited; `raw_ref` never dropped; no system time in services (the limiter takes an injected clock and is throttling, not replay time).
- `product.md`: every claim links to the CAT021 record(s) behind it through `raw_ref`; if the data does not support an answer, say "not enough evidence".
- `data-contracts.md`: C5 citations are `{kind, id, label}`, kind `cat021_record` (id = raw_ref) or `event` (id = event uuid).

## Not in scope (Part 2)

- Embeddings and similar-event search (SCRUM-35).
- Event stories.
- The real API (SCRUM-37).
- Any change in `web/`, `contracts/` or `services/pipeline/`.
- Streaming answers, conversation memory across questions, authentication.

## Open items (Part 2)

1. **Tracks list endpoint (for Role 1).** `query_tracks` can only see aircraft that have an event. A `GET /api/tracks` list endpoint in `contracts/openapi.yaml` would remove that limit. Role 3 opens an issue for Role 1; the contract is not changed here.
2. **Event context in the question.** The UI sends the selected event as a text prefix of `question` (`web/src/domain/askContext.ts`, about 100 characters). The 500-character limit counts that prefix. If a typed question is refused for length, the UI should show the 422 detail; that is a Role 1 matter.
3. **HTTP 429 in the UI.** The UI may not show the 429 detail well. Role 1 checks it when the guard is live.
4. **Guard strength.** The in-memory guard does not cap spend on serverless (requirement 12.5). A shared store (for example a database table) is not planned.
