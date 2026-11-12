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

## Contracts (v1, changed 2026-11-12 for the recorded-data pivot)

- **C1 `telemetry`:** adds `sac`, `sic`, `track_number`, `raw_ref`.
- **C2 `weather_reports`:** optional; on the cut list.
- **C3 `events`:** carries `raw_refs` so every event cites its records.
- **C5 API:** `GET /api/tracks/{icao24}` returns 4D points with `raw_ref`; new
  `GET /api/raw/{raw_ref}`; citations gain kind `cat021_record`.
- **C6 clock:** one clock; replay is the only required mode.

Change a contract only by a pull request that edits `contracts/` and
`.kiro/steering/data-contracts.md` together, reviewed by producer and consumer.

## Setup

_To be written once `infra/` exists._

## License

See [LICENSE](LICENSE).
