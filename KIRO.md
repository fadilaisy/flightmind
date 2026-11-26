# How we built FlightMind with Kiro

One line per finished spec task or Jira ticket (spec tasks are written by the "log ticked
task" hook), plus a short review every Sunday. This file is the source for the Devpost Kiro
write-up, the README section and the Kiro part of the video.

Line format:
`date | role | spec/task | what Kiro did | fixed by hand (or "nothing")`

The spec/task column takes a spec and task (`ingest/2.3`) or a Jira key plus `(chat)` or
`(spec)`, for example `SCRUM-32 (chat)`.

## Week of 2026-11-09

<!-- hook lines go here -->
2026-11-15 | Role 3 | SCRUM-31 local stack | Kiro wrote infra/docker-compose.yml (timescaledb-ha:pg16 with Timescale + pgvector in one image), infra/db/init/00_extensions.sql and the fixtures/seed.sql placeholder, wiring contracts/schema.sql to load on first start; verified live that both extensions load, all 5 tables build and telemetry is a hypertable | fixed the init mount by hand: first draft mounted a subfolder into /docker-entrypoint-initdb.d, which Postgres does not scan, so switched to per-file mounts with 00/01/02 numeric prefixes to force run order
2026-11-17 | Role 3 | SCRUM-32 (chat) model providers | Kiro compared providers, edited schema.sql, data-contracts.md and tech.md, then after review switched the retired text-embedding-004 to gemini-embedding-001, reverted to vector(1024) via output_dimensionality, and added the README third-party services table and L2-normalize note | by hand: Zahran rejected Kiro's one-sided switch to vector(768) and chose to keep vector(1024); Fadil's review caught the retired model and missing disclosure
2026-11-17 | Role 3 | SCRUM-33 (chat) mock API | Kiro wrote services/intel/mock_api (all 7 paths of openapi.yaml from synthetic data) and 12 tests that validate every response against openapi.yaml; checked by breaking the data on purpose (both bad bodies were caught) and by running the server over HTTP | nothing in the code; the /api/stream payload was a Kiro assumption, and Fadil later confirmed the UI does not use that endpoint, so it stays unused
2026-11-17 | Role 1 | SCRUM-39 (spec) web-ui spec | Wrote requirements, design and 18 tasks plus steering ui.md, then read the Figma Foundations page through the Figma MCP and added colour and type tokens to design.md | nothing
2026-11-17 | Role 1 | web-ui/1 | Scaffolded Vite + React + TypeScript in web/; npm run build passes | nothing
2026-11-17 | Role 1 | web-ui/2 | API client typed from contracts/types.ts, mock client, sample fixture, 2 passing tests, "Record not found: <raw_ref>" on 404 | nothing
2026-11-22 | Fadil | SCRUM-19 (spec) hooks and reviewer agent | Kiro: spec only; hooks and agent files hand-written in chat, not yet re-saved in the Agent Hooks panel (clip pending) | hook and agent files typed by hand from setup-prompts.md; re-save in the panel is still to do
2026-11-22 | Fadil | SCRUM-19 (chat) Kiro Crew Stop hook | We build in Kiro Crew, which does not read .kiro/hooks/, so the contract-types guard was added as a Crew Stop hook in the dashboard. Demo: the Crew agent edited contracts/openapi.yaml, the hook continued it once ("Continued by a hook"), and the agent ran the openapi-typescript generator itself | the hook script scripts/crew-hooks/contract-types-guard.py was written outside Kiro
2026-11-25 | Fadil | SCRUM-40 (spec) event feed and investigation panel | Kiro wrote the spec (6 tasks) and the web code: event feed with states, investigation panel with ask box and citation chips, raw record viewer with hex and ASCII; build and 11 tests pass | by hand: TODO, tasks 3 to 5 not yet checked in a browser against the SCRUM-33 mock API
2026-11-25 | Fadil | web-ui/3 | Tokens extended from get_variable_defs on frame 5 (58:1847), shell with Map, 3D and Records tabs in the URL (?tab=), header shows mode, sim_time and sample data label; read App bar 58:1848. Differences: no logo mark, no Load recording button or file name (frames 1 to 3 out of scope), tabs are ours not Clean/Events/Trajectory/Export; build and 14 tests pass | checked in headless Chrome at 1440 x 900 against docs/design/prototype-v2.html (docs/kiro/figma-check/app.png): tabs, ?tab= URL, event list, right column, header line; not clicked through by a person
2026-11-25 | Fadil | web-ui/3 (restyle) | Restyled the app to prototype v2 (docs/design/prototype-v2.html): app bar with logo and tabs Events, Trajectory, Records (?tab=, Trajectory default), 3-column grid, event list with type badges, state line, search and type chips, investigation panel as cards in the right column, empty boxes for map, charts, scrubber and compression card; Inter and JetBrains Mono loaded; screenshots in docs/kiro/figma-check/ | checked in headless Chrome at 1440 x 900 against the prototype; PR #13 review fixes applied (store wired, window format, ask prefix, offline fonts). Left: Events and Records tabs are empty; 3D and Profile buttons disabled; no Show raw points button; header shows replay, sim_time and Sample data instead of Recorded data, offline; right column is gray cards, the prototype uses one white column; flagged window shows ISO times; chips use EVENT_LABEL not short names; Figma tab names (Map, 3D, Records) replaced by the prototype tabs
2026-11-25 | Fadil | web-ui/4 | Store with eventId, icao24, scrubTs, rawRef and eventStates (reuses flightmind.eventStates); 5 tests; not wired into views yet | nothing
2026-11-25 | Role 3 | SCRUM-34 (spec) agent-mcp | Spec Builder wrote the spec (requirements, design, 8 tasks) and implemented tasks 1 to 4 and 6: a stdio MCP server with one tool, get_track, that calls GET /api/tracks/{icao24} and returns it unchanged; 23 new tests (35 in services/intel); also run through a real MCP client over stdio with the launch line from mcp.json: known aircraft, unknown aircraft, API down, server stayed alive each time | by hand: FastMCP cannot take a parameter named from, so the spec switched to the low-level Server and pinned mcp below 2; .kiro/settings/mcp.json was written in chat because the Spec Builder agent is blocked from that folder. A second run by Claude Code through the same SDK client over stdio passed all six calls (found, from filter, unknown aircraft, missing icao24, API stopped, API restarted). Not verified: task 7, a person using get_track from Kiro (neither run used Kiro). Kiro Crew probably does not read .kiro/settings/mcp.json (like .kiro/hooks, SCRUM-19), so there it needs a manually added server entry. Data is the synthetic mock, not a real recording
2026-11-26 | Role 3 | SCRUM-38 (spec) api-deploy | kiro-cli chat wrote the spec (requirements, design, 16 tasks in two phases) and implemented tasks 1 to 7: serve.py, an ASGI dispatcher that sends /api/ to the API app and everything else to the built web UI without changing the API app; 19 tests (54 in services/intel); a two-stage root Dockerfile (216 MB, non-root); infra/smoke.py; the deploy section in infra/README.md. Kiro built the image and ran the smoke check against the container: 6 of 6 passed. Kiro found that StaticFiles raises HTTPException when called as a bare ASGI app and handled it | by hand, outside Kiro: the prompts fixed the design decisions (Railway, one container, no railway.json because Config as Code ends 2026-12-01, VITE_API_BASE=/. as a same-origin workaround); task 8 browser check; the task 8 and 9 result lines. Task 9 (deploy) is not done: Railway refused to create the project because the account's trial has expired
2026-11-26 | Role 3 | api-deploy/17-20 | Host changed to Vercel after Railway, Render and Azure for Students each refused. kiro-cli chat added the Vercel build (root pyproject.toml, vercel.json, .vercelignore, infra/vercel_entry.py, infra/vercel_build.py), 7 tests (61 in services/intel), and rewrote the spec and infra/README.md for Vercel; it ran the build script locally and left the deploy alone | by hand, outside Kiro: the deploy with `vercel deploy --temporary`; one fix to vercel.json (exclude .pytest_cache from the bundle) after the first upload failed; the task 19 result and the README notes. Task 19 is not finished: the temporary URL works from an outside network but Vercel's firewall refuses Zahran's own network with 403, and the deployment still has to be claimed

## Trailer corrections

Commits are never rewritten. A wrong trailer is fixed here, and `scripts/kiro-stats` moves
the commit from "was" to "now" when it counts. Line format: `sha | was | now | reason`

b35126b | hook | vibe | Kiro chat session wrote it, see docs/kiro/sessions/2026-11-14-scrum-31-32-chat.md
efcab93 | none | vibe | Kiro chat session wrote it, see docs/kiro/sessions/2026-11-14-scrum-31-32-chat.md
ce2a636 | none | vibe | Kiro chat session wrote it, see docs/kiro/sessions/2026-11-14-scrum-31-32-chat.md
1b1d747 | none | vibe | Kiro chat session wrote it, see docs/kiro/sessions/2026-11-14-scrum-31-32-chat.md
e8d5d4d | none | vibe | Kiro chat session wrote it, see docs/kiro/sessions/2026-11-14-scrum-31-32-chat.md
2766b21 | spec scrum-19/1-4 | none | hook and agent files typed by hand from setup-prompts.md, not generated from the spec; see the SCRUM-19 line above

### Sunday review 2026-11-22 (SCRUM-43)
- Stats (`scripts/kiro-stats`, main at 6cc62b8): 2 specs (web-ui, scrum-19), 7 spec tasks done and 18 open, 4 IDE hooks plus 1 Kiro Crew Stop hook (lives in the Crew dashboard, script in `scripts/crew-hooks/`), 6 steering files, 1 custom agent, 7 KIRO.md entries before this review. 37 commits: `Kiro: spec` 6, `vibe` 15, `hook` 0, `none` 5, after 5 trailer corrections. By person: Fadil and Zahran have commits; Koolkar has none yet.
- What Kiro sped up:
  - SCRUM-33: a mock API for all 7 paths of `openapi.yaml` with 12 tests that validate every response against the contract, so the UI could start before the pipeline exists.
  - SCRUM-39: the web-ui spec (requirements, design, 18 tasks) plus colour and type tokens read from Figma through the Figma MCP.
  - SCRUM-31: the local Timescale + pgvector stack in one session, checked live.
- What Kiro got wrong:
  - SCRUM-31: mounted a subfolder into `/docker-entrypoint-initdb.d`, which Postgres does not scan.
  - SCRUM-32: switched the contract to `vector(768)` on its own and picked the retired `text-embedding-004`; caught in review.
  - SCRUM-33: guessed the `/api/stream` payload; the UI does not use it.
  - SCRUM-19: we wrote hooks in Kiro IDE format, but we build in Kiro Crew, which ignores `.kiro/hooks/`.
- What we changed in steering or hooks because of it:
  - Added the Crew Stop hook that makes the agent regenerate `contracts/types.ts` after it edits `openapi.yaml` (blocks once, then lets the turn end). Demoed on 2026-11-22.
  - Pinned `openapi-typescript@7` so every machine writes the same `types.ts`; the pipeline test hook treats "no tests collected" as a pass.
  - Added the "Trailer corrections" section, which `scripts/kiro-stats` applies, and allowed Jira keys with `(chat)` or `(spec)` in the spec/task column.
- Next week: the pipeline (SCRUM-20, 22, 23, 24) has no commits yet and blocks detection, compression and real citations. Use `Kiro: hook` when a hook does the work, since that count is still 0.
- Credits used / left (per person): Fadil TODO, Koolkar TODO, Zahran TODO.
