# FlightMind

Turn recorded ASTERIX CAT021 (ADS-B) files into a small, searchable flight history:
a 4D trajectory view, compression that never drops an event, automatic detection of
unusual events, and AI summaries where every claim links to the raw CAT021 record.

Built with [Kiro](https://kiro.dev) for Kiroween 2026 (Frankenstein category).
See [KIRO.md](KIRO.md) for how we used it.

## Repo structure

| Path | Owner | What lives there |
| --- | --- | --- |
| `.kiro/steering/`, `.kiro/hooks/`, `.kiro/agents/` | Role 1 | Shared Kiro context, hooks, reviewer agent |
| `.kiro/specs/web-ui/` | Role 1 | UI spec (generated in Kiro) |
| `.kiro/specs/{ingest,compression,detectors,storage}/` | Role 2 | Pipeline specs (generated in Kiro) |
| `.kiro/specs/{embeddings,agent-mcp,api-deploy}/` | Role 3 | Intelligence specs (generated in Kiro) |
| `contracts/` | Role 1 approves | `schema.sql`, `openapi.yaml`, generated `types.ts` |
| `services/pipeline/` | Role 2 | CAT021 decode, replay, filters, compression, detectors |
| `services/intel/` | Role 3 | Stories, embeddings, agent, MCP server, HTTP API |
| `web/` | Role 1 | 4D trajectory view, event feed, investigation panel |
| `fixtures/` | Role 2 | Small CAT021 samples + seed SQL (committed) |
| `data/` | everyone | Full recordings (gitignored) |
| `infra/` | Role 3 | Docker Compose: Postgres + Timescale + pgvector |
| `scripts/` | Role 1 | `kiro-stats` and other tooling |
| `docs/kiro/` | Role 1 | Session notes and clip log for the Kiro write-up |

## roles
FlightMind is split by where the data is. Role 2 owns everything up to a clean row in Postgres. Role 3 owns everything that turns rows into answers. Role 1 owns what the judges see. Each person only asks Kiro to write code in their own folders and specs, so nobody pays credits for the same code twice.

Role 1: PM and lead (Fadil)

Mission: the product, the design, the shared Kiro setup, and every submission deliverable.

Owns: scope decisions and the cut list, the web UI (4D trajectory view, event feed, investigation panel, compression view), design quality (our weakest score), contract approval.

Kiro: writes the steering files, creates the hooks and the data-quality-reviewer agent, owns KIRO.md and the weekly recording review.

Specs: web-ui.

Delivers: demo video, README, Kiro write-up, Devpost submission, advisor quote.

Folders: .kiro/steering, .kiro/hooks, .kiro/agents, web/, docs/.

Does not touch: services/pipeline/ or services/intel/. Requests go to the owner as a Jira issue.

Epics: SCRUM-7, SCRUM-13, SCRUM-14.

Role 2: Data pipeline (Koolkar)

Mission: get recorded CAT021 data in, decode it, shrink it without losing events, detect events, and store it.

Owns: the CAT021 recording and fixtures, the decoder, replay and the shared clock, compression, the detectors (squawk, go-around, holding), the Postgres schema and migrations.

Specs: ingest, compression, detectors, storage.

Proves it with: Hypothesis property tests (decode/encode round-trips, compression never drops an event point) and the raw vs stored size number for the README.

Works with: the advisor on detector thresholds.

Folders: services/pipeline/, fixtures/.

Does not touch: embeddings, the agent, the API or the UI.

Epics: SCRUM-8, SCRUM-9, SCRUM-10.

Role 3: Intelligence and API (Zahran)

Mission: turn stored events into cited answers, serve them through an API and an MCP server, and keep the live URL up.

Owns: the local Docker stack, the mock API (unblocks Fadil's UI), the real API including /api/raw/{raw_ref}, event stories and embeddings, vector search, the agent with citations and the "not enough evidence" rule, the FrankenDB MCP server, deployment.

Specs: embeddings, agent-mcp, api-deploy.

Proves it with: three demo questions answered with citations in under 30 seconds each.

Folders: services/intel/, infra/.

Does not touch: ingest, compression, detectors or UI code.

Epics: SCRUM-11, SCRUM-12.

Shared rules

The roles meet only at the contracts in contracts/. Changing one needs a PR reviewed by the producer and consumer and approved by Fadil.

Definition of done: the spec task is ticked in tasks.md, the tests pass, and there is a KIRO.md line saying what Kiro did and what was fixed by hand.

Every commit ends with a Kiro: trailer (spec, vibe, hook or none).

Sync for 15 minutes every Monday and Thursday: what shipped, what is blocked, credits left.



## Contracts (v1, changed 2026-11-12 for the recorded-data pivot)

- **C1 `telemetry`:** adds `sac`, `sic`, `track_number`, `raw_ref`.
- **C2 `weather_reports`:** optional; on the cut list.
- **C3 `events`:** carries `raw_refs` so every event cites its records.
- **C5 API:** `GET /api/tracks/{icao24}` returns 4D points with `raw_ref`; new
  `GET /api/raw/{raw_ref}`; citations gain kind `cat021_record`.
- **C6 clock:** one clock; replay is the only required mode.

Change a contract only by a pull request that edits `contracts/` and
`.kiro/steering/data-contracts.md` together, reviewed by producer and consumer.

## Third-party services

AI APIs that do real work in FlightMind. Keys come from environment variables and are
never committed.

| Purpose | Model | Provider | Key (env var) |
|---------|-------|----------|---------------|
| LLM (event stories, cited agent answers) | `claude-haiku-5-5` (Claude Haiku 5.5), set by `FLIGHTMIND_LLM_MODEL` | Anthropic Claude API, through the official `anthropic` Python SDK ([docs](https://platform.claude.com/docs)) | `ANTHROPIC_API_KEY` |
| Embeddings (similar-event search) | `gemini-embedding-001`, requested at `output_dimensionality=1024` | Google Gemini API ([docs](https://ai.google.dev/gemini-api/docs/embeddings)) | `GEMINI_API_KEY` |

The 1024 setting applies to the embedding model and matches `event_embeddings.embedding`
(`vector(1024)`). Embeddings are L2-normalized before storage.

## Web UI (`web/`)

React single-page app with three tabs (Events, Trajectory, Records). Types come from `contracts/types.ts`.

Libraries that do real work in the web app:

| Library | Used for |
| --- | --- |
| [MapLibre GL JS](https://maplibre.org/) | Map view. Basemap tiles are OpenStreetMap raster tiles (`tile.openstreetmap.org`); the map shows "WGS-84 · basemap © OpenStreetMap contributors". |
| [three.js](https://threejs.org/) | 3D trajectory view (WebGL, orbit controls, fat lines). |
| [uPlot](https://github.com/leeoniya/uPlot) | Altitude, ground speed and vertical-rate charts. |
| [React](https://react.dev/) 19 | UI. |
| [Vite](https://vitejs.dev/) 7 and Vitest | Dev server, build and tests. |
| [Inter](https://rsms.me/inter/) and [JetBrains Mono](https://www.jetbrains.com/lp/mono/) (via `@fontsource`) | Text and data fonts. |

Run it (Node 20 or newer):

```
cd web
npm install
npm run dev        # http://127.0.0.1:5173, local mock API (sample data from web/tests/fixtures/mini.json)
npm run build      # type-check and production build
npm test           # unit and smoke tests
```

To run against the SCRUM-33 mock API (4 events, 270 points, compression report) or any API that follows
`contracts/openapi.yaml`, set `VITE_API_BASE` to its base URL, without a trailing slash:

```
# bash
VITE_API_BASE=https://flightmind-roan.vercel.app npm run dev
# PowerShell
$env:VITE_API_BASE="https://flightmind-roan.vercel.app"; npm run dev
```

With `VITE_API_BASE` empty, the app uses the local mock and labels the numbers "sample data".
## Setup

_To be written once `infra/` exists._

## License

See [LICENSE](LICENSE).
