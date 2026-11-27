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

Recording upload (SCRUM-62, contract 1.2.0, `mock_api/uploads.py`):

- `POST /api/recordings`, `PUT .../parts/{n}`, `POST .../complete`, `POST .../process`,
  then preview, recipe, quarantine and export. The order checks, the sha256 (same file twice
  returns the first upload) and the first-bytes check (pcap, pcapng or a CAT021 block) are
  real. The bytes are then dropped.
- Status after complete: `scanning` for 1.5 s, then `scanned` with one CAT021 stream (`s1`)
  and one CAT062 stream (`s2`, not supported); a raw `.atx`/`.ast`/`.bin` file has one
  stream, `raw`. After process: queued, decoding, filtering, detecting, storing, then
  `ready` about 10 s later.
- A ready upload serves the rec01 sample through `?recording=<id>`, so its raw_refs still
  start with `rec01:`. A file named `bad.pcap` fails after scanning, for the UI's failed state.
- Uploads live in memory and only work against a local mock: on Vercel each instance has its
  own memory and requests are capped at 4.5 MB.
- `/api/compression/{recording_id}` returns a `CompressionReport`. Counts and byte sizes are
  computed from the synthetic records (kept = event points plus each track's first and last
  point), `/api/tracks` still returns every point, and `max_position_error_m` is an invented
  constant. The mock measures both sizes in synthetic record bytes, while the real report
  compares the recording file size with the Postgres row size, so the real ratio will
  differ. Do not quote the mock ratio (for example in the video). A recording with no data
  (`raw_bytes` 0) returns 404 with `Recording '<id>' has no data yet.`, the same status as an
  unknown id, so the UI needs only one "no report" state.

## MCP server (SCRUM-34)

`mcp_server/` is a stdio MCP server with four tools: `query_tracks`, `search_events`,
`get_track` and `get_raw` (the same tools the cited agent uses, see "Cited agent (SCRUM-36)").
`get_track(icao24, from?, to?, max_points?)` calls
`GET /api/tracks/{icao24}` and, without `max_points`, returns the body unchanged, so every point
keeps its `raw_ref`. With `max_points` (2 to 200) it thins the track and keeps the first, last
and event points. `search_events(type?, airport?, since?)` lists events,
`query_tracks(callsign?, icao24?, from?, to?)` summarises aircraft that have at least one event
(at most 20 per call; the result then has `truncated: true` and `candidates_total`, so narrow by
callsign or icao24). Each summary has `min_alt_raw_ref` and `max_alt_raw_ref`, the first record
where the lowest and highest altitude occur, so a claim about an altitude extreme can cite the
record that shows it,
and `get_raw(raw_ref)` returns one raw record. Descriptions and schemas live in
`agent/tools.py`. The server is a thin HTTP client: it never reads the database, so the mock API
can be replaced by the real API with no change here.

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

Checked in Kiro on 2026-11-25 (task 7 of the spec, clip in `docs/kiro/scrum-34/`):

- The Kiro IDE skips the workspace `.kiro/settings/mcp.json` while the folder is in Restricted
  Mode. Click "Restricted Mode" in the status bar, choose Trust, then run Developer: Reload
  Window. `flightmind` then shows as Connected (1 tool) under MCP Servers.
- The relative path in `args` works, so Kiro starts workspace servers in the workspace root.
- Through Kiro's chat CLI (`kiro-cli chat` from the repo root, which reads the same file):
  `8A0F21` returned 60 points with `raw_ref`, `ZZZZZZ` returned the unknown-aircraft message,
  and with the API stopped it returned the unreachable message. The server stayed up.

The calls above were driven through `kiro-cli` by Claude Code, not typed into the IDE chat
panel by a person. Task 9 of the spec redid them by hand.

Checked again on 2026-11-26 (task 9, clip `docs/kiro/scrum-34/2026-11-26_role3_mcp-get_track-ide.mp4`):

- Zahran typed the three asks into the Kiro IDE chat panel. `8A0F21` returned 60 points,
  callsign GIA123, `raw_ref` `rec01:0` to `rec01:2`. `ZZZZZZ` returned the unknown-aircraft
  message. With the API stopped it returned the unreachable message. Claude Code started and
  stopped the mock API and recorded the screen.
