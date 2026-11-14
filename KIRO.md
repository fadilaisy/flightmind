# How we built FlightMind with Kiro

One line per finished spec task (written by the "log ticked task" hook), plus a short
review every Sunday. This file is the source for the Devpost Kiro write-up, the README
section and the Kiro part of the video.

Line format:
`date | role | spec/task | what Kiro did | fixed by hand (or "nothing")`

## Week of 2026-11-09

<!-- hook lines go here -->
2026-11-15 | Role 3 | SCRUM-31 local stack | Kiro wrote infra/docker-compose.yml (timescaledb-ha:pg16 with Timescale + pgvector in one image), infra/db/init/00_extensions.sql and the fixtures/seed.sql placeholder, wiring contracts/schema.sql to load on first start; verified live that both extensions load, all 5 tables build and telemetry is a hypertable | fixed the init mount by hand: first draft mounted a subfolder into /docker-entrypoint-initdb.d, which Postgres does not scan, so switched to per-file mounts with 00/01/02 numeric prefixes to force run order

### Sunday review
- Stats (`scripts/kiro-stats`):
- What Kiro sped up:
- What Kiro got wrong:
- What we changed in steering or hooks because of it:
- Credits used / left (per person):
