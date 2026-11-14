# infra — local stack (SCRUM-31)

One Postgres with **TimescaleDB** and **pgvector**, loaded with the schema and
the fixture seed, for every teammate's laptop.

## Run

From the repo root:

```bash
docker compose -f infra/docker-compose.yml up -d
```

First start loads, in order:

1. `infra/db/init/00_extensions.sql` — TimescaleDB + pgvector
2. `contracts/schema.sql` — tables, hypertable, trigger
3. `fixtures/seed.sql` — fixture rows (owned by Role 2, SCRUM-22)

Connect:

```
host=localhost port=5432 db=flightmind user=flightmind password=flightmind
```

## Reset (after a schema or seed change)

Init scripts run only on an empty data volume. To re-load them:

```bash
docker compose -f infra/docker-compose.yml down -v
docker compose -f infra/docker-compose.yml up -d
```

## Notes

- `docker compose down` (without `-v`) keeps the data volume.
- Dev-only password; the deployed stack (SCRUM-38) uses its own secrets.