- Kiro Crew (0.13.1) does **not** read `.kiro/settings/mcp.json`. Customize, MCP Servers lists
  13 servers (Crew's own and the ones in the user-level `~/.kiro/settings/mcp.json`) and
  `flightmind` is not one of them (`docs/kiro/scrum-34/2026-11-26_role3_crew-mcp-servers.png`).
  To use it in Crew, add it by hand in Customize, MCP Servers, Add Custom, with an absolute
  path to `run.py`.

Notes:

- `mcp` is pinned `>=1.2,<2`. Version 2 renamed `FastMCP` to `MCPServer`, and the server
  uses the low-level `Server` so the tool can keep the contract's parameter name `from`.
- Tests: `python -m pytest -q` from `services/intel` (`tests/test_mcp_server.py`).

### Third-party libraries (for the README disclosure list)

- `mcp` (official Model Context Protocol Python SDK): serves the MCP tools over stdio.
- `httpx`: HTTP client that calls the FlightMind API.
- `anthropic` (official Claude Python SDK, `>=2.14,<3`): calls the Claude API for the cited agent.

## Cited agent (SCRUM-36)

`POST /api/ask` has two modes. **Without a key** it answers by keyword from canned text, as
before. **With `ANTHROPIC_API_KEY` set** it runs a Claude agent (`agent/`): the model calls four
read-only tools (`query_tracks`, `search_events`, `get_track`, `get_raw`) over the API, then
returns claims that each cite a record (`cat021_record`) or an event. Nothing else is read.

**How it is switched on.** Only `ANTHROPIC_API_KEY` itself turns it on, and only when it is
non-empty. `ANTHROPIC_AUTH_TOKEN` is ignored on purpose, and the key is passed to the SDK
explicitly. Set `FLIGHTMIND_ASK=canned` to force canned answers even with a key. Set the key in
your own shell, never in a file in the repo.

| Variable | Meaning |
| --- | --- |
| `ANTHROPIC_API_KEY` | Turns the agent on. Server-side only; never in the web bundle. |
| `FLIGHTMIND_LLM_MODEL` | Model id. Default `claude-haiku-5-5`. |
| `FLIGHTMIND_ASK` | `canned` forces the keyword answers. |
| `FLIGHTMIND_ASK_PER_MINUTE` | Questions per client per minute. Default 5. |
| `FLIGHTMIND_ASK_PER_DAY` | Questions per process per day. Default 300. |
| `FLIGHTMIND_API_BASE` | API the MCP server calls. Default `http://localhost:8000`. |

**Evidence rule.** The server, not the model, enforces citations. A citation must name an event
id or `raw_ref` that a tool returned in this run, with the matching kind. Invalid citations are
dropped, a claim left with no citation is dropped, and when nothing is left the answer is
`not_enough_evidence`. The answer text and its citations come from the same validated claims.

**Limits.** A question is at most 500 characters (422 otherwise). At most 6 model calls and 25 s
per question, 20 s per model call, `max_tokens` 4096. The agent's `get_track` returns at most 60
points by default (up to 200 on request) and reports how many the full track has.
`query_tracks` searches at most 20 aircraft per call, with 5 track requests in flight, and only
aircraft that have at least one detected event, because the API has
no list of aircraft; an aircraft without events can be missing from its result. A Claude API
failure (bad key, rate limit, timeout, connection) gives `not_enough_evidence` and logs only the
error class.

**Guard.** The sixth question from one client in a minute gets 429, and a process stops after the
daily limit. This is request throttling, not a spend cap: on a serverless host each instance
counts on its own. The real cap is a spend limit in the Claude Console with auto-reload off.
Token usage per call and a summary per question are logged on `flightmind.agent`.

**Run it locally** (PowerShell, from `services/intel`):

```powershell
$env:ANTHROPIC_API_KEY = "<your key>"      # typed in your shell only
.\.venv\Scripts\python.exe -m uvicorn mock_api.app:app --port 8000
```

The three demo questions (in a second shell):

```powershell
$q = '{"question":"Any emergency squawk 7700?"}'
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/ask -ContentType 'application/json' -Body $q
# then:
#   Which aircraft went around at WIII, and at what altitude did the go-around start?
#   How long did LNI456 hold, and at what altitude?
```

Each answer should come back with `status` `ok` and citations that open through
`GET /api/raw/{raw_ref}` or `GET /api/events/{id}`, in under 30 seconds. The proof runs are
tasks 22 to 24 of `.kiro/specs/agent-mcp/tasks.md`.

Tests use a fake client and never call Claude: `python -m pytest -q`. The root `Dockerfile` copies
`services/intel/agent/` next to `mock_api/`; `tests/test_dockerfile.py` fails if an imported
package is not copied.


## Public entry point (SCRUM-38)

`serve.py` serves the built web UI and the API on one origin: paths that start with `/api/` go to
the API app, every other path is the static web build. It does not change the API app, so the real
API replaces the mock with no code change. `/docs`, `/redoc` and `/openapi.json` are not exposed.
On Vercel the CDN serves the web build, so `infra/vercel_entry.py` builds the app with `web_dist=""`
(API only); the Docker image uses `FLIGHTMIND_WEB_DIST` instead.

| Variable | Meaning |
| --- | --- |
| `FLIGHTMIND_API_APP` | `module:attribute` of the API app. Default `mock_api.app:app`. A value that cannot be imported stops the server at start, with the value in the message. |
| `FLIGHTMIND_WEB_DIST` | Folder with the built web UI (must hold `index.html`). Unset or empty means API only, and every non-API path answers 404. |

Run it locally from `services/intel`:

```powershell
$env:FLIGHTMIND_WEB_DIST = "<path to web/dist>"   # optional
.\.venv\Scripts\python.exe -m uvicorn serve:app --port 8000
```

Runtime dependencies for the image are in `requirements-serve.txt` (`fastapi`, `uvicorn`).
Tests: `tests/test_serve.py`. Deploy steps: see "Deploy (SCRUM-38)" in `infra/README.md`.

### Third-party services (for the README disclosure list)

- Vercel (Hobby plan): hosts the public demo. The web build is served from its CDN and `serve.py` runs as one Vercel Function through `infra/vercel_entry.py`. The root `README.md` is owned by Role 1, so the line there is requested by issue.
