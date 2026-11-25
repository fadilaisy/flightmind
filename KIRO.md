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
