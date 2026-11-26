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


## Deploy (SCRUM-38)

Phase 1: one container on Railway serves the built web UI and the **mock API**
(synthetic data, no database) on one origin. Paths that start with `/api/` go to the API;
every other path is the static web build. **The public demo uses sample data.**

Public URL: _to be filled in task 9_ (with the date the smoke check passed).

There is no `railway.json` or `railway.toml`: Railway's Config as Code stops being read on
2026-12-01. Railway builds the root `Dockerfile` as it finds it, so the settings below live in
Railway, not in the repo.

### Steps

Deploy from a clean checkout of `main` (a fresh `git clone`, or a worktree with no local
changes), because `railway up` uploads the working directory. `.dockerignore` limits what is sent.
The exact `railway` flags below are not yet run on this machine; task 9 confirms them against the
installed CLI and corrects this list.

1. **Login:** `railway login`.
2. **Create or link the project:** `railway init` for a new project, or `railway link` for an existing one.
3. **Deploy:** `railway up` from the repo root.
4. **Public domain:** `railway domain`, or Service, Settings, Networking, Generate Domain.
5. **Healthcheck:** Service, Settings, Deploy, Healthcheck Path = `/api/meta`. Set the restart policy to "on failure" in the same place.
6. **Smoke check:** `python infra/smoke.py https://<name>.up.railway.app` (standard library only; exit 0 means all six checks passed).
7. **Redeploy:** `railway up` again from a clean checkout of `main`, then repeat step 6.
8. **Roll back:** open the service's Deployments list in Railway and redeploy the previous deployment (the CLI equivalent is confirmed in task 9). Repeat step 6.

### Settings that live in Railway, not in the repo

| Setting | Value | Where |
| --- | --- | --- |
| Project and service | one project, one service, built from the root `Dockerfile` (auto-detected) | Railway project |
| Public domain | generated `*.up.railway.app` | Service, Settings, Networking |
| Healthcheck path | `/api/meta` | Service, Settings, Deploy |
| Restart policy | on failure | Service, Settings, Deploy |
| Variables | none in phase 1 (`PORT` is set by Railway) | Service, Variables |
| Plan | must not sleep or stop at a credit limit (account decision, Zahran) | Railway account |

Phase 2 would add `DATABASE_URL`, `COARENA_API_KEY` and `GEMINI_API_KEY` as Railway variables only,
and `FLIGHTMIND_API_APP` to switch to the real API. No secret belongs in the repo.

### Run the image locally

```bash
docker build -t flightmind-web .
docker run -d --name flightmind-web-check -p 8080:8080 -e PORT=8080 flightmind-web
python infra/smoke.py http://localhost:8080
docker rm -f flightmind-web-check
```

### Known workaround: `VITE_API_BASE=/.`

The web client builds URLs as `${VITE_API_BASE}${path}` and falls back to its in-browser fixture
when the base is empty, so it has no way to say "same origin". The Dockerfile builds with
`VITE_API_BASE=/.`: the browser turns `/./api/meta` into `/api/meta` on whichever host serves the
page. This is a workaround for a gap in `web/` (Role 1). The page cannot tell it is on the mock, so
its "Sample data" label does not show; that is why the README and Devpost text say the public demo
uses sample data. Remove the workaround when Role 1 adds a same-origin base.
