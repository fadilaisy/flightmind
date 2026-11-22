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
2026-11-17 | Role 3 | SCRUM-33 (chat) mock API | Kiro wrote services/intel/mock_api (all 7 paths of openapi.yaml from synthetic data) and 12 tests that validate every response against openapi.yaml; checked by breaking the data on purpose (both bad bodies were caught) and by running the server over HTTP | nothing
2026-11-17 | Role 1 | SCRUM-39 (spec) web-ui spec | Wrote requirements, design and 18 tasks plus steering ui.md, then read the Figma Foundations page through the Figma MCP and added colour and type tokens to design.md | nothing
2026-11-17 | Role 1 | web-ui/1 | Scaffolded Vite + React + TypeScript in web/; npm run build passes | nothing
2026-11-17 | Role 1 | web-ui/2 | API client typed from contracts/types.ts, mock client, sample fixture, 2 passing tests, "Record not found: <raw_ref>" on 404 | nothing
2026-11-22 | Fadil | SCRUM-19 (spec) hooks and reviewer agent | Kiro: spec only; hooks and agent files hand-written in chat, not yet re-saved in the Agent Hooks panel (clip pending) | hook and agent files typed by hand from setup-prompts.md; re-save in the panel is still to do

## Trailer corrections

Commits are never rewritten. A wrong trailer is fixed here, and `scripts/kiro-stats` moves
the commit from "was" to "now" when it counts. Line format: `sha | was | now | reason`

b35126b | hook | vibe | Kiro chat session wrote it, see docs/kiro/sessions/2026-11-14-scrum-31-32-chat.md
efcab93 | none | vibe | Kiro chat session wrote it, see docs/kiro/sessions/2026-11-14-scrum-31-32-chat.md
ce2a636 | none | vibe | Kiro chat session wrote it, see docs/kiro/sessions/2026-11-14-scrum-31-32-chat.md
1b1d747 | none | vibe | Kiro chat session wrote it, see docs/kiro/sessions/2026-11-14-scrum-31-32-chat.md
e8d5d4d | none | vibe | Kiro chat session wrote it, see docs/kiro/sessions/2026-11-14-scrum-31-32-chat.md
2766b21 | spec scrum-19/1-4 | none | hook and agent files typed by hand from setup-prompts.md, not generated from the spec; see the SCRUM-19 line above

### Sunday review
- Stats (`scripts/kiro-stats`):
- What Kiro sped up:
- What Kiro got wrong:
- What we changed in steering or hooks because of it:
- Credits used / left (per person):
